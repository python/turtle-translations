"""Tooling for maintaining the turtle docstring catalogs."""

import argparse
import platform
from datetime import datetime, timezone
from pathlib import Path

from babel.messages.catalog import Catalog
from babel.messages.pofile import read_po, write_po

ROOT = Path(__file__).resolve().parent.parent
PO_DIR = ROOT / "po"
POT = PO_DIR / "turtle.pot"
PROJECT = "turtle-translations"
BUGS_ADDRESS = "https://github.com/python/turtle-translations/issues"



def _extract_docstrings():
    # XXX: turtle.write_docstringdict() only extracts a subset of docstrings and
    #  appends a newline to every docstring.
    import turtle

    skip = set(turtle._alias_list) | {"Pen", "RawPen", "done"}
    result = {}
    for name in turtle.__all__:
        if name in skip:
            continue
        if name in turtle._tg_screen_functions:
            key = f"_Screen.{name}"
        elif name in turtle._tg_turtle_functions:
            key = f"Turtle.{name}"
        else:
            key = name
        result[key] = eval(key, vars(turtle)).__doc__
    return dict(sorted(result.items()))


def build_template():
    catalog = Catalog(
        project=PROJECT,
        version=platform.python_version(),
        msgid_bugs_address=BUGS_ADDRESS,
        charset="utf-8",
        header_comment=(
            "# Docstrings of the Python turtle module.\n"
            f"# Extracted from Python {platform.python_version()}.\n"
            "# This file was generated via 'scripts/i18n.py extract'."
        ),
    )
    for key, doc in _extract_docstrings().items():
        catalog.add(doc, auto_comments=[f"turtle.{key}"])
    return catalog


def write_catalog(catalog, path, **kwargs):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        write_po(f, catalog, width=None, **kwargs)


def read_catalog(path, **kwargs):
    with path.open("rb") as f:
        return read_po(f, **kwargs)


def cmd_extract(args):
    catalog = build_template()
    write_catalog(catalog, POT)
    print(f"{POT.relative_to(ROOT)}: {len(catalog)} docstrings "
          f"from Python {platform.python_version()}")


def po_files(langs=None):
    if langs:
        return [PO_DIR / f"{lang}.po" for lang in langs]
    return sorted(PO_DIR.glob("*.po"))


def cmd_init(args):
    path = PO_DIR / f"{args.lang}.po"
    template = read_catalog(POT)
    catalog = Catalog(
        locale=args.lang,
        project=PROJECT,
        version=template.version,
        msgid_bugs_address=BUGS_ADDRESS,
        charset="utf-8",
        fuzzy=False,
    )
    catalog.update(template)
    write_catalog(catalog, path)
    print(f"Created: {path.relative_to(ROOT)}")


def cmd_update(args):
    template = read_catalog(POT)
    for path in po_files(args.langs):
        catalog = read_catalog(path)
        catalog.update(template, no_fuzzy_matching=args.no_fuzzy)
        catalog.version = template.version
        catalog.revision_date = datetime.now(timezone.utc)
        write_catalog(catalog, path, ignore_obsolete=args.drop_obsolete)
        print(f"Updated: {path.relative_to(ROOT)}")


def _load_docsdict(path):
    catalog = read_catalog(path)
    return {
        comment.removeprefix("turtle."): message.string
        for message in catalog
        if message.id and message.string and not message.fuzzy
        for comment in message.auto_comments
    }


MODULE_FOOTER = """
# turtle imports this module after defining its classes, so drop entries for
# names this version of turtle does not have.
import turtle

for _key in list(docsdict):
    _obj = turtle
    for _attr in _key.split("."):
        _obj = getattr(_obj, _attr, None)
    if _obj is None:
        del docsdict[_key]
"""


def _render_module(source, docsdict):
    lines = [f"# Generated from {source.name}. Do not edit.",
             "",
             "docsdict = {"
            ]
    for key, doc in sorted(docsdict.items()):
        lines.append(f"    {key!r}: {doc!r},")
    lines.append("}")
    return "\n".join(lines) + "\n" + MODULE_FOOTER


def _compile_catalogs(output_dir=ROOT):
    """Write a `turtle_docstringdict_<lang>.py` module for each PO file."""
    written = []
    for path in po_files():
        # turtle lowercases the language before importing it!
        target = Path(output_dir) / f"turtle_docstringdict_{path.stem.lower()}.py"
        target.write_text(_render_module(path, _load_docsdict(path)), encoding="utf-8")
        written.append(target)
    return written


def cmd_compile(args):
    for path in _compile_catalogs():
        print(f"Compiled: {path.relative_to(ROOT)}")


def _catalog_stats(path):
    catalog = read_catalog(path)
    translated = fuzzy = total = 0
    for message in catalog:
        if not message.id:
            continue
        total += 1
        if message.fuzzy:
            fuzzy += 1
        elif message.string:
            translated += 1
    return translated, fuzzy, total


def cmd_stats(args):
    for path in po_files():
        translated, fuzzy, total = _catalog_stats(path)
        pct = 100 * translated // total if total else 0
        print(f"{path.stem:10} {translated:4}/{total} translated "
              f"({pct}%), {fuzzy} fuzzy")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("extract", help="write `po/turtle.pot`").set_defaults(func=cmd_extract)

    p = sub.add_parser("init", help="create a PO file for a new language")
    p.add_argument("lang", help="language code, e.g. `pl`")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("update", help="merge the template into PO files")
    p.add_argument("langs", nargs="*", help="languages to update (default: all)")
    p.add_argument("--no-fuzzy", action="store_true",
                   help="do not fuzzy-match changed docstrings")
    p.add_argument("--drop-obsolete", action="store_true",
                   help="remove entries no longer in the template")
    p.set_defaults(func=cmd_update)

    sub.add_parser("compile", help="compile PO files").set_defaults(func=cmd_compile)

    sub.add_parser("stats", help="catalog completeness").set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
