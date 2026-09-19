# Copyright 2023-2024 The glTF-Blender-IO-MSFS2024 authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
from pathlib import Path

# Ensure _addons_utils is resolvable whether bundled inside this extension package
# or located side-by-side in scripts/addons/ (legacy)
_pkg_dir = Path(__file__).resolve().parent
if (_pkg_dir / "_addons_utils").is_dir() and str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))
elif (_pkg_dir.parent / "_addons_utils").is_dir() and str(_pkg_dir.parent) not in sys.path:
    sys.path.insert(0, str(_pkg_dir.parent))

from _addons_utils.reload import reload_addon
reload_addon(__name__)

import bpy

bl_info = {
    "name": "Microsoft Flight Simulator 2024: glTF Extension",
    "module_name": "io_scene_gltf2_msfs_2024",
    "author": "Asobo Studio (ykhodja and mrichecoeur)",
    "description": "Toolkit to export/import GLTF Models for Microsoft Flight Simulator 2024",
    "location": "View 3d Tools and Menus, Objects properties, Material properties and Light properties",
    "blender": (3, 3, 0),
    "version": (6, 4, 9),
    "category": "Import-Export",
    "doc_url": "https://docs.flightsimulator.com/msfs2024/html/3_Models_And_Textures/Plugins/Blender_Plugin/Blender_Plugin_Properties.htm"
}


class MSFS2024AddonPrefs(bpy.types.AddonPreferences):

    bl_idname = __name__

    make_relative_on_save: bpy.props.BoolProperty(
        name="Make Paths Relative On Save",
        description=(
            "Save external files (textures, linked libraries, etc.) with \n"
            "relative paths instead of absolute ones, so the .blend can \n"
            "be shared without missing file issues."
        ),
        default=True,
    )  # type: ignore

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "make_relative_on_save")

        # Remote repository & update info
        box = layout.box()
        box.label(text="Repositório Remoto & Atualizações (Blender 4.2+ / 5.x):", icon="URL")
        col = box.column(align=True)
        col.label(text="Para atualizações automáticas, adicione o link abaixo em:")
        col.label(text="Preferences > Get Extensions > Repositories > Add Remote Repository:")
        row = col.row()
        row.scale_y = 1.1
        row.label(text="https://grd-brasil.github.io/GRD_gltf2_msfs2024/", icon="WORLD")
        
        row_btn = box.row(align=True)
        op_gh = row_btn.operator("wm.url_open", text="GitHub Releases", icon="COMMUNITY")
        op_gh.url = "https://github.com/GRD-Brasil/GRD_gltf2_msfs2024/releases"
        op_repo = row_btn.operator("wm.url_open", text="Página da Extensão", icon="HELP")
        op_repo.url = "https://grd-brasil.github.io/GRD_gltf2_msfs2024/"

def get_addon_prefs():
    addon_name = __package__
    return bpy.context.preferences.addons[addon_name].preferences

def get_version_string():
    return str(bl_info['version'][0]) + '.' + str(bl_info['version'][1]) + '.' + str(bl_info['version'][2])

# endregion

# region ######################### REGISTRATION #################################
from _addons_utils.registration import Registration

RG = Registration(
    file=__file__,
    package=__package__
)

def register():
    try:
        bpy.utils.register_class(MSFS2024AddonPrefs)
    except:
        pass
    RG.register()

def unregister():
    try:
        bpy.utils.unregister_class(MSFS2024AddonPrefs)
    except:
        pass
    RG.unregister()

# endregion

# region ######################### IMPORT #################################
from .io.imp.msfs_import import Import
from .io.imp import msfs_import_panels

# region importer panel blender < 4.2

def register_panel():
    """
    Entry point for the glTF add-on (blender < 4.2) to register or unregister
    the importer panel.
    """
    try:
        bpy.utils.register_class(msfs_import_panels.MSFS2024_PT_importer_panel)
    except Exception:
        pass

    return unregister_panel

def unregister_panel():
    try:
        bpy.utils.unregister_class(msfs_import_panels.MSFS2024_PT_importer_panel)
    except Exception:
        pass

# endregion

# region importer panel blender >= 4.2
def draw_import(context: bpy.types.Context, layout: bpy.types.UILayout):
    """
    Draws the importer panel for the glTF add-on (Blender ≥ 4.2).
    """
    header, body = layout.panel("MSFS2024_PT_importer_panel", default_closed=False)
    header.use_property_split = False
    if header:
        msfs_import_panels.draw_importer_header(context, header)
    if body:
        msfs_import_panels.draw_importer_panel(context, body)
# enregion

class glTF2ImportUserExtension(Import):
    def __init__(self):
        super().__init__()

# endregion

# region ######################### EXPORT #################################
from .io.exp.gltf_hooks import Export

class glTF2ExportUserExtension(Export):
    def __init__(self):
        super().__init__()
# endregion
