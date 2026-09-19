"""
Utilities to manipulate geometry node modifiers and node groups.
"""

from typing import Any

import bpy

def get_input_identifier(
    node_group: bpy.types.NodeGroup, input_label: str
) -> None | str:
    """Get the unique identifier of a node group input by using input label name.

    Returns:
        str: The identifier if found, otherwise None.
    """
    if bpy.app.version < (4, 0, 0):

        inputs = node_group.inputs
        input = inputs.get(input_label, None)
        if not input:
            return None
        identifier = input.identifier
        return identifier
    else:
        for item in node_group.interface.items_tree:  # type: ignore
            if not item.in_out == "INPUT" or not item.name == input_label:  # type: ignore
                continue

            return item.identifier
    return None

def get_modifier_by_node_group(
    obj:bpy.types.Object,
    node_group_id_name: str,
) -> bpy.types.Modifier | None:
    """Get the first modifier of an object using provided node_group 

    Object data should be of curve type.
    """
    if not obj.type == "CURVE":
        return None
    for mod in obj.modifiers:
        if not mod.type == "NODES" or not mod.node_group:
            continue
        
        if mod.node_group.name.startswith(
            node_group_id_name
        ):
            return mod

    return None

def _is_geometry_node_modifier(modifier):
    if modifier.type != "NODES":
        return False
    node_group: bpy.types.NodeGroup = modifier.node_group  # type: ignore
    if not node_group:
        return False
    return True

# --- Blender 5.x compatibility -------------------------------------------
# Blender 5.0 stopped storing Geometry Nodes modifier inputs as ID properties:
# modifier["Socket_1"] now raises "id properties not supported for this type".
# Inputs live under modifier.properties.inputs.<identifier>.value instead.
# Menu sockets expose an enum *string* there, while Blender < 5 stored the
# item index as an int. The helpers below keep the int convention so callers
# (gizmo creation, ASOBO_gizmo_object import/export) stay version independent.
def _get_input_property_5x(modifier: bpy.types.Modifier, input_identifier: str):
    return getattr(modifier.properties.inputs, input_identifier, None)


def _get_value_rna_property(prop):
    return prop.bl_rna.properties.get("value")


def _get_modifier_input_5x(modifier: bpy.types.Modifier, input_identifier: str) -> Any | None:
    prop = _get_input_property_5x(modifier, input_identifier)
    if prop is None:
        return None
    value = prop.value
    rna_prop = _get_value_rna_property(prop)
    if rna_prop is not None and rna_prop.type == "ENUM":
        item = rna_prop.enum_items.get(value)
        if item is not None:
            return item.value
    return value


def _set_modifier_input_5x(modifier: bpy.types.Modifier, input_identifier: str, value: Any):
    prop = _get_input_property_5x(modifier, input_identifier)
    if prop is None:
        return
    rna_prop = _get_value_rna_property(prop)
    if rna_prop is not None and rna_prop.type == "ENUM" and not isinstance(value, str):
        for item in rna_prop.enum_items:
            if item.value == value:
                value = item.identifier
                break
    prop.value = value
# -------------------------------------------------------------------------


def get_modifier_input(
    modifier: bpy.types.Modifier, input_label: str
) -> Any | None:
    """
    Get modifier input value using input label
    """
    if not _is_geometry_node_modifier(modifier):
        raise TypeError("Not a valid Geometry Node modifier!")

    input_identifier = get_input_identifier(modifier.node_group, input_label)
    if not input_identifier:
        return None
    if bpy.app.version >= (5, 0, 0):
        return _get_modifier_input_5x(modifier, input_identifier)
    return modifier[input_identifier]


def set_modifier_input(modifier: bpy.types.Modifier, input_label: str, value: Any):
    """
    Set modifier input value using input label
    """
    if not _is_geometry_node_modifier(modifier):
        raise TypeError("Not a valid Geometry Node modifier!")

    input_identifier = get_input_identifier(modifier.node_group, input_label)
    if not input_identifier:
        return
    if bpy.app.version >= (5, 0, 0):
        _set_modifier_input_5x(modifier, input_identifier, value)
        return
    modifier[input_identifier] = value
