"""Hatchling build hook to compile the PO catalogs when the wheel is built."""

import sys
import tempfile
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

sys.path.insert(0, str(Path(__file__).parent))
import i18n


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        self.generated = tempfile.TemporaryDirectory()
        output = Path(self.generated.name)
        for path in i18n._compile_catalogs(output):
            build_data["force_include"][str(path)] = path.relative_to(output).as_posix()

    def finalize(self, version, build_data, artifact_path):
        self.generated.cleanup()
