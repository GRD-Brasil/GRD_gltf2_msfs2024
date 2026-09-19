"""
UI Tree View.

Meant to be reimplemented.
Cf implementation example in msfs_multi_export_objects.py and msfs_multi_export_presets.py
"""
from __future__ import annotations

import bpy
from typing import Any, TYPE_CHECKING

from _addons_utils.ui.tree_widget.view_ope import TREEVIEW_OT_ToggleItemExpand
from _addons_utils.ui.tree_widget.manager import TreeManager
if TYPE_CHECKING:
    from _addons_utils.ui.tree_widget.item import TreeItem

class UL_TreeView():
    """
    Tree view mixin for UILists.

    Adds tree-like behavior when drawing items 
    (expand/collapse states, parent–child relationships, etc.).

    It is intended to be used as a 
    secondary base class alongside bpy.types.UIList.
    """
    # View Options:
    _indent_scale = 4
    tree_manager_name = None
    def custom_draw_item(
        self,
        context: bpy.types.Context,
        index: int,
        item: TreeItem,
        layout: bpy.types.UILayout
    ):
        raise NotImplementedError()

    def draw_item(
        self,
        context: bpy.types.Context,
        layout: bpy.types.UILayout,
        data: Any,
        item: TreeItem,
        icon: int,
        active_data: Any,
        active_propname: str,
        index: int
    ):
        if not self.layout_type in {"DEFAULT", "COMPACT"}:
            return
        # Set context pointer for right-click
        layout.context_pointer_set("tree_item", item)

        tree_manager: TreeManager | None = TreeManager.tree_manager_instances.get(
            self.tree_manager_name, None
        )
        if not tree_manager:
            return

        if (
            tree_manager.MULTISELECTION_SUPPORT 
            and tree_manager._has_multiselection
            and item.selected
        ):
            layout.alert = True

        row = layout.row(align=True)
        for _ in range(item.all_parent_count * self._indent_scale):
            # use layout.row instead of layout.separator_spacer
            row = layout.row(align=True)

        if item.expanded and item.children_count:
            op = row.operator(
                TREEVIEW_OT_ToggleItemExpand.bl_idname,
                text="",
                icon="DOWNARROW_HLT",
                emboss=False
            )
            op.tree_manager_name = tree_manager.unique_name
            op.item_index = index

        elif not item.expanded and item.children_count:
            op = row.operator(
                TREEVIEW_OT_ToggleItemExpand.bl_idname,
                text="",
                icon="RIGHTARROW",
                emboss=False
            )
            op.tree_manager_name = tree_manager.unique_name
            op.item_index = index

        if tree_manager.CHECKABLE_ITEMS:
            check_row = row.row()
            check_row.scale_x = 0.25
            check_row.prop(item, "checked", icon_only=True)

        self.custom_draw_item(context, index, item, layout)

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

        ui_tree :list[TreeItem]= getattr(data, propname)

        flt_flags = []
        flt_neworder = []

        flt_flags = [self.bitflag_filter_item] * len(ui_tree)

        for i, item in enumerate(ui_tree):

            if item.hidden:
                flt_flags[i] &= ~self.bitflag_filter_item

        self.save_flags_in_tree_manager(flt_flags)
        return flt_flags, flt_neworder

    def save_flags_in_tree_manager(self, flt_flags):
        """Save flags in tree manager class.
        Used for item selection system in order to not select hidden items.
        """
        tree_manager: TreeManager | None = TreeManager.tree_manager_instances.get(
            self.tree_manager_name, None
        )
        if not tree_manager:
            return
        tree_manager.save_flt_flags(flt_flags)

    def show_parents_of_filtered_items(self, ui_tree: list[TreeItem], flt_flags):
        """
        Ensure that all parents of currently visible items are also marked visible.
        Call this after filtering.
        """
        for item, flag in zip(ui_tree,flt_flags):
            if not (flag & self.bitflag_filter_item):
                continue
            for parent_item in item.all_parent_indexes:
                flt_flags[parent_item.value] |= self.bitflag_filter_item
