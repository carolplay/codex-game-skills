import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'skills/play-whiteout-survival-macros'
spec = importlib.util.spec_from_file_location('macro_package', ROOT / 'scripts/macro_package.py')
pkg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pkg)

class PackageTests(unittest.TestCase):
    def test_all_published_profiles_validate(self):
        for path in (ROOT / 'macros').glob('*.json'):
            for profile in pkg.read(path)['profiles']:
                tasks, identity = pkg.load_manifest(path, profile)
                self.assertEqual('daily', tasks[-1][0])
                self.assertEqual(pkg.read(ROOT / 'catalog.json')['package_version'], identity['package_version'])

    def test_daily_profiles_use_mixed_cycle_without_repeating_components(self):
        for path in (ROOT / 'macros').glob('shift-*.json'):
            for profile in pkg.read(path)['profiles'].values():
                tasks=[a['task'] for a in profile['actions']]
                self.assertEqual(1,tasks.count('intel_cycle'))
                for component in ('intel_rescue','intel_hero','intel_beast','intel_firebeast'):
                    self.assertNotIn(component,tasks)
                    self.assertTrue(profile['excluded'][component])

    def test_generated_cycle_still_matches_current_component_content(self):
        spec=importlib.util.spec_from_file_location('cycle_builder',ROOT / 'scripts/build_intel_cycle.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        flows={k:pkg.read(ROOT / f'actions/wos-intel-{k}.json') for k in ('beast','rescue','hero','firebeast')}
        generated=builder.build(flows);published=pkg.read(ROOT / 'actions/wos-intel-cycle.json')
        for key in ('steps','task_contract','component_versions','repeat_from'):
            self.assertEqual(generated[key],published[key])

    def test_main_uses_same_current_actions_as_other_mature_roles(self):
        for path in (ROOT / 'macros').glob('*.json'):
            profiles=pkg.read(path)['profiles']
            self.assertEqual(profiles['mature-test'],profiles['main'])

    def test_upgrades_remain_available_but_outside_every_daily_profile(self):
        catalog, flows = pkg.load_actions()
        for task in ('research', 'construction'):
            self.assertIn(task, flows)
            self.assertFalse(catalog['actions'][task]['include_in_daily'])
            for path in (ROOT / 'macros').glob('shift-*.json'):
                for profile in pkg.read(path)['profiles'].values():
                    self.assertNotIn(task, [a['task'] for a in profile['actions']])
                    self.assertTrue(profile['excluded'][task])

    def test_duplicate_exit_conditions_are_rejected_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'package'; shutil.copytree(ROOT, root)
            path = root / 'actions/wos-store-free.json'; flow = pkg.read(path)
            duplicate = dict(flow['task_contract']['exits'][-1], name='duplicate-close')
            flow['task_contract']['exits'].append(duplicate)
            path.write_text(json.dumps(flow))
            catalog_path = root / 'catalog.json'; catalog = pkg.read(catalog_path)
            catalog['actions']['store_free']['sha256'] = pkg.digest(flow)
            catalog_path.write_text(json.dumps(catalog))
            with self.assertRaisesRegex(ValueError, 'duplicate exit conditions'):
                pkg.load_actions(root)

    def test_changed_action_rejected_before_backend_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'package'; shutil.copytree(ROOT, root)
            action = root / 'actions/wos-mail-rewards.json'
            data = pkg.read(action); data['steps'] = []
            action.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'hash'):
                pkg.load_manifest(root / 'macros/shift-3.json', 'main', root)

    def test_new_action_cannot_disappear_from_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'package'; shutil.copytree(ROOT, root)
            path = root / 'macros/shift-3.json'; data = pkg.read(path)
            data['profiles']['main']['excluded'].pop('vip')
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'explicitly excluded'):
                pkg.load_manifest(path, 'main', root)

    def test_empty_exclusion_and_reordered_daily_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'manifest.json'; data = pkg.read(ROOT / 'macros/shift-3.json')
            data['profiles']['main']['excluded']['vip'] = ''
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'reason'):
                pkg.load_manifest(path, 'main')
            data['profiles']['main']['excluded']['vip'] = 'pending validation'
            data['profiles']['main']['actions'].reverse(); path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'daily must follow'):
                pkg.load_manifest(path, 'main')

    def test_order_changes_manifest_identity(self):
        data = pkg.read(ROOT / 'macros/shift-3.json'); before = pkg.digest(data)
        actions = data['profiles']['main']['actions']; actions[0], actions[1] = actions[1], actions[0]
        self.assertNotEqual(before, pkg.digest(data))

class RunnerTests(unittest.TestCase):
    def test_startup_failure_keeps_pinned_identities_and_never_executes_tasks(self):
        import sys
        from unittest.mock import Mock, patch
        sys.path.insert(0, str(ROOT / 'scripts'))
        import run_visit
        executor = Mock(); executor.CuaMcp.return_value.start.side_effect = RuntimeError('locked startup fixture')
        batch = Mock(); checker = Mock(); checker.check.return_value = {'status':'passed','issues':[]}
        version_module = Mock(); version_module.SUITE_VERSION = pkg.read(ROOT / 'catalog.json')['executor_min_version']
        version_module.suite_identity.return_value = {'suite_version':'0.1.3','actions':['pinned-fixture']}
        modules = {'window_macro':executor, 'task_batch':batch, 'check_run':checker, 'workflow_versions':version_module}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); config = folder / 'config.json'; config.write_text('{}')
            args = ['run_visit.py','--executor-dir',str(folder),'--config',str(config),
                    '--manifest',str(ROOT / 'macros/shift-3.json'),'--profile','main',
                    '--log-root',str(folder / 'runs'),'--lock-file',str(folder / 'lock'),
                    '--guard-script',str(folder / 'guard.py'),'--execute']
            with patch.object(sys,'argv',args), patch.object(run_visit.importlib,'import_module',side_effect=modules.__getitem__):
                self.assertEqual(1,run_visit.main())
            report = pkg.read(next((folder / 'runs').glob('*/summary.json')))
            self.assertEqual('wos-shift-3',report['package']['macro_id'])
            self.assertEqual(pkg.read(ROOT / 'macros/shift-3.json')['macro_version'],report['package']['macro_version'])
            self.assertEqual(['pinned-fixture'],report['versions']['actions'])
            self.assertIn('locked startup fixture',report['startup_or_batch_error'])
            batch.run_batch.assert_not_called(); executor.CuaMcp.return_value.close.assert_called_once()
