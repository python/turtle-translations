"""Catalog compilation and version selection regressions."""

import ast
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import i18n
import sources

ROOT = Path(__file__).resolve().parent.parent


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = sources.read_sources()

    def test_union_contains_every_source_and_method(self):
        catalog = i18n.build_template(self.data)
        originals = set()
        for version, info in self.data["versions"].items():
            for key, original in self.data["groups"][info["group"]].items():
                originals.add(original)
                message = catalog.get(original)
                self.assertTrue(any(comment.startswith(f"turtle.{key} (Python ")
                                    for comment in message.auto_comments))
        self.assertEqual(len(catalog), len(originals))

    def test_comments_group_versions_per_method_without_filling_gaps(self):
        data = {
            "versions": {version: {"group": version}
                         for version in ("3.11", "3.12", "3.13", "3.14")},
            "groups": {
                "3.11": {"Turtle.left": "Shared", "Turtle.right": "Shared"},
                "3.12": {"Turtle.left": "Shared"},
                "3.13": {"Turtle.left": "Changed"},
                "3.14": {"Turtle.left": "Shared"},
            },
        }
        catalog = i18n.build_template(data)
        self.assertEqual(catalog.get("Shared").auto_comments, [
            "turtle.Turtle.left (Python 3.11–3.12, 3.14)",
            "turtle.Turtle.right (Python 3.11)",
        ])
        self.assertEqual(catalog.get("Changed").auto_comments, [
            "turtle.Turtle.left (Python 3.13)",
        ])

    def test_newest_docstrings_precede_older_variants(self):
        data = {
            "versions": {version: {"group": version}
                         for version in ("3.10", "3.9", "3.11")},
            "groups": {
                "3.9": {"Turtle.left": "Oldest", "Turtle.right": "Shared"},
                "3.10": {"Turtle.left": "Older", "Turtle.right": "Shared",
                         "Turtle.removed": "Removed"},
                "3.11": {"Turtle.left": "Newest", "Turtle.right": "Shared"},
            },
        }
        template = i18n.build_template(data)
        expected = ["Newest", "Shared", "Older", "Removed", "Oldest"]
        self.assertEqual([message.id for message in template if message.id], expected)
        self.assertEqual(template.version, "3.9–3.11")

        catalog = i18n.Catalog(locale="pl")
        for original in reversed(expected):
            catalog.add(original, string=f"Translation: {original}")
        catalog.update(template)
        path = self.root / "pl.po"
        i18n.write_catalog(catalog, path)
        messages = [message for message in i18n.read_catalog(path) if message.id]
        self.assertEqual([message.id for message in messages], expected)
        for message in messages:
            self.assertEqual(message.string, f"Translation: {message.id}")
            self.assertFalse(message.fuzzy)

    def test_matching_requires_original_and_reviewed_translation(self):
        catalog = i18n.build_template(self.data)
        for message in catalog:
            if message.id:
                message.string = f"Translation: {message.id}"
        docs = self.data["groups"]["3.11"]
        catalog.get(docs["Turtle.forward"]).flags.add("fuzzy")
        catalog.get(docs["Turtle.back"]).string = ""
        catalog.get(docs["Turtle.left"]).auto_comments = ["turtle.WrongMethod"]
        catalog.get(docs["Turtle.right"]).auto_comments = []
        path = self.root / "pl.po"
        i18n.write_catalog(catalog, path)
        compiled = i18n._load_docsdict(path, docs)
        for key in ("Turtle.forward", "Turtle.back"):
            self.assertNotIn(key, compiled)
        for key in ("Turtle.left", "Turtle.right"):
            self.assertEqual(compiled[key], f"Translation: {docs[key]}")
        self.assertIn("Turtle.settiltangle", compiled)
        self.assertNotIn("Turtle.teleport", compiled)
        self.assertEqual(compiled["Turtle.tiltangle"], f"Translation: {docs['Turtle.tiltangle']}")
        newer = i18n._load_docsdict(path, self.data["groups"]["3.14"])
        self.assertNotIn("Turtle.settiltangle", newer)
        self.assertIn("Turtle.teleport", newer)
        self.assertIn("_Screen.save", newer)
        self.assertNotEqual(compiled["Turtle.tiltangle"], newer["Turtle.tiltangle"])

    def test_new_source_does_not_reuse_old_translation(self):
        catalog = i18n.build_template(self.data)
        original = self.data["groups"]["3.11"]["Turtle.tiltangle"]
        catalog.get(original).string = "Old translation"
        path = self.root / "pl.po"
        i18n.write_catalog(catalog, path)
        self.assertEqual(i18n._load_docsdict(path, {"Turtle.tiltangle": original}),
                         {"Turtle.tiltangle": "Old translation"})
        self.assertEqual(i18n._load_docsdict(path, {"Turtle.tiltangle": "Changed text"}), {})

    def test_update_preserves_existing_translation(self):
        catalog = i18n.build_template(self.data)
        original = self.data["groups"]["3.11"]["Turtle.forward"]
        catalog.get(original).string = "Naprzód"
        catalog.update(i18n.build_template(self.data))
        self.assertEqual(catalog.get(original).string, "Naprzód")
        self.assertFalse(catalog.get(original).fuzzy)

    def test_compilation_and_language_discovery(self):
        catalog = i18n.build_template(self.data)
        for lang in ("pl", "pt_BR"):
            i18n.write_catalog(catalog, self.root / f"{lang}.po")
        with patch.object(i18n, "PO_DIR", self.root):
            paths = i18n._compile_catalogs(self.root)
        self.assertEqual(len(paths), 12)
        self.assertTrue((self.root / "turtle_docstringdict_pt_br.py").is_file())
        self.assertTrue((self.root / "turtle_translations" / "pl" / "py311.py").is_file())
        self.assertFalse((self.root / "turtle_translations" / "pl" / "py310.py").exists())
        for path in paths:
            ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 10))
        spec = importlib.util.spec_from_file_location(
            "fixture_translations", ROOT / "turtle_translations" / "__init__.py",
            submodule_search_locations=[str(self.root / "turtle_translations")],
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.available(), ["pl", "pt_br"])

    def test_shim_dispatch_and_import_isolation(self):
        modules = {}
        for group in self.data["groups"]:
            name = f"turtle_translations.{i18n._module_name('pl', group)}"
            modules[name] = types.SimpleNamespace(docsdict={"group": group})
        modules.update({"turtle": None, "tkinter": None, "babel": None})
        cases = [(2, 7, "3.11"), (3, 9, "3.11")]
        cases += [(3, minor, f"3.{min(minor, 14)}") for minor in range(11, 18)]
        cases.append((4, 0, "3.14"))
        code = i18n._render_shim("pl", self.data)
        for major, minor, group in cases:
            for release in ("alpha", "final"):
                with self.subTest(version=(major, minor, release)):
                    with patch.dict(sys.modules, modules), patch.object(
                        sys, "version_info", (major, minor, 0, release, 0)
                    ):
                        namespace = {}
                        exec(code, namespace)
                    self.assertEqual(namespace["docsdict"], {"group": group})

    def test_fresh_turtle_import_with_translated_fixture(self):
        # A separate process ensures configuration is applied before turtle's
        # module-level wrappers copy the translated method docstrings.
        catalog = i18n.build_template(self.data)
        for message in catalog:
            if message.id:
                message.string = "Polish fixture: " + message.id
        path = self.root / "pl.po"
        i18n.write_catalog(catalog, path)
        with patch.object(i18n, "po_files", return_value=[path]):
            i18n._compile_catalogs(self.root)
        shutil.copyfile(ROOT / "turtle_translations" / "__init__.py",
                        self.root / "turtle_translations" / "__init__.py")
        (self.root / "turtle.cfg").write_text("language = pl\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-c", '''
import turtle
import turtle_docstringdict_pl
assert turtle_docstringdict_pl.docsdict
assert turtle.Turtle.forward.__doc__.startswith("Polish fixture: ")
assert turtle.forward.__doc__.startswith("Polish fixture: ")
assert turtle.fd.__doc__ == turtle.forward.__doc__
assert turtle.Screen.__doc__.startswith("Polish fixture: ")
'''], cwd=self.root, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
