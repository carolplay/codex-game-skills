#!/usr/bin/env python3
"""Read and validate pinned WOS packages; importing this module never performs input."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def load_actions(root=ROOT):
    root = Path(root).resolve()
    catalog = read(root / 'catalog.json')
    flows = {}
    declared = set()
    for task, item in catalog['actions'].items():
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root / 'actions'):
            raise ValueError(f'{task}: action path outside package')
        flow = read(path)
        for key in ('action_id', 'action_version'):
            if flow.get(key) != item[key]:
                raise ValueError(f'{task}: {key} differs from catalog')
        if digest(flow) != item['sha256']:
            raise ValueError(f'{task}: action hash differs from catalog')
        exit_conditions = [digest(step['before']) for step in flow.get('task_contract', {}).get('exits', [])]
        if len(exit_conditions) != len(set(exit_conditions)):
            raise ValueError(f'{task}: duplicate exit conditions would make recovery ambiguous')
        flows[task] = flow
        declared.add(path)
    if declared != set((root / 'actions').glob('*.json')):
        raise ValueError('Action files and catalog differ; register every action')
    return catalog, flows


def load_manifest(manifest, profile, root=ROOT):
    catalog, flows = load_actions(root)
    macro = read(Path(manifest))
    if macro['package_version'] != catalog['package_version']:
        raise ValueError('Manifest package version differs from catalog')
    selected = macro['profiles'][profile]
    tasks = []
    for pin in selected['actions']:
        task = pin['task']
        for key in ('action_id', 'action_version', 'sha256'):
            if pin[key] != catalog['actions'][task][key]:
                raise ValueError(f'{task}: manifest pin differs from catalog')
        tasks.append(task)
    if len(tasks) != len(set(tasks)):
        raise ValueError('Duplicate action in manifest')
    exclusions = selected['excluded']
    expected = {t for t, item in catalog['actions'].items() if not item['utility']}
    if set(tasks) & set(exclusions) or set(tasks) | set(exclusions) != expected:
        raise ValueError('Every business action must be selected or explicitly excluded')
    if any(not isinstance(reason, str) or not reason.strip() for reason in exclusions.values()):
        raise ValueError('Exclusions require a reason')
    if 'daily' in tasks and tasks[-1] != 'daily':
        raise ValueError('daily must follow the actions that can earn task progress')
    identity = {'package_version': catalog['package_version'],
                'macro_id': macro['macro_id'], 'macro_version': macro['macro_version'],
                'manifest_sha256': digest(macro), 'profile': profile,
                'catalog_sha256': digest(catalog)}
    return [(task, flows[task]) for task in tasks], identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    catalog, flows = load_actions(args.root)
    counts = {}
    for path in sorted((args.root / 'macros').glob('*.json')):
        macro = read(path)
        counts[path.name] = {}
        for profile in macro['profiles']:
            tasks, _ = load_manifest(path, profile, args.root)
            counts[path.name][profile] = len(tasks)
    print(json.dumps({'package_version': catalog['package_version'],
                      'action_count': len(flows), 'manifests': counts}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
