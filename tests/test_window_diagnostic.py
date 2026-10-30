import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('window_diag', Path(__file__).parents[1] / 'scripts/analyze_window_diagnostic.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class DiagnosticTests(unittest.TestCase):
    def sample(self):
        return dict(session={}, targetApps=[{'pid': 1}], targetWindowsAll=[{}],
                    targetWindowsOnScreen=[{'kCGWindowBounds': {'Width': 717, 'Height': 1055}, 'kCGWindowLayer': 0}],
                    activeDisplayQueryError=0,
                    displays=[{'id': 20, 'bounds': dict(x=0, y=0, w=1920, h=1080)}])

    def test_point_outside_display_is_not_permission_denial(self):
        r = m.analyze(self.sample(), [2426, 271])
        self.assertIn('failed_point_outside_current_displays', r['findings'])
        self.assertIsNone(r['input_authorized'])

    def test_missing_lock_key_is_unknown(self):
        self.assertIsNone(m.analyze(self.sample())['lock_state'])

    def test_locked_is_explicit(self):
        s = self.sample(); s['session']['CGSSessionScreenIsLocked'] = True
        self.assertIn('session_reports_locked', m.analyze(s)['findings'])

    def test_negative_monitor_origin_and_exclusive_edge(self):
        self.assertTrue(m.contains(dict(x=-2560, y=0, w=2560, h=1440), [-100, 50]))
        self.assertFalse(m.contains(dict(x=0, y=0, w=1920, h=1080), [1920, 10]))

    def test_nil_and_empty_window_queries_differ(self):
        s = self.sample(); s['targetWindowsAll'] = None
        self.assertIn('window_query_unavailable', m.analyze(s)['findings'])
        s['targetWindowsAll'] = []; s['targetWindowsOnScreen'] = []
        self.assertIn('no_target_window_in_query', m.analyze(s)['findings'])

    def test_process_alive_does_not_imply_onscreen_window(self):
        s = self.sample(); s['targetWindowsOnScreen'] = []
        self.assertIn('target_windows_exist_but_none_onscreen', m.analyze(s)['findings'])

    def test_topology_change(self):
        s = self.sample(); p = self.sample(); p['displays'][0]['id'] = 1
        self.assertIn('display_topology_changed_between_snapshots', m.analyze(s, previous=p)['findings'])


if __name__ == '__main__':
    unittest.main()
