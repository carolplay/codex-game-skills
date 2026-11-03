#!/usr/bin/env python3
"""Archive macro evidence, then expire run images only; default is a dry run."""
import argparse
import collections
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import time

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'local-data/crossmacro/v2/runs'
LIBRARY = ROOT / 'local-data/macro-materials'
IMAGE = {'.jpg', '.jpeg', '.png'}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.new')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    os.replace(temp, path)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    started = time.time()
    cutoff = started - 72 * 3600
    maintenance = ROOT / 'local-data/maintenance'
    maintenance.mkdir(parents=True, exist_ok=True)
    # Never inspect/delete an active producer's files. JSON leases alone are insufficient.
    with (ROOT / 'local-data/crossmacro/v2/visit.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status': 'skipped_active_executor', 'input_sent': False}))
            return
        images = {}
        logs = {}
        results = []
        for folder, dirs, files in os.walk(RUNS, followlinks=False):
            dirs[:] = [x for x in dirs if not (Path(folder) / x).is_symlink()]
            for name in files:
                p = Path(folder) / name
                if p.is_symlink():
                    continue
                st = p.stat()
                if p.suffix.lower() in IMAGE:
                    images[p] = st
                else:
                    logs[p] = (st.st_size, st.st_mtime_ns)
                if name == 'result.json':
                    try:
                        data = json.loads(p.read_text())
                    except (ValueError, OSError):
                        # Unknown/incomplete results are never eligible for expiration.
                        continue
                    results.append((p, data))

        selected = collections.defaultdict(set)
        metadata = {}
        known_folders = {p.parent for p, _ in results}
        representatives = {}
        for p, data in results:
            workflow = data.get('workflow') or {}
            steps = data.get('steps') or []
            outcome = tuple((s.get('name'), bool(s.get('skipped')), bool(s.get('after_verified')))
                            for s in steps)
            key = (workflow.get('action_id'), workflow.get('action_version'),
                   data.get('status'), outcome)
            # Preserve latest representative of each actual branch for each version.
            stamp = data.get('ended_unix', p.stat().st_mtime) or p.stat().st_mtime
            if workflow and (key not in representatives or stamp > representatives[key][0]):
                representatives[key] = (stamp, p, data)
            if data.get('status') != 'passed':
                # All failures retain entry plus the failing transition and its retries.
                frames = sorted(x for x in p.parent.iterdir() if x in images and '-native' not in x.stem)
                numbered = [x for x in frames if re.match(r'^\d+-', x.name)]
                highest = max((int(x.name.split('-')[0]) for x in numbered), default=-1)
                for x in frames:
                    if not re.match(r'^\d+-', x.name) or int(x.name.split('-')[0]) >= highest - 1 or x.name.startswith('00-'):
                        selected[x].add('failure_entry_and_transition')
                        metadata[x] = {'result': str(p.relative_to(ROOT)), 'workflow': workflow,
                                       'status': data.get('status'), 'error': data.get('error')}
        for _, p, data in representatives.values():
            # Before frames + last observation per numbered step capture branch transitions;
            # native duplicates and crop caches are unnecessary to represent a stable branch.
            groups = collections.defaultdict(list)
            for x in p.parent.iterdir():
                if x not in images or '-native' in x.stem:
                    continue
                match = re.match(r'^(\d+)-(before|after.*)\.', x.name)
                if match:
                    groups[match[1]].append(x)
            for group in groups.values():
                before = [x for x in group if x.stem.endswith('before')]
                after = [x for x in group if x not in before]
                for x in before + (sorted(after)[-1:] if after else []):
                    selected[x].add('version_branch_representative')
                    metadata.setdefault(x, {'result': str(p.relative_to(ROOT)),
                                            'workflow': data.get('workflow'), 'status': data.get('status')})

        # Explicit report/fixture image references outside bulky run logs are pinned.
        # Historical deletion manifests are not curated evidence references.
        ref_pattern = re.compile(r'(?:' + re.escape(str(ROOT)) + r'/)?'
                                 r'local-data/crossmacro/v2/runs/[^\s\"\'<>\)\]]+?\.(?:jpg|jpeg|png)', re.I)
        for source_root in [ROOT / 'local-data/orchestration', ROOT / 'local-data/crossmacro/v3', ROOT / 'docs', ROOT / 'skills']:
            if not source_root.exists():
                continue
            for folder, dirs, files in os.walk(source_root, followlinks=False):
                dirs[:] = [x for x in dirs if not (Path(folder) / x).is_symlink()]
                for name in files:
                    p = Path(folder) / name
                    if p.suffix not in {'.json', '.md', '.py'} or p.is_symlink() or p.stat().st_size > 8 * 1024**2:
                        continue
                    try:
                        text = p.read_text()
                    except (UnicodeError, OSError):
                        continue
                    for ref in ref_pattern.findall(text):
                        target = Path(ref) if ref.startswith('/') else ROOT / ref
                        if target in images:
                            selected[target].add('explicit_report_or_fixture_reference')

        # Unclassified samples (manual experiments/anchors) have no reliable workflow
        # metadata. Archive their raw frames rather than guessing they are disposable.
        for p in images:
            if 'derived' not in p.relative_to(RUNS).parts and p.parent not in known_folders:
                selected[p].add('unclassified_original_sample')

        index_path = LIBRARY / 'index.json'
        index = json.loads(index_path.read_text()) if index_path.exists() else {'schema_version': 1, 'samples': {}}
        for ref in index['samples']:
            p = ROOT / ref
            if p in images:
                selected[p].add('previously_curated')
        candidates = [p for p, st in images.items() if st.st_mtime < cutoff and p not in selected]
        stats = {'status': 'planned', 'apply': args.apply, 'started_unix': started,
                 'cutoff_utc': dt.datetime.fromtimestamp(cutoff, dt.timezone.utc).isoformat(),
                 'retention_hours': 72, 'images_scanned': len(images),
                 'recent_images_preserved': sum(s.st_mtime >= cutoff for s in images.values()),
                 'selected_material_paths': len(selected), 'candidate_delete_count': len(candidates),
                 'candidate_logical_bytes': sum(images[p].st_size for p in candidates),
                 'non_image_files_preserved': len(logs), 'input_sent': False}
        if not args.apply:
            save(maintenance / 'screenshot-retention-plan.json', stats)
            print(json.dumps(stats))
            return
        # Persist and verify durable material mapping BEFORE unlinking any run image.
        for p, reasons in selected.items():
            sha = digest(p)
            blob = LIBRARY / 'blobs' / sha[:2] / (sha + p.suffix.lower())
            blob.parent.mkdir(parents=True, exist_ok=True)
            if not blob.exists():
                os.link(p, blob)
            if blob.stat().st_size != images[p].st_size or digest(blob) != sha:
                raise RuntimeError('Material verification failed: ' + str(p))
            ref = str(p.relative_to(ROOT))
            old = index['samples'].get(ref, {})
            index['samples'][ref] = {**old, **metadata.get(p, {}), 'sha256': sha,
                                      'blob': str(blob.relative_to(ROOT)),
                                      'reasons': sorted(set(old.get('reasons', [])) | reasons)}
        index.update(updated_unix=time.time(), policy='72h run images; curated immutable samples; all logs')
        save(index_path, index)
        groups = collections.defaultdict(dict)
        for source, sample in index['samples'].items():
            workflow = sample.get('workflow') or {}
            key = (workflow.get('action_id', 'unclassified'),
                   workflow.get('action_version', 'unknown'))
            groups[key][source] = sample
        catalog = ['# 宏素材目录', '', '| Action | 版本 | 关键帧数 | 素材索引 |',
                   '|---|---|---:|---|']
        for (action, version), samples in sorted(groups.items()):
            safe = re.sub(r'[^A-Za-z0-9._-]', '_', action + '--' + version)
            relative = 'actions/' + safe + '.json'
            save(LIBRARY / relative, {'action': action, 'version': version, 'samples': samples})
            catalog.append(f'| {action} | {version} | {len(samples)} | [打开]({relative}) |')
        (LIBRARY / 'CATALOG.md').write_text('\n'.join(catalog) + '\n')
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        audit = maintenance / ('screenshot-deletions-' + stamp + '.jsonl')
        removed = 0
        with audit.open('w') as out:
            for p in candidates:
                old = images[p]
                current = p.stat()
                if (current.st_ino, current.st_mtime_ns, current.st_size) != (old.st_ino, old.st_mtime_ns, old.st_size):
                    raise RuntimeError('Image changed during cleanup: ' + str(p))
                out.write(json.dumps({'path': str(p.relative_to(ROOT)), 'bytes': old.st_size,
                                      'mtime_ns': old.st_mtime_ns, 'reason': 'expired_unselected_run_image'}) + '\n')
                out.flush()
                p.unlink()
                removed += 1
        for p, signature in logs.items():
            if not p.exists() or (p.stat().st_size, p.stat().st_mtime_ns) != signature:
                raise RuntimeError('Non-image file missing/changed: ' + str(p))
        for p, st in images.items():
            if st.st_mtime >= cutoff and not p.exists():
                raise RuntimeError('Recent image missing: ' + str(p))
        stats.update(status='completed', removed_images=removed, all_logs_unchanged=True,
                     all_recent_images_preserved=True, deletion_audit=str(audit.relative_to(ROOT)),
                     finished_unix=time.time())
        save(maintenance / ('screenshot-retention-' + stamp + '.json'), stats)
        save(maintenance / 'screenshot-retention-latest.json', stats)
        print(json.dumps(stats))


if __name__ == '__main__':
    main()
