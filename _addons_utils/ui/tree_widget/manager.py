"""
Utilities for UI Tree Widget.

Meant to be reimplemented.

Cf implementation example in msfs_multi_export_objects.py and msfs_multi_export_presets.py
"""
from __future__ import annotations

import bpy
from typing import Any, Iterable, TYPE_CHECKING, Callable, Type
from _addons_utils.ui.tree_widget.view_ope import (
    TREEVIEW_OT_SelectAllItems,
    TREEVIEW_OT_CheckAllItems,
)

if TYPE_CHECKING:
    # Avoid circular import for type hinting
    from _addons_utils.ui.tree_widget.item import IntItem, TreeItem
    from _addons_utils.ui.tree_widget.view import UL_TreeView
# region UITreeManager


class TreeManager:
    """
    Tree Manager.

    Manage TreeItem collection.

    Objective is to have a collection of tree items that reflects a collection of data.
    
    This class manages items hierarchy, expand and collapsed items, checked items
    and items multi selection.

    Reimplement it to fit your needs (cf region with overridables functions)
    """
    instances_count = 0
    tree_manager_instances: dict[str, TreeManager] = {}

    def __init__(
        self,
        unique_name:str,
        ul_tree_view_class: Type[UL_TreeView],
        on_selection_function: Callable | None = None,
        data_collection_getter: Callable | None = None,
        alphabetical_order: bool = True,
        multiselection_support: bool = True,
        checkable_items: bool = True,
        
    ) -> None:
        # Remove white spaces in unique name
        unique_name = "".join(unique_name.split())
        if unique_name in TreeManager.tree_manager_instances:
            raise Exception("A TreeManager with same name already exists!")
        TreeManager.instances_count +=1

        self.unique_name = unique_name
        self.data_collection_getter = data_collection_getter
        self.ul_tree_view_class : Type[UL_TreeView] = ul_tree_view_class

        self.on_selection_function: Callable | None = on_selection_function
        # region Manager settings
        self.ALPHABETICAL_ORDER :bool = alphabetical_order
        self.MULTISELECTION_SUPPORT = multiselection_support
        self.CHECKABLE_ITEMS = checkable_items
        # endregion

        self.ui_tree_prop_name : str 
        self.active_index_prop_name : str 
        self.old_active_index_prop_name :str 

        TreeManager.tree_manager_instances[self.unique_name] = self
        self._expanded_items = []

        # Filter flags must be set in UIList filter_items() if you want
        # Multiselection to work with filters
        self._flt_flags = []

        self._has_multiselection = False # Track if user selected multiple items
        self._updating_props = False #Prevent recursion error when updating prop in multiselection

        self.register(ul_tree_view_class)

    # region OVERRIDABLES FUNCTIONS
    def get_data_name(self, data) -> str:
        """
        Get data name for alphabetical ordering
        """
        return data.name

    def get_data_children(
        self, 
        data: bpy.types.bpy_struct
    ) -> list[bpy.types.bpy_struct]:
        """
        Return a list of data children.
        Children must have list have a "name" attribute.
        """
        return []

    def set_ui_tree_item_name(
        self,
        item: TreeItem,
        data: bpy.types.bpy_struct
    ):
        """
        Set UITreeItem name according to data.
        Item name will drive list order (Alphabetically ordered) and
         is used by filters functions.
        """
        item.name = data.name

    def get_expanded_items(self) -> set[str]:
        """
        Get list of items name that are expanded in ui tree
        """
        expanded_ui_tree_items = set()
        for item in self.get_ui_tree_collection():
            if item.expanded:
                expanded_ui_tree_items.add(item.name)
        return expanded_ui_tree_items

    def is_data_checked(self, data: Any)->bool:
        return False

    def on_data_checked(self, checked: bool, data: Any):
        pass

    def draw_context_menu(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        """
        Custom draw function for right click menu.
        """

        # Select Operators
        layout.separator()
        select_all_ope = layout.operator(
            TREEVIEW_OT_SelectAllItems.bl_idname,
            text="Select All",
            icon="RESTRICT_SELECT_OFF",
        )
        select_all_ope.tree_manager_name = self.unique_name
        select_all_ope.select = True

        deselect_all_ope = layout.operator(
            TREEVIEW_OT_SelectAllItems.bl_idname,
            text="Deselect All",
            icon="RESTRICT_SELECT_ON",
        )
        deselect_all_ope.tree_manager_name = self.unique_name
        deselect_all_ope.select = False

        # Check Operators
        if self.CHECKABLE_ITEMS:
            layout.separator()
            check_all_ope = layout.operator(
                TREEVIEW_OT_CheckAllItems.bl_idname,
                text="Check All",
                icon="CHECKBOX_HLT",
            )
            check_all_ope.tree_manager_name = self.unique_name
            check_all_ope.check = True

            uncheck_all_ope = layout.operator(
                TREEVIEW_OT_CheckAllItems.bl_idname,
                text="Uncheck All",
                icon="CHECKBOX_DEHLT",
            )
            uncheck_all_ope.tree_manager_name = self.unique_name
            uncheck_all_ope.check = False
    # endregion

    def get_data_collection(self) -> Iterable:
        """
        Return main data Collection Iterable.
        """
        if not self.data_collection_getter:
            raise Exception("[TreeManager] Provide a data_collection_getter on init\n," 
                            "or implement get_data_collection() in derived class")
        return self.data_collection_getter()

    def get_ui_tree_collection(self) -> bpy.types.bpy_prop_collection_idprop[TreeItem]:
        """
        Return Collection property of UITreeItem.This is
        the collection that will be displayed in UIList view.
        """
        return getattr(bpy.context.scene, self.ui_tree_prop_name)

    def _get_ui_tree_active_index(self) -> int:
        """
        Return ui list active item property.
        """
        return getattr(bpy.context.window_manager, self.active_index_prop_name)

    def set_ui_tree_active_index(self, value: int | None, update_selection: bool = False):
        """
        Set ui list active item property.
        Selection update is disabled by default in order to prevent infinite recusion.
        """
        if value is None:
            value = -1 # No active item in UI
        if update_selection:
            # Trigger prop update function
            setattr(bpy.context.window_manager, self.active_index_prop_name, value)
        else:
            bpy.context.window_manager[self.active_index_prop_name] = value

    def _get_ui_old_tree_active_index(self) -> int:
        """
        Return ui list old active item property.
        Used for multiselection.
        """
        return getattr(bpy.context.window_manager, self.old_active_index_prop_name)

    def _set_ui_old_tree_active_index(self, value: int):
        """
        Set ui list old active item property.
        Used for multiselection.
        """
        setattr(bpy.context.window_manager, self.old_active_index_prop_name, value)

    def set_ui_tree_active_item_by_data(
        self, data: bpy.types.bpy_struct, 
        update_selection: bool = False
    ):
        """
        Set active item with corresponding data
        """
        
        ui_tree_collection = self.get_ui_tree_collection()
        for i, item in enumerate(ui_tree_collection):
            item: TreeItem
            item_data = item.get_data()
            if item_data == data:
                self.set_ui_tree_active_index(i, update_selection)
                return

    def _create_tree_item_from_data(
        self,
        data: bpy.types.bpy_struct,
        parent_item: None | TreeItem = None,
        child_index=0,
    ):
        """
        Create UITreeItem from provided data.
        """
        ui_tree_collection = self.get_ui_tree_collection()
        ui_tree_item: TreeItem = ui_tree_collection.add()
        item_index = len(ui_tree_collection) - 1
        ui_tree_item.index = item_index
        # Store tree manager import class in item so we call tree manager from item (cf _on_item_checked)
        ui_tree_item.tree_manager_name = self.unique_name

        # Set properties depending on parent state
        if not parent_item:
            ui_tree_item.parent_index = -1
        else:
            ui_tree_item.parent_index = ui_tree_collection.find(parent_item.name)

            # Generate list of parents ordered by proximity
            p_index_item :IntItem = ui_tree_item.all_parent_indexes.add()
            p_index_item.value = ui_tree_item.parent_index
            for item in parent_item.all_parent_indexes:
                p_index_item :IntItem = ui_tree_item.all_parent_indexes.add()
                p_index_item.value = item.value
            ui_tree_item.all_parent_count = len(ui_tree_item.all_parent_indexes)

            ui_tree_item.parent_full_data_path = parent_item.full_data_path
            # Item is not visible in list if parent is not expanded
            ui_tree_item.hidden = not parent_item.expanded
            ui_tree_item.child_index = child_index

        ui_tree_item.set_data(data)
        self.set_ui_tree_item_name(ui_tree_item, data)

        # Restore checked state
        ui_tree_item.checked = self.is_data_checked(data)
        # Restore expanded state
        ui_tree_item.expanded = ui_tree_item.name in self._expanded_items

        # Process item children
        children_data = self.get_data_children(data)
        ui_tree_item.children_count = len(children_data)

        children_range_start = len(ui_tree_collection)
        if self.ALPHABETICAL_ORDER:
            children_data = sorted(
                children_data, 
                key=self.get_data_name, 
                reverse=False
            )

        for i, child_data in enumerate(children_data):
            self._create_tree_item_from_data(
                data=child_data,
                parent_item=ui_tree_item,
                child_index=i,
            )
        # Be carefull here, do not use ui_tree_item reference after adding new items in collection
        # This is likely to crash, as internal code may re-allocate
        # the whole container (the collection) memory at some point.

        # In our case, this caused 'item.all_children_count' to be randomly reset because
        # ui_tree_item was pointing to a stale RNA struct after children were added.
        # Always re-fetch the item from the collection after modifying it.
        ui_tree_item = ui_tree_collection[item_index]
        if ui_tree_item.children_count:
            # Get range of item children
            children_range_end = len(ui_tree_collection)

            ui_tree_item.all_children_count = children_range_end - children_range_start

    def _generate_ui_tree_items(self, data_collection: Iterable):
        """
        Generate UI Items from data_collection prop.
        Process entire hierarchy with children items.
        """
        for data in data_collection:
            self._create_tree_item_from_data(data)

    def generate_ui_collection(self):
        """
        Generate a flat collection of UITreeItem
        from data_collection_prop.
        Preserve expanded state of UITreeItems using names.
        """
        self._expanded_items = self.get_expanded_items()
        # We need to clear the list used to draw items in the ui
        ui_tree_collection = self.get_ui_tree_collection()
        ui_tree_collection.clear()
        data_collection = self.get_data_collection()
        if self.ALPHABETICAL_ORDER:
            data_collection = sorted(
                data_collection, 
                key=self.get_data_name, 
                reverse=False
            )
        self._generate_ui_tree_items(data_collection)

        self._expanded_items = []

    def clear_ui_collection(self):
        ui_tree_collection = self.get_ui_tree_collection()
        ui_tree_collection.clear()

    def expand_ui_tree_item(
        self,
        expand: bool,
        item_index: int, 
        set_active: bool = False,
        update_selection: bool = False
    ) :
        """
        Set expand state of UITreeItem

        Args:
            expand: Wanted expand state.
            item_index: Index of item to expand.
            set_active: Set active item to preserve UIList scrolling. Defaults to False.
            update_selection: Triggers active index property update.
        Return:
            Return True if ui_tree_collection_prop len changed.
        """
        item: TreeItem
        item_list = self.get_ui_tree_collection()
        item = item_list[item_index]
        data = item.get_data()
        if not data:
            print(f"Item {str(item)} has no data.")
            return

        if item.expanded and expand:
            return

        if not item.expanded and not expand:
            return

        item.expanded = expand
        if item.children_count == 0:
            return

        expanded_parent_items = set([item_index])
        for i in range(item_index + 1, len(item_list)):
            try:
                child_item = item_list[i]
            except:
                break
            if child_item.parent_index in expanded_parent_items:

                parent_item = item_list[child_item.parent_index]
                if not expand:
                    # When collapsing all children even nested ones should be hidden
                    child_item.hidden = True
                    expanded_parent_items.add(i)  
                else:
                    # When expanding, only children with expanded parent should be visible
                    child_item.hidden = not parent_item.expanded 
                    if parent_item.expanded:
                        expanded_parent_items.add(i)
            else:
                break

        if set_active:
            self.set_ui_tree_active_index(item_index, update_selection)

    def get_active_item(self) -> TreeItem | None:
        ui_tree_collection_prop = self.get_ui_tree_collection()
        active_index = self._get_ui_tree_active_index()
        if active_index < 0: # if -1, means not active index set
            return None
        try:
            active_item = ui_tree_collection_prop[active_index]
            return active_item
        except IndexError:
            return None

    # region MultiSelection
    def save_flt_flags(self, flt_flags):
        self._flt_flags = flt_flags

    def item_visible_after_ui_filter(self, item: TreeItem)->bool:
        """
        Is an item visible after UIList filtering.
        """
        if not self._flt_flags:
            return True
        try:
            if self._flt_flags[item.index] : 
                return True
            return False
        except:
            return True

    def unselect_all(self):
        item_collection = self.get_ui_tree_collection()
        for item in item_collection:
            item:TreeItem
            item.selected = False

        self._has_multiselection = False
        if self.on_selection_function:
            self.on_selection_function(self, bpy.context) # type: ignore
        self.set_ui_tree_active_index(None)

    def select_all_visible(self):
        item_collection = self.get_ui_tree_collection()
        for item in item_collection:
            item:TreeItem
            if self.item_visible_after_ui_filter(item):
                item.selected = True
        active_index = self._get_ui_tree_active_index()
        if len(item_collection) and active_index < 0:
            self.set_ui_tree_active_index(0, update_selection=False)

        self.update_has_multiselection_state()
        if self.on_selection_function:
            self.on_selection_function(self, bpy.context)  # type: ignore

    def update_has_multiselection_state(self):
        selected_items = self.get_selected_items()
        self._has_multiselection = len(selected_items) > 1

        # If one item is selected but active item is not,
        # then multiselection is considered enabled.
        active_item = self.get_active_item()
        if not active_item:
            return
        if not active_item.selected and len(selected_items):
            self._has_multiselection = True

    def get_selected_items(self)->list[TreeItem]:
        """
        Must be launched after update_selected_items() 
        if you want to get up to date list.
        """
        ui_tree_collection_prop = self.get_ui_tree_collection()
        selected_items = []
        for item in ui_tree_collection_prop:
            if item.selected :
                selected_items.append(item)
        return selected_items

    def update_selected_items(self):
        """
        This must be called when user set active item in hierarchy
        in order to update items selection state.
        """
        old_active_index = self._get_ui_old_tree_active_index()
        active_index = self._get_ui_tree_active_index()
        if old_active_index != -1:

            bpy.ops.treeview.set_items_selection(
                "INVOKE_DEFAULT",
                old_active_index=old_active_index,
                new_active_index=active_index,
                tree_manager_name=self.unique_name
            )
        # Get Active index again, it can change during items selection
        active_index = self._get_ui_tree_active_index()
        self._set_ui_old_tree_active_index(active_index)

    def check_all(self, checked: bool = True, visible_only: bool = True):
        item_collection = self.get_ui_tree_collection()
        for item in item_collection:
            item: TreeItem
            if visible_only and not self.item_visible_after_ui_filter(item):
                continue
            item.checked = checked

    def get_checked_items(self)->list[TreeItem]:
        if not self.CHECKABLE_ITEMS:
            return []
        ui_tree_collection_prop = self.get_ui_tree_collection()
        checked_items = []
        for item in ui_tree_collection_prop:
            if item.checked :
                checked_items.append(item)
        return checked_items

    @staticmethod
    def _get_nested_attr(obj: Any, attr: str) -> Any:
        """Get nested attribute value.
            example : obj.my_attr_.nested_attrib
            """
        parts = attr.split(".")
        value = obj
        for part in parts:
            value = getattr(value, part)

        return value

    @staticmethod
    def _set_nested_attr(
        obj: Any, 
        attr: str, 
        value: Any, 
        trigger_update: bool = False
    ):
        """Set nested attribute..
        example : obj.my_attr_.nested_attrib
        """
        parts = attr.split(".")
        len_parts = len(parts)
        attr = obj
        for i, part in enumerate(parts):
            if i == (len_parts - 1):
                if trigger_update:
                    setattr(attr, part, value)
                else:
                    attr[part] = value
                return
            attr = getattr(attr, part)

    def update_prop_on_selected_data(
        self,
        prop_name: str,
        active_data: bpy.types.bpy_struct,
        trigger_update: bool = True,
    ):
        """
        Update data property on selected items data except active.
        Only update if active item is in selected items list.
        Update only if item data class is identical to active_data class.
        Args:
            selected items with same class.
            prop_name: Property name.
            active_obj: Currently edited object.
        """
        if self._updating_props:
            return
        if not self._has_multiselection:
            return
        self._updating_props = True

        # Check if item being edited is part of selection
        active_data_in_selection = False
        selected_items = self.get_selected_items()
        for item in selected_items:
            data = item.get_data()
            if data != active_data:
                continue
            active_data_in_selection = True
            break

        if not active_data_in_selection:
            self._updating_props = False
            return

        for item in selected_items:
            data = item.get_data()

            if data == active_data:
                continue

            if not isinstance(data,type(active_data)):
                continue

            try:
                before_value = TreeManager._get_nested_attr(data, prop_name)
                value = TreeManager._get_nested_attr(active_data, prop_name)
                if before_value == value:

                    continue

                # Can trigger property update functions
                TreeManager._set_nested_attr(data, prop_name, value, trigger_update)

            except :
                pass
        self._updating_props = False

    @staticmethod
    def make_update_callback(unique_name:str, prop_name: str):
        """
        Create a function that be can be used by a property update callback.
        """
        def _update(self, context):
            tree_manager: TreeManager | None = TreeManager.tree_manager_instances.get(
                unique_name, None
            )
            if not tree_manager:
                return
            tree_manager.update_prop_on_selected_data(prop_name, self)
        return _update
    # endregion

    # region Register

    def register(
        self,
        ul_tree_view_class: Type[UL_TreeView]
    ):
        """
        Register all necessary properties (ui tree collection, ui tree active index etc).
        Link TreeManager with provided UL_TreeView.
        """
        self.ul_tree_view_class: Type[UL_TreeView] = ul_tree_view_class

        self.ul_tree_view_class.tree_manager_name = self.unique_name

        self.ui_tree_prop_name = f"{self.unique_name}_ui_tree"
        self.active_index_prop_name = f"{self.unique_name}_active_index"
        self.old_active_index_prop_name = f"{self.unique_name}_old_active_index"

        # Import here to avoid circular import
        from _addons_utils.ui.tree_widget.item import TreeItem
        setattr(
            bpy.types.Scene,
            self.ui_tree_prop_name,
            bpy.props.CollectionProperty(type=TreeItem),
        )

        # Store UI related prop in window manager for better UI Performance.
        # WARNING: these are not saved !
        # In big scenes, properties stored in bpy.types.Scene can cause slow down since it can trigger various updates on access.
        # For example msfs_ui_active_index can freeze template_list on click if it is a bpy.types.Scene property

        if self.MULTISELECTION_SUPPORT:
            # Default multi selection function
            def on_update(_self, context):
                self.update_selected_items()

            if self.on_selection_function:

                def on_update(_self, context):
                    self.update_selected_items()
                    self.on_selection_function(self, context) # type: ignore
            setattr(
                bpy.types.WindowManager,
                self.active_index_prop_name,
                bpy.props.IntProperty(
                    name="Active item", 
                    default=0, 
                    update=on_update
                ),
            )
            setattr(
                bpy.types.WindowManager,
                self.old_active_index_prop_name,
                bpy.props.IntProperty(default=0),
            )

        else:
            on_update = None
            if self.on_selection_function:
                def on_update(_self, context):
                    self.on_selection_function(self, context) # type: ignore

            setattr(
                bpy.types.WindowManager,
                self.active_index_prop_name,
                bpy.props.IntProperty(
                    name="Active item",
                    default=0,
                    update=on_update
                ),
            )

        # Right Click Menu
        # Add custom draw function to UIList context menu
        if not(self._draw_context_menu in bpy.types.UI_MT_button_context_menu._dyn_ui_initialize()):
            bpy.types.UI_MT_button_context_menu.append(self._draw_context_menu)

    def unregister(self):
        try:
            # Only remove if there are no TreeManager instances
            if (
                not TreeManager.tree_manager_instances
                and self._draw_context_menu
                in bpy.types.UI_MT_button_context_menu._dyn_ui_initialize()
            ):
                bpy.types.UI_MT_button_context_menu.remove(self._draw_context_menu)
        except:
            pass
        try:
            TreeManager.tree_manager_instances.pop(self.unique_name)
            delattr(bpy.types.Scene, self.ui_tree_prop_name)
            delattr(bpy.types.WindowManager, self.active_index_prop_name)
            delattr(bpy.types.WindowManager, self.old_active_index_prop_name)

        except Exception:
            pass
    # endregion

    @staticmethod
    def _draw_context_menu(self, context):
        """
        Entry point for right click menu draw function.
        Launch draw_context_menu of the treemanager instance associated with
        the current ui_tree_item.
        """
        tree_item: TreeItem | None = getattr(context, "tree_item", None)

        if not tree_item:
            return

        tree_manager: TreeManager | None = TreeManager.tree_manager_instances.get(
            tree_item.tree_manager_name, None
        )
        if not tree_manager:
            return

        tree_manager.draw_context_menu(context, self.layout)

    def draw(
        self, context, layout: bpy.types.UILayout, rows: int = 10, type: str = "DEFAULT"
    ):
        layout.template_list(
            self.ul_tree_view_class.__name__,
            "",
            context.scene,
            self.ui_tree_prop_name,
            context.window_manager,
            self.active_index_prop_name,
            rows=rows,
            type=type,
            sort_lock=True,
        )


# endregion
