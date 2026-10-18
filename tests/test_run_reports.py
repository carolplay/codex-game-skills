import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('run_reports',Path(__file__).parents[1]/'scripts/run_reports.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class RunReportTests(unittest.TestCase):
    def test_final_replaces_checkpoint_and_device_is_not_another_run(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            for name,data in [('r.checkpoint.json',{'run_id':'r','role':'test','status':'running'}),('r.json',{'run_id':'r','role':'test','status':'complete','tasks_all_complete':False}),('r.device.json',{'run_id':'r','category':'device'})]:
                (p/name).write_text(json.dumps(data))
            rows=module.rows_for(p);self.assertEqual(1,len(rows));self.assertEqual('final',rows[0]['report_kind']);self.assertIn('daily_tasks_incomplete',rows[0]['warnings'])
    def test_closed_dispatch_without_report_is_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            rows=module.rows_for(directory,{'runs':[{'run_id':'missing','role':'test','status':'complete'}]})
            self.assertEqual('missing',rows[0]['report_kind']);self.assertIsNone(rows[0]['screenshots'])
    def test_missing_action_counts_and_shared_usage_never_become_estimated_cost(self):
        with tempfile.TemporaryDirectory() as directory:
            data={'run_id':'r','role':'test','metrics':{'usage_start':{'used_percent':10},'usage_end':{'used_percent':20},'credits':{'attributable_cost':7},'actions':[{'screenshots':1},{}]}}
            (Path(directory)/'r.json').write_text(json.dumps(data));row=module.rows_for(directory)[0]
            self.assertIsNone(row['credit_cost']);self.assertIsNone(row['screenshots']);self.assertIsNone(row['total_tokens'])
if __name__=='__main__':unittest.main()
