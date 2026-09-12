"""Docstring translations for the Python 'turtle' module."""

import pkgutil


def available():
    """Return a list of the available languages."""
    return sorted(
        info.name for info in pkgutil.iter_modules(__path__)
        if not info.name.startswith("_")
    )
