import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('material_store', Path(__file__).resolve().parents[1] / 'scripts/prepare_macro_material_store.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MaterialStoreTests(unittest.TestCase):
    def fixture(self, root):
        library = root / 'local-data/macro-materials'
        (root / 'local-data/crossmacro/v2').mkdir(parents=True)
        data = b'example private image'
        digest = hashlib.sha256(data).hexdigest()
        blob = library / 'blobs' / digest[:2] / (digest + '.jpg')
        blob.parent.mkdir(parents=True)
        blob.write_bytes(data)
        original = root / 'local-data/crossmacro/v2/original.jpg'
        os.link(blob, original)
        (library / 'index.json').write_text(json.dumps({'samples': {'original': {
            'sha256': digest, 'blob': str(blob.relative_to(root)),
            'workflow': {'action_id': 'test', 'action_version': '1'}}}}))
        return library, original, blob.stat().st_ino

    def test_relocation_preserves_hardlinks_old_paths_and_portable_access(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            library, original, inode = self.fixture(root)
            result = module.prepare(root, True)
            self.assertTrue(library.is_symlink())
            manifest = library.resolve().parent / 'assets.jsonl'
            item = json.loads(manifest.read_text())
            relocated = manifest.parent / item['file']
            self.assertEqual(relocated.stat().st_ino, inode)
            self.assertEqual(original.stat().st_ino, inode)
            self.assertEqual(relocated.read_bytes(), original.read_bytes())
            self.assertEqual(result['images_copied'], 0)
            self.assertEqual(module.prepare(root, True)['blob_files'], 1)

    def test_corrupt_blob_never_relocates_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            library, original, _ = self.fixture(root)
            original.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'content mismatch'):
                module.prepare(root, True)
            self.assertFalse(library.is_symlink())
            self.assertTrue((library / 'index.json').is_file())

    def test_real_executor_lock_skips_without_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            library, _, _ = self.fixture(root)
            with (root / 'local-data/crossmacro/v2/visit.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.assertEqual(module.prepare(root, True)['status'], 'skipped_active_executor')
            self.assertFalse(library.is_symlink())
            self.assertFalse((root / 'local-data/material-store').exists())


if __name__ == '__main__':
    unittest.main()
