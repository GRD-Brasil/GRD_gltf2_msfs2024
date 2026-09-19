from __future__ import annotations
from typing import Type
import re
from pathlib import Path

import bpy

from enum import Enum
from . import append_utils
from . import asset_path_utils
from . import versions


class AssetLibrary(Enum):
    def check_id_name(self, id_name):
        id_name_parts = id_name.split("_", maxsplit=3)
        if len(id_name_parts) < 3:
            Exception(
                f"id_name doesn't follow nomenclature : '.MSFS_%VERSIONS%_%uniqueName% "
            )
        if id_name_parts[0] == ".MSFS_":
            raise Exception(f"id_name doesn't start with .MSFS_ preffix!")
        if id_name_parts[1] not in versions.Supported_MSFS.list():
            raise Exception(
                f"id_name MSFS version is not valid {id_name_parts[1]}. Valid versions are {versions.Supported_MSFS.list()}!"
            )

        special_characters = re.findall(r"[^A-Za-z0-9_]", id_name_parts[2])
        if special_characters:
            special_characters = "".join(special_characters)
            raise Exception(
                f"id_name {id_name} contains special characters: {special_characters}"
            )

    def __init__(self, id_name: str, asset_path: str):
        self.check_id_name(id_name)

        self.id_name: str = id_name
        self.label_name: str = id_name.replace(".", "")
        self.asset_path: str = asset_path

        self.DATA_BLOCK_TYPE: str = ""

    @classmethod
    def get_by_id_name(cls, id_name: str) -> AssetLibrary | None:
        """
        Retrieve an Asset entry by its id_name.
        """
        for entry in cls:
            if entry.id_name == id_name:
                return entry

        return None
    
    def append_asset(
        self, 
        link: bool = False
        ) -> bpy.types.bpy_struct | None:
            blend_filepath = str(self._get_latest_blend_path())
            return append_utils.append_asset(
                blend_filepath,
                self.DATA_BLOCK_TYPE,
                self.id_name,
                link=link,
                unique_mode=True,
                msfs_asset_path_only=True
            )
    
    def _get_latest_blend_path(self) -> Path:
        """Find the most recent blend file in datafiles/assets.

        Uses blend file naming convention : %name%-3_6_0.

        Returns:
            Absolute path to blend file.
        """
        
        datafiles_dir = asset_path_utils.get_absolute_datafiles_dir()
        found_library_path = None

        for version in versions.SupportedBlender:
            if not bpy.app.version >= version.value:
                continue
            version_suffix = f"-{version.value[0]}_{version.value[1]}_{version.value[2]}"
            _asset_path = self.asset_path + version_suffix + ".blend"
            absolute_asset_path = datafiles_dir / _asset_path
            if absolute_asset_path.exists():
                found_library_path = absolute_asset_path

        if not found_library_path:
            raise Exception(f"Blender version {bpy.app.version} is not supported!")

        return found_library_path
# region Node Groups Inputs


class NodeGroupInputs(Enum):
    def __init__(self, input_label):
        """
        Node groupe input labels.
        Labels must be unique.
        """
        self.input_label: str = input_label


class EmptyInputs(NodeGroupInputs):
    pass


class MSFS2024CollisionInputs(NodeGroupInputs):
    TYPE = "Collision Type"
    ROAD_COLLIDER = "Road Collider"
    GROUND_COLLIDER = "Ground Collider"


# endregion


# region Nodegroup
class NodeGroupLibrary(AssetLibrary):
    """
    Registry of node group assets.
    """

    COLLISIONS = (
        ".MSFS_2024_Collision",
        "assets/nodes/gizmos",
        MSFS2024CollisionInputs,
    )
    BOUNDING_VOLUME = (
        ".MSFS_2024_Bounding_Volume",
        "assets/nodes/gizmos",
        EmptyInputs,
    )

    def __init__(
        self, id_name: str, asset_path: str, node_group_inputs: Type[NodeGroupInputs]
    ):
        super().__init__(id_name, asset_path)
        self.DATA_BLOCK_TYPE: str = "node_groups"
        self.node_group_inputs = node_group_inputs

    

    def append_modifier(
        self,
        object: bpy.types.Object,
        link: bool = False,
    ) -> bpy.types.Modifier | None:
        """
        Appends a node_group and applies it
        as a modifier to the given object.
        """

        node_group = self.append_asset(link)

        if not node_group:
            raise Exception("Can't append node group!")

        # Create a new Geometry Nodes modifier
        modifier = object.modifiers.new(name=self.label_name, type="NODES")
        modifier.node_group = node_group
        if bpy.app.version >= (4, 0, 0):
            modifier.show_group_selector = False

        return modifier


# endregion

#region Asset Update
def _remove_number_suffix(name: str) -> str:
    """Remove potential suffix like .001"""
    return re.sub(r"\.\d+$", "", name)


def update_appended_assets():
    """
    Update assets that were appended as a copy (link=False).
    """
    current_file = Path(bpy.path.abspath(bpy.data.filepath))

    if asset_path_utils.in_datafiles(current_file):
        print(
            "Skip MSFS libraries link update since this file is an asset library source!"
        )
        return

    updated_ids: dict[str, bpy.types.bpy_struct] = {}
    to_delete: list[bpy.types.bpy_struct] = []
    # import here to prevent circular import 
    from .asset_library import NodeGroupLibrary
    # Update node groups
    for node_group in bpy.data.node_groups.values():
        relative_datafiles_path = append_utils.get_asset_msfs_path(node_group)
        if not relative_datafiles_path:
            continue
        absolute_asset_path = asset_path_utils.get_absolute_datafiles_dir() / relative_datafiles_path
        if not absolute_asset_path.exists():
            continue
        id_name = node_group.name

        # remove potential suffix like .001
        clean_id_name = _remove_number_suffix(id_name)

        registry_entry = NodeGroupLibrary.get_by_id_name(clean_id_name)
        if not registry_entry:
            continue
        updated_node_group = None
        if clean_id_name in updated_ids:
            updated_node_group = updated_ids[clean_id_name]
        else:
            # Rename old node_group to prevent numbered suffis on appended asset
            node_group.name = ".To_Purge"

            to_delete.append(node_group)
            updated_node_group = append_utils.append_asset(
                blend_filepath=absolute_asset_path,
                datablock_type=registry_entry.DATA_BLOCK_TYPE,
                id_name=clean_id_name,
                unique_mode=False,
            )
            updated_ids[clean_id_name] = updated_node_group

        if not updated_node_group:
            print(f"Update node group couldn't be appended {id_name}")
            continue

        # Replace old node_group by new_ones
        for obj in bpy.data.objects:
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group == node_group:
                    mod.node_group = updated_node_group

        node_group.user_remap(updated_node_group)

        # updated_node_group.name = clean_id_name
        print(f"Node group {id_name} was updated")

    for node_group in to_delete:
        bpy.data.node_groups.remove(node_group)

# endregion