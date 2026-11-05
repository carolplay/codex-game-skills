import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('retention', Path(__file__).resolve().parents[1] / 'scripts/retain_macro_screenshots.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
store_spec = importlib.util.spec_from_file_location('prepare_macro_material_store', Path(__file__).resolve().parents[1] / 'scripts/prepare_macro_material_store.py')
store_module = importlib.util.module_from_spec(store_spec)
store_spec.loader.exec_module(store_module)


class EmergencyCleanupTests(unittest.TestCase):
    def test_shared_material_is_kept_until_last_source_is_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runs = root / 'local-data/crossmacro/v2/runs'
            library = root / 'local-data/macro-materials'
            runs.mkdir(parents=True)
            data = b'private screenshot'
            sha = hashlib.sha256(data).hexdigest()
            blob = library / 'blobs' / sha[:2] / (sha + '.jpg')
            blob.parent.mkdir(parents=True)
            blob.write_bytes(data)
            sources = [runs / 'a.jpg', runs / 'b.jpg']
            for p in sources:
                os.link(blob, p)
            (runs / 'result.json').write_text('{"status":"passed"}')
            original_log = (runs / 'result.json').read_bytes()
            outsider = root / 'config.jpg'
            outsider.write_bytes(b'runtime template')
            index = {'samples': {str(p.relative_to(root)): {
                'sha256': sha, 'blob': str(blob.relative_to(root))} for p in sources}}
            (library / 'index.json').write_text(json.dumps(index))
            store_module.prepare(root, True)
            disk = lambda _: SimpleNamespace(free=100 + sum(not p.exists() for p in sources))
            with patch.multiple(module, ROOT=root, RUNS=runs, LIBRARY=library), patch.object(module.shutil, 'disk_usage', disk), patch.dict('sys.modules', {'prepare_macro_material_store': store_module}):
                first = module.emergency_free_space(1 / 1024**3, True)
                self.assertEqual(first['removed_images'], 1)
                self.assertTrue(blob.exists())
                self.assertEqual(len(json.loads((library / 'index.json').read_text())['samples']), 1)
                second = module.emergency_free_space(1 / 1024**3, True)
                self.assertEqual(second['removed_material_blobs'], 1)
                self.assertFalse(blob.exists())
                self.assertEqual((runs / 'result.json').read_bytes(), original_log)
                self.assertEqual(outsider.read_bytes(), b'runtime template')
                self.assertTrue(second['all_non_image_logs_unchanged'])


if __name__ == '__main__':
    unittest.main()
