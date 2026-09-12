"""Hatchling build hook to compile the PO catalogs when the wheel is built."""

import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

sys.path.insert(0, str(Path(__file__).parent))
import i18n


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # The generated modules are gitignored, so hatch need to be told to ship them.
        build_data["artifacts"] = [
            str(path.relative_to(self.root)) for path in i18n._compile_catalogs()
        ]
