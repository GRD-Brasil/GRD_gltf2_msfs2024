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
from __future__ import annotations

import uuid
import os
import bpy

from typing import Any

from .  import multi_export
from . import  export_settings
from . import constants

from _addons_utils.ui.tree_widget.item import TreeItem
from _addons_utils.ui.tree_widget.manager import TreeManager
from _addons_utils.ui.tree_widget.view import UL_TreeView
from _addons_utils.ui.tree_widget.view_ope import  TREEVIEW_OT_ExpandAllItems

from ..com import msfs_path_utils
from ..com import msfs_logs

PRESET_TREE_MANAGER: PresetsTreeManager | None = None
PRESETS_TREE_MANAGER_UNIQUE_NAME: str = "PRESET_TREE_MANAGER"

LAYER_TREE_MANAGER_UNIQUE_NAME: str = "LAYER_TREE_MANAGER"

# region Static
def update_relative_path(self, context: bpy.types.Context):
    PRESET_TREE_MANAGER.update_prop_on_selected_data("folder_path", self)

def set_relative_path(preset: MultiExporterPreset, value: str):

    preset["folder_path"] = msfs_path_utils.get_relative_path_to_scene(value)

def get_relative_path(preset: MultiExporterPreset):
    return preset.get("folder_path", "")

def update_group_path(self, context: bpy.types.Context):
    PRESET_TREE_MANAGER.update_prop_on_selected_data("folder_path", self)

    presets = context.scene.msfs_multi_exporter_presets
    for preset in presets:
        if preset.group_id == self.name:
            # preset["folder_path"] does not trigger prop update function
            preset["folder_path"] = self.folder_path

def set_group_relative_path(group: MultiExporterPresetGroup, value:str):
 
    group["folder_path"] = msfs_path_utils.get_relative_path_to_scene(value)
    
    presets = bpy.context.scene.msfs_multi_exporter_presets
    for preset in presets:
        if preset.group_id == group.name:
            # preset["folder_path"] does not trigger prop update function
            preset["folder_path"] = group.folder_path

def get_group_relative_path(group: MultiExporterPresetGroup):
    return group.get("folder_path", "")

def update_group_presets_settings(self, context: bpy.types.Context):
    presets = context.scene.msfs_multi_exporter_presets
    settings_presets = context.scene.msfs_multi_exporter_settings_presets
    for preset in presets:
        if preset.group_id == self.name:
            # preset["settings_preset"] does not trigger prop update function
            preset["settings_preset"] = settings_presets.find(self.settings_preset)
    PRESET_TREE_MANAGER.update_prop_on_selected_data("settings_preset", self)


def update_checked_collection(
    self: MultiExporterPresetLayer, 
    context: bpy.types.Context
):
    preset = context.scene.msfs_multi_exporter_presets[self.preset_id]
    layers = preset.layers
    collection = self.collection
    if self.is_scene_collection:
        collection = context.scene.collection

    for col in collection.children_recursive:
        if col.name in layers:
            # layer["enabled"] does not trigger prop update function
            layers[col.name]["enabled"] = self.enabled

    MSFS2024_LayersUtils.update_parent_checked_collection_recursive(
        self.name,
        layers
    )


# endregion

# region Groups
class MultiExporterPresetGroup(bpy.types.PropertyGroup):
    ## name : guid of the Preset Group
    group_name: bpy.props.StringProperty(
        name="",
        default="",
        description="Name of the presets's group",
        update=TreeManager.make_update_callback(
            PRESETS_TREE_MANAGER_UNIQUE_NAME,
            "group_name"
        )
    )  # type: ignore

    folder_path: bpy.props.StringProperty(
        name="",
        default="",
        subtype="DIR_PATH",
        description="Path to the directory where you want the presets to be exported",
        update=update_group_path,
        set=set_group_relative_path,
        get=get_group_relative_path,
        options={"PATH_SUPPORTS_BLEND_RELATIVE"} if bpy.app.version >= (4,5,0) else set()
    )  # type: ignore

    enabled: bpy.props.BoolProperty(
        name="",
        default=False,
        description="Enable/Disable the group for the export",
    )  # type: ignore

    settings_preset: bpy.props.EnumProperty(
        name="Settings Preset", 
        items=export_settings.get_setting_presets_items, 
        update=update_group_presets_settings
    )  # type: ignore

    full_data_path: bpy.props.StringProperty(
        description="Use by Tree View for fast data access."
    )  # type: ignore

    def get_child_presets(self):
        all_presets = bpy.context.scene.msfs_multi_exporter_presets
        child_presets = []
        for preset in all_presets:
            if preset.group_id == self.name:
                child_presets.append(preset)
        return child_presets

    def update_full_data_path(self, scene: None | bpy.types.Scene = None):
        if scene is None:
            scene = bpy.context.scene
        preset_groups = scene.msfs_multi_exporter_preset_groups
        index = preset_groups.find(self.name)
        # Faster than repr() in order to get full data_path
        self.full_data_path = f"bpy.context.scene.msfs_multi_exporter_preset_groups[{index}]"

    @staticmethod
    def update_groups_full_data_path(scene: None | bpy.types.Scene = None):
        """More efficient than calling update_full_data_path multiple times 
        when updating all scene group presets.
        """
        if scene is None:
            scene = bpy.context.scene
        presets : list[MultiExporterPresetGroup]= scene.msfs_multi_exporter_preset_groups
        for i, group in enumerate(presets):
            group.full_data_path = f"bpy.context.scene.msfs_multi_exporter_preset_groups[{i}]"

class MSFS2024_OT_AddPresetGroup(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_add_preset_group"
    bl_label = "Add group"
    bl_options = {"INTERNAL"}
    def execute(self, context: bpy.types.Context):
        groups = context.scene.msfs_multi_exporter_preset_groups
        group : MultiExporterPresetGroup = groups.add()
        group.name = str(uuid.uuid4())
        group.group_name = f"Group.{len(groups)}"
        group.folder_path = ""
        group.update_full_data_path()
        PRESET_TREE_MANAGER.generate_ui_collection()
        PRESET_TREE_MANAGER.set_ui_tree_active_item_by_data(group, update_selection=True)
        return {"FINISHED"}

class MSFS2024_OT_RemovePresetGroup(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_remove_preset_group"
    bl_label = "Remove group"
    bl_description = "Remove the group from the group list"
    bl_options = {"INTERNAL"}

    group_id: bpy.props.StringProperty(default="")  # type: ignore

    def remove_preset_group(
        self,
        group_id: str,
        groups: bpy.types.bpy_prop_collection_idprop[MultiExporterPresetGroup],
        presets: bpy.types.bpy_prop_collection_idprop[MultiExporterPreset],
    ):
        for preset_id in presets.keys():
            idx = presets.find(preset_id)
            if presets[idx].group_id == group_id:
                presets.remove(idx)

        group_idx = groups.find(group_id)

        groups.remove(group_idx)

    def execute(self, context: bpy.types.Context):

        to_remove = set([self.group_id])
        # Also remove selected preset groups
        selected_items = PRESET_TREE_MANAGER.get_selected_items()
        for item in selected_items:
            data = item.get_data()
            if isinstance(data, MultiExporterPresetGroup):
                to_remove.add(data.name)

        groups = bpy.context.scene.msfs_multi_exporter_preset_groups
        presets = bpy.context.scene.msfs_multi_exporter_presets
        for id in to_remove:
            self.remove_preset_group(id, groups, presets)

        # Refresh full data path after a preset deletion
        MultiExporterPresetGroup.update_groups_full_data_path()
        MultiExporterPreset.update_presets_full_data_path()

        PRESET_TREE_MANAGER.generate_ui_collection()
        return {"FINISHED"}


class MSFS2024_OT_IsolateGroupPresetObjects(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_isolate_group_preset_object"
    bl_label = "Isolate group's object"
    bl_options = {"INTERNAL"}

    group_id: bpy.props.StringProperty(default="")  # type: ignore

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.mode == "OBJECT"

    def execute(self, context: bpy.types.Context):
        bpy.ops.object.hide_view_clear()
        bpy.ops.object.select_all(action='DESELECT')
        presets = context.scene.msfs_multi_exporter_presets
        for preset in presets:
            if preset.group_id == self.group_id:
                MSFS2024_OT_IsolatePresetObjects.select_preset_layers(preset)
        bpy.ops.object.hide_view_set(unselected=True)
        return {"FINISHED"}

class MSFS2024_OT_DuplicatePresetGroup(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_duplicate_preset_group"
    bl_label = "Duplicate group"
    bl_options = {"INTERNAL"}

    group_id: bpy.props.StringProperty(default="")  # type: ignore

    def execute(self, context: bpy.types.Context):
        groups = context.scene.msfs_multi_exporter_preset_groups

        active_group: MultiExporterPresetGroup = groups[self.group_id]
        duplicated_group: MultiExporterPreset = MSFS2024_PresetUtils.get_duplicated_preset_group(
            context,
            active_group
        )
        
        PRESET_TREE_MANAGER.generate_ui_collection()
        PRESET_TREE_MANAGER.set_ui_tree_active_item_by_data(duplicated_group, update_selection=True)
        return {"FINISHED"}

# endregion

# region Layers
class MultiExporterPresetLayer(bpy.types.PropertyGroup):
    collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection
    )  # type: ignore

    is_scene_collection: bpy.props.BoolProperty(
        name="is scene collection",
        description="True when layer represents a scene root collection",
        default=False,

    )  # type: ignore

    enabled: bpy.props.BoolProperty(
        name="Enabled",
        default=False,
        description="Enable/Disable the collection for the preset",
    )  # type: ignore

    full_data_path: bpy.props.StringProperty(
        description="Use by Tree View for fast data access."
    )  # type: ignore

    preset_id: bpy.props.StringProperty(default="")  # type: ignore

    def get_layer_objects(
        self,
    ) -> set[bpy.types.Object]:

        objects = set()
        if not self.collection:
            # Happen in background process
            # Scene collection reference is broken on scene reopening
            return objects
        
        try:
            objects = set(self.collection.objects)
        except RuntimeError:
            # deleted collection
            return objects
        
        return objects
    
class MSFS2024_LayersUtils:

    @staticmethod
    def get_collection_parents(
        collection: bpy.types.Collection, 
        parent_names: list | None = None
    ):
        """
        Returns a list of all parents for the given collection, ordered from
        the closest parent to the top-level parent.
        """
        if parent_names is None:
            parent_names = []
        for parent_collection in bpy.data.collections:
            if collection.name in parent_collection.children.keys():
                parent_names.append(parent_collection.name)
                MSFS2024_LayersUtils.get_collection_parents(parent_collection, parent_names)
                break
        return parent_names

    @staticmethod
    def load_layers(preset: MultiExporterPreset):
        _scene_collections: list = bpy.context.scene.collection.children_recursive
        _scene_collections.append(bpy.context.scene.collection)

        # Retrieve scene collections from bpy.data.collections instead of
        # scene.collection.children_recursive
        # This avoids the error:
        #      "RuntimeError: Error: RNA_property_pointer_set: cannot assign an embedded ID to an IDProperty"
        # which occurs when assigning layer.collection (PointerProperty).

        scene_collections = [col for col in bpy.data.collections if col in _scene_collections]

        # Store enabled layers
        enabled_layers = set()
        for layer in preset.layers:
            if layer.enabled:
                enabled_layers.add(layer.name)

        # Recreate all layers
        preset.layers.clear()
        for collection in scene_collections:

            layer = preset.layers.add()
            layer.name = collection.name
            layer.collection = collection
            layer.preset_id = preset.name
            layer.enabled = layer.name in enabled_layers

        preset.update_full_data_path(update_layers=True)

class MSFS2024_OT_EditLayers(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_edit_layers"
    bl_label = "Edit layers"
    bl_description = "Edit layers to be enabled or disabled for the preset"
    bl_options = {"INTERNAL"}

    preset_id: bpy.props.StringProperty(default="")  # type: ignore
    layers_tree_manager: LayerTreeManager | None = None

    def execute(self, context: bpy.types.Context):
        return {"FINISHED"}

    def __del__(self):
        try:
            self.layers_tree_manager.unregister()
        except:
            pass
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):

        # Register Layer Tree Manager
        global LAYER_TREE_MANAGER_UNIQUE_NAME
        self.layers_tree_manager = LayerTreeManager(
            unique_name=LAYER_TREE_MANAGER_UNIQUE_NAME,
            ul_tree_view_class=MSFS2024_UL_Layers,
            alphabetical_order=True,
            multiselection_support=True,
            checkable_items=True,
        )
        
        preset = context.scene.msfs_multi_exporter_presets[self.preset_id]
        MSFS2024_LayersUtils.load_layers(preset)

        # Generate Layers UI List
        context.scene.msfs_edited_preset_id = self.preset_id
        self.layers_tree_manager.generate_ui_collection()

        wm = context.window_manager
        return wm.invoke_popup(self, width=500)

    def draw(self, context: bpy.types.Context):
        # Title
        self.layout.label(text=self.bl_label)
        if bpy.app.version >= (4,2,0):
            self.layout.separator(type="LINE")
        else:
            self.layout.separator()
        row = self.layout.row()
        row.alignment = "RIGHT"
        TREEVIEW_OT_ExpandAllItems.draw_expand_all_buttons(
            row, 
            self.layers_tree_manager.unique_name
        )
        self.layers_tree_manager.draw(context, self.layout, rows=15)
# endregion

# region Settings
class MSFS2024_OT_EditPresetSettings(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_edit_preset_settings"
    bl_label = "Edit Preset Settings"
    bl_description = "Edit the preset settings used to export the model"
    bl_options = {"INTERNAL"}

    preset_id: bpy.props.StringProperty(default="") # type: ignore

    def execute(self, context: bpy.types.Context):
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        preset = context.scene.msfs_multi_exporter_presets[self.preset_id]
        layout.prop(preset, "settings_preset", text="Export Preset")

class MSFS2024_OT_EditGroupSettings(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_edit_group_settings"
    bl_label = "Edit Group Settings"
    bl_description = "Edit the preset settings used to export the group of models"
    bl_options = {"INTERNAL"}

    group_id: bpy.props.StringProperty(default="") # type: ignore

    def execute(self, context: bpy.types.Context):
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        group = context.scene.msfs_multi_exporter_preset_groups[self.group_id]
        layout.prop(group, "settings_preset", text="Export Preset")
# endregion

# region Presets
class MultiExporterPreset(bpy.types.PropertyGroup):
    ## name : guid of Preset
    preset_name: bpy.props.StringProperty(
        name="",
        default="",
        description="Name of the glTF to export",
        update= TreeManager.make_update_callback(
            PRESETS_TREE_MANAGER_UNIQUE_NAME,
            "preset_name"
        )
    )  # type: ignore

    folder_path: bpy.props.StringProperty(
        name="",
        default="",
        subtype="DIR_PATH",
        description="Path to the directory where you want your model to be exported",
        update=update_relative_path,
        set=set_relative_path,
        get=get_relative_path,
        options={"PATH_SUPPORTS_BLEND_RELATIVE"} if bpy.app.version >= (4,5,0) else set()
    )  # type: ignore

    enabled: bpy.props.BoolProperty(
        name="",
        default=False,
        description="Enable/Disable the preset for the export",
    )  # type: ignore

    layers: bpy.props.CollectionProperty(type=MultiExporterPresetLayer)  # type: ignore
    group_id: bpy.props.StringProperty(default="")  # type: ignore

    settings_preset: bpy.props.EnumProperty(
        name="Settings Preset",
        items=export_settings.get_setting_presets_items,
        update=TreeManager.make_update_callback(
            PRESETS_TREE_MANAGER_UNIQUE_NAME, 
            "settings_preset"
        ),
    )  # type: ignore

    full_data_path: bpy.props.StringProperty(
        description="Use by Tree View for fast data access."
    )  # type: ignore

    def get_preset_objects(self)->set[bpy.types.Object]:
        objects = set()
        for layer in self.layers:
            layer: MultiExporterPresetLayer
            if not layer.enabled:
                continue
            layer_objects = layer.get_layer_objects()
            if not layer_objects:
                continue
            objects.update(layer_objects)
        return objects

    def get_preset_collections(self)->list[bpy.types.Collection]:
        collections = []
        for layer in self.layers:
            if not layer.enabled:
                continue

            if layer.collection is None:
                continue
            try:
                layer.collection.objects
            except RuntimeError:
                # deleted collection
                continue
            collections.append(layer.collection)
        return collections

    def update_full_data_path(
        self, 
        scene: None | bpy.types.Scene = None, 
        update_layers: bool = False
    ):
        if scene is None:
            scene = bpy.context.scene
        presets = scene.msfs_multi_exporter_presets
        preset_index = presets.find(self.name)
        # Faster than repr() in order to get full data_path
        self.full_data_path = f"bpy.context.scene.msfs_multi_exporter_presets[{preset_index}]"
        if update_layers:

            for i, layer in enumerate(self.layers):

                layer.full_data_path =f"{self.full_data_path}.layers[{i}]"

    @staticmethod
    def update_presets_full_data_path(
        scene: None | bpy.types.Scene = None, 
        update_layers: bool = False
    ):
        """More efficient than calling update_full_data_path multiple times 
        when updating all scene presets.
        """
        if scene is None:
            scene = bpy.context.scene
        presets : list[MultiExporterPreset]= scene.msfs_multi_exporter_presets
        for i, preset in enumerate(presets):
            preset.full_data_path = f"bpy.context.scene.msfs_multi_exporter_presets[{i}]"
            if update_layers:
                return
            for i, layer in enumerate(preset.layers):
                layer.full_data_path =f"{preset.full_data_path}.layers[{i}]"


# region Preset Operators
class MSFS2024_OT_AddPreset(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_add_preset"
    bl_label = "Add preset"
    bl_options = {"INTERNAL"}

    group_id: bpy.props.StringProperty(default="")  # type: ignore

    def execute(self, context: bpy.types.Context) -> set[str]:
        presets = context.scene.msfs_multi_exporter_presets
        groups = context.scene.msfs_multi_exporter_preset_groups
        
        preset: MultiExporterPreset = presets.add()
        preset.name = str(uuid.uuid4())
        preset.preset_name = f"Preset.{len(presets)}"
        
        folder_path = ""
        if self.group_id != "":
            group: MultiExporterPresetGroup = groups[self.group_id]
            folder_path = group.folder_path
            
        preset.folder_path = folder_path
        preset.group_id = self.group_id
        preset.update_full_data_path()

        MSFS2024_LayersUtils.load_layers(preset)

        PRESET_TREE_MANAGER.generate_ui_collection()
        PRESET_TREE_MANAGER.set_ui_tree_active_item_by_data(preset, update_selection=True)
        return {"FINISHED"}

class MSFS2024_OT_RemovePreset(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_remove_preset"
    bl_label = "Remove preset"
    bl_description = "Remove the preset from the preset list"
    bl_options = {"INTERNAL"}

    preset_id: bpy.props.StringProperty(default="")  # type: ignore

    def remove_preset(
        self,
        preset_id: str,
        presets: bpy.types.bpy_prop_collection_idprop[MultiExporterPreset],
    ):
        idx = presets.find(preset_id)
        presets.remove(idx)

    def execute(self, context: bpy.types.Context):
        presets = context.scene.msfs_multi_exporter_presets
        to_remove = set([self.preset_id])
        # Also remove selected presets
        selected_items = PRESET_TREE_MANAGER.get_selected_items()
        for item in selected_items:
            data = item.get_data()
            if isinstance(data, MultiExporterPreset):
                to_remove.add(data.name)

        presets = bpy.context.scene.msfs_multi_exporter_presets
        for id in to_remove:
            self.remove_preset(id, presets)

        # Refresh full data path after a preset deletion
        MultiExporterPreset.update_presets_full_data_path()

        PRESET_TREE_MANAGER.generate_ui_collection()
        return {"FINISHED"}

class MSFS2024_OT_IsolatePresetObjects(bpy.types.Operator):
    bl_idname = "msfs2024.multi_isolate_preset_object"
    bl_label = "Isolate preset's object"
    bl_options = {"INTERNAL"}

    preset_id: bpy.props.StringProperty(default="")  # type: ignore

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.mode == "OBJECT"

    @staticmethod
    def select_preset_layers(preset: MultiExporterPreset):
        objects = preset.get_preset_objects()
        for obj in objects:
            obj.select_set(True)

    def execute(self, context: bpy.types.Context):
        preset = context.scene.msfs_multi_exporter_presets[self.preset_id]
        bpy.ops.object.hide_view_clear()
        bpy.ops.object.select_all(action='DESELECT')
        MSFS2024_OT_IsolatePresetObjects.select_preset_layers(preset)
        bpy.ops.object.hide_view_set(unselected=True)
        return {"FINISHED"}

class MSFS2024_OT_RenamePreset(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_rename_preset"
    bl_label = "Rename"
    bl_description = "Rename Preset"
    bl_options = {"INTERNAL"}

    group_id: bpy.props.StringProperty(default="")  # type: ignore

    preset_id: bpy.props.StringProperty(default="")  # type: ignore

    new_name: bpy.props.StringProperty(name="New Name", default="")  # type: ignore

    def execute(self, context: bpy.types.Context):
        if not self.new_name.strip():
            self.report({"WARNING"}, "Invalid Name")
            return {"CANCELLED"}
        if self.group_id:
            self.group.group_name = self.new_name
        elif self.preset_id:
            self.preset.preset_name = self.new_name
        PRESET_TREE_MANAGER.generate_ui_collection()
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        if self.group_id:
            groups = context.scene.msfs_multi_exporter_preset_groups

            self.group = groups.get(self.group_id, None)
            if not self.group:
                return {"CANCELLED"}
            self.group: MultiExporterPresetGroup
            self.new_name = self.group.group_name
        elif self.preset_id:
            presets = context.scene.msfs_multi_exporter_presets
            self.preset = presets.get(self.preset_id, None)
            if not self.preset:
                return {"CANCELLED"}
            self.preset: MultiExporterPreset
            self.new_name = self.preset.preset_name

        else:
            return {"CANCELLED"}

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.prop(self, "new_name", text="")

class MSFS2024_OT_DuplicatePreset(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_duplicate_preset"
    bl_label = "Duplicate preset"
    bl_options = {"INTERNAL"}

    preset_id: bpy.props.StringProperty(default="")  # type: ignore
    
    def execute(self, context: bpy.types.Context) -> set[str]:
        active_preset: MultiExporterPreset = context.scene.msfs_multi_exporter_presets[self.preset_id]
        preset: MultiExporterPreset = MSFS2024_PresetUtils.get_duplicated_preset(
            context,
            active_preset
        )
        
        PRESET_TREE_MANAGER.generate_ui_collection()
        PRESET_TREE_MANAGER.set_ui_tree_active_item_by_data(preset, update_selection=True)
        return {"FINISHED"}

class MSFS2024_PresetUtils:
    @staticmethod
    def get_duplicate_name(name: str, nbr_elem: int):
        split_name = name.split('.')
        last_split_elem = len(split_name) - 1
        suffix = split_name[last_split_elem]
        
        if suffix.isdigit():
            new_suffix = '.' + str(nbr_elem)
            split_name[last_split_elem] = new_suffix
        else:
            split_name.append('.0')
            
        return ''.join(split_name)
    
    @staticmethod 
    def get_duplicated_preset_group(context: bpy.types.Context, group: MultiExporterPresetGroup):
        presets = context.scene.msfs_multi_exporter_presets
        groups = context.scene.msfs_multi_exporter_preset_groups
        
        duplicated_group: MultiExporterPresetGroup = groups.add()
        duplicated_group.name = str(uuid.uuid4())
        
        active_group_name = group.group_name
        group_prefixes = [group.group_name.split('.')[0] for group in groups]
        duplicated_group.group_name = MSFS2024_PresetUtils.get_duplicate_name(
            active_group_name,
            len(group_prefixes)
        )
        
        duplicated_group.folder_path = group.folder_path
        duplicated_group.settings_preset = group.settings_preset
        
        for preset in presets.values():
            if preset.group_id == group.name:
                MSFS2024_PresetUtils.get_duplicated_preset(
                    context,
                    preset,
                    duplicated_group.name
                )
        
        return duplicated_group
    
    @staticmethod
    def get_duplicated_preset(context: bpy.types.Contex, preset: MultiExporterPreset, group_id: str|None =None):
        presets = context.scene.msfs_multi_exporter_presets
        duplicated_preset: MultiExporterPreset = presets.add()
        duplicated_preset.name = str(uuid.uuid4())
        
        active_preset_name = preset.preset_name
        preset_prefixes = [preset.preset_name.split('.')[0] for preset in presets]
        duplicated_preset.preset_name = MSFS2024_PresetUtils.get_duplicate_name(
            active_preset_name,
            len(preset_prefixes)
        )
        
        duplicated_preset.folder_path = preset.folder_path
        duplicated_preset.group_id = preset.group_id if group_id is None else group_id
        duplicated_preset.settings_preset = preset.settings_preset
        
        # We need to load layer and to enable the same from the preset
        # layers are readonly we can't just copy the list
        MSFS2024_LayersUtils.load_layers(duplicated_preset)
        for layer in duplicated_preset.layers:
            if layer.name not in preset.layers:
                continue
            layer.enabled = preset.layers[layer.name].enabled
            
        return duplicated_preset
# endregion

# endregion

# region UI Layer TreeView
class LayerTreeManager(TreeManager):

    # Inherited Functions
    def get_data_collection(self) -> list[MultiExporterPresetLayer]:
        
        preset_id :int= bpy.context.scene.msfs_edited_preset_id
        preset: MultiExporterPreset = bpy.context.scene.msfs_multi_exporter_presets[preset_id]
        if not preset:
            return []

        # Find root scene_layer
        scene_layer = None
        index = 0
        for i, layer in enumerate(preset.layers):
            if not layer.is_scene_collection:
                continue
            scene_layer = layer
            index = i
            break
        
        # Create root scene_layer if it doesnt exist
        if not scene_layer:
            scene_layer: MultiExporterPresetLayer = preset.layers.add()
            index = len(preset.layers) - 1

        scene_layer.preset_id = preset.name
        scene_layer.name = "Scene Collection"
        scene_layer.is_scene_collection = True

        scene_layer.full_data_path = preset.full_data_path + f".layers[{index}]"
    

        preset_data_path = getattr(preset,"full_data_path",None)
        if not preset_data_path:
            preset.update_full_data_path()

        return [scene_layer]

  
    def get_expanded_items(self) -> set[str]:
        """
        Get list of items name that should be expanded in ui tree
        """
        preset_id = bpy.context.scene.msfs_edited_preset_id
        preset = bpy.context.scene.msfs_multi_exporter_presets[preset_id]
        if not preset:
            return {}

        expanded_layers = {"Scene Collection"}

        for layer in preset.layers:
            if layer.enabled and layer.collection:
                expanded_layers.add(layer.name)
                # We need to add the parent of enabled layers to expand them to get to their children
                parent_names = MSFS2024_LayersUtils.get_collection_parents(layer.collection)
                expanded_layers.update(set(parent_names))

        return expanded_layers

   
    def get_data_children(
        self, data: bpy.types.bpy_struct
    ) -> list[bpy.types.bpy_struct]:

        if isinstance(data, MultiExporterPresetLayer):
            data: MultiExporterPresetLayer
            layer = data
            child_layers = []
            preset_id = bpy.context.scene.msfs_edited_preset_id
            preset = bpy.context.scene.msfs_multi_exporter_presets[preset_id]

            collection = layer.collection
            if layer.is_scene_collection:
                collection = bpy.context.scene.collection

            if not collection:
                return child_layers

            if not collection.children:
                return child_layers

            for col in collection.children:
                for _layer in preset.layers:
                    if not _layer.collection:
                        continue
                    if _layer.collection != col:
                        continue

                    child_layers.append(_layer)
                    break

            return child_layers

        return []


    def on_data_checked(self, checked: bool, data: Any):
        if isinstance(data, MultiExporterPresetLayer):
            layer: MultiExporterPresetLayer = data
            layer.enabled = checked


    def is_data_checked(self, data: Any)->bool:
        if isinstance(data, MultiExporterPresetLayer):
            layer: MultiExporterPresetLayer = data
            return layer.enabled
        return False

class MSFS2024_UL_Layers(bpy.types.UIList, UL_TreeView):

    use_filter_invert: bpy.props.BoolProperty(
        name="Filter Invert", 
        default=False,
        options=set()
    )  # type: ignore

    parents_of_filtered_items: bpy.props.BoolProperty(
        name="Show Parents Of Filtered Items",
        description=("Show parents of filtered items.\n"
                     "When disabled, child items can be shown individually") ,
        default=True,
        options=set()
    )  # type: ignore

    check_only: bpy.props.BoolProperty(
        name="Checked",
        description="Show checked items only",
        default=False,
        update=lambda self, ctx: self._sync_state("check")
    ) # type: ignore

    uncheck_only: bpy.props.BoolProperty(
        name="Unchecked",
        description="Show unchecked items only",
        default=False,
        update=lambda self, ctx: self._sync_state("uncheck")
    ) # type: ignore

    def _sync_state(self, source):
        # Prevent recursion
        if source == "check":
            self["uncheck_only"] = False
        elif source == "uncheck" :
            self["check_only"] = False

    # Hack using a boolproperty to reset filters
    # We can't create an operator that could reset filters since
    # we have no acess to UI_List instance.
    reset_filters: bpy.props.BoolProperty(
        name="Reset",
        description="Reset Filters",
        default=False,
        update=lambda self, ctx: self.on_reset_filters(ctx),
        options={"HIDDEN", "SKIP_SAVE"},
    )  # type: ignore

    def on_reset_filters(self, context):
        self.use_filter_invert = False
        self.parents_of_filtered_items = True
        self.check_only = False
        self.uncheck_only = False
        # Make button appears unchecked
        self["reset_filters"] = False

    # Inherited Methods

    def custom_draw_item(self,
        context: bpy.types.Context,
        index: int,
        item: TreeItem,
        layout: bpy.types.UILayout
    ):

        item: TreeItem
        data = item.get_data()
        if not data:
            return
        if isinstance(data, MultiExporterPresetLayer):
            self.draw_preset_layer(data, item, index, layout)

    def draw_preset_layer(
        self,
        preset_layer: MultiExporterPresetLayer,
        item: TreeItem,
        index: int,
        row: bpy.types.UILayout,
    ):
        collection = preset_layer.collection
        if collection:
            row.label(text=preset_layer.collection.name)
        else:
            # Scene collection case
            row.label(text=preset_layer.name)

    def draw_filter(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        row = layout.row(align=True)
        row.prop(self, "filter_name", text="", icon="VIEWZOOM")
        row.prop(
            self, "use_filter_invert", text="", icon="ARROW_LEFTRIGHT", icon_only=True
        )
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Filters:")
        row.prop(
            self, "reset_filters", icon="RECOVER_LAST", toggle=True, icon_only=True
        )
        row = box.row(align=True)
        row.prop(self, "check_only", icon="CHECKBOX_HLT", toggle=True)
        row.prop(self, "uncheck_only", icon="CHECKBOX_DEHLT", toggle=True)
        col = box.column(align=True)
        if bpy.app.version < (4, 2, 0):
            col.separator()
        else:
            col.separator(type="LINE")
        col.prop(self, "parents_of_filtered_items")

    def filter_items(self, context: bpy.types.Context, data: Any|None, propname: str):
        """
        This function gets the collection property (as the usual tuple (data, propname)), and must return two lists:
        * The first one is for filtering, it must contain 32bit integers were self.bitflag_filter_item marks the
          matching item as filtered (i.e. to be shown). The upper 16 bits (including self.bitflag_filter_item) are
          reserved for internal use, the lower 16 bits are free for custom use.
        * The second one is for reordering, it must return a list containing the new indices of the items (which
          gives us a mapping org_idx -> new_idx).

        Please note that the default UI_UL_list defines helper functions for common tasks (see its doc for more info).
        If you do not make filtering and/or ordering, return empty list(s) (this will be more efficient than
        returning full lists doing nothing!).

        """
        flt_flags, flt_neworder = super().filter_items(context, data, propname)

        ui_tree = getattr(data, propname)
        helper_funcs = bpy.types.UI_UL_list

        # Filtering by name
        if self.filter_name:
            flt_flags = helper_funcs.filter_items_by_name(
                self.filter_name,
                self.bitflag_filter_item,
                ui_tree,
                "name",
                reverse=self.use_filter_invert
            )
        if not flt_flags:
            flt_flags = [self.bitflag_filter_item] * len(ui_tree)

        msfs_layers_ui_tree :list[TreeItem]= getattr(data, propname)
        for i, item in enumerate(msfs_layers_ui_tree):
            if self.check_only and not item.checked:
                flt_flags[i] &= ~self.bitflag_filter_item
            elif self.uncheck_only and item.checked:
                flt_flags[i] &= ~self.bitflag_filter_item

        if self.parents_of_filtered_items:
            self.show_parents_of_filtered_items(ui_tree, flt_flags)
        return flt_flags, flt_neworder

# endregion

# region UI Presets TreeView
def _on_selection(tree_manager: TreeManager, context: bpy.types.Context):
    """
    This function is used by PRESET_TREE_MANAGERand is called 
    when list active index changed.

    It has two roles:
    - Update items selection in UIList.

    - Select objects in 3d scene when msfs_ui_tree_presets_sync_selection 
    is enabled :
        Select all layers objects of a preset.
        Select all layers objects of for each layer of a preset group.
    """

    if not context.scene.msfs_ui_tree_presets_sync_selection:
        return
    #Deselect 
    for obj in context.view_layer.objects:
        obj.select_set(False)

    selected_items = tree_manager.get_selected_items()

    for item in selected_items:
    
        
        item: TreeItem
        data = item.get_data()
        presets = []
        if isinstance(data, MultiExporterPresetGroup):
            presets = data.get_child_presets()
        elif isinstance(data, MultiExporterPreset):
            # item is a lod group
            presets = [data]
        else:
            continue

        

        for preset in presets:
            objects = preset.get_preset_objects()
            for obj in objects:
                obj.select_set(True)
                context.view_layer.objects.active = obj

class PresetsTreeManager(TreeManager):
    # region Manager settings
    ALPHABETICAL_ORDER = True
    MULTISELECTION_SUPPORT = True
    CHECKABLE_ITEMS = True
    # endregion

    @classmethod
    def get_data_collection(cls) -> list[MultiExporterPreset|MultiExporterPresetGroup]:
        data_list = []
        for data in bpy.context.scene.msfs_multi_exporter_presets:
            data: MultiExporterPreset
            if not data.group_id:
                data_list.append(data)
        for data in bpy.context.scene.msfs_multi_exporter_preset_groups:
            data_list.append(data)
        return data_list

    @classmethod
    def get_data_name(cls, data: bpy.types.bpy_struct) -> str:
        """
        Get data name for alphabetical ordering
        """
        if isinstance(data, MultiExporterPresetGroup):
            return data.group_name
        elif isinstance(data, MultiExporterPreset):
            return data.preset_name

    @classmethod
    def get_data_children(
        cls,
        data: bpy.types.bpy_struct
    ) -> list[bpy.types.bpy_struct]:
        if isinstance(data, MultiExporterPresetGroup):
            return data.get_child_presets()

        return []

    @classmethod
    def set_ui_tree_item_name(cls, item: TreeItem, data: bpy.types.bpy_struct):
        """
        Set UITreeItem name according to data.
        Item name will drive list order (Alphabetically ordered) and
         is used by filters functions.
        """
        if isinstance(data, MultiExporterPresetGroup):
            data: MultiExporterPresetGroup
            item.name = data.group_name
        elif isinstance(data, MultiExporterPreset):
            data: MultiExporterPreset
            # Add preset group name suffix when avaialable
            # Usefull for filtering groups
            parent_data: MultiExporterPresetGroup
            parent_data = item.get_parent_data()
            item.name = ""
            if parent_data:
                item.name = parent_data.group_name

            item.name += data.preset_name

    @classmethod
    def on_data_checked(cls, checked: bool, data: Any):
        if isinstance(data, MultiExporterPresetGroup):
            preset_group: MultiExporterPresetGroup = data
            preset_group.enabled = checked

        elif isinstance(data, MultiExporterPreset):
            preset: MultiExporterPreset = data
            preset.enabled = checked

    @classmethod
    def is_data_checked(cls, data: Any)->bool:
        if isinstance(data, MultiExporterPresetGroup):
            preset_group: MultiExporterPresetGroup = data
            return preset_group.enabled

        elif isinstance(data, MultiExporterPreset):
            preset: MultiExporterPreset = data
            return preset.enabled
        return False

    def draw_context_menu(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        super().draw_context_menu(context, layout)
        layout.separator()
        export_selected_ope = layout.operator(
            multi_export.MSFS2024_OT_ExportSelectedItems.bl_idname,
            text="Export Selected",
            icon="EXPORT",
        )
        export_selected_ope.export_mode = constants.ExportModes.PRESETS.identifier


class MSFS2024_UL_Presets(bpy.types.UIList, UL_TreeView):

    use_filter_invert: bpy.props.BoolProperty(
        name="Filter Invert", default=False, options=set()
    )  # type: ignore

    parents_of_filtered_items: bpy.props.BoolProperty(
        name="Show Parents Of Filtered Items",
        description=("Show parents of filtered items.\n"
                     "When disabled, child items can be shown individually") ,
        default=True,
        options=set()
    )  # type: ignore

    check_only: bpy.props.BoolProperty(
        name="Checked",
        description="Show checked items only",
        default=False,
        update=lambda self, ctx: self._sync_state("check")
    ) # type: ignore

    uncheck_only: bpy.props.BoolProperty(
        name="Unchecked",
        description="Show unchecked items only",
        default=False,
        update=lambda self, ctx: self._sync_state("uncheck")
    ) # type: ignore

    def _sync_state(self, source):
        # Prevent recursion
        if source == "check":
            self["uncheck_only"] = False
        elif source == "uncheck" :
            self["check_only"] = False

    # Hack using a boolproperty to reset filters
    # We can't create an operator that could reset filters since
    # we have no acess to UI_List instance.
    reset_filters: bpy.props.BoolProperty(
        name="Reset",
        description="Reset Filters",
        default=False,
        update=lambda self, ctx: self.on_reset_filters(ctx),
        options={"HIDDEN", "SKIP_SAVE"},
    )  # type: ignore

    def on_reset_filters(self, context):
        self.use_filter_invert = False
        self.parents_of_filtered_items = True
        self.check_only = False
        self.uncheck_only = False
        # Make button appears unchecked
        self["reset_filters"] = False

    def custom_draw_item(self,
        context: bpy.types.Context,
        index: int,
        item: TreeItem,
        layout: bpy.types.UILayout
    ):
        item: TreeItem
        data = item.get_data()
        if not data:
            return
        row = layout.row(align=True)
        if isinstance(data, MultiExporterPresetGroup):
            preset_group: MultiExporterPresetGroup = data
            self.draw_preset_group(preset_group, item, index, row)

        elif isinstance(data, MultiExporterPreset):
            preset: MultiExporterPreset = data
            self.draw_preset(preset, item, index, row)
        else:
            row.label(text="Not Implemented")

    def draw_preset(self, preset: MultiExporterPreset, item: TreeItem, index:int , row: bpy.types.UILayout):
        item: TreeItem
        row.label(text=preset.preset_name)
        ope = row.operator(
            MSFS2024_OT_RenamePreset.bl_idname,
            text="",
            icon="GREASEPENCIL",
            emboss=False
        )
        ope.preset_id = preset.name
        ope.group_id = ""
        if bpy.app.version > (4, 0, 0):
            row.prop(preset, "folder_path", text="", placeholder="Export Folder")
        else:
            row.prop(preset, "folder_path", text="")
        row.operator(MSFS2024_OT_IsolatePresetObjects.bl_idname, text="", icon="HIDE_OFF").preset_id = preset.name
        row.operator(MSFS2024_OT_EditLayers.bl_idname, text="", icon="COLLECTION_NEW").preset_id = preset.name
        row.operator(MSFS2024_OT_DuplicatePreset.bl_idname, text="", icon="DUPLICATE").preset_id = preset.name
        row.operator(MSFS2024_OT_RemovePreset.bl_idname, text="", icon="REMOVE").preset_id = preset.name

    def draw_preset_group(
        self,
        preset_group: MultiExporterPresetGroup,
        item: TreeItem,
        index: int,
        row: bpy.types.UILayout,
    ):

        row.label(text=preset_group.group_name)
        ope = row.operator(
            MSFS2024_OT_RenamePreset.bl_idname,
            text="",
            icon="GREASEPENCIL",
            emboss=False,
        )
        ope.group_id = preset_group.name
        ope.preset_id = ""

        if bpy.app.version > (4, 0, 0):
            row.prop(preset_group, "folder_path", text="", placeholder="Export Folder")
        else:
            row.prop(preset_group, "folder_path", text="")

        row.operator(MSFS2024_OT_IsolateGroupPresetObjects.bl_idname, text="", icon="HIDE_OFF").group_id = preset_group.name
        row.operator(MSFS2024_OT_AddPreset.bl_idname, text="", icon="ADD").group_id = preset_group.name
        row.operator(MSFS2024_OT_DuplicatePresetGroup.bl_idname, text="", icon="DUPLICATE").group_id = preset_group.name
        row.operator(MSFS2024_OT_RemovePresetGroup.bl_idname, text="", icon="REMOVE").group_id = preset_group.name

    def draw_filter(self, context: bpy.types.Context, layout: bpy.types.UILayout):

        row = layout.row(align=True)
        row.prop(self, "filter_name", text="", icon="VIEWZOOM")
        row.prop(self, "use_filter_invert", text="", icon="ARROW_LEFTRIGHT", icon_only=True)

        box = layout.box()
        row = box.row()
        row.label(text="Filters:")
        row.prop(
            self, "reset_filters", icon="RECOVER_LAST", toggle=True, icon_only=True
        )
        row = box.row(align=True)
        row.prop(self, "check_only", icon="CHECKBOX_HLT", toggle=True)
        row.prop(self, "uncheck_only", icon="CHECKBOX_DEHLT", toggle=True)

        col = box.column(align=True)
        if bpy.app.version < (4, 2, 0):
            col.separator()
        else:
            col.separator(type="LINE")

        col = box.column(align=False)
        col.prop(self, "parents_of_filtered_items")

    def filter_items(self, context: bpy.types.Context, data: Any|None, propname: str):
        """
        This function gets the collection property (as the usual tuple (data, propname)), and must return two lists:
        * The first one is for filtering, it must contain 32bit integers were self.bitflag_filter_item marks the
          matching item as filtered (i.e. to be shown). The upper 16 bits (including self.bitflag_filter_item) are
          reserved for internal use, the lower 16 bits are free for custom use.
        * The second one is for reordering, it must return a list containing the new indices of the items (which
          gives us a mapping org_idx -> new_idx).

        Please note that the default UI_UL_list defines helper functions for common tasks (see its doc for more info).
        If you do not make filtering and/or ordering, return empty list(s) (this will be more efficient than
        returning full lists doing nothing!).

        """
        flt_flags, flt_neworder = super().filter_items(context, data, propname)

        ui_tree = getattr(data, propname)
        if not flt_flags:
            flt_flags = [self.bitflag_filter_item] * len(ui_tree)

        data_tree = [item.get_data() for item in ui_tree]

        # Filtering by group name and preset name
        # Directly use name from data to support live renaming of preset and group,
        # without having to regenerate ui items.
        if self.filter_name:
            for i, _data in enumerate(data_tree):
                preset_name = getattr(_data, "preset_name", None)
                group_name = getattr(_data, "group_name", None)

                name = preset_name if not group_name else group_name

                if name is not None:
                    name = name.lower()
                    if self.use_filter_invert:
                        if self.filter_name.lower() in name:
                            flt_flags[i] &= ~self.bitflag_filter_item
                    else:
                        if not self.filter_name.lower() in name:
                            flt_flags[i] &= ~self.bitflag_filter_item

        msfs_presets_ui_tree: list[TreeItem] = getattr(data, propname)
        for i, item in enumerate(msfs_presets_ui_tree):
            if self.check_only and not item.checked:
                flt_flags[i] &= ~self.bitflag_filter_item
            elif self.uncheck_only and item.checked:
                flt_flags[i] &= ~self.bitflag_filter_item

        if self.parents_of_filtered_items:
            self.show_parents_of_filtered_items(ui_tree, flt_flags)

        self.save_flags_in_tree_manager(flt_flags)

        return flt_flags, flt_neworder

# enregion

# region Panel
class MSFS2024_PT_MultiExporterPresetsView(bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Multi-Export glTF 2.0"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return (
            context.scene.msfs_multi_exporter_current_tab
            == constants.Tabs.PRESETS.identifier
        )

    def draw_active_preset_settings(self, context: bpy.types.Context, preset: MultiExporterPreset, layout: bpy.types.UILayout):
        box = layout.box()
        box.label(text="Preset Settings:")
        row = box.row()
        row.prop(preset, "preset_name",text="Name")

        if bpy.app.version > (4, 0, 0):
            box.prop(preset, "folder_path", text="Export Path", placeholder="Export Folder")
        else:
            box.prop(preset, "folder_path", text="Export Path")
        box.prop(preset, "settings_preset", text="Export Preset")

    def draw_active_preset_group_settings(
        self,
        context: bpy.types.Context,
        preset_group: MultiExporterPresetGroup,
        layout: bpy.types.UILayout,
    ):
        box = layout.box()
        box.label(text="Preset Group Settings:")
        box.prop(preset_group, "group_name",text="Name")
        if bpy.app.version > (4, 0, 0):
            box.prop(preset_group, "folder_path", text="Export Path", placeholder="Export Folder")
        else:
            box.prop(preset_group, "folder_path", text="Export Path")
        box.prop(preset_group, "settings_preset", text="Export Preset")

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        row = layout.row()
        row.operator(MSFS2024_OT_AddPreset.bl_idname, text="Add Preset").group_id = ""
        row.operator(MSFS2024_OT_AddPresetGroup.bl_idname, text="Add Group")
        row = layout.row()
        row.prop(context.scene,"msfs_ui_tree_presets_sync_selection",text="Sync Selection")
        TREEVIEW_OT_ExpandAllItems.draw_expand_all_buttons(
            row, 
            PRESET_TREE_MANAGER.unique_name
        )
        PRESET_TREE_MANAGER.draw(context, layout, rows=4)
        active_item = PRESET_TREE_MANAGER.get_active_item()
        if active_item:
            active_data = active_item.get_data()
            if isinstance(active_data,MultiExporterPreset):
                self.draw_active_preset_settings(context,active_data,layout)
            elif isinstance(active_data,MultiExporterPresetGroup):
                self.draw_active_preset_group_settings(context,active_data,layout)

        multi_export.draw_export_button(context, layout, constants.ExportModes.PRESETS)

class MSFS2024_PT_PresetsLogs(bpy.types.Panel):
    bl_label = "Logs"
    bl_parent_id = "MSFS2024_PT_MultiExporterPresetsView"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Multi-Export glTF 2.0"

    register_order = 1
    
    def draw(self, context: bpy.types.Context):
        layout = self.layout
        msfs_logs.get_logger().tree_manager.draw(context, layout, 5)

    def draw_header_preset(self, context: bpy.types.Context) -> None:
        logger = msfs_logs.get_logger()
        logger.tree_manager.draw_header_preset(context, self.layout, logger)
# endregion

def register():
    bpy.types.Scene.msfs_multi_exporter_presets = bpy.props.CollectionProperty(type=MultiExporterPreset) # type: ignore
    bpy.types.Scene.msfs_multi_exporter_preset_groups = bpy.props.CollectionProperty(type=MultiExporterPresetGroup) # type: ignore
    global PRESET_TREE_MANAGER
    global PRESETS_TREE_MANAGER_UNIQUE_NAME
    PRESET_TREE_MANAGER = PresetsTreeManager(
        unique_name=PRESETS_TREE_MANAGER_UNIQUE_NAME,
        ul_tree_view_class=MSFS2024_UL_Presets,
        on_selection_function=_on_selection,
        alphabetical_order=True,
        multiselection_support=True,
        checkable_items=True,
    )

    bpy.types.Scene.msfs_ui_tree_presets_sync_selection = bpy.props.BoolProperty( # type: ignore
        default=False,
        description="Select corresponding scene objects when an item is selected in exporter hierarchy",
    )
    

    bpy.types.Scene.msfs_edited_preset_id = bpy.props.StringProperty( options={"SKIP_SAVE"}) # type: ignore

def unregister():
    try:
        global PRESET_TREE_MANAGER
        del bpy.types.Scene.msfs_multi_exporter_presets  # type: ignore
        del bpy.types.Scene.msfs_multi_exporter_preset_groups  # type: ignore
        PRESET_TREE_MANAGER.unregister()  # type: ignore
        del bpy.types.Scene.msfs_ui_tree_presets_sync_selection  # type: ignore

    except:
        pass
