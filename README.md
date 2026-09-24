# turtle-translations

Translations of the docstrings of Python's [`turtle`](https://docs.python.org/3/library/turtle.html)
module.

## Working with translations

Translations live in gettext catalogs in the `po/` directory.

### Extracting the template

The shared template contains all distinct English docstrings for Python 3.11–3.16,
including historical patch releases.
Regenerate it from the committed source mappings (no Tkinter required):

```console
$ python scripts/i18n.py extract
po/turtle.pot: 119 distinct docstrings from Python 3.11.0–3.16.0
```

To refresh the mappings first, use a local CPython checkout with stable release
tags and `upstream/3.15` and `upstream/main` (3.16) for development snapshots:

```console
$ git -C ../cpython fetch upstream --tags
$ python scripts/i18n.py extract --cpython ../cpython
```

This reads Git objects without switching branches or changing the CPython checkout.
The committed [compatibility report](sources/README.md) records source revisions,
method-level changes, and shared dictionary groups. Extraction compares every
locally available stable tag in each supported series and rejects gaps in patch
numbers. Fetch tags first to include the latest releases. Series without a stable
release use a development branch snapshot, recorded as `x.y.0`; prerelease tags
are excluded. Source indentation is normalized consistently across Python versions.

### Adding a language

Create a new catalog from the template for your language:

```console
$ python scripts/i18n.py init ga
Created: po/ga.po
```

You can now translate it with your tool of choice.

Add `turtle_docstringdict_<lang>.py` (with a lowercase language code) to
`tool.check-wheel-contents.toplevel` in `pyproject.toml` so package inspection
expects the new language's generated shim.

### Updating the catalogs

After refreshing the source mappings and template, merge the changes
into the existing catalogs:

```console
$ python scripts/i18n.py update            # all languages
$ python scripts/i18n.py update pl ga      # specific languages
```

Docstrings whose original text changed are fuzzy-matched by default and marked
`#, fuzzy` for review. Fuzzy entries are not shipped until the flag is removed.
Pass `--no-fuzzy` to skip the matching and `--drop-obsolete` to delete entries
that no longer exist in the template rather than keeping them commented out.

### Checking progress

```console
$ python scripts/i18n.py stats
pl            0/119 translated (0%), 0 fuzzy
```

### Compiling

Each PO file compiles to a top-level `turtle_docstringdict_<lang>.py` shim and
internal version-specific dictionaries under
`turtle_translations/<lang>/py3<minor><patch>.py` (for example, `py31310.py`
for 3.13.10). Identical source dictionaries share the module named for their
earliest version. The shim exports `docsdict`,
which is what `turtle` loads. Compilation matches each method's English source
text, omitting untranslated and fuzzy entries so their help stays English.
One PO entry can serve multiple methods and versions; extracted comments identify
each use. All English variants remain in the shared catalog.
Comments use minor versions for the newest variant of each method in a series;
only older variants within that series include patch numbers to distinguish them.

The generated modules are built automatically when the wheel is built, so you
normally only need this to test locally:

```console
$ python scripts/i18n.py compile
Compiled: turtle_translations/pl/py3110.py
Compiled: turtle_translations/pl/py3113.py
Compiled: turtle_translations/pl/py3120.py
Compiled: turtle_translations/pl/py3126.py
Compiled: turtle_translations/pl/py3130.py
Compiled: turtle_translations/pl/py31310.py
Compiled: turtle_translations/pl/py3140.py
Compiled: turtle_translations/pl/py3141.py
Compiled: turtle_translations/pl/__init__.py
Compiled: turtle_docstringdict_pl.py
```

The shim uses `sys.version_info[:3]`:

| Python | Dictionary |
| --- | --- |
| 3.10 and older | 3.11.0 |
| 3.11.0–3.11.2 | 3.11.0 |
| 3.11.3 and later 3.11 patches | 3.11.3 |
| 3.12.0–3.12.5 | 3.12.0 |
| 3.12.6 and later 3.12 patches | 3.12.6 |
| 3.13.0–3.13.9 | 3.13.0 |
| 3.13.10 and later 3.13 patches | 3.13.10 |
| 3.14.0 | 3.14.0 |
| 3.14.1 and newer | Shared 3.14.1–3.16.0 |

Python 3.11–3.16 is supported. The older-version fallback does not extend the
package's `>=3.11` installation requirement. Future Python versions use the newest
dictionary until their sources are analyzed. Prerelease suffixes are ignored;
development snapshots are selected by their major, minor, and patch numbers.
No runtime dependencies are needed
to import the shim; builds require Babel and Hatchling, but neither Tkinter nor a
CPython checkout. `turtle_translations.available()` lists language codes.

## Using translations

Install the package and place a `turtle.cfg` file in your working directory:

```ini
language = pl
```

Start a fresh Python process there and import `turtle`. Its class and module-level
help will use the available translations.

## Tests

Install Babel and Hatchling and run:

```console
$ python -m unittest discover -s tests -v
```

Runtime integration tests require Tkinter, but do not create a window.
