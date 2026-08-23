import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packaging"))

from macos_launcher import (  # noqa: E402
    BUNDLE_VERSION_FILE,
    PACKAGED_FILES_MANIFEST,
    _sync_runtime,
)


class MacOSLauncherSyncTests(unittest.TestCase):
    def test_bundle_update_preserves_user_files_and_removes_stale_packaged_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            source = temporary_root / "source"
            destination = temporary_root / "destination"
            (source / "modules").mkdir(parents=True)
            (source / BUNDLE_VERSION_FILE).write_text("first\n", encoding="utf-8")
            (source / "modules" / "old_module.py").write_text("OLD = True\n", encoding="utf-8")

            _sync_runtime(source, destination)
            user_file = destination / "save" / "user-settings.json"
            user_file.parent.mkdir(parents=True)
            user_file.write_text("{}\n", encoding="utf-8")

            (source / "modules" / "old_module.py").unlink()
            (source / "modules" / "new_module.py").write_text("NEW = True\n", encoding="utf-8")
            (source / BUNDLE_VERSION_FILE).write_text("second\n", encoding="utf-8")
            _sync_runtime(source, destination)

            self.assertFalse((destination / "modules" / "old_module.py").exists())
            self.assertTrue((destination / "modules" / "new_module.py").exists())
            self.assertTrue(user_file.exists())
            self.assertTrue((destination / PACKAGED_FILES_MANIFEST).exists())

    def test_same_bundle_version_does_not_overwrite_runtime(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            source = temporary_root / "source"
            destination = temporary_root / "destination"
            source.mkdir()
            (source / BUNDLE_VERSION_FILE).write_text("same\n", encoding="utf-8")
            (source / "entry.py").write_text("VALUE = 1\n", encoding="utf-8")

            _sync_runtime(source, destination)
            (destination / "entry.py").write_text("VALUE = 2\n", encoding="utf-8")
            _sync_runtime(source, destination)

            self.assertEqual(
                (destination / "entry.py").read_text(encoding="utf-8"),
                "VALUE = 2\n",
            )


if __name__ == "__main__":
    unittest.main()
