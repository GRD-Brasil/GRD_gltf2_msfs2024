from enum import Enum


class Supported_MSFS(Enum):
    msfs_2024 = "2024"

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class SupportedBlender(Enum):
    blender_33 = (3, 3, 0)
    blender_42 = (4, 2, 0)

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))
