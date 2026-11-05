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
import shutil
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


def emergency_free_space(gib, apply=False):
    """One-off explicit user override: expire recollectable images, oldest first.

    Unlike normal maintenance this may unpin curated/quoted images, and may reach
    recent images if needed. Logs, runtime templates and other folders are never
    candidates. Removed provenance is journaled before unlinking.
    """
    if gib <= 0:
        raise ValueError('Expected a positive free-space target')
    maintenance = ROOT / 'local-data/maintenance'
    maintenance.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'local-data/crossmacro/v2/visit.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return dict(status='skipped_active_executor', input_sent=False)
        free_before = shutil.disk_usage(ROOT).free
        target = free_before + int(gib * 1024**3)
        started = time.time()
        images, logs = [], {}
        for folder, dirs, files in os.walk(RUNS, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(folder) / d).is_symlink()]
            for name in files:
                p = Path(folder) / name
                if p.is_symlink():
                    continue
                st = p.stat()
                if p.suffix.lower() in IMAGE:
                    images.append((st.st_mtime_ns, str(p), st.st_size, st.st_ino))
                else:
                    logs[p] = (st.st_size, st.st_mtime_ns)
        images.sort()
        if not apply:
            return dict(status='planned', target_gib=gib, candidate_images=len(images),
                        oldest_first=True, may_expire_curated=True, may_expire_recent=True)
        index = json.loads((LIBRARY / 'index.json').read_text())
        references = collections.Counter(x['blob'] for x in index['samples'].values())
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        audit = maintenance / ('emergency-screenshot-deletions-' + stamp + '.jsonl')
        save(maintenance / 'emergency-space-recovery-plan.json', dict(
            started_unix=started, free_before=free_before, target_free_bytes=target,
            target_freed_bytes=target-free_before, audit=str(audit.relative_to(ROOT))))
        removed = blobs = logical = recent = 0
        error = None
        try:
            with audit.open('w') as journal:
                for mtime_ns, filename, size, inode in images:
                    if shutil.disk_usage(ROOT).free >= target:
                        break
                    p = Path(filename)
                    now = p.stat()
                    if (now.st_mtime_ns, now.st_size, now.st_ino) != (mtime_ns, size, inode):
                        raise RuntimeError('Image changed during cleanup: ' + filename)
                    ref = str(p.relative_to(ROOT))
                    sample = index['samples'].get(ref)
                    blob = None
                    if sample and references[sample['blob']] == 1:
                        blob = ROOT / sample['blob']
                        blob.resolve().relative_to((LIBRARY / 'blobs').resolve())
                        if blob.is_symlink():
                            raise ValueError('Symlinked material blob refused')
                    journal.write(json.dumps(dict(path=ref, bytes=size, mtime_ns=mtime_ns,
                        reason='user_authorized_oneoff_space_recovery_recollect_later',
                        removed_material_record=sample,
                        blob_to_unlink=str(blob.relative_to(ROOT)) if blob else None),
                        ensure_ascii=False) + '\n')
                    journal.flush()
                    p.unlink()
                    removed += 1
                    logical += size
                    recent += mtime_ns / 1e9 >= started - 72 * 3600
                    if sample:
                        index['samples'].pop(ref)
                        references[sample['blob']] -= 1
                        if blob and blob.exists():
                            blob.unlink()
                            blobs += 1
                    if removed % 2000 == 0:
                        print(json.dumps(dict(removed_images=removed,
                            actual_free_bytes=shutil.disk_usage(ROOT).free)), flush=True)
        except Exception as exc:
            error = str(exc)
        # Persist the remaining valid library, even after a partial stop. The
        # deletion journal preserves all removed index records and old hashes.
        index.update(updated_unix=time.time(), last_emergency_deletion_audit=str(audit.relative_to(ROOT)))
        save(LIBRARY / 'index.json', index)
        groups = collections.defaultdict(dict)
        for source, sample in index['samples'].items():
            workflow = sample.get('workflow') or {}
            action, version = workflow.get('action_id') or 'unclassified', workflow.get('action_version') or 'unknown'
            safe = re.sub(r'[^A-Za-z0-9._-]', '_', action + '--' + version)
            groups[safe][source] = sample
        catalog = ['# 宏素材目录', '', '部分旧截图按用户空间回收要求移除，缺口与原校验值见删除审计。', '',
                   '| Action / 版本 | 关键帧数 | 素材索引 |', '|---|---:|---|']
        for p in (LIBRARY / 'actions').glob('*.json'):
            data = json.loads(p.read_text())
            data['samples'] = groups.get(p.stem, {})
            save(p, data)
            if data['samples']:
                catalog.append(f'| {p.stem} | {len(data["samples"])} | [打开](actions/{p.name}) |')
        (LIBRARY / 'CATALOG.md').write_text('\n'.join(catalog) + '\n')
        resolved = LIBRARY.resolve()
        if resolved.name == 'legacy-library' and (resolved.parent.parent / 'store.json').is_file():
            from prepare_macro_material_store import write_portable_manifest
            portable = write_portable_manifest(resolved, index, resolved.parent / 'assets.jsonl')
            store_path = resolved.parent.parent / 'store.json'
            store = json.loads(store_path.read_text())
            store.update(portable)
            store.update(content_verified=False, old_report_links_preserved=False,
                         latest_emergency_audit=str(audit.relative_to(ROOT)), updated_unix=time.time())
            save(store_path, store)
        logs_unchanged = all(p.exists() and (p.stat().st_size, p.stat().st_mtime_ns) == signature
                             for p, signature in logs.items())
        if not logs_unchanged:
            error = 'Non-image log changed during cleanup'
        free_after = shutil.disk_usage(ROOT).free
        result = dict(status='completed' if free_after >= target and not error else 'partial',
            started_unix=started, finished_unix=time.time(), target_freed_bytes=target-free_before,
            free_before=free_before, free_after=free_after, actual_free_increase=free_after-free_before,
            removed_images=removed, removed_material_blobs=blobs, removed_logical_image_bytes=logical,
            removed_recent_images=recent, remaining_material_references=len(index['samples']),
            all_non_image_logs_unchanged=logs_unchanged, input_sent=False, error=error,
            audit=str(audit.relative_to(ROOT)), oneoff_override=True)
        save(maintenance / 'emergency-space-recovery-latest.json', result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--free-gib', type=float,
                        help='Explicit one-off override: free this many GiB from recollectable screenshots, oldest first')
    args = parser.parse_args()
    if args.free_gib is not None:
        print(json.dumps(emergency_free_space(args.free_gib, args.apply)))
        return
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
        # A locally separated library keeps its portable manifest current. The
        # compatibility symlink preserves all historical repo-relative evidence.
        resolved = LIBRARY.resolve()
        if resolved.name == 'legacy-library' and (resolved.parent.parent / 'store.json').is_file():
            from prepare_macro_material_store import write_portable_manifest
            portable = write_portable_manifest(resolved, index, resolved.parent / 'assets.jsonl')
            stats['portable_material_store'] = portable
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
