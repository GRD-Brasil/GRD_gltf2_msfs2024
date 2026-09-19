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
from enum import Enum

import bpy

from _addons_utils.ui.tree_widget.item import TreeItem
from _addons_utils.ui.tree_widget.manager import TreeManager
from _addons_utils.ui.tree_widget.view import UL_TreeView
from _addons_utils.ui.tree_widget.view_ope import  TREEVIEW_OT_SelectAllItems

IMAGES_TREE_MANAGER_UNIQUE_NAME: str = "IMAGES_TREE_MANAGER"

class MSFS2024ImageFlagsEnum(Enum):
    """
        Enum describing the parameters of image contains Tuples of:
        ( 
            The name that appears in the UI, 
            Default Value, 
            attribute name of the property, 
            name that appear in the flags when it's exported/imported
        )
    """

    ## Parameters
    QUALITYHIGH = "Quality High", False, "msfs_image_quality_high", "+QUALITYHIGH"
    ALPHAPRESERVATION = "Alpha Preservation", False, "msfs_image_alpha_preserv", "+ALPHAPRESERVATION"
    NOREDUCTION = "No Reduction", False, "msfs_image_no_reduction", "+NOREDUCE"
    NOMIPMAP = "No Mipmap", False, "msfs_image_no_mipmap", "+NOMIPMAP"
    PRECOMPUTEDINVAVG = "PreComputed Inverse Average", False, "msfs_image_prec_inv_avg", "+PRECOMPUTEDINVAVG"
    ANISOTROPIC = "Anisotropic", None, "msfs_image_anisotropic", "+ANISOTROPIC="

    def flag_name(self):
        assert isinstance(self.value, tuple) and len(self.value) > 0
        if isinstance(self.value, tuple) and len(self.value) > 0:
            return self.value[0]
        return None

    def default_value(self):
        assert isinstance(self.value, tuple) and len(self.value) > 1
        if isinstance(self.value, tuple) and len(self.value) > 1:
            return self.value[1]
        return None

    def attribute_name(self):
        assert isinstance(self.value, tuple) and len(self.value) > 2
        if isinstance(self.value, tuple) and len(self.value) > 2:
            return self.value[2]
        return None

    def flag_code(self):
        assert isinstance(self.value, tuple) and len(self.value) > 3
        if isinstance(self.value, tuple) and len(self.value) > 3:
            return self.value[3]
        return None

class ImagesTreeManager(TreeManager):

    @staticmethod
    def make_update_callback(unique_name:str, prop_name: str):
        """
        Create a function that be can be used by a property update callback.

        In this case we need to override this function since flags attribute 
        are not directly accessible from item image data . 
        
        Flags are store in an image property group named 'msfs_flags'.
        """
        def _update(self, context):
            tree_manager: TreeManager | None = TreeManager.tree_manager_instances.get(
                unique_name, None
            )
            if not tree_manager:
                return
            active_item = tree_manager.get_active_item()
            active_data = None
            if active_item:
                active_data = active_item.get_data()
            if not active_data:
                return

            tree_manager.update_prop_on_selected_data(f"msfs_flags.{prop_name}", active_data)
        return _update


class MSFS2024ImageFlags(bpy.types.PropertyGroup):
    

    msfs_image_quality_high: bpy.props.BoolProperty(
        name=MSFS2024ImageFlagsEnum.QUALITYHIGH.flag_name(),
        default=MSFS2024ImageFlagsEnum.QUALITYHIGH.default_value(),
        update=ImagesTreeManager.make_update_callback(
            IMAGES_TREE_MANAGER_UNIQUE_NAME, 
            "msfs_image_quality_high"
        )
    ) # type: ignore

    msfs_image_alpha_preserv: bpy.props.BoolProperty(
        name=MSFS2024ImageFlagsEnum.ALPHAPRESERVATION.flag_name(),
        default=MSFS2024ImageFlagsEnum.ALPHAPRESERVATION.default_value(),
        update=ImagesTreeManager.make_update_callback(
            IMAGES_TREE_MANAGER_UNIQUE_NAME, 
            "msfs_image_alpha_preserv"
        ),
    ) # type: ignore

    msfs_image_no_reduction: bpy.props.BoolProperty(
        name=MSFS2024ImageFlagsEnum.NOREDUCTION.flag_name(),
        default=MSFS2024ImageFlagsEnum.NOREDUCTION.default_value(),
        update=ImagesTreeManager.make_update_callback(
            IMAGES_TREE_MANAGER_UNIQUE_NAME, 
            "msfs_image_no_reduction"
        ),
    ) # type: ignore

    msfs_image_no_mipmap: bpy.props.BoolProperty(
        name=MSFS2024ImageFlagsEnum.NOMIPMAP.flag_name(),
        default=MSFS2024ImageFlagsEnum.NOMIPMAP.default_value(),
        update=ImagesTreeManager.make_update_callback(
            IMAGES_TREE_MANAGER_UNIQUE_NAME, 
            "msfs_image_no_mipmap"
        ),
    ) # type: ignore

    msfs_image_prec_inv_avg: bpy.props.BoolProperty(
        name=MSFS2024ImageFlagsEnum.PRECOMPUTEDINVAVG.flag_name(),
        default=MSFS2024ImageFlagsEnum.PRECOMPUTEDINVAVG.default_value(),
        update=ImagesTreeManager.make_update_callback(
            IMAGES_TREE_MANAGER_UNIQUE_NAME, 
            "msfs_image_prec_inv_avg"
        ),
    ) # type: ignore

    msfs_image_anisotropic: bpy.props.EnumProperty(
        name=MSFS2024ImageFlagsEnum.ANISOTROPIC.flag_name(),
        items = (
            ("NONE", "Disabled", ""),
            ("0", "x0 (Standard)", ""),
            ("2", "x2 (High)", ""),
            ("4", "x4 (Very High)", ""),
            ("8", "x8 (Extreme)", ""),
            ("16", "x16 (Insane)", "")
        ),
        update=ImagesTreeManager.make_update_callback(
            IMAGES_TREE_MANAGER_UNIQUE_NAME, 
            "msfs_image_anisotropic"
        ),
    ) # type: ignore

    def to_string(self):
        result = ""
        result += MSFS2024ImageFlagsEnum.QUALITYHIGH.flag_code() if self.msfs_image_quality_high else ""
        result += MSFS2024ImageFlagsEnum.ALPHAPRESERVATION.flag_code() if self.msfs_image_alpha_preserv else ""
        result += MSFS2024ImageFlagsEnum.NOREDUCTION.flag_code() if self.msfs_image_no_reduction else ""
        result += MSFS2024ImageFlagsEnum.NOMIPMAP.flag_code() if self.msfs_image_no_mipmap else ""
        result += MSFS2024ImageFlagsEnum.PRECOMPUTEDINVAVG.flag_code() if self.msfs_image_prec_inv_avg else ""
        result += MSFS2024ImageFlagsEnum.ANISOTROPIC.flag_code() +  self.msfs_image_anisotropic if self.msfs_image_anisotropic != "NONE" else ""
        return result

def _draw_image_properties(layout, image: bpy.types.Image):
    flags = image.msfs_flags

    layout = layout
    box = layout.box()

    row = box.row()
    row.prop(flags, MSFS2024ImageFlagsEnum.QUALITYHIGH.attribute_name())
    row = box.row()
    row.prop(flags, MSFS2024ImageFlagsEnum.ALPHAPRESERVATION.attribute_name())
    row = box.row()
    row.prop(flags, MSFS2024ImageFlagsEnum.NOREDUCTION.attribute_name())
    row = box.row()
    row.prop(flags, MSFS2024ImageFlagsEnum.NOMIPMAP.attribute_name())
    row = box.row()
    row.prop(flags, MSFS2024ImageFlagsEnum.PRECOMPUTEDINVAVG.attribute_name())
    row = box.row()
    row.prop(flags, MSFS2024ImageFlagsEnum.ANISOTROPIC.attribute_name())

    row = layout.row()
    return

class MSFS2024_PT_ImageProperties(bpy.types.Panel):
    bl_label = "MSFS2024 Image Flags"
    bl_idname = "IMAGE_PT_msfs2024_image_properties"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "MSFS2024"

    @classmethod
    def poll(cls, context):
        return context.edit_image is not None
    
    def draw(self, context):
        image = context.edit_image
        _draw_image_properties(self.layout, image)

class MSFS2024_UL_Images(bpy.types.UIList, UL_TreeView):
    use_filter_invert: bpy.props.BoolProperty(
        name="Filter Invert", 
        default=False,
        options=set()
    )  # type: ignore

    # Inherited Methods

    def custom_draw_item(self, context, index, item, layout):
        item: TreeItem
        data = item.get_data()
        if not data:
            return
        if isinstance(data, bpy.types.Image):
            self.draw_image(data, item, index, layout)

    def draw_image(self, image: bpy.types.Image, item, index, row:bpy.types.UILayout):
        row.label(text=image.name)

    def draw_filter(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, "filter_name", text="", icon="VIEWZOOM")
        row.prop(
            self, "use_filter_invert", text="", icon="ARROW_LEFTRIGHT", icon_only=True
        )
        col = layout.column(align=False)
        col.prop(self, "parents_of_filtered_items")

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

        return flt_flags, flt_neworder


class MSFS2024_OT_SetImageFlags(bpy.types.Operator):
    bl_idname = "msfs2024.set_image_flags"
    bl_label = "Set Image Flags"
    bl_description = (
        "Set flags on images.\n"
        "Supports multi-selection (Shift and Alt), allowing you to \n"
        "edit flags on multiple images at once.\n"
        "WARNING: Flags are set in xml during export!"
    )
    bl_options = {"INTERNAL"}

    images_tree_manager: ImagesTreeManager | None = None

    def execute(self, context):
        return {"FINISHED"}

    def __del__(self):
        try:
            self.images_tree_manager.unregister()
        except:
            pass
    def invoke(self, context, event):

        # Register Image Tree Manager
        self.images_tree_manager = ImagesTreeManager(
            unique_name=IMAGES_TREE_MANAGER_UNIQUE_NAME,
            ul_tree_view_class=MSFS2024_UL_Images,
            data_collection_getter=lambda: bpy.data.images,
            alphabetical_order=True,
            multiselection_support=True,
            checkable_items=False,
        )

        self.images_tree_manager.generate_ui_collection()
        wm = context.window_manager
        return wm.invoke_popup(self)

    def draw(self, context):
        # Title
        self.layout.label(text=self.bl_label)
        if bpy.app.version >= (4,2,0):
            self.layout.separator(type="LINE")
        else:
            self.layout.separator()
        if not len(self.images_tree_manager.get_ui_tree_collection()):
            self.layout.label(text="No Images found in this file.", icon="ERROR")
            return

        active_item = self.images_tree_manager.get_active_item()
        image = None
        if active_item:
            image = active_item.get_data()

        if image:
            icon = self.layout.icon(image)
            self.layout.template_icon(icon, scale=8)

        row = self.layout.row()
        select_all_ope = row.operator(
            TREEVIEW_OT_SelectAllItems.bl_idname,
            text="Select All",
            icon="RESTRICT_SELECT_OFF",
        )
        select_all_ope.tree_manager_name = self.images_tree_manager.unique_name
        select_all_ope.select = True
        deselect_all_ope = row.operator(
            TREEVIEW_OT_SelectAllItems.bl_idname,
            text="Deselect All",
            icon="RESTRICT_SELECT_ON",
        )
        deselect_all_ope.tree_manager_name = self.images_tree_manager.unique_name
        deselect_all_ope.select = False

        self.images_tree_manager.draw(context, self.layout, rows=15)

        if image:
            _draw_image_properties(self.layout, image)


def register():
    bpy.types.Image.msfs_flags = bpy.props.PointerProperty(
        name="Flags", 
        type=MSFS2024ImageFlags
    )

def unregister():
    try:
        del bpy.types.Image.msfs_flags
    except:
        pass
