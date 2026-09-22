"""Exercise the wheel's actual loader contract with translated fixture data."""

import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import i18n

ROOT = Path(__file__).resolve().parent.parent


class PackageTests(unittest.TestCase):
    def test_wheel_with_translations_and_stale_legacy_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("scripts", "sources", "turtle_translations"):
                shutil.copytree(ROOT / name, root / name,
                                ignore=shutil.ignore_patterns("__pycache__"))
            for name in ("pyproject.toml", "README.md", "LICENSE", ".gitignore"):
                shutil.copyfile(ROOT / name, root / name)
            catalog = i18n.build_template()
            for message in catalog:
                if message.id:
                    message.string = "Polish fixture: " + message.id
            i18n.write_catalog(catalog, root / "po" / "pl.po")
            (root / "turtle_translations" / "pl.py").write_text("raise RuntimeError\n")
            result = subprocess.run(
                [sys.executable, "-m", "hatchling", "build", "-t", "wheel"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            wheel = next((root / "dist").glob("*.whl"))
            with zipfile.ZipFile(wheel) as archive:
                names = archive.namelist()
                self.assertIn("turtle_docstringdict_pl.py", names)
                self.assertNotIn("turtle_translations/pl.py", names)
                for group in (310, 311, 312, 313, 314):
                    self.assertIn(f"turtle_translations/pl/py{group}.py", names)
            runtime = root / "runtime"
            runtime.mkdir()
            (runtime / "turtle.cfg").write_text("language = pl\n")
            result = subprocess.run(
                [sys.executable, "-I", "-c", '''
import sys
sys.path.insert(0, sys.argv[1])
import turtle_docstringdict_pl as pl
assert pl.docsdict
assert "turtle" not in sys.modules
assert "tkinter" not in sys.modules
assert "babel" not in sys.modules
import turtle_translations
assert turtle_translations.available() == ["pl"]
import turtle
assert turtle.Turtle.forward.__doc__.startswith("Polish fixture: ")
assert turtle.forward.__doc__.startswith("Polish fixture: ")
assert turtle.fd.__doc__ == turtle.forward.__doc__
''', str(wheel)], cwd=runtime, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
