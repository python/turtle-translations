"""Docstring translations for the Python 'turtle' module."""

import pkgutil


def available():
    """Return a list of the available languages."""
    return sorted({
        language
        for info in pkgutil.iter_modules(__path__)
        for language, separator, version in [info.name.rpartition("_")]
        if separator and language and version.isdecimal()
    })
