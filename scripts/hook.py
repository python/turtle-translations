"""Hatchling build hook to compile the PO catalogs when the wheel is built."""

import sys
import tempfile
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

sys.path.insert(0, str(Path(__file__).parent))
import i18n


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        self._build_dir = tempfile.TemporaryDirectory()
        for path in i18n._compile_catalogs(self._build_dir.name):
            build_data["force_include"][str(path)] = path.name

    def finalize(self, version, build_data, artifact_path):
        self._build_dir.cleanup()
