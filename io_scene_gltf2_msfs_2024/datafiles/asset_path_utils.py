from __future__ import annotations

from pathlib import Path

ADDON_DATAFILES_DIR = Path("io_scene_gltf2_msfs_2024/datafiles")

def get_absolute_datafiles_dir() -> Path:
    """Get absolute datafiles directory"""
    assets_dir = Path(__file__).parent
    return assets_dir

def in_datafiles(path: Path | str) -> bool:
    """Check if path uses datafiles directory."""
    return ADDON_DATAFILES_DIR.as_posix() in Path(path).as_posix()

def relative_to_absolute_asset_path(relative_asset_path: str) -> Path|None:
    datafiles_dir = get_absolute_datafiles_dir()
    absolute_asset_path = datafiles_dir / Path(relative_asset_path)
    if absolute_asset_path.exists():
        found_library_path = absolute_asset_path

    if not found_library_path:
        return None
    
    return found_library_path

def absolute_to_relative_asset_path(absolute_asset_path: Path | str) -> Path|None:
    absolute_asset_path = Path(absolute_asset_path)
    asset_dir = get_absolute_datafiles_dir()
    return absolute_asset_path.relative_to(asset_dir)
    

