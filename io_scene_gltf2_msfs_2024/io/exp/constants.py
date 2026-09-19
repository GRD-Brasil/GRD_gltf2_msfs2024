from __future__ import annotations
from enum import Enum

class ExportModes(Enum):
    OBJECTS = ("OBJECTS", "Objects")
    PRESETS = ("PRESETS", " Presets")

    def __init__(self, identifier: str, label: str):
        self.identifier = identifier
        self.label = label

    @classmethod
    def from_identifier(cls, identifier: str) -> ExportModes | None:
        """
        Return the ExportModes enum member matching the given identifier.
        """
        for mode in cls:
            if mode.identifier == identifier:
                return mode
        return None


EXPORT_MODES_ENUM_ITEMS = (
    (ExportModes.OBJECTS.identifier, ExportModes.OBJECTS.label, ""),
    (ExportModes.PRESETS.identifier, ExportModes.PRESETS.label, ""),
)

class Tabs(Enum):
    OBJECTS = ("OBJECTS", "Objects")
    PRESETS = ("PRESETS", " Presets")
    SETTINGS = ("SETTINGS", " Settings")

    def __init__(self, identifier: str, label: str):
        self.identifier = identifier
        self.label = label
