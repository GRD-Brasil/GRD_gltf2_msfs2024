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

import uuid
import bpy
import addon_utils

from bpy.app.handlers import persistent

from _addons_utils import p4
from io_scene_gltf2_msfs_2024 import get_addon_prefs
from io_scene_gltf2_msfs_2024.datafiles import asset_library
from .utils import  msfs_mesh_utils
from ..io.exp.presets import (
    MultiExporterPreset,
    MultiExporterPresetGroup
)
from ..io.exp import presets, export_settings
from .msfs_lights import force_update_all_lights
from .utils.msfs_scene_utils import MSFS2024_SceneUtils
from ..io.com import msfs_path_utils
from ..io.com import msfs_logs

from . import msfs_gizmo

initial_objects = set()

@persistent
def new_object_handler(scene):
    """
    Add a default vertex color on new object or converted object (curve to mesh for example). 
    When there is no color attribute, shader vertex color node outputs
    a black color. Since there is no way to detect the presence of a color attribute 
    in shaders, we assign a default white color every time an object is created.
    """
    # Store obj and it's current type in a tuple
    current_objects = set()
    for obj in bpy.data.objects:
        current_objects.add((obj, obj.type))

    new_objects = current_objects - initial_objects

    for obj_def in new_objects:
        obj = obj_def[0]
        if obj.type == 'MESH':
            msfs_mesh_utils.add_default_vcolor(obj.data)

    initial_objects.clear()
    initial_objects.update(current_objects)

converting_old_gizmo = False
if bpy.app.version >= (4,5,0):

    @persistent  
    def blend_import_pre_handler(blend_import_context:bpy.types.BlendImportContext):
        """Prepare to replace old gizmo on scene append.
        """
        global converting_old_gizmo
        if converting_old_gizmo:
            return
        
        msfs_gizmo.register_old_gizmo_properties()

    @persistent  
    def blend_import_post_handler(blend_import_context:bpy.types.BlendImportContext):
        """Replace old gizmo after scene append.
        """
        global converting_old_gizmo
        if converting_old_gizmo:
            return
        #Prevent import handlers to be launched recursively
        #Can happen during collision gizmos creation
        converting_old_gizmo = True
        for scene in bpy.data.scenes:
            msfs_gizmo.replace_old_gizmos(scene)
        msfs_gizmo.unregister_old_gizmo_properties()
        converting_old_gizmo = False

@persistent
def load_pre_handler(filepath:str):
    # Prepare to replace old gizmo before scene opening
    msfs_gizmo.register_old_gizmo_properties()

# a scene that user opened, or created with save as
scene_opened_for_edit = "" 

@persistent
def load_post_handler(filepath:str):
    global scene_opened_for_edit
    if bpy.app.version < (3,6,0):
        filepath = bpy.path.abspath(bpy.data.filepath)
    scene_opened_for_edit = filepath

    # Prevent blend_import_pre_handler and  blend_import_post_handler handlers to be launched during scene loading
    # Can happen during collision gizmos creation
    global converting_old_gizmo
    converting_old_gizmo = True

    asset_library.update_appended_assets()

    addon_name = "io_scene_gltf2_msfs"
    (loaded_default, loaded_state) = addon_utils.check(addon_name)
    # Update material graph nodes if 2020 addon is not enabled
    if not loaded_default and not loaded_state:
        MSFS2024_SceneUtils.update_msfs2024_materials_graphs()

    force_update_all_lights()

    original_scene = bpy.context.scene
    for scene in bpy.data.scenes:
        # Gizmo retro compatibility

        msfs_gizmo.replace_old_gizmos(scene)
        # region Presets compatibility
        preset_list : list[MultiExporterPreset] = scene.msfs_multi_exporter_presets
        for preset in preset_list:        
            if preset.preset_name == "":
                preset.preset_name = preset.name
                preset.name = str(uuid.uuid4())

        MultiExporterPreset.update_presets_full_data_path(scene)
        MultiExporterPresetGroup.update_groups_full_data_path(scene)
        # endregion

        # region Object LODS compatibility
        lod_groups : list[MultiExporterPresetGroup] = scene.msfs_multi_exporter_lod_groups
        for lod_group in lod_groups:
            if lod_group.group_name != "":
                lod_group.name = lod_group.group_name
        # endregion

        # region Settings Presets
        settings_presets = scene.msfs_multi_exporter_settings_presets
        if len(settings_presets) <= 0:
            settings_preset = settings_presets.add()
            settings_preset.name = "Default"
            export_settings.MSFS2024_OT_AddSettingsPreset.apply_version_dependent_defaults(
                settings_preset
            )
        # Force exporter ui tree items generation
        bpy.context.window.scene = scene
        bpy.ops.msfs2024.reload_lod_groups()

        if bpy.context.window.scene != original_scene:
            bpy.context.window.scene = original_scene

        presets.PRESET_TREE_MANAGER.generate_ui_collection()

    msfs_gizmo.unregister_old_gizmo_properties()

    # Clear logs
    logger = msfs_logs.get_logger()
    logger.clear_logs()

    converting_old_gizmo = False

new_scene = False

@persistent
def on_save_pre(filepath:str):
    """
    Convert paths to be relative.
    """
    global scene_opened_for_edit
    global new_scene
    # We can't set relative path if scene is not saved
    # So return here in order to save again using save_post handler
    
    if not bpy.data.is_saved:
        # New scene
        new_scene = True
        return
    
    for scene in bpy.data.scenes:
        for lod_group in scene.msfs_multi_exporter_lod_groups:
            lod_group["folder_path"] = msfs_path_utils.get_relative_path_to_scene(
                lod_group.folder_path
            )

        for preset in scene.msfs_multi_exporter_presets:
            preset["folder_path"] = msfs_path_utils.get_relative_path_to_scene(
                preset.folder_path
            )

        for preset_group in scene.msfs_multi_exporter_preset_groups:
            preset_group["folder_path"] = msfs_path_utils.get_relative_path_to_scene(
                preset_group.folder_path
            )

    # Make other paths relative (image, scene link etc)
    addon_prefs = get_addon_prefs()
    if not addon_prefs:
        print("[MSFS2024][SAVE][ERROR] Addon prefs not found!")
    if addon_prefs and addon_prefs.make_relative_on_save:
        bpy.ops.file.make_paths_relative()

    new_scene = False

    if filepath and scene_opened_for_edit == filepath:
        if p4.use_p4():
            p4.p4_edit(filepath)
        scene_opened_for_edit = ""

@persistent
def on_save_post(filepath:str):
    """
    Save new scene again to convert paths to relative
    """
    global new_scene
    global scene_opened_for_edit

    scene_opened_for_edit = filepath
    if not new_scene:
        return
    try:
        bpy.ops.wm.save_mainfile()

    except:
        pass

def register():
    
    if on_save_pre not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(on_save_pre)
    if on_save_post not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(on_save_post)
    if bpy.app.version >= (4,5,0):
        if blend_import_pre_handler not in bpy.app.handlers.blend_import_pre:
            bpy.app.handlers.blend_import_pre.append(blend_import_pre_handler)
        if blend_import_post_handler not in bpy.app.handlers.blend_import_post:
            bpy.app.handlers.blend_import_post.append(blend_import_post_handler)
    if load_pre_handler not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(load_pre_handler) 
    if load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post_handler) 
    if new_object_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(new_object_handler)
    if new_object_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(new_object_handler)


def unregister():
    if on_save_pre in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(on_save_pre)
    if on_save_post in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(on_save_post)
    if bpy.app.version >= (4,5,0):
        if blend_import_pre_handler in bpy.app.handlers.blend_import_pre:
            bpy.app.handlers.blend_import_pre.remove(blend_import_pre_handler)
        if blend_import_post_handler in bpy.app.handlers.blend_import_post:
            bpy.app.handlers.blend_import_post.remove(blend_import_post_handler)
    if load_pre_handler in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(load_pre_handler) 
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)
    if new_object_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(new_object_handler)
    if new_object_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(new_object_handler)
