import bpy

class AddonUtilsPreferences(bpy.types.PropertyGroup):
    pass
    
def register():
    bpy.types.Scene.addon_utils_preferences = bpy.props.PointerProperty(
        name="Addon Utils Preferences",
        type=AddonUtilsPreferences
    )

def unregister():
    try:
        del bpy.types.Scene.addon_utils_preferences
    except AttributeError:
        pass
