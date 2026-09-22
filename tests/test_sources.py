"""Source extraction checks, independent of the adjacent CPython checkout."""

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sources


class SourceTests(unittest.TestCase):
    def test_recorded_version_differences(self):
        data = sources.read_sources()
        self.assertEqual(list(data["versions"]), [f"3.{n}" for n in range(11, 17)])
        self.assertEqual([len(docs) for docs in data["groups"].values()],
                         [102, 103, 102, 106])
        for minor in (14, 15, 16):
            self.assertEqual(data["versions"][f"3.{minor}"]["group"], "3.14")
        groups = data["groups"]
        for old, new, added, removed, changed in (
            ("3.11", "3.12", 1, 0, 3),
            ("3.12", "3.13", 0, 1, 9),
            ("3.13", "3.14", 4, 0, 2),
        ):
            before, after = groups[old], groups[new]
            self.assertEqual(len(after.keys() - before.keys()), added)
            self.assertEqual(len(before.keys() - after.keys()), removed)
            self.assertEqual(sum(before[k] != after[k] for k in before.keys() & after.keys()),
                             changed)

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
