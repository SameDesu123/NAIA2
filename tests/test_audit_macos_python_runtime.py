from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT_PATH = Path(__file__).parents[1] / "packaging" / "audit_macos_python_runtime.py"
SPEC = importlib.util.spec_from_file_location("audit_macos_python_runtime", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AuditMacosPythonRuntimeTests(unittest.TestCase):
    def test_parses_otool_dependencies(self) -> None:
        output = """/tmp/python (architecture x86_64):
\t@executable_path/../lib/libpython3.12.dylib (compatibility version 3.12.0, current version 3.12.0)
\t/usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1336.0.0)
/tmp/python (architecture arm64):
\t@executable_path/../lib/libpython3.12.dylib (compatibility version 3.12.0, current version 3.12.0)
"""

        self.assertEqual(
            MODULE.parse_otool_paths(output),
            (
                "@executable_path/../lib/libpython3.12.dylib",
                "/usr/lib/libSystem.B.dylib",
                "@executable_path/../lib/libpython3.12.dylib",
            ),
        )

    def test_parses_install_ids_without_architecture_headers(self) -> None:
        output = """/tmp/libpython.dylib (architecture x86_64):
/build/x86_64/libpython3.12.dylib
/tmp/libpython.dylib (architecture arm64):
/build/arm64/libpython3.12.dylib
"""

        self.assertEqual(
            MODULE.parse_otool_install_ids(output),
            {
                "/build/x86_64/libpython3.12.dylib",
                "/build/arm64/libpython3.12.dylib",
            },
        )

    def test_allows_bundle_relative_and_macos_system_dependencies(self) -> None:
        for dependency in (
            "@loader_path/libssl.3.dylib",
            "@rpath/libpython3.12.dylib",
            "@executable_path/../lib/libpython3.12.dylib",
            "/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation",
            "/usr/lib/libSystem.B.dylib",
        ):
            with self.subTest(dependency=dependency):
                self.assertTrue(MODULE.is_allowed_dependency(dependency, set()))

    def test_rejects_host_specific_absolute_dependencies(self) -> None:
        for dependency in (
            "/Library/Frameworks/Python.framework/Versions/3.12/Python",
            "/opt/homebrew/opt/openssl/lib/libssl.3.dylib",
            "/Users/runner/hostedtoolcache/Python/3.12/lib/libpython3.12.dylib",
        ):
            with self.subTest(dependency=dependency):
                self.assertFalse(MODULE.is_allowed_dependency(dependency, set()))

    def test_allows_a_dylibs_own_install_id(self) -> None:
        install_id = "/temporary/build/lib/libpython3.12.dylib"

        self.assertTrue(MODULE.is_allowed_dependency(install_id, {install_id}))


if __name__ == "__main__":
    unittest.main()
