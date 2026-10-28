import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).parents[1] / 'skills/play-whiteout-survival-macros/scripts/npc_rally_ledger.py'
spec = importlib.util.spec_from_file_location('npc_ledger', path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class RallyLedgerTests(unittest.TestCase):
    def event(self, kind, event_id='one', **extra):
        return dict(kind=kind, event_id=event_id, role='test-role', activity='polar_terror',
                    observed_at='2026-10-27T18:00:00-07:00', evidence='local-only/sample.json', **extra)

    def result(self, events):
        return m.summarize(events, day='2026-10-28', role='test-role')

    def test_ten_dispatches_are_not_ten_completed_rallies(self):
        r = self.result([self.event('initiated', str(i), actual_dispatch_verified=True) for i in range(10)])
        self.assertEqual(10, r['actual_starts']); self.assertEqual(0, r['confirmed_own_victories'])
        self.assertFalse(r['quota_completed'])

    def test_auto_join_and_member_victory_do_not_count(self):
        r = self.result([self.event('autojoin_enabled'), self.event('victory', 'two', victory_verified=True)])
        self.assertEqual(0, r['confirmed_own_victories'])

    def test_daily_boundary_is_utc_not_local(self):
        e = self.event('victory', own_initiator_verified=True, victory_verified=True)
        self.assertEqual(1, self.result([e])['confirmed_own_victories'])
        e['observed_at'] = '2026-10-27T16:59:59-07:00'
        self.assertEqual(0, self.result([e])['confirmed_own_victories'])

    def test_deduplicate_reports_and_settle_exact_start(self):
        s = self.event('initiated', 'start1', actual_dispatch_verified=True)
        v = self.event('victory', 'report1', own_initiator_verified=True,
                       victory_verified=True, start_event_id='start1')
        r = self.result([s, v, v]); self.assertEqual(1, r['confirmed_own_victories'])
        self.assertEqual([], r['pending_start_ids'])

    def test_other_role_and_bear_do_not_count(self):
        e = self.event('victory', own_initiator_verified=True, victory_verified=True)
        e['activity'] = 'bear_hunt'; self.assertEqual(0, self.result([e])['confirmed_own_victories'])
        e['activity'] = 'polar_terror'; e['role'] = 'other-role'
        self.assertEqual(0, self.result([e])['confirmed_own_victories'])

    def test_no_action_busy_skip_is_not_dispatch(self):
        r = self.result([self.event('initiated', actual_dispatch_verified=False)])
        self.assertEqual(0, r['actual_starts'])

    def test_missing_evidence_and_naive_dates(self):
        e = self.event('victory', own_initiator_verified=True, victory_verified=True)
        e['evidence'] = None; self.assertEqual(0, self.result([e])['confirmed_own_victories'])
        with self.assertRaises(ValueError): m.utc_day('2026-10-28T01:00:00')

    def test_current_day_human_evidence_can_count_without_replaying(self):
        e = self.event('victory', own_initiator_verified=True, victory_verified=True)
        r = self.result([e]); self.assertEqual(9, r['remaining_victories'])

    def test_ten_unique_own_victories_complete_quota(self):
        r = self.result([self.event('victory', str(i), own_initiator_verified=True,
                                   victory_verified=True) for i in range(10)])
        self.assertTrue(r['quota_completed']); self.assertEqual(0, r['remaining_victories'])

class ReportListTests(unittest.TestCase):
    def extract(self, lines, evidence='saved-ocr.json'):
        return m.events_from_report_list({'lines':[{'text':x} for x in lines]},
            own_name='Example', role='role', local_timezone='America/Vancouver', evidence=evidence)

    def test_own_initiator_only_and_repeated_screenshots_share_key(self):
        lines=['大获全胜', '［ABC］Example集结攻击4级剑齿虎获胜', '2026-10-27 21:35:50',
               '大获全胜', '[ABC]Other集结攻击8级深渊龙龟获胜', '2026-10-27 21:35:49']
        a=self.extract(lines);b=self.extract(lines,'second-ocr.json')
        self.assertEqual(1,len(a));self.assertEqual(a[0]['event_id'],b[0]['event_id'])
        self.assertEqual('2026-10-28T04:35:50+00:00',a[0]['observed_at'])
        r=m.summarize(a+b,day='2026-10-28',role='role')
        self.assertEqual(1,r['confirmed_own_victories'])

    def test_missing_date_and_similar_other_name_are_not_evidence(self):
        self.assertEqual([],self.extract(['AnotherExample集结攻击4级剑齿虎获胜','2026-10-2721:35:50']))
        self.assertEqual([],self.extract(['Example集结攻击4级剑齿虎获胜','大获全胜','2026-10-2721:35:50']))

    def test_bear_or_player_report_does_not_become_polar_terror(self):
        for target in ['猎熊陷阱', 'Other', '未知野兽']:
            self.assertEqual([], self.extract(['Example集结攻击'+target+'获胜', '2026-10-2721:35:50']))


if __name__ == '__main__': unittest.main()
