from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT_PATH = Path(__file__).parents[1] / "packaging" / "prune_python_runtime.py"
SPEC = importlib.util.spec_from_file_location("prune_python_runtime", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PrunePythonRuntimeTests(unittest.TestCase):
    def test_prunes_only_release_audit_development_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            runtime = Path(temporary_directory) / "resources" / "python"
            (runtime / "lib" / "package" / "tests").mkdir(parents=True)
            (runtime / "lib" / "package" / "tests" / "test_module.py").write_text("test")
            (runtime / "lib" / "package" / "__pycache__").mkdir()
            (runtime / "lib" / "package" / "__pycache__" / "module.pyc").write_bytes(b"pyc")
            (runtime / "lib" / "package" / "README.md").write_text("documentation")
            (runtime / "lib" / "package" / "module.py").write_text("value = 1")

            result = MODULE.prune_python_runtime(runtime)

            self.assertEqual(result.removed_directories, 2)
            self.assertEqual(result.removed_markdown_files, 1)
            self.assertFalse((runtime / "lib" / "package" / "tests").exists())
            self.assertFalse((runtime / "lib" / "package" / "__pycache__").exists())
            self.assertFalse((runtime / "lib" / "package" / "README.md").exists())
            self.assertTrue((runtime / "lib" / "package" / "module.py").is_file())

    def test_refuses_to_prune_an_unrelated_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(RuntimeError, "Refusing to prune"):
                MODULE.prune_python_runtime(temporary_directory)


if __name__ == "__main__":
    unittest.main()
