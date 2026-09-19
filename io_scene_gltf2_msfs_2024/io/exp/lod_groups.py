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
from typing import Any

import re

import bpy

from _addons_utils.ui.tree_widget.item import TreeItem
from _addons_utils.ui.tree_widget.manager import TreeManager
from _addons_utils.ui.tree_widget.view import UL_TreeView
from _addons_utils.ui.tree_widget.view_ope import  TREEVIEW_OT_ExpandAllItems

from .  import multi_export
from .export_settings import get_setting_presets_items
from . import constants

from ..com import msfs_path_utils
from ..com import msfs_logs


LOD_GROUP_TREE_MANAGER: LODGroupTreeManager | None = None
LOD_GROUP_TREE_MANAGER_UNIQUE_NAME: str = "LOD_GROUP_TREE_MANAGER"

# region Properties
class MultiExporterLOD(bpy.types.PropertyGroup):

    objectLOD: bpy.props.PointerProperty(
        name="Object",
        type=bpy.types.Object
    )  # type: ignore

    collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection
    )  # type: ignore

    enabled: bpy.props.BoolProperty(
        name="Enabled",
        default=False,
        description="Enable/Disable to export"
    )  # type: ignore

    lod_value: bpy.props.FloatProperty(
        name="LOD Value",
        default=0,
        min=0,
        max=999,
        precision=4,
        update=TreeManager.make_update_callback(
            LOD_GROUP_TREE_MANAGER_UNIQUE_NAME, 
            "lod_value"
        ),
    )  # type: ignore

    file_name: bpy.props.StringProperty(
        name="File name",
        default="",
        description="File name of the exported model",
        update=TreeManager.make_update_callback(
            LOD_GROUP_TREE_MANAGER_UNIQUE_NAME, 
            "file_name"
        ),
    )  # type: ignore

    group_name: bpy.props.StringProperty(
        name="Group Name",
        default=""
    )  # type: ignore

    full_data_path: bpy.props.StringProperty(
        description="Use by Tree View for fast data access."
    )  # type: ignore

    def to_dict(self):
        """
        Serialize LOD properties to dictionnary.
        """
        lod_props = {}
        lod_object = self.objectLOD
        try:
            if lod_object:
                lod_object.name
        except RuntimeError:
            # deleted object
            lod_object = None
        lod_props["objectLOD"] = lod_object
        collection = self.collection
        try:
            if collection:
                collection.name
        except RuntimeError:
            collection = None

        lod_props["collection"] = self.collection
        lod_props["file_name"] = self.file_name
        lod_props["name"] = self.name
        lod_props["group_name"] = self.group_name
        lod_props["enabled"] = self.enabled
        lod_props["lod_value"] = self.lod_value

        return lod_props

    def get_lod_objects(
        self,
    ) -> set[bpy.types.Object]:

        objects = set()

        if bpy.context.scene.multi_exporter_grouped_by_collections:
            objects = set(self.collection.all_objects)
        else:
            in_scene = False
            try:
                # Try accessing name to check if still in bpy.data
                # Check if it is in current scene
                in_scene = self.objectLOD.name in bpy.context.scene.objects  # type: ignore
                if not in_scene:
                    return objects
            except:
                # Deleted objects
                return objects

            objects = set((self.objectLOD,))
            children = self.objectLOD.children_recursive

            if children:
                objects.update(set(children))
            
        return objects

class MultiExporterLODGroup(bpy.types.PropertyGroup):

    register_order = 1 #register after MultiExportLOD class

    def update_autogenerate_lod(self, context: bpy.types.Context):
        LOD_GROUP_TREE_MANAGER.update_prop_on_selected_data(
            "autogenerate_lods", self
        )

    def update_relative_path(self, context: bpy.types.Context):

        LOD_GROUP_TREE_MANAGER.update_prop_on_selected_data(
            "folder_path", self
        )

    def set_relative_path(self, value: str):

        self["folder_path"] = msfs_path_utils.get_relative_path_to_scene(value)

    def get_relative_path(self):
        return self.get("folder_path", "")

    def update_group_lod_enabled(self, context: bpy.types.Context):
        LOD_GROUP_TREE_MANAGER.update_prop_on_selected_data(
         "enabled", self
        )

    def enabled_lod_count(self):
        count = 0
        for lod in self.lods:
            if lod.enabled:
                count += 1
        return count

    # We will need to keep this for retro-compatibility
    group_name: bpy.props.StringProperty(
        name="Group Name",
        default=""
    )  # type: ignore

    lods: bpy.props.CollectionProperty(type=MultiExporterLOD)  # type: ignore

    folder_path: bpy.props.StringProperty(
        name="Export Folder Path",
        default="",
        subtype="DIR_PATH",
        description="Path to the directory where you want your model to be exported",
        update=update_relative_path,
        set=set_relative_path,
        get=get_relative_path,
        options=(
            {"PATH_SUPPORTS_BLEND_RELATIVE"} if bpy.app.version >= (4, 5, 0) else set()
        ),
    )  # type: ignore

    generate_xml: bpy.props.BoolProperty(
        name="Generate XML",
        description=(
            "Generate XML or update it if already exists.\n"
            "XML update is conservative:\n"
            "Only LOD entries are modified, other attributes like animation are untouched."
        ),
        default=True,
        update=TreeManager.make_update_callback(
            LOD_GROUP_TREE_MANAGER_UNIQUE_NAME, "generate_xml"
        ),
    )  # type: ignore

    overwrite_guid: bpy.props.BoolProperty(
        name="Overwrite GUID",
        default=False,
        description="If an XML file already exists in the location to export to, the GUID will be overwritten",
        update=TreeManager.make_update_callback(LOD_GROUP_TREE_MANAGER_UNIQUE_NAME,"overwrite_guid")
    )  # type: ignore

    autogenerate_lods: bpy.props.BoolProperty(
        name="Autogenerate LODs",
        default=False,
        description=(
            "If enabled, only the first enabled LOD will be exported.\n" 
            "When the Microsoft Flight Simulator 2024's BuildPackage process will be used,\n"
            "LODs will be generated automatically, using Simplygon."
        ),
        update=update_autogenerate_lod
    )  # type: ignore

    enabled: bpy.props.BoolProperty(
        name="Enabled",
        default=False,
        description="Enable/Disable all LODs to export"
    )  # type: ignore

    settings_preset: bpy.props.EnumProperty(
        name="Settings Preset",
        items=get_setting_presets_items,
        update=TreeManager.make_update_callback(LOD_GROUP_TREE_MANAGER_UNIQUE_NAME,"settings_preset")
    ) # type: ignore

    full_data_path: bpy.props.StringProperty(
        description="Use by Tree View for fast data access."
    ) # type: ignore

    def to_dict(self):
        """
        Serialize LODGroup properties to dictionnary.
        """
        lod_group_dict = {}
        lod_group_dict["name"] = self.name
        lod_group_dict["group_name"] = self.group_name
        lod_group_dict["folder_path"] = self.folder_path
        lod_group_dict["generate_xml"] = self.generate_xml
        lod_group_dict["autogenerate_lods"] = self.autogenerate_lods
        lod_group_dict["enabled"] = self.enabled
        lod_group_dict["settings_preset"] = self.settings_preset
        lod_group_dict["lods"] = []
        for lod in self.lods:
            lop_dict = lod.to_dict()
            lod_group_dict["lods"].append(lop_dict)

        return lod_group_dict

    def get_lod_group_objects(
        self,
        enabled_only: bool = False
    ) -> set[bpy.types.Object]:

        objects =set()
        for lod in self.lods:
            if enabled_only and not lod.enabled:
                continue
            lod: MultiExporterLOD
            objects.update(lod.get_lod_objects())

        return objects
# endregion

# region Operators
class MSFS2024_OT_ReloadLODGroups(bpy.types.Operator):
    bl_idname = "msfs2024.reload_lod_groups"
    bl_label = "Reload LOD groups"
    bl_description = "Reload LOD Groups. Press it when adding, deleting or renaming LOD Groups"
    bl_options = {"INTERNAL"}

    def get_group_name_from_lod_name(self, context, name):
        matches = re.findall("^x[0-9]_|_LOD[0-9]+", name)
        # If a blender_object starts with xN_ or ends with _LODN, treat as an LOD
        if matches:
            # Get base blender_object group name from blender_object
            for match in matches:
                filtered_string = name.replace(match, "")
                return filtered_string

        # If prefix or suffix isn't found, use the blender_object name as the group
        return name

    # region Groups getter

    def get_new_groups_sorted_by_objects(self, context: bpy.types.Context):
        found_lod_groups = {}

        for blender_object in context.scene.objects:
            if blender_object.parent is not None:
                continue

            lod_group_name = self.get_group_name_from_lod_name(context, blender_object.name)

            if lod_group_name not in found_lod_groups:
                found_lod_groups[lod_group_name] = []

            found_lod_groups[lod_group_name].append(blender_object)
        return found_lod_groups

    def get_new_groups_sorted_by_collections(self, context: bpy.types.Context):
        found_lod_groups = {}
        scene_collections = context.scene.collection.children_recursive

        for collection in scene_collections:
            lod_group_name = self.get_group_name_from_lod_name(context, collection.name)

            if lod_group_name not in found_lod_groups:
                found_lod_groups[lod_group_name] = []

            found_lod_groups[lod_group_name].append(collection)

        return found_lod_groups
    # end region

    def store_lod_groups_to_dicts(self, context: bpy.types.Context):
        """
        Serialize lod groups into a dictionnary.
        """
        lod_groups = context.scene.msfs_multi_exporter_lod_groups
        lod_groups_dicts = {}
        for lod_group in lod_groups:
            lod_group_dict = lod_group.to_dict()
            lod_groups_dicts[lod_group.name] = lod_group_dict
        return lod_groups_dicts

    def create_lod_from_old_lod_dict(self, old_lod, lod_group, object_key):
        lod = lod_group.lods.add()
        for key, value in old_lod.items():
            setattr(lod, key, value)
        # Only set file name if user changed it
        if (
            old_lod["file_name"].strip()
            and old_lod["file_name"] != old_lod[object_key].name
        ):
            lod.file_name = old_lod["file_name"]
        else:
            lod.file_name = old_lod[object_key].name

        return lod

    def reload_lod_groups(self, context: bpy.types.Context):
        """
        Recreate lod groups while preserving custom settings .
        """
        grouped_by_collections = context.scene.multi_exporter_grouped_by_collections
        lod_groups = context.scene.msfs_multi_exporter_lod_groups
        if grouped_by_collections:
            new_lod_groups = self.get_new_groups_sorted_by_collections(context)
        else:
            new_lod_groups = self.get_new_groups_sorted_by_objects(context)

        # Store original lod_groups in dict before clear()
        old_lod_groups_dicts = self.store_lod_groups_to_dicts(context)
        lod_groups.clear()

        # Force alphabetical order
        ordered_new_lod_groups_keys = list(new_lod_groups.keys())
        ordered_new_lod_groups_keys.sort(reverse=False)

        for i, new_lod_group_name in enumerate(ordered_new_lod_groups_keys):
            new_lods = new_lod_groups[new_lod_group_name]
            old_lod_group = old_lod_groups_dicts.get(new_lod_group_name, None)

            lod_group: MultiExporterLODGroup = lod_groups.add()
            # Manually format Full data path, much faster than repr()
            lod_group.full_data_path = f"bpy.context.scene.msfs_multi_exporter_lod_groups[{i}]"
            if old_lod_group:
                # Recreate lod_group with original settings
                for key, value in old_lod_group.items():
                    if key == "lods":
                        continue
                    # lod_group[key] will not trigger property update function
                    lod_group[key] = value

                lod_group.name = old_lod_group["name"]
            else:
                # New lod_group with default settings
                lod_group.name = new_lod_group_name

            sorted_new_lods = sorted(new_lods, key=lambda x: x.name, reverse=False)
            # Lodgroup lods creation:
            for i, new_lod in enumerate(sorted_new_lods):
                # Here new_lod can be an object or a collection
                old_lod = None
                object_key = "objectLOD"
                if grouped_by_collections:
                    object_key = "collection"

                if old_lod_group:
                    for lod in old_lod_group["lods"]:
                        if new_lod == lod[object_key]:
                            old_lod = lod

                if old_lod:
                    # Recreate lod with old_lod settings
                    lod = self.create_lod_from_old_lod_dict(
                        old_lod, 
                        lod_group, 
                        object_key
                    )
                else:
                    # New lod with default settings
                    lod = lod_group.lods.add()
                    lod["file_name"] = new_lod.name

                # Renaming
                if grouped_by_collections:
                    lod["collection"] = new_lod
                    if new_lod:
                        lod["name"] = new_lod.name
                else:
                    lod["objectLOD"] = new_lod
                    if new_lod:
                        lod["name"] = new_lod.name
                lod["group_name"] = lod_group.name

                # Faster than repr()
                lod.full_data_path = lod_group.full_data_path + f".lods[{i}]"

    # endregion

    def execute(self, context: bpy.types.Context):
        # Reset Multiselection
        LOD_GROUP_TREE_MANAGER.unselect_all()
        self.reload_lod_groups(context)
        LOD_GROUP_TREE_MANAGER.generate_ui_collection()
        return {"FINISHED"}


class MSFS2024_OT_EditLODGroupSettings(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_edit_lod_group_settings"
    bl_label = "Edit LOD Group Settings"
    bl_description = "Edit the preset settings used to export the LODS contained in a the LOD group"
    bl_options = {"INTERNAL"}

    lod_group_id: bpy.props.StringProperty(default="") # type: ignore

    def execute(self, context: bpy.types.Context):
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        lod_group = context.scene.msfs_multi_exporter_lod_groups[self.lod_group_id]
        layout.prop(lod_group, "settings_preset", text="Export Preset")
        layout.separator()
        layout.prop(lod_group, "generate_xml", text="Generate XML")

        box = layout.box()
        box.prop(lod_group, "overwrite_guid", text="Overwrite GUID")
        box.prop(lod_group, "autogenerate_lods", text="Enable Auto LOD")
        box.enabled = lod_group.generate_xml

# endregion


# region UI TreeView


def _on_selection(tree_manager: TreeManager, context: bpy.types.Context):
    """
    This function is used by LodGroupTreeManager and is called 
    when list active index changed.

    It has two roles:
    - Update items selection in UIList.

    - Select objects in 3d scene when msfs_ui_tree_objects_sync_selection 
    is enabled :
        Select all lods of lodgroup when selected item is a lod group.
        Select lod when selected item is a lod.
    """
    if not context.scene.msfs_ui_tree_objects_sync_selection:
        return

    # Deselect
    for obj in context.view_layer.objects:
        obj.select_set(False)
    selected_items = tree_manager.get_selected_items()

    for item in selected_items:

        item: TreeItem
        data = item.get_data()
        lods = []
        if isinstance(data, MultiExporterLODGroup):
            lods = data.lods
        elif isinstance(data, MultiExporterLOD):
            lods = [data]
        else:
            continue

        for lod in lods:

            object_lod = lod.objectLOD
            collection_lod = lod.collection
            if not object_lod and not collection_lod:
                continue

            blender_object = None
            if object_lod:
                try:
                    lod.objectLOD.name
                except RuntimeError:
                    # Deleted
                    continue
                blender_object = lod.objectLOD

            if collection_lod:
                try:
                    lod.collection.name
                except RuntimeError:
                    # Deleted
                    continue
                blender_object = lod.collection

            try:
                if isinstance(blender_object, bpy.types.Collection):
                    for obj in blender_object.objects:
                        obj.select_set(True)
                        context.view_layer.objects.active = obj
                elif isinstance(blender_object, bpy.types.Object):
                    blender_object.select_set(True)
                    for child in blender_object.children_recursive:
                        child.select_set(True)
                    context.view_layer.objects.active = blender_object
            except RuntimeError:
                # Not in view_layer
                pass


class LODGroupTreeManager(TreeManager):

    # endregion
    LOD_NAME_PATTERN = re.compile(r"^x[0-9]_|_lod[0-9]+$",re.IGNORECASE)

    def get_data_children(
        self, data: bpy.types.bpy_struct
    ) -> list[bpy.types.bpy_struct]:
        if isinstance(data, MultiExporterLODGroup):
            return data.lods
        else:
            return []

    def get_clean_lod_name(self, lod_name:str, index:int)->str:
        new_name = lod_name
        new_suffix = f"_LOD{index}"
        if self.LOD_NAME_PATTERN.search(new_name):
            new_name = self.LOD_NAME_PATTERN.sub(new_suffix, new_name)
        return new_name

    def set_ui_tree_item_name(self, item: TreeItem, data: bpy.types.bpy_struct):
        """
        Set UITreeItem name according to data.
        Item name will drive list order (Alphabetically ordered) and
         is used by filters functions.
        """

        if isinstance(data, MultiExporterLODGroup):
            lod_group: MultiExporterLODGroup = data
            item.name = lod_group.name

        elif isinstance(data, MultiExporterLOD):
            lod: MultiExporterLOD = data
            item.name = self.get_clean_lod_name(lod.name ,item.child_index)

    def on_data_checked(self, checked: bool, data: Any):
        if isinstance(data, MultiExporterLODGroup):
            lod_group: MultiExporterLODGroup = data
            lod_group.enabled = checked

        elif isinstance(data, MultiExporterLOD):
            lod: MultiExporterLOD = data
            lod.enabled = checked

    def is_data_checked(self, data: Any)->bool:
        if isinstance(data, MultiExporterLODGroup):
            lod_group: MultiExporterLODGroup = data
            return lod_group.enabled

        elif isinstance(data, MultiExporterLOD):
            lod: MultiExporterLOD = data
            return lod.enabled
        return False

    def draw_context_menu(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        super().draw_context_menu(context, layout)
        layout.separator()
        export_selected_ope = layout.operator(
            multi_export.MSFS2024_OT_ExportSelectedItems.bl_idname,
            text="Export Selected",
            icon="EXPORT",
        )
        export_selected_ope.export_mode = constants.ExportModes.OBJECTS.identifier

    # endregion


class MSFS2024_UL_LODGroups(bpy.types.UIList, UL_TreeView):

    use_filter_invert: bpy.props.BoolProperty(
        name="Filter Invert", default=False, options=set()
    )  # type: ignore

    lods_only: bpy.props.BoolProperty(
        name="LODs",
        description=(
            "Only show objects or collections with suffixes '_LOD0', '_LOD1' etc,\n"
            "Or with prefixes 'x0_', 'x1_' 'x2_' etc"
        ),
        default=False,
        options=set()
    )  # type: ignore

    active_only: bpy.props.BoolProperty(
        name="Active",
        description="Only show LOD group containing active object or active collection",
        default=False,
        options=set()
    )  # type: ignore

    visible_only: bpy.props.BoolProperty(
        name="Visible",
        description="Only show LOD group that are visible in viewport",
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
        self.lods_only = False
        self.active_only = False
        self.visible_only = False
        self.parents_of_filtered_items = True
        self.check_only = False
        self.uncheck_only = False
        # Make button appears unchecked
        self["reset_filters"] = False

    def _sync_state(self, source):
        # Prevent recursion
        if source == "check":
            self["uncheck_only"] = False
        elif source == "uncheck":
            self["check_only"] = False

    # Inherited Methods
    def custom_draw_item(self, context, index, item, layout):
        item: TreeItem
        data = item.get_data()
        if not data:
            return
        row = layout.row(align=True)
        if isinstance(data, MultiExporterLODGroup):
            self.draw_lod_group(data, item, index, row)

        elif isinstance(data, MultiExporterLOD):

            self.draw_lod(data, item, index, row)
        else:
            row.label(text="Not Implemented")

    def draw_lod(self, lod, item, index, row):
        lod_group = item.get_parent_data()
        if not lod_group:
            return
        item: TreeItem

        row.prop(lod, "file_name", text=f"LOD{item.child_index}", expand=False)

        if lod_group.generate_xml and not lod_group.autogenerate_lods:
            row = row.row(align=True)
            row.ui_units_x = 8
            row.label(text="", icon="FULLSCREEN_ENTER")
            row.prop(lod, "lod_value", text="", expand=False)

    def draw_lod_group(self, lod_group, item, index, row):

        small_row = row.row()
        small_row.scale_x = 0.7
        small_row.label(text=lod_group.name)
        if bpy.app.version > (4, 0, 0):
            row.prop(lod_group, "folder_path", text="", placeholder="Export Folder")
        else:
            row.prop(lod_group, "folder_path", text="")

    def draw_filter(self, context, layout):

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
        row.prop(self, "lods_only", icon="OBJECT_DATAMODE", toggle=True)
        row.prop(self, "active_only", icon="LAYER_ACTIVE", toggle=True)
        row.prop(self, "visible_only", icon="HIDE_OFF", toggle=True)
        row = box.row(align=True)
        row.prop(self, "check_only", icon="CHECKBOX_HLT", toggle=True)
        row.prop(self, "uncheck_only", icon="CHECKBOX_DEHLT", toggle=True)
        col = box.column(align=True)
        if bpy.app.version < (4, 2, 0):
            col.separator()
        else:
            col.separator(type="LINE")
        col.prop(self, "parents_of_filtered_items")

    @staticmethod
    def has_lod_name(name: str) -> bool:
        """
        Check if the given name starts with x0, x1 or 
        ends with _LOD e.g.,'LOD', 'LOD0', 'LOD1'.
        """
        matches = LODGroupTreeManager.LOD_NAME_PATTERN.search(name)

        return bool(matches)

    @staticmethod
    def is_lods_only_item(item: TreeItem) -> bool:
        """Check if item corresponds to lod or lod group following naming conventions.

        For lodgroup , check if the first two lods follows naming conventions.
        """
        data = item.get_data()
        if not data:
            return False

        if isinstance(data, MultiExporterLODGroup):
            # Check if one of two first lods have a valid lod name
            for lod in data.lods[:2]:
                if MSFS2024_UL_LODGroups.has_lod_name(lod.name):
                    return True
            return False

        elif isinstance(data, MultiExporterLOD):
            return MSFS2024_UL_LODGroups.has_lod_name(data.name)

        return False

    def is_active(self, context, item) -> bool:
        """
        Check if the given item coresponds to active object.
        """

        data = item.get_data()
        if not data:
            return
        if isinstance(data, MultiExporterLODGroup):
            lod_group = data
            for lod in lod_group.lods:
                if lod.objectLOD == context.view_layer.objects.active:
                    return True
                if lod.collection == context.view_layer.active_layer_collection.collection:
                    return True

        elif isinstance(data, MultiExporterLOD):

            lod = data
            if lod.objectLOD == context.view_layer.objects.active:
                return True
            if lod.collection == context.view_layer.active_layer_collection.collection:
                return True

        return False

    def _get_layer_collection(self,context,collection)->bpy.types.LayerCollection:
        for layer_collection in bpy.context.view_layer.layer_collection.children:
            if layer_collection.collection == collection:
                return layer_collection
        return None

    def is_visible(self, context, item) -> bool:
        """
        Check if the given item coresponds to a visible object.
        """

        data = item.get_data()
        if not data:
            return

        if isinstance(data, MultiExporterLODGroup):
            lod_group = data
            for lod in lod_group.lods:
                if lod.objectLOD and lod.objectLOD.visible_get(view_layer=context.view_layer): 
                    return True
                collection = lod.collection
                if not collection:
                    return
                layer_collection = self._get_layer_collection(context,collection)
                if layer_collection and not ( layer_collection.hide_viewport or layer_collection.exclude):
                    return True

        elif isinstance(data, MultiExporterLOD):

            lod = data
            if lod.objectLOD and lod.objectLOD.visible_get(view_layer=context.view_layer): 
                return True
            collection = lod.collection
            if not collection:
                return
            layer_collection = self._get_layer_collection(context,collection)
            if layer_collection and not ( layer_collection.hide_viewport or layer_collection.exclude):
                return True

        return False

    def filter_items(self, context, data, propname):
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

        # msfs_lod_groups_ui_tree
        msfs_lod_groups_ui_tree :list[TreeItem]= getattr(data, propname)
        helper_funcs = bpy.types.UI_UL_list

        # Filtering by name
        if self.filter_name:
            flt_flags = helper_funcs.filter_items_by_name(
                self.filter_name,
                self.bitflag_filter_item,
                msfs_lod_groups_ui_tree,
                "name",
                reverse=self.use_filter_invert,
            )  
        for i, item in enumerate(msfs_lod_groups_ui_tree):
            if self.lods_only and not MSFS2024_UL_LODGroups.is_lods_only_item(item):
                flt_flags[i] &= ~self.bitflag_filter_item
            if self.active_only and not self.is_active(context, item):
                flt_flags[i] &= ~self.bitflag_filter_item

            if self.visible_only and not self.is_visible(context, item):
                flt_flags[i] &= ~self.bitflag_filter_item

            if self.check_only and not item.checked:
                flt_flags[i] &= ~self.bitflag_filter_item
            elif self.uncheck_only and item.checked:
                flt_flags[i] &= ~self.bitflag_filter_item

        if self.parents_of_filtered_items:
            self.show_parents_of_filtered_items(msfs_lod_groups_ui_tree, flt_flags)

        self.save_flags_in_tree_manager(flt_flags)

        return flt_flags, flt_neworder


# endregion


class MSFS2024_OT_SetHierarchyMode(bpy.types.Operator):
    """Set Hierarchy Mode for user. Shows a popup that
    warns user about the reset of export settings."""

    bl_idname = "msfs2024.set_hierarchy_mode"
    bl_label = "Objects export settings will be reset. Switch?"
    bl_description = "Switch between hierarchy modes (Objects or Collections)"
    bl_options = {"INTERNAL"}

    hierarchy_mode: bpy.props.EnumProperty(
        name="Mode",
        default="objects",
        description="Group LODs by objects or collections "
        "(WARNING: Switching hierarchy mode will"
        "reset objects export settings)",
        items=(
            (
                "objects",
                "Objects",
                "LOD Group are generated from objects hierarchy",
                "OBJECT_DATA",
                0
            ),
            (
                "collections",
                "Collections",
                "LOD Group are generated from collections hierarchy",
                "OUTLINER_COLLECTION",
                1
            )
        )
    )  # type: ignore

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True

    def execute(self, context: bpy.types.Context):
        if (
            self.hierarchy_mode == "objects"
            and context.scene.multi_exporter_grouped_by_collections
        ):

            context.scene.multi_exporter_grouped_by_collections = False
        elif (
            self.hierarchy_mode == "collections"
            and not context.scene.multi_exporter_grouped_by_collections
        ):
            context.scene.multi_exporter_grouped_by_collections = True
        else:
            self.report({"INFO"}, f"Already set to {self.hierarchy_mode} mode")
        return {"FINISHED"}

    def invoke(self, context, event):
        if bpy.app.version > (4,0,0):
            return context.window_manager.invoke_confirm(
                self,
                event,
                title="",
                message="WARNING: Switching hierarchy mode will reset objects export settings.",
                icon="WARNING"
            )
        else:
            return context.window_manager.invoke_confirm(
                self,
                event
            )

# region Panel
class MSFS2024_PT_MultiExporterObjectsView(bpy.types.Panel):
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
            == constants.Tabs.OBJECTS.identifier
        )

    def get_number_lods(self, context: bpy.types.Context):
        lod_groups = context.scene.msfs_multi_exporter_lod_groups

        total_lods = 0
        for lod_group in lod_groups:
            total_lods += len(lod_group.lods)

        return total_lods

    def draw_active_lod_group_settings(self, context, lod_group, layout):
        box = layout.box()
        box.label(text="LOD Group Settings:")
        row = box.row()
        if bpy.app.version > (4, 0, 0):
            row.prop(lod_group, "folder_path", text="", placeholder="Export Folder")
        else:
            row.prop(lod_group, "folder_path", text="")
        box.prop(lod_group, "settings_preset", text="Export Preset")
        row = box.row()
        row.prop(lod_group, "generate_xml", text="Generate XML")
        row = row.split()

        row.prop(lod_group, "autogenerate_lods", text="Enable Auto LOD")
        row.prop(lod_group, "overwrite_guid", text="Overwrite GUID")
        row.enabled = lod_group.generate_xml

    def draw(self, context: bpy.types.Context):
        layout = self.layout

        layout.operator(
            MSFS2024_OT_ReloadLODGroups.bl_idname,
            text="Reload LODs",
            icon="FILE_REFRESH",
        )
        row = layout.row(align=True)
        row.label(text="Mode:")

        row = row.row(align=False)
        row.scale_x = 2
        icon = "OBJECT_DATA"
        text = "Objects"
        if context.scene.multi_exporter_grouped_by_collections:
            icon = "OUTLINER_COLLECTION"
            text = "Collections"
        row.operator_menu_enum(
            MSFS2024_OT_SetHierarchyMode.bl_idname,
            "hierarchy_mode",
            text=text,
            icon=icon
        )
        row = layout.row()
        row.prop(
            context.scene, "msfs_ui_tree_objects_sync_selection", text="Sync Selection"
        )
        TREEVIEW_OT_ExpandAllItems.draw_expand_all_buttons(
            row, 
            LOD_GROUP_TREE_MANAGER.unique_name
        )
        total_lods = self.get_number_lods(context)

        if total_lods == 0:
            box = layout.box()
            box.label(text="No LODs found in scene")
        else:
            LOD_GROUP_TREE_MANAGER.draw(
                context, 
                layout, 
                rows=4
            )
            active_item = LOD_GROUP_TREE_MANAGER.get_active_item()
            if active_item:
                active_data = active_item.get_data()
                lod_group = None
                if isinstance(active_data,MultiExporterLODGroup):
                    lod_group = active_data
                elif isinstance(active_data, MultiExporterLOD):
                    lod_group = active_item.get_parent_data()
                if lod_group:
                    self.draw_active_lod_group_settings(context,lod_group, layout)


        multi_export.draw_export_button(context, layout, constants.ExportModes.OBJECTS)


class MSFS2024_PT_ObjectsLogs(bpy.types.Panel):
    bl_label = "Logs"
    bl_parent_id = "MSFS2024_PT_MultiExporterObjectsView"
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

#####################################################################

def update_grouped_by(self, context: bpy.types.Context):
    context.scene.msfs_multi_exporter_lod_groups.clear()
    bpy.ops.msfs2024.reload_lod_groups()


def register():
    bpy.types.Scene.msfs_multi_exporter_lod_groups = bpy.props.CollectionProperty(type=MultiExporterLODGroup) # type: ignore
    global LOD_GROUP_TREE_MANAGER
    global LOD_GROUP_TREE_MANAGER_UNIQUE_NAME

    LOD_GROUP_TREE_MANAGER = LODGroupTreeManager(
        unique_name=LOD_GROUP_TREE_MANAGER_UNIQUE_NAME,
        ul_tree_view_class=MSFS2024_UL_LODGroups,
        on_selection_function=_on_selection,
        data_collection_getter=lambda: bpy.context.scene.msfs_multi_exporter_lod_groups,
        alphabetical_order=True,
        multiselection_support=True,
        checkable_items=True,
    )

    bpy.types.Scene.msfs_ui_tree_objects_sync_selection = bpy.props.BoolProperty( # type: ignore
        default=False, 
        description="Select corresponding scene objects when an item is selected in exporter hierarchy"
    )

    bpy.types.Scene.multi_exporter_grouped_by_collections = bpy.props.BoolProperty( # type: ignore
        name="Grouped by collections",
        default=False,
        description="Group LODs by collections "
                    "(WARNING: if you change this option it will "
                    "reset the objects view of the multi-exporter)",
        update=update_grouped_by
    )

def unregister():
    
    try:
        global LOD_GROUP_TREE_MANAGER
        del bpy.types.Scene.msfs_multi_exporter_lod_groups # type: ignore
        LOD_GROUP_TREE_MANAGER.unregister()
        del LOD_GROUP_TREE_MANAGER
        del bpy.types.Scene.msfs_ui_tree_objects_sync_selection # type: ignore
        del bpy.types.Scene.multi_exporter_grouped_by_collections # type: ignore
        
    except:
        pass
