#!/usr/bin/env python3
"""Remove disposable WOS images; keep runtime templates and explicit fixtures.

Pixels are transient. Neither recency, a failed run nor a report link makes an
image reusable. This command never operates the game or removes non-image logs.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
IMAGE = {'.jpg', '.jpeg', '.png', '.webp'}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.new')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    os.replace(temp, path)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def protected_images(root):
    protected = {}
    for config in (root/'local-data/crossmacro/v2').glob('*config.json'):
        data = json.loads(config.read_text())
        for value in data.get('image_templates', {}).values():
            for name in value if isinstance(value, list) else [value]:
                path = Path(name)
                if not path.is_absolute():
                    path = root/path
                if not path.is_file():
                    raise ValueError('Missing runtime template: ' + str(path))
                protected[path.resolve()] = 'runtime_template:' + str(config.relative_to(root))
    manifest = root/'local-data/material-store/wos/reusable-images.json'
    if manifest.exists():
        for item in json.loads(manifest.read_text()).get('images', []):
            path = (root/item['path']).resolve()
            consumer = (root/item['consumer']).resolve()
            if not path.is_relative_to(root) or not consumer.is_relative_to(root):
                raise ValueError('Reusable image/consumer outside workspace')
            if not item.get('purpose') or not consumer.is_file() or not path.is_file():
                raise ValueError('Reusable image needs an existing consumer and purpose')
            if digest(path) != item['sha256']:
                raise ValueError('Reusable image checksum mismatch: ' + str(path))
            protected[path] = 'explicit_reusable_fixture:' + item['purpose']
    return protected


def scopes(root):
    local = root/'local-data'
    fixed = ['crossmacro/v2/runs', 'crossmacro/v3', 'crossmacro/runs',
             'crossmacro/daily-runs', 'orchestration/v2-shifts',
             'orchestration/bear-materials', 'material-store/wos/private']
    result = [local/name for name in fixed]
    result += list((local/'orchestration').glob('bear-hunt-*'))
    experiments = local/'experiments'
    if experiments.exists():
        result += [p for p in experiments.iterdir() if p.name.startswith(
            ('wos-', 'bear-', 'lock-probe-', 'viewport-', 'display-reconnect-',
             'update-', 'island-', 'labyrinth-', 'lighthouse-'))]
    return [p for p in result if p.is_dir() and not p.is_symlink()]


def maintain(root=ROOT, apply=False):
    root = Path(root).resolve()
    maintenance = root/'local-data/maintenance'
    maintenance.mkdir(parents=True, exist_ok=True)
    lock_path = root/'local-data/crossmacro/v2/visit.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'status':'skipped_active_executor', 'input_sent':False}
        protected = protected_images(root)  # validate all consumers before deleting
        before = shutil.disk_usage(root).free
        candidates = []
        seen = set()
        for scope in scopes(root):
            for directory, dirs, files in os.walk(scope, followlinks=False):
                dirs[:] = [n for n in dirs if not (Path(directory)/n).is_symlink()]
                for name in files:
                    path = Path(directory)/name
                    if path.is_symlink() or path.suffix.lower() not in IMAGE:
                        continue
                    resolved = path.resolve()
                    if resolved in seen or resolved in protected:
                        continue
                    seen.add(resolved)
                    candidates.append((path, path.stat()))
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        journal = maintenance/('disposable-images-' + stamp + '.jsonl')
        removed = 0
        if apply:
            with journal.open('w') as out:
                for path, stat in candidates:
                    current = path.stat()
                    if (current.st_ino,current.st_size,current.st_mtime_ns) != (stat.st_ino,stat.st_size,stat.st_mtime_ns):
                        raise ValueError('Image changed during cleanup: ' + str(path))
                    out.write(json.dumps({'path':str(path.relative_to(root)),
                        'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,
                        'reason':'not_a_runtime_template_or_explicit_reusable_fixture'}) + '\n')
                    out.flush()
                    path.unlink()
                    removed += 1
            library = root/'local-data/material-store/wos/private/legacy-library'
            index = library/'index.json'
            if index.exists():
                old = json.loads(index.read_text())
                surviving = {}
                for key, item in old.get('samples', {}).items():
                    blob = root/item['blob']
                    if blob.is_file():
                        surviving[key] = item
                index.rename(library/('index-retired-' + stamp + '.json'))
                save(index, {'policy_version':'2.0.0','samples':surviving,
                             'source':'explicit_runtime_and_fixture_consumers_only'})
            # Preserve old provenance as a log; stop advertising removed blobs.
            portable = root/'local-data/material-store/wos/private/assets.jsonl'
            if portable.exists():
                portable.rename(portable.with_name('assets-retired-' + stamp + '.jsonl'))
            portable.parent.mkdir(parents=True, exist_ok=True)
            portable.write_text('')
        result = {'policy_version':'2.0.0','status':'completed' if apply else 'dry_run',
            'candidate_images':len(candidates),'candidate_logical_bytes':sum(s.st_size for _,s in candidates),
            'removed_images':removed,'protected_images':len(protected),
            'protected_consumers':{str(p):why for p,why in protected.items()},
            'non_image_files_deleted':0,'recent_image_exemption':False,
            'non_image_logs_preserved':True,'input_sent':False,
            'free_before':before,'free_after':shutil.disk_usage(root).free,
            'journal':str(journal.relative_to(root)) if apply else None,
            'ended_unix':time.time()}
        if apply:
            save(maintenance/'screenshot-retention-latest.json',result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args = parser.parse_args()
    print(json.dumps(maintain(apply=args.apply),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
