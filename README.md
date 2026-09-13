# turtle-translations

Translations of the docstrings of Python's [`turtle`](https://docs.python.org/3/library/turtle.html)
module.

## Working with translations

Translations live in gettext catalogs in the `po/` directory.

### Extracting the template

The template is extracted from the `turtle` module of the Python you run the
script with, so use the latest Python version available:

```console
$ python scripts/i18n.py extract
po/turtle.pot: 103 docstrings from Python 3.16.0a0
```

### Adding a language

Create a new catalog from the template for your language:

```console
$ python scripts/i18n.py init ga
Created: po/ga.po
```

You can now translate it with your tool of choice.

### Updating the catalogs

After re-extracting the template against a newer Python, merge the changes
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
pl           42/103 translated (40%), 3 fuzzy
```

### Compiling

Each PO file compiles to a `turtle_translations/<lang>.py` module containing a
`docsdict`, which is what `turtle` loads. The generated modules are built
automatically when the wheel is built, so you normally only need this to test
locally:

```console
$ python scripts/i18n.py compile
Compiled: turtle_translations/pl.py
```
