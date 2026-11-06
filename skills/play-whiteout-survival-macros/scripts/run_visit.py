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
    p.add_argument('--backend', choices=['legacy-cua', 'current-turn'], default='current-turn')
    p.add_argument('--bridge-root', type=Path)
    p.add_argument('--lease-file', type=Path)
    a = p.parse_args()
    if a.execute and a.backend == 'current-turn' and (not a.bridge_root or not a.lease_file):
        p.error('current-turn requires --bridge-root and --lease-file')
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
    if a.backend == 'current-turn' and version < (0, 4, 18):
        raise ValueError('Current-turn backend requires executor0.4.18 or newer')
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
    lease_owner = None
    transport = None
    transport_sources = {}
    try:
        if a.backend == 'current-turn':
            lease_owner = 'current-turn-' + uuid.uuid4().hex
            lease = json.loads(a.lease_file.read_text())
            lease.update(owner=lease_owner, phase='macro', deadline_unix=time.time()+7200, backend='official-current-turn')
            a.lease_file.write_text(json.dumps(lease, indent=2)+'\n')
            transport = importlib.import_module('current_turn_backend')
            config['current_turn_bridge'] = str(a.bridge_root.resolve())
            import hashlib
            for name in ['current_turn_backend.py', 'current_turn_controller.mjs']:
                raw = (a.executor_dir/name).read_bytes()
                transport_sources[name] = hashlib.sha256(raw).hexdigest()
                (folder/name).write_bytes(raw)
            backend = transport.CurrentTurnBackend(config)
            for task, flow in selected:
                (folder / (task+'-action-source.json')).write_text(json.dumps(flow, ensure_ascii=False, indent=2)+'\n')
            (folder / 'runner-source.py').write_bytes(Path(__file__).read_bytes())
            print(json.dumps({'bridge': str(a.bridge_root.resolve()), 'run':str(folder), 'waiting_for':'official-current-turn-controller'}), flush=True)
        else:
            backend = macro.CuaMcp(config)
        backend.start()
        summary = batch.run_batch(config, selected, backend)
    except (Exception, KeyboardInterrupt) as exc:
        summary['startup_or_batch_error'] = str(exc)
    finally:
        if backend is not None:
            try:
                backend.close()
            except Exception as exc:
                summary['backend_close_error'] = str(exc)
        summary.setdefault('versions', frozen_versions)
        summary['package'] = identity
        summary['device_backend'] = a.backend
        if a.backend == 'current-turn':
            import hashlib
            summary['transport_version'] = transport.BRIDGE_VERSION if transport else None
            summary['transport_sources'] = transport_sources
            summary['locked_execution_accepted'] = False
            if lease_owner is not None:
                lease = json.loads(a.lease_file.read_text())
                if lease.get('owner') == lease_owner:
                    lease.update(owner=None, phase='released', released_unix=time.time())
                    a.lease_file.write_text(json.dumps(lease, indent=2)+'\n')
        summary['viewport_calibration'] = config.get('viewport_calibration')
        summary['started_unix'] = started
        summary['ended_unix'] = time.time()
        summary['elapsed_seconds'] = summary['ended_unix'] - started
        audit = check.check(list(folder.glob('*/result.json')))
        if summary.get('startup_or_batch_error'):
            audit['status'] = 'needs_review'
            audit['issues'].append({'type': 'startup_failure', 'reason': summary['startup_or_batch_error']})
        summary['audit'] = audit
        summary['status'] = 'passed' if not summary.get('backend_close_error') and len(summary['tasks']) == len(selected) and all(t['status'] == 'passed' for t in summary['tasks']) else 'completed_with_deviations'
        (folder / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'summary': str(folder / 'summary.json'), 'status': summary['status']}, ensure_ascii=False))
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
