from __future__ import annotations
import bpy
import re
from pathlib import Path

from . import asset_path_utils


#region MSFS_ASSET_PATH_TAG Tag

MSFS_ASSET_PATH_TAG = "msfs_asset_path"

def _set_asset_msfs_path(asset: bpy.types.bpy_struct, blend_filepath: Path | str):
    """Add a MSFS_ASSET_PATH_TAG to asset.

    This property is not lost even when addon is disabled.
    """
    asset[MSFS_ASSET_PATH_TAG] = str(asset_path_utils.absolute_to_relative_asset_path(blend_filepath))


def get_asset_msfs_path(asset: bpy.types.bpy_struct) -> Path | None:
    msfs_asset_path = None
    try:
        msfs_asset_path = Path(asset[MSFS_ASSET_PATH_TAG])
    except:
        pass
    return msfs_asset_path

#endregion

def append_asset(
    blend_filepath: str | Path,
    datablock_type: str,
    id_name: str,
    link: bool = False,
    unique_mode: bool = False,
    msfs_asset_path_only : bool = True
) -> bpy.types.bpy_struct | None:
    """
    Append asset in current scene.

    If unique_mode is True, the function will first check if the asset
    is already present in the current blend file and return it is found.

    This prevents duplicating assets when appending multiple times.

    Appended assets and libraries are tagged with special msfs tags.
    """
    data_list = getattr(bpy.data, datablock_type)

    if unique_mode:
        # Get asset if it already in blend file
        asset = data_list.get(id_name, None)
        if asset and msfs_asset_path_only:
            # Only get asset with same msfs_asset_path
            msfs_datafiles_path = get_asset_msfs_path(asset)
            relative_blend_filepath = asset_path_utils.absolute_to_relative_asset_path(blend_filepath)
            if msfs_datafiles_path == relative_blend_filepath:
                return asset
        elif asset:
                return asset
    
    ids_before = set(data_list.keys())
    with bpy.data.libraries.load(str(blend_filepath), link=link) as (
        data_from,
        data_to,
    ):
        for _id_name in getattr(data_from, datablock_type):
            if id_name == _id_name:

                setattr(data_to, datablock_type, [id_name])
                break

    data_list_after = getattr(bpy.data, datablock_type)
    ids_after = set(data_list_after.keys())

    # Get appended_id_name by comparing the ids after append.
    # So we are sure to get the new appended data.
    # This prevent any id_name conflict (blend adds .001 when id_name already exists)
    id_names_diff = ids_after.difference(ids_before)
    asset = None
    appended_id_name = None
    if not id_names_diff:
        return None

    for name in id_names_diff:
        if name.startswith(id_name):
            appended_id_name = name
            break

    if not appended_id_name:
        return None

    asset = data_list_after.get(appended_id_name, None)
    if not asset:
        return None

    if msfs_asset_path_only:
        _set_asset_msfs_path(asset, blend_filepath)

    return asset

