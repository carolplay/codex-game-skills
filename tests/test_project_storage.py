import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('storage',Path(__file__).resolve().parents[1]/'scripts/project_storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)


class StorageTests(unittest.TestCase):
    def test_shared_and_nested_paths_do_not_double_count_or_follow_alias(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);child=root/'child';child.mkdir()
            original=child/'log';original.write_bytes(b'x'*8192)
            os.link(original,child/'hardlink')
            (child/'alias').symlink_to(root,target_is_directory=True)
            result=storage.measure([root,child])
            self.assertEqual(result['files'],1)
            self.assertEqual(result['logical_bytes'],8192)

    def test_maintenance_line_stops_before_cap(self):
        self.assertTrue(storage.assess(4_499_999_999)['allow_new_batch'])
        self.assertEqual(storage.assess(4_500_000_000)['status'],'cleanup_required')
        self.assertFalse(storage.assess(4_500_000_000)['allow_new_batch'])
        self.assertEqual(storage.assess(5_000_000_000)['status'],'over_limit')
