"""Source extraction checks, independent of the adjacent CPython checkout."""

import ast
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sources


class SourceTests(unittest.TestCase):
    def test_recorded_version_differences(self):
        data = sources.read_sources()
        self.assertEqual(list(data["versions"]), [
            *(f"3.{minor}.{patch}" for minor, last in ((11, 16), (12, 14), (13, 15), (14, 7))
              for patch in range(last + 1)),
            "3.15.0", "3.16.0",
        ])
        self.assertEqual([len(docs) for docs in data["groups"].values()],
                         [102, 102, 103, 103, 102, 102, 106, 106])
        for version in ("3.14.1", "3.15.0", "3.16.0"):
            self.assertEqual(data["versions"][version]["group"], "3.14.1")
        groups = data["groups"]
        for old, new, added, removed, changed in (
            ("3.11.0", "3.11.3", 0, 0, 1),
            ("3.12.0", "3.12.6", 0, 0, 3),
            ("3.13.0", "3.13.10", 0, 0, 8),
            ("3.14.0", "3.14.1", 0, 0, 8),
            ("3.11.3", "3.12.6", 1, 0, 3),
            ("3.12.6", "3.13.10", 0, 1, 9),
            ("3.13.10", "3.14.1", 4, 0, 2),
        ):
            before, after = groups[old], groups[new]
            self.assertEqual(len(after.keys() - before.keys()), added)
            self.assertEqual(len(before.keys() - after.keys()), removed)
            self.assertEqual(sum(before[k] != after[k] for k in before.keys() & after.keys()),
                             changed)

    def test_collect_release_tags_and_development_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                return subprocess.check_output(
                    ["git", "-C", directory, *args], text=True, stderr=subprocess.PIPE
                ).strip()

            git("init")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            (root / "Lib").mkdir()
            source = root / "Lib" / "turtle.py"
            source.write_text('''
_tg_screen_functions = []
_tg_turtle_functions = []
_alias_list = []
__all__ = ["Turtle"]
class Turtle:
    """Original."""
class _Screen:
    pass
''')
            git("add", "Lib/turtle.py")
            git("commit", "-m", "Original")
            baseline = git("rev-parse", "HEAD")
            git("tag", "-a", "v3.11.0", "-m", "Annotated release")
            git("tag", "v3.11.1")
            source.write_text(source.read_text().replace("Original.", "Changed."))
            git("commit", "-am", "Changed")
            changed = git("rev-parse", "HEAD")
            git("tag", "v3.11.2")
            git("tag", "v3.11.3rc1")
            git("tag", "v3.16.0a1")
            git("update-ref", "refs/remotes/upstream/main", "HEAD")

            with patch.object(sources, "SERIES", ("3.11", "3.16")):
                data = sources.collect_sources(root)
                self.assertEqual(list(data["versions"]),
                                 ["3.11.0", "3.11.1", "3.11.2", "3.16.0"])
                self.assertEqual(data["versions"]["3.11.0"]["commit"], baseline)
                self.assertEqual(data["versions"]["3.11.1"]["group"], "3.11.0")
                self.assertEqual(data["versions"]["3.16.0"], {
                    "ref": "upstream/main", "commit": changed, "group": "3.11.2",
                })
                self.assertEqual(data["groups"]["3.11.2"], {"Turtle": "Changed."})
                # Once a series has a stable release, its tags replace the snapshot.
                git("tag", "v3.16.0")
                self.assertEqual(sources.collect_sources(root)["versions"]["3.16.0"]["ref"],
                                 "v3.16.0")
                git("tag", "-d", "v3.11.1")
                with self.assertRaisesRegex(ValueError, "Incomplete release tags"):
                    sources.collect_sources(root)
                git("tag", "-d", "v3.11.0", "v3.11.2")
                with self.assertRaisesRegex(ValueError, "No release tags"):
                    sources.collect_sources(root)

    def test_inheritance_aliases_and_unexecuted_source(self):
        source = '''
raise RuntimeError("Must never execute the source")
_tg_screen_functions = ["clear"]
_tg_turtle_functions = ["forward", "fd"]
_alias_list = ["fd"]
__all__ = _tg_screen_functions + _tg_turtle_functions + ["Turtle"]
class Base:
    def forward(self):
        """Move forward.
        Preserve indentation.
        """
    fd = forward
class Turtle(Base):
    """A turtle."""
class ScreenBase:
    def clear(self):
        """Clear the screen."""
class _Screen(ScreenBase):
    pass
'''
        docs = sources.extract_docstrings(source)
        self.assertEqual(set(docs), {"Turtle.forward", "_Screen.clear", "Turtle"})
        self.assertEqual(docs["Turtle.forward"], "Move forward.\nPreserve indentation.\n")
        tree = ast.parse(source)
        tree.body[3].value = ast.List(elts=[], ctx=ast.Load())
        docs = sources.extract_docstrings(ast.unparse(tree))
        self.assertEqual(docs["Turtle.fd"], docs["Turtle.forward"])

    def test_extraction_matches_running_turtle(self):
        import turtle

        docs = sources.extract_docstrings(Path(turtle.__file__).read_text(encoding="utf-8"))
        skip = set(turtle._alias_list) | {"Pen", "RawPen", "done"}
        expected = {}
        for name in turtle.__all__:
            if name in skip:
                continue
            if name in turtle._tg_screen_functions:
                key, obj = f"_Screen.{name}", getattr(turtle._Screen, name)
            elif name in turtle._tg_turtle_functions:
                key, obj = f"Turtle.{name}", getattr(turtle.Turtle, name)
            else:
                key, obj = name, getattr(turtle, name)
            if obj.__doc__:
                expected[key] = sources.normalize_docstring(obj.__doc__)
        self.assertEqual(docs, expected)


if __name__ == "__main__":
    unittest.main()
