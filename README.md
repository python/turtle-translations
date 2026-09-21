# turtle-translations

Translations of the docstrings of Python's [`turtle`](https://docs.python.org/3/library/turtle.html)
module.

## Working with translations

Translations live in gettext catalogs in the `po/` directory.

### Extracting the template

The shared template contains all distinct English docstrings for Python 3.10–3.16.
Regenerate it from the committed source mappings (no Tkinter required):

```console
$ python scripts/i18n.py extract
po/turtle.pot: 121 distinct docstrings from Python 3.10–3.16
```

To refresh the mappings first, use a local CPython checkout with `upstream/3.10`
through `upstream/3.15` and `upstream/main` (3.16):

```console
$ python scripts/i18n.py extract --cpython ../cpython
```

This reads Git objects without switching branches or changing the CPython checkout.
The committed [compatibility report](sources/README.md) records source revisions,
method-level changes, and shared dictionary groups. The analysis covers these
branch snapshots, not every historical patch release. Source indentation is
normalized consistently across Python versions.

### Adding a language

Create a new catalog from the template for your language:

```console
$ python scripts/i18n.py init ga
Created: po/ga.po
```

You can now translate it with your tool of choice.

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
pl            0/121 translated (0%), 0 fuzzy
```

### Compiling

Each PO file compiles to a top-level `turtle_docstringdict_<lang>.py` shim and
internal version-specific dictionaries. The shim exports `docsdict`, which is
what `turtle` loads. Compilation matches both the method name and its English
source text, omitting untranslated and fuzzy entries so their help stays English.
One PO entry can serve multiple methods and versions; extracted comments identify
each use. All English variants remain in the shared catalog.

The generated modules are built automatically when the wheel is built, so you
normally only need this to test locally:

```console
$ python scripts/i18n.py compile
Compiled: turtle_translations/pl_310.py
Compiled: turtle_translations/pl_311.py
Compiled: turtle_translations/pl_312.py
Compiled: turtle_translations/pl_313.py
Compiled: turtle_translations/pl_314.py
Compiled: turtle_docstringdict_pl.py
```

The shim uses `sys.version_info[:2]`:

| Python | Dictionary |
| --- | --- |
| 3.10 and older | 3.10 |
| 3.11 | 3.11 |
| 3.12 | 3.12 |
| 3.13 | 3.13 |
| 3.14 and newer | Shared 3.14–3.16 |

Python 3.10–3.16 is supported. The older-version fallback does not extend the
package's `>=3.10` installation requirement. Future Python versions use the newest
dictionary until their sources are analyzed. No runtime dependencies are needed
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
