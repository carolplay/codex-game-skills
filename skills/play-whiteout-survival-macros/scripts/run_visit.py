#!/usr/bin/env python3
"""One local invocation of a pinned manifest. Coordination is the caller's responsibility."""
import argparse
import fcntl
import importlib
import json
from pathlib import Path
import signal
import sys
import time
import uuid
import macro_package


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--executor-dir', required=True, type=Path)
    p.add_argument('--config', required=True, type=Path)
    p.add_argument('--log-root', required=True, type=Path)
    p.add_argument('--lock-file', required=True, type=Path)
    p.add_argument('--guard-script', required=True, type=Path)
    choice = p.add_mutually_exclusive_group(required=True)
    choice.add_argument('--manifest', type=Path)
    choice.add_argument('--tasks', nargs='+')
    p.add_argument('--profile', choices=['main', 'mature-test', 'under30-test'])
    p.add_argument('--execute', action='store_true', help='Omit for validation only; performs no input')
    a = p.parse_args()
    catalog, flows = macro_package.load_actions()
    if a.manifest:
        if not a.profile:
            p.error('--manifest requires --profile')
        selected, identity = macro_package.load_manifest(a.manifest, a.profile)
    else:
        selected = [(task, flows[task]) for task in a.tasks]
        identity = {'package_version': catalog['package_version'],
                    'macro_id': 'targeted-development', 'macro_version': 'adhoc',
                    'catalog_sha256': macro_package.digest(catalog)}
    # Freeze validated in-memory flows before starting a backend.
    sys.path.insert(0, str(a.executor_dir.resolve()))
    macro = importlib.import_module('window_macro')
    batch = importlib.import_module('task_batch')
    check = importlib.import_module('check_run')
    versions = importlib.import_module('workflow_versions')
    version = tuple(map(int, versions.SUITE_VERSION.split('.')))
    if version < tuple(map(int, catalog['executor_min_version'].split('.'))):
        raise ValueError('Executor is older than package requirement')
    frozen_versions = versions.suite_identity(selected)
    if not a.execute:
        print(json.dumps({'validation': 'passed', 'package': identity,
                          'versions': frozen_versions, 'game_input': False}, ensure_ascii=False))
        return 0
    lock = a.lock_file.open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    config = json.loads(a.config.read_text())
    folder = a.log_root / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
    folder.mkdir(parents=True)
    config['log_dir'] = str(folder)
    config['guard_command'] = [sys.executable, str(a.guard_script.resolve())]
    summary = {'run_mode': 'macro_only_record_deviations', 'agent_fallback': False,
               'selected_tasks': [task for task, _ in selected], 'started_unix': time.time(),
               'tasks': [], 'runtime_model_calls': 0, 'versions': frozen_versions}
    started = summary['started_unix']
    def cancelled(signum, frame):
        raise KeyboardInterrupt('Visit cancelled')
    signal.signal(signal.SIGTERM, cancelled)
    backend = None
    try:
        backend = macro.CuaMcp(config)
        backend.start()
        summary = batch.run_batch(config, selected, backend)
    except (Exception, KeyboardInterrupt) as exc:
        summary['startup_or_batch_error'] = str(exc)
    finally:
        if backend is not None:
            backend.close()
        summary.setdefault('versions', frozen_versions)
        summary['package'] = identity
        summary['started_unix'] = started
        summary['ended_unix'] = time.time()
        summary['elapsed_seconds'] = summary['ended_unix'] - started
        audit = check.check(list(folder.glob('*/result.json')))
        if summary.get('startup_or_batch_error'):
            audit['status'] = 'needs_review'
            audit['issues'].append({'type': 'startup_failure', 'reason': summary['startup_or_batch_error']})
        summary['audit'] = audit
        summary['status'] = 'passed' if len(summary['tasks']) == len(selected) and all(t['status'] == 'passed' for t in summary['tasks']) else 'completed_with_deviations'
        (folder / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'summary': str(folder / 'summary.json'), 'status': summary['status']}, ensure_ascii=False))
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
