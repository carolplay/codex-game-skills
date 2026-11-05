#!/usr/bin/env python3
"""Count project storage without following aliases or counting hardlinks twice."""
import argparse
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[1]
LIMIT_BYTES = 5_000_000_000
MAINTENANCE_BYTES = 4_500_000_000


def measure(roots):
    seen = set()
    totals = {'allocated_bytes':0, 'logical_bytes':0, 'files':0}
    scopes = []
    for root in roots:
        root = Path(root).resolve()
        if not root.is_dir():
            continue
        part = {'path':str(root), 'allocated_bytes':0, 'logical_bytes':0, 'files':0}
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [n for n in dirs if not (Path(directory)/n).is_symlink()]
            for path in [Path(directory), *(Path(directory)/n for n in files)]:
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    continue
                if stat.S_ISLNK(info.st_mode) or (info.st_dev, info.st_ino) in seen:
                    continue
                seen.add((info.st_dev, info.st_ino))
                part['allocated_bytes'] += info.st_blocks * 512
                if stat.S_ISREG(info.st_mode):
                    part['logical_bytes'] += info.st_size
                    part['files'] += 1
        scopes.append(part)
        for key in totals:
            totals[key] += part[key]
    return {**totals, 'scopes':scopes, **assess(totals['allocated_bytes']),
            'accounting':'allocated blocks; symlinks excluded, hardlinks once; APFS clone sharing may be conservatively overcounted'}


def assess(allocated_bytes):
    return {'limit_bytes':LIMIT_BYTES, 'maintenance_bytes':MAINTENANCE_BYTES,
            'status':'over_limit' if allocated_bytes >= LIMIT_BYTES else
                     'cleanup_required' if allocated_bytes >= MAINTENANCE_BYTES else 'ok',
            'allow_new_batch':allocated_bytes < MAINTENANCE_BYTES}


def project_usage(root=ROOT):
    root = Path(root).resolve()
    return measure([root, root.parent/'CrossMacro'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = project_usage()
    print(json.dumps(result, indent=2))
    if args.check and not result['allow_new_batch']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
