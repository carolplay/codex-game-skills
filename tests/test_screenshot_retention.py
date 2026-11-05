import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('retention',Path(__file__).resolve().parents[1]/'scripts/retain_macro_screenshots.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class RetentionTests(unittest.TestCase):
    def fixture(self, root):
        runs=root/'local-data/crossmacro/v2/runs/current';runs.mkdir(parents=True)
        disposable=runs/'fresh-failure.jpg';disposable.write_bytes(b'fresh failure pixels')
        log=runs/'result.json';log.write_text(json.dumps({'status':'failed','image':str(disposable)}))
        template=runs/'active-template.png';template.write_bytes(b'operational template')
        (runs.parents[1]/'role-1-config.json').write_text(json.dumps({'image_templates':{'test':str(template)}}))
        foreign=root/'local-data/guild-bot/evidence.png';foreign.parent.mkdir(parents=True);foreign.write_bytes(b'foreign evidence')
        return disposable,log,template,foreign

    def test_recent_failed_and_report_referenced_pixels_expire_logs_and_templates_survive(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);image,log,template,foreign=self.fixture(root);before=log.read_bytes()
            preview=module.maintain(root,False)
            self.assertEqual(preview['candidate_images'],1);self.assertTrue(image.exists())
            result=module.maintain(root,True)
            self.assertEqual(result['removed_images'],1);self.assertFalse(image.exists())
            self.assertEqual(log.read_bytes(),before);self.assertTrue(template.exists());self.assertTrue(foreign.exists())

    def test_invalid_fixture_consumer_or_checksum_stops_before_any_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);image,_,_,_=self.fixture(root)
            manifest=root/'local-data/material-store/wos/reusable-images.json';manifest.parent.mkdir(parents=True)
            consumer=root/'fixture-test.py';consumer.write_text('fixture consumer')
            manifest.write_text(json.dumps({'images':[{'path':str(image.relative_to(root)),
                'consumer':'fixture-test.py','purpose':'maintained regression','sha256':'wrong'}]}))
            with self.assertRaisesRegex(ValueError,'checksum'):module.maintain(root,True)
            self.assertTrue(image.exists())
            data=json.loads(manifest.read_text());data['images'][0]['sha256']=hashlib.sha256(image.read_bytes()).hexdigest();manifest.write_text(json.dumps(data))
            self.assertEqual(module.maintain(root,True)['removed_images'],0)

    def test_busy_real_lock_skips_and_does_not_remove_lock(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);image,_,_,_=self.fixture(root);path=root/'local-data/crossmacro/v2/visit.lock'
            with path.open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.assertEqual(module.maintain(root,True)['status'],'skipped_active_executor')
            self.assertTrue(image.exists());self.assertTrue(path.exists())


if __name__=='__main__':unittest.main()
