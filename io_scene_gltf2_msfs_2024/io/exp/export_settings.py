# glTF-Blender-IO-MSFS2024
# Copyright 2018-2021 The glTF-Blender-IO authors
# Copyright 2022 The glTF-Blender-IO-MSFS2024 authors
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


import bpy
from io_scene_gltf2_msfs_2024.blender.utils import bpy_props as bpy_props_utils

from ..com.msfs_constants import (
    EXPORT_ANIMATION_MODE,
    EXPORT_IMAGE_FORMAT
)

from . import constants

if bpy.app.version >= (5, 0, 0):
    # Blender 5.0 moved draco from io.com to io.exp
    from io_scene_gltf2.io.exp import draco as gltf2_io_draco_compression_extension
elif bpy.app.version >= (4, 5, 0):
    from io_scene_gltf2.io.com import draco as gltf2_io_draco_compression_extension
else:
    from io_scene_gltf2.io.com import gltf2_io_draco_compression_extension


def on_enable_msfs_extension(self, context: bpy.types.Context):
    if bpy.app.version < (4, 2, 0):
        self.export_nla_strips = True
        return

    self.export_animation_mode = 'NLA_TRACKS'
    if self.enable_msfs_extension:
        self.export_influence_nb = min(self.export_influence_nb, 4)


def set_influence_nb(self, value: int):
    self["export_influence_nb"] = value
    if not self.enable_msfs_extension:
        return

    if value > 4:
        self["export_influence_nb"] = 4


def get_influence_nb(self):
    return self.get("export_influence_nb", 4)


def _get_export_animation_mode(_self)->int:
    """
    Safely get export animation mode.
    """
    return bpy_props_utils.safe_enum_prop_get(
        _self=_self,
        enum_name= "export_animation_mode",
        enum_indexes= range(len(EXPORT_ANIMATION_MODE)), 
        default_index=1
    )


def _set_export_animation_mode(self, value: int):
    """Does nothing  special, enum_property needs to be provided a set function
    when defining a custom get function.
    """
    self["export_animation_mode"] = value


class MSFS2024_PT_export_settings_panels:
    @classmethod    
    def get_active_multi_exporter_settings(cls, context: bpy.types.Context)->MSFS2024_MultiExporterSettings:
        settings_presets = context.scene.msfs_multi_exporter_settings_presets
        active_settings_preset_name = context.scene.msfs_multi_exporter_settings_presets_enum

        return settings_presets[active_settings_preset_name]


# region Properties Group
class PerObjectTransformReset(bpy.types.PropertyGroup):
    """Transform export settings, used when MSFS2024_MultiExporterSettings.reset_origins
    is set to "PER_OBJECT"
    """
    reset_translation: bpy.props.BoolProperty(
        name="Reset Translation",
        default=False,
        description=(
            "Reset translation of the node.\n" 
            "If enabled, the translation will be reset to (0.0, 0.0, 0.0).\n"
            "WARNING : Effective only when reset origins is set to 'Per Object' in export settings"
        )
    ) # type: ignore
    
    reset_rotation: bpy.props.BoolProperty(
        name="Reset Rotation",
        default=False,
        description=(
            "Reset rotation of the node.\n" 
            "If enabled, the rotation will be reset to (0.0, 0.0, 0.0).\n"
            "WARNING : Effective only when reset origins is set to 'Per Object' in export settings"
        )
    ) # type: ignore
    
    reset_scale: bpy.props.BoolProperty(
        name="Reset Scale",
        default=False,
        description=(
            "Reset scale of the node.\n" 
            "If enabled, the scale will be reset to (0.0, 0.0, 0.0).\n"
            "WARNING : Effective only when reset origins is set to 'Per Object' in export settings"
        )
    ) # type: ignore

class RootTransformReset(bpy.types.PropertyGroup):
    """Transform export settings for root nodes, used when MSFS2024_MultiExporterSettings.reset_origins
    is set to ALL_ROOTS.
    """
    reset_translation: bpy.props.BoolProperty(
        name="Reset Translation",
        default=True,
        description=(
            "Reset translation of the root node.\n" 
            "If enabled, the translation will be reset to (0.0, 0.0, 0.0).\n"
        )
    ) # type: ignore
    
    reset_rotation: bpy.props.BoolProperty(
        name="Reset Rotation",
        default=True,
        description=(
            "Reset rotation of the root node.\n" 
            "If enabled, the rotation will be reset to (0.0, 0.0, 0.0).\n"
        )
    ) # type: ignore
    
    reset_scale: bpy.props.BoolProperty(
        name="Reset Scale",
        default=True,
        description=(
            "Reset scale of the root node.\n" 
            "If enabled, the scale will be reset to (0.0, 0.0, 0.0).\n"
        )
    ) # type: ignore
class MSFS2024_MultiExporterSettings(bpy.types.PropertyGroup):

    register_order = 1 #register after ResetTransform Class

    # region General Options
    name: bpy.props.StringProperty(name="Name") # type: ignore

    # keep original texture option Check
    export_keep_originals: bpy.props.BoolProperty(
        name="Keep original",
        description=(
            "Keep original textures files if possible. "
            "WARNING: if you use more than one texture, "
            "where pbr standard requires only one, only one texture will be used. "
            "This can lead to unexpected results"
        ),
        default=True,
    )  # type: ignore

    # Texture directory path
    export_texture_dir: bpy.props.StringProperty(
        name="Textures",
        description="Folder to place texture files in (if you don't set an absolute path,"
                     "it will be relative to your exported models)",
        default=""
    ) # type: ignore

    # Copyright string UI
    export_copyright: bpy.props.StringProperty(
        name="Copyright",
        description="Legal rights and conditions for the model",
        default=""
    ) # type: ignore

    # Remember export settings check
    will_save_settings: bpy.props.BoolProperty(
        name="Remember Export Settings",
        description="Store glTF export settings in the Blender project.",
        default=True
    ) # type: ignore
    # endregion

    # region MSFS2024 Parameters
    enable_msfs_extension: bpy.props.BoolProperty(
        name="Use Microsoft Flight Simulator 2024 Extensions",
        description="Enable Microsoft Flight Simulator 2024 Extensions",
        default=True,
        update=on_enable_msfs_extension
    ) # type: ignore

    # Texture Lib
    generate_texturelib: bpy.props.BoolProperty(
        name="Generate TextureLib",
        description="Generate XMLs for the textures after the export",
        default=True,
    ) # type: ignore

    # Export Process
    reset_origins: bpy.props.EnumProperty(
        name="Reset Origins",
        items=(
                (
                    "DISABLED",
                    "Disabled",
                    "Disable reset of origins"
                ),
                (
                    "ALL_ROOTS",
                    "All Roots",
                    "Reset translation, rotation and scale of exported gltf's root nodes"
                ),
                (
                    "PER_OBJECT",
                    "Per Object",
                    "Reset translation, rotation and scale of specified nodes according\n"
                    "to the object parameters specified in the MSFS2024 Transform Properties panel:\n"
                    "Reset translation, Reset rotation and Reset scale"
                )
            ),
            description="Reset Origins options",
            default="DISABLED"
    ) # type: ignore
    
    export_transform_properties: bpy.props.PointerProperty(
        name="Export Transform Properties",
        type=RootTransformReset,
        description="Reset Transform Properties for MSFS2024 Root Nodes"
    ) # type: ignore

    remove_lod_prefix: bpy.props.BoolProperty(
        name="Remove LOD prefix",
        description="Remove LOD prefixes 'x0_/x1_...' on node names",
        default=False
    ) # type: ignore

    merge_nodes: bpy.props.BoolProperty(
        name="Merge nodes",
        description="Merge Meshes into one root mesh to export",
        default=False
    ) # type: ignore

    export_as_submodel: bpy.props.BoolProperty(
        name="Export as submodel",
        description="This option is dedicated to 'Merge models'\n"
                    "(You need to use it for models contained in <MergeModel> element in the xml only)",
        default=False
    ) # type: ignore
    # endregion

    # region Include Options
    # Export Selected Only Check
    use_selection: bpy.props.BoolProperty(
        name="Selected Objects",
        description=(
            "Export selected objects only. "
            "Disabled for the use of the MultiExporter (Needs to be always checked)"
        ),
        default=True
    ) # type: ignore

    # Export Visible Only Check
    use_visible: bpy.props.BoolProperty(
        name="Visible Objects",
        description="Export visible objects only",
        default=False
    ) # type: ignore

    # Export Custom Properties Check
    export_extras: bpy.props.BoolProperty(
        name="Custom Properties",
        description="Export custom properties as glTF extras. "
                    "Must be disabled for export dedicated to Microsoft Flight Simulator 2024",
        default=False,
    ) # type: ignore

    # Export Camera Check
    export_cameras: bpy.props.BoolProperty(
        name="Cameras",
        description="Export cameras",
        default=False
    ) # type: ignore

    # Export Punctual Lights Check
    export_lights: bpy.props.BoolProperty(
        name="Punctual Lights",
        description=(
            "Export directional, point, and spot lights. "
            "Uses 'KHR_lights_punctual' glTF extension"
        ),
        default=True,
    ) # type: ignore
    # endregion

    # region Transform Options
    # Y Up Check
    export_yup: bpy.props.BoolProperty(
        name="+Y Up", description="Export using glTF convention, +Y up", default=True
    ) # type: ignore
    # endregion

    # region Scene Graph
    if bpy.app.version >= (4, 2, 0):
        # Export geometry node instances
        export_gn_mesh: bpy.props.BoolProperty(
            name="Geometry Nodes Instances (Experimental)",
            description="Export Geometry nodes instance meshes",
            default=False
        ) # type: ignore

        # Export GPU instances
        export_gpu_instances: bpy.props.BoolProperty(
            name="GPU Instances",
            description="Export using EXT_mesh_gpu_instancing. "
                        "Limited to children of a given Empty. "
                        "Multiple materials might be omitted",
            default=False
        ) # type: ignore

        # Flatten Objects
        export_hierarchy_flatten_objs: bpy.props.BoolProperty(
            name="Flatten Object Hierarchy",
            description="Flatten Object Hierarchy. "
                        "Useful in case of non decomposable transformation matrix",
            default=False
        ) # type: ignore

        export_hierarchy_full_collections: bpy.props.BoolProperty(
            name="Full Collection Hierarchy",
            description="Export full hierarchy, including intermediate collections",
            default=False
        ) # type: ignore
    # endregion

    # region Mesh
    # Export Meshes
    export_mesh: bpy.props.BoolProperty(
        name="",
        description=(
            "Enable/Disable export meshes"
            "(Useful to export animations only)"
        ),
        default=True,
    ) # type: ignore

    # Export Apply Modifiers Check
    export_apply: bpy.props.BoolProperty(
        name="Apply Modifiers",
        description=(
            "Apply modifiers (excluding Armatures) to mesh objects. "
            "WARNING: prevents exporting shape keys"
        ),
        default=False,
    ) # type: ignore

    # Export UVs Check
    export_texcoords: bpy.props.BoolProperty(
        name="UVs",
        description="Export UVs (texture coordinates) with meshes",
        default=True,
    ) # type: ignore

    # Export Normals Check
    export_normals: bpy.props.BoolProperty(
        name="Normals",
        description="Export vertex normals with meshes",
        default=True
    ) # type: ignore
 
    # Export Tangents Check
    export_tangents: bpy.props.BoolProperty(
        name="Tangents",
        description="Export vertex tangents with meshes",
        default=False
    ) # type: ignore

    if bpy.app.version < (4, 2, 0):
        # Export Vertex Colors Check
        export_colors: bpy.props.BoolProperty(
            name="Vertex Colors",
            description="Export vertex colors with meshes",
            default=True,
        ) # type: ignore
    else:
        export_vertex_color: bpy.props.EnumProperty(
            name="Use Vertex Color",
            items=(
                (
                    'MATERIAL',
                    'Material',
                    "Export vertex color when used by material"
                ),
                (
                    'NONE',
                    'None',
                    "Do not export vertex color"
                )
            ),
            description="How to export vertex color",
            default='MATERIAL'
        ) # type: ignore

        export_all_vertex_colors: bpy.props.BoolProperty(
            name='Export all vertex colors',
            description=(
                'Export all vertex colors, even if not used by any material. '
                'If no Vertex Color is used in the mesh materials, a fake COLOR_0 will be created, '
                'in order to keep material unchanged'
            ),
            default=True
        ) # type: ignore

        export_active_vertex_color_when_no_material: bpy.props.BoolProperty(
            name='Export active vertex color when no material',
            description='When there is no material on object, export active vertex color',
            default=True
        ) # type: ignore

    # Export Attributes Colors Check
    export_attributes: bpy.props.BoolProperty(
        name='Attributes',
        description='Export Attributes (when starting with underscore)',
        default=False
    ) # type: ignore

    # Export Loose Edge Check
    use_mesh_edges: bpy.props.BoolProperty(
        name="Loose Edges",
        description=(
            "Export loose edges as lines, using the material from the first material slot"
        ),
        default=False,
    ) # type: ignore

    # Export Loose Points Check
    use_mesh_vertices: bpy.props.BoolProperty(
        name="Loose Points",
        description=(
            "Export loose points as glTF points, using the material from the first material slot"
        ),
        default=False,
    ) # type: ignore

    # endregion

    # region Material
    # Export materials option Check
    export_materials: bpy.props.EnumProperty(
        name="Materials",
        items=(
            ("EXPORT", "Export", "Export all materials used by included objects"),
            (
                "PLACEHOLDER",
                "Placeholder",
                "Do not export materials, but write multiple primitive groups per mesh, keeping material slot information",
            ),
            (
                "NONE",
                "No export",
                "Do not export materials, and combine mesh primitive groups, losing material slot information",
            ),
        ),
        description="Export materials ",
        default="EXPORT",
    ) # type: ignore

    # Export Image format UI (Auto/Jpeg/None)
    export_image_format: bpy.props.EnumProperty(
        name="Images",
        items=EXPORT_IMAGE_FORMAT,
        description=(
            "Output format for images. PNG is lossless and generally preferred, but JPEG might be preferable for web "
            "applications due to the smaller file size. Alternatively they can be omitted if they are not needed"
        ),
        default="AUTO",
    ) # type: ignore

    # JPEG Quality
    export_jpeg_quality: bpy.props.IntProperty(
        name='Image quality',
        description='Quality of image export',
        default=75,
        min=0,
        max=100
    ) # type: ignore

    # Create WebP 
    export_image_add_webp: bpy.props.BoolProperty(
        name="Create WebP",
        description=(
            "Creates WebP textures for every texture. "
            "For already WebP textures, nothing happens"
        ),
        default=False
    ) # type: ignore

    # WebP Fallback
    export_image_webp_fallback: bpy.props.BoolProperty(
        name="WebP fallback",
        description=(
            "For all WebP textures, create a PNG fallback texture"
        ),
        default=False
    ) # type: ignore

    # Export unused images
    export_unused_images: bpy.props.BoolProperty(
        name="Unused images",
        description="Export images not assigned to any material",
        default=False
    ) # type: ignore

    # Export unused Textures
    export_unused_textures: bpy.props.BoolProperty(
        name="Prepare Unused textures",
        description=(
            "Export image texture nodes not assigned to any material. "
            "This feature is not standard and needs an external extension to be included in the glTF file"
        ),
        default=False
    ) # type: ignore
    # endregion

    # region Compression
    # Draco compression check 
    export_draco_mesh_compression_enable: bpy.props.BoolProperty(
        name='Draco mesh compression',
        description=(
            "Compress mesh using Draco. "
            "WARNING: Draco compression is not supported in Microsoft Flight Simulator 2024"
        ),
        default=False
    ) # type: ignore

    # Draco compression level
    export_draco_mesh_compression_level: bpy.props.IntProperty(
        name='Compression level',
        description='Compression level (0 = most speed, 6 = most compression, higher values currently not supported)',
        default=6,
        min=0,
        max=10
    ) # type: ignore

    # Draco compression position quatization
    export_draco_position_quantization: bpy.props.IntProperty(
        name='Position quantization bits',
        description='Quantization bits for position values (0 = no quantization)',
        default=14,
        min=0,
        max=30
    ) # type: ignore
 
    # Draco compression normal quatization
    export_draco_normal_quantization: bpy.props.IntProperty(
        name='Normal quantization bits',
        description='Quantization bits for normal values (0 = no quantization)',
        default=10,
        min=0,
        max=30
    ) # type: ignore

    # Draco compression texture coordinate quatization
    export_draco_texcoord_quantization: bpy.props.IntProperty(
        name='Texcoord quantization bits',
        description='Quantization bits for texture coordinate values (0 = no quantization)',
        default=12,
        min=0,
        max=30
    ) # type: ignore

    # Draco compression vertex color quatization
    export_draco_color_quantization: bpy.props.IntProperty(
        name='Color quantization bits',
        description='Quantization bits for color values (0 = no quantization)',
        default=10,
        min=0,
        max=30
    ) # type: ignore

    # Draco compression generic quantization
    export_draco_generic_quantization: bpy.props.IntProperty(
        name="Generic quantization bits",
        description="Quantization bits for generic coordinate "
                    "values like weights or joints (0 = no quantization)",
        default=12,
        min=0,
        max=30
    ) # type: ignore
    # endregion

    # region Lighting
    if bpy.app.version >= (3, 6, 0):
        # Lighting Modes
        export_import_convert_lighting_mode: bpy.props.EnumProperty(
            name="Lighting Mode",
            items=(
                (
                    "SPEC",
                    "Standard",
                    "Physically-based glTF lighting units (cd, lx, nt)"
                ),
                (
                    "COMPAT",
                    "Unitless",
                    "Non-physical,"
                    " unitless lighting. Useful when exposure controls are not available"
                ),
                (
                    "RAW",
                    "Raw (Deprecated)",
                    "Blender lighting strengths with no conversion"
                )
            ),
            description="Optional backwards compatibility for non-standard render engines. Applies to lights",
            default="SPEC"
        ) # type: ignore

    # endregion

    # region Shape Keys
    # Export Shape Keys check
    export_morph: bpy.props.BoolProperty(
        name="Shape Keys",
        description=(
            "Export shape keys (morph targets). "
        ),
        default=False
    ) # type: ignore

    # Export Shape Keys Normals check
    export_morph_normal: bpy.props.BoolProperty(
        name="Shape Key Normals",
        description=(
            "Export vertex normals with shape keys (morph targets). "
        ),
        default=False
    ) # type: ignore

    # Export Shape Keys Tangent check
    export_morph_tangent: bpy.props.BoolProperty(
        name="Shape Key Tangents",
        description=(
            "Export vertex tangents with shape keys (morph targets). "
        ),
        default=False
    ) # type: ignore

    if bpy.app.version > (4, 2, 0):
        # Use Sparse Accessors
        export_try_sparse_sk: bpy.props.BoolProperty(
            name="Use Sparse Accessor if better",
            description="Try using Sparse Accessor if it saves space",
            default=True
        ) # type: ignore
 
        # Omit Sparse accessors if empty
        export_try_omit_sparse_sk: bpy.props.BoolProperty(
            name="Omitting Sparse Accessor if data is empty",
            description="Omitting Sparse Accessor if data is empty",
            default=False
        ) # type: ignore
    # endregion

    # region Skinning
    # Skinning Option Check
    export_skins: bpy.props.BoolProperty(
        name="Skinning", description="Export skinning (armature) data", default=True
    ) # type: ignore

    # Export All Bone Influences Check
    export_all_influences: bpy.props.BoolProperty(
        name="Include All Bone Influences",
        description="Allow > 4 joint vertex influences. Models may appear incorrectly in many viewers",
        default=False,
    ) # type: ignore

    if bpy.app.version >= (4, 2, 0):
        # Nb bone influence
        export_influence_nb: bpy.props.IntProperty(
            name="Bone Influences",
            description="Choose how many Bone influences to export",
            default=4,
            min=1,
            set=set_influence_nb,
            get=get_influence_nb
        ) # type: ignore

    # endregion

    # region Armature

    # Deformation Bones Only Check
    export_def_bones: bpy.props.BoolProperty(
        name="Export Deformation Bones Only",
        description="Export Deformation bones only (and needed bones for hierarchy)",
        default=False,
    ) # type: ignore

    if bpy.app.version >= (3, 6, 0):
        # Use rest position check
        export_rest_position_armature: bpy.props.BoolProperty(
            name="Use Rest Position Armature",
            description=(
                "Export armatures using rest position as joints' rest pose. "
                "When off, current frame pose is used as rest pose"
            ),
            default=True
        ) # type: ignore

        # Flatten Bones Check
        export_hierarchy_flatten_bones: bpy.props.BoolProperty(
            name="Flatten Bone Hierarchy",
            description="Flatten Bone Hierarchy. Useful in case of non decomposable transformation matrix",
            default=False
        ) # type: ignore

    if bpy.app.version >= (4, 2, 0):
        # Remove Armature Object
        export_armature_object_remove: bpy.props.BoolProperty(
            name="Remove Armature Object",
            description=(
                "Remove Armature object if possible. "
                "If Armature has multiple root bones, object will not be removed"
            ),
            default=False
        ) # type: ignore
    # endregion

    # region Animation Options
    # Export Animation Options Check
    export_animations: bpy.props.BoolProperty(
        name="Animations",
        description="Exports active actions and NLA tracks as glTF animations",
        default=True,
    ) # type: ignore

    # Use Current Frame Check
    export_current_frame: bpy.props.BoolProperty(
        name="Use Current Frame",
        description="Export the scene in the current animation frame",
        default=False,
    ) # type: ignore

    # Limit to Playback Range Check
    export_frame_range: bpy.props.BoolProperty(
        name="Limit to Playback Range",
        description="Clips animations to selected playback range",
        default=True,
    ) # type: ignore

    # Always Sample Animations Check
    export_force_sampling: bpy.props.BoolProperty(
        name="Always Sample Animations",
        description="Apply sampling to all animations",
        default=True,
    ) # type: ignore

    # Sampling Rate Slider (1-120)
    export_frame_step: bpy.props.IntProperty(
        name="Sampling Rate",
        description="How often to evaluate animated values (in frames)",
        default=1,
        min=1,
        max=120,
    ) # type: ignore

    # Animation mode export
    if bpy.app.version >= (3, 6, 0):
        export_animation_mode: bpy.props.EnumProperty(
            name="Animation mode",
            items=EXPORT_ANIMATION_MODE,
            description="Export Animation mode",
            default="NLA_TRACKS",
            get=_get_export_animation_mode,
            set=_set_export_animation_mode,
        )  # type: ignore

        # Optimize Animation Force keeping channels for bones Check
        export_optimize_animation_keep_anim_armature: bpy.props.BoolProperty(
            name="Force keeping channels for bones",
            description=(
                "if all keyframes are identical in a rig, "
                "force keeping the minimal animation. "
                "When off, all possible channels for "
                "the bones will be exported, even if empty "
                "(minimal animation, 2 keyframes)"
            ),
            default=False
        ) # type: ignore

        # Optimize Animation Force keeping channels for objects Check
        export_optimize_animation_keep_anim_object: bpy.props.BoolProperty(
            name='Force keeping channel for objects',
            description=(
                "If all keyframes are identical for object transformations, "
                "force keeping the minimal animation"
            ),
            default=False
        ) # type: ignore

        # Export negative frames check
        export_negative_frame: bpy.props.EnumProperty(
            name='Negative Frames',
            items=(
                (
                    'SLIDE',
                    'Slide',
                    'Slide animation to start at frame 0'
                ),
               (
                   'CROP',
                   'Crop',
                   'Keep only frames above frame 0'
               )
           ),
            description='Negative Frames are slid or cropped',
            default='CROP'
        ) # type: ignore

        # Set all glTF Animation starting at 0 check
        export_anim_slide_to_zero: bpy.props.BoolProperty(
            name='Set all glTF Animation starting at 0',
            description=(
                "Set all glTF animation starting at 0.0s. "
                "Can be useful for looping animations"
            ),
            default=False
        ) # type: ignore

        # Bake all objects animation check
        export_bake_animation: bpy.props.BoolProperty(
            name='Bake All Objects Animations',
            description=(
                "Force exporting animation on every object. "
                "Can be useful when using constraints or driver. "
                "Also useful when exporting only selection"
            ),
            default=False
        ) # type: ignore

        # Split animation by object when animation mode is set to scene check
        export_anim_scene_split_object: bpy.props.BoolProperty(
            name='Split Animation by Object',
            description=(
                "Export Scene as seen in Viewport, "
                "But split animation by Object"
            ),
            default=True
        ) # type: ignore

        # Reset pose bones between actions check
        export_reset_pose_bones: bpy.props.BoolProperty(
            name='Reset pose bones between actions',
            description=(
                "Reset pose bones between each action exported. "
                "This is needed when some bones are not keyed on some animations"
            ),
            default=True
        ) # type: ignore

    else:
        # Group by NLA Track Check
        export_nla_strips: bpy.props.BoolProperty(
            name="Group by NLA Track",
            description=(
                "When on, multiple actions become part of the same glTF animation if "
                "they're pushed onto NLA tracks with the same name. "
                "When off, all the currently assigned actions become one glTF animation"
            ),
            default=True,
        ) # type: ignore

        # Export NLA strips merged animation name
        export_nla_strips_merged_animation_name: bpy.props.StringProperty(
            name='Merged Animation Name',
            description=(
                "Name of single glTF animation to be exported"
            ),
            default='Animation'
        ) # type: ignore

    # Optimize Animation Size Check
    export_optimize_animation_size: bpy.props.BoolProperty(
        name="Optimize Animation Size",
        description=(
            "Reduces exported filesize by removing duplicate keyframes"
            "Can cause problems with stepped animation"
        ),
        default=True,
    ) # type: ignore

    # Export all armature actions check
    export_anim_single_armature: bpy.props.BoolProperty(
        name="Export all Armature Actions",
        description=(
            "Export all actions, bound to a single armature. "
            "WARNING: Option does not support exports including multiple armatures"
        ),
        default=False
    ) # type: ignore

    # Export shape key animation check
    export_morph_animation: bpy.props.BoolProperty(
        name='Shape Key Animations',
        description='Export shape keys animations (morph targets)',
        default=False
    ) # type: ignore

    # Reset shape keys between actions check
    export_morph_reset_sk_data: bpy.props.BoolProperty(
        name='Reset shape keys between actions',
        description=(
            "Reset shape keys between each action exported. "
            "This is needed when some SK channels are not keyed on some animations"
        ),
        default=False
    ) # type: ignore

    if bpy.app.version >= (4, 2, 0):
        # Disable viewport for objects when exporting animations
        export_optimize_disable_viewport: bpy.props.BoolProperty(
            name="Disable viewport for other objects",
            description=(
                "When exporting animations, disable viewport for other objects "
                "(for performance)"
            ),
            default=False
        ) # type: ignore

    # endregion
# endregion

# region Operators
class MSFS2024_OT_AddSettingsPreset(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_add_settings_preset"
    bl_label = "Add settings preset"
    bl_options = {"INTERNAL"}

    @staticmethod
    def apply_version_dependent_defaults(preset: MSFS2024_MultiExporterSettings):
        """Apply Blender-version-dependent default settings to the preset."""

        if bpy.app.version >= (3, 6, 0):
            defaut_anim_mode = "ACTIONS" if bpy.app.version >= (4, 5, 0) else "NLA_TRACKS"
            preset.export_animation_mode = defaut_anim_mode

    def execute(self, context: bpy.types.Context):
        settings_presets = context.scene.msfs_multi_exporter_settings_presets
        settings_preset = settings_presets.add()
        settings_preset.name = f"Settings preset {len(settings_presets) - 1}"
        self.apply_version_dependent_defaults(settings_preset)

        # Update Enum
        context.scene.msfs_multi_exporter_settings_presets_enum = settings_preset.name
        return {"FINISHED"}


class MSFS2024_OT_RemoveSettingsPreset(bpy.types.Operator):
    bl_idname = "msfs2024.multi_export_remove_settings_preset"
    bl_label = "Remove settings preset"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        settings_presets = context.scene.msfs_multi_exporter_settings_presets
        active_settings_preset_name = context.scene.msfs_multi_exporter_settings_presets_enum
        if active_settings_preset_name == "Default":
            return {"CANCELLED"}

        setting_preset_idx = settings_presets.find(active_settings_preset_name)
        settings_presets.remove(setting_preset_idx)

        # Set previous value to enum after removing
        context.scene.msfs_multi_exporter_settings_presets_enum = settings_presets[setting_preset_idx - 1].name
        return {"FINISHED"}


class MSFS2024_OT_EditSettingsPresetName(bpy.types.Operator, MSFS2024_PT_export_settings_panels):
    bl_idname = "msfs2024.multi_export_edit_settings_preset_name"
    bl_label = "Edit settings preset name"
    bl_options = {"INTERNAL"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        self.layout.prop(active_settings_preset, "name")

    def execute(self, context: bpy.types.Context):
        return {"FINISHED"}


# endregion

# region Panels
class MSFS2024_PT_export_settings_preset(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = ""
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"HIDE_HEADER"}


    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        active_settings_preset_name = context.scene.msfs_multi_exporter_settings_presets_enum

        row = layout.row()
        col = row.column()
        col.prop(
            context.scene,
            "msfs_multi_exporter_settings_presets_enum",
            text=""
        )
        col = row.column()
        col.operator(MSFS2024_OT_EditSettingsPresetName.bl_idname, text="", icon="TEXT")
        if active_settings_preset_name == "Default":
            col.enabled = False

        col = row.column()
        col.operator(MSFS2024_OT_AddSettingsPreset.bl_idname, text="", icon="ADD")

        col = row.column()
        col.operator(MSFS2024_OT_RemoveSettingsPreset.bl_idname, text="", icon="REMOVE")
        if active_settings_preset_name == "Default":
            col.enabled = False

class MSFS2024_PT_export_main(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "General"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):

        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.prop(context.scene, "msfs_background_export")
        layout.separator()
        layout.prop(active_settings_preset, "export_copyright")
        layout.prop(active_settings_preset, "will_save_settings")

class MSFS2024_PT_export_texture(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Textures"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw_header(self, context: bpy.types.Context):
        self.layout.label(icon="FILE_IMAGE")

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.prop(active_settings_preset, "export_keep_originals")
        if active_settings_preset.export_keep_originals is False:
            layout.prop(active_settings_preset, "export_texture_dir", icon="FILE_FOLDER")

# region MSFS2024
class MSFS2024_PT_MSFS2024_export(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Microsoft Flight Simulator 2024"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw_header(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)

        self.layout.label(icon='TOOL_SETTINGS')
        self.layout.prop(active_settings_preset, "enable_msfs_extension", text="")

    def draw(self, context: bpy.types.Context):
        return

class MSFS2024_PT_MSFS2024_texture(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Textures"
    bl_parent_id = "MSFS2024_PT_MSFS2024_export"
    bl_options = {"DEFAULT_CLOSED"}

    register_order = 1 # Register after MSFS2024_PT_MSFS2024_export class

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.active = active_settings_preset.enable_msfs_extension
        layout.prop(
            active_settings_preset,
            "generate_texturelib",
            text="Generate TextureLib"
        )

class MSFS2024_PT_MSFS2024_process(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Export Process"
    bl_parent_id = "MSFS2024_PT_MSFS2024_export"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.active = active_settings_preset.enable_msfs_extension
        
        row = layout.row()
        row.prop(active_settings_preset, "reset_origins")
        if active_settings_preset.reset_origins == "ALL_ROOTS":
            box = layout.box()
            box.prop(active_settings_preset.export_transform_properties, "reset_translation")
            box.prop(active_settings_preset.export_transform_properties, "reset_rotation")
            box.prop(active_settings_preset.export_transform_properties, "reset_scale")
            
        layout.prop(active_settings_preset, "remove_lod_prefix")
        layout.prop(active_settings_preset, "merge_nodes")
        layout.prop(active_settings_preset, "export_as_submodel")

# endregion

class MSFS2024_PT_export_include(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Include"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        # To use the MultiExporter panel, it's important to have "use selected" to True
        col = layout.column(heading="", align=True)
        col.prop(active_settings_preset, "use_selection")
        col.enabled = False
        
        col = layout.column(heading="Limit to", align=True)
        col.prop(active_settings_preset, "use_visible")

        if not active_settings_preset.enable_msfs_extension:
            col = layout.column(heading="", align=True)
            col.prop(active_settings_preset, "export_extras")

        col = layout.column(heading="Data", align=True)
        col.prop(active_settings_preset, "export_cameras")
        col.prop(active_settings_preset, "export_lights")

class MSFS2024_PT_export_transform(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Transform"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        layout.prop(active_settings_preset, "export_yup")
        # Yup is always enabled when using msfs extension
        layout.enabled = not active_settings_preset.enable_msfs_extension
class MSFS2024_PT_export_scene_graph(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Scene Graph"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        active_settings_preset = MSFS2024_PT_export_settings_panels.get_active_multi_exporter_settings(context)

        return (
            context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier
            and not active_settings_preset.enable_msfs_extension
            and bpy.app.version >= (4, 2, 0)
        )

    def draw(self, context: bpy.types.Context):
        if bpy.app.version < (4, 2, 0):
            return
        
        active_settings_preset = self.get_active_multi_exporter_settings(context)

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.prop(active_settings_preset, "export_gn_mesh")
        layout.prop(active_settings_preset, "export_gpu_instances")
        layout.prop(active_settings_preset, "export_hierarchy_flatten_objs")
        layout.prop(active_settings_preset, "export_hierarchy_full_collections")

class MSFS2024_PT_export_geometry(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Mesh"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw_header(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)

        self.layout.label(icon="MESH_DATA")
        self.layout.prop(active_settings_preset, "export_mesh", text="")

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.active = active_settings_preset.export_mesh
        layout.prop(active_settings_preset, "export_apply")
        layout.prop(active_settings_preset, "export_texcoords")
        layout.prop(active_settings_preset, "export_normals")

        col = layout.column()
        col.prop(active_settings_preset, "export_tangents")
        col.active = active_settings_preset.export_normals

        if bpy.app.version < (4, 2, 0):
            layout.prop(active_settings_preset, "export_colors")

        if bpy.app.version >= (3, 6, 0):
            layout.prop(active_settings_preset, "export_attributes")

        layout.prop(active_settings_preset, "use_mesh_edges")
        layout.prop(active_settings_preset, "use_mesh_vertices")

        if bpy.app.version >= (4, 2, 0):
            header, body = layout.panel("MSFS2024_PT_export_vertex_colors", default_closed=True)
            header.label(text="Vertex Colors")
            if body:
                body.prop(active_settings_preset, "export_vertex_color")
                body.prop(active_settings_preset, "export_all_vertex_colors")
                body.prop(active_settings_preset, "export_active_vertex_color_when_no_material")

class MSFS2024_PT_export_material(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Material"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw_header(self, context: bpy.types.Context):
        self.layout.label(icon="MATERIAL_DATA")

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.prop(active_settings_preset, "export_materials")
        col = layout.column()
        col.active = active_settings_preset.export_materials == "EXPORT"

        if active_settings_preset.enable_msfs_extension:
            return

        col.prop(active_settings_preset, "export_image_format")

        if bpy.app.version >= (3, 6, 0):
            col.prop(active_settings_preset, "export_jpeg_quality")

        if bpy.app.version >= (4, 2, 0):
            col.prop(active_settings_preset, "export_image_add_webp")
            col.prop(active_settings_preset, "export_image_webp_fallback")

            header, body = layout.panel("MSFS2024_PT_export_unused_images_textures", default_closed=True)
            header.label(text="Unused Textures & Images")
            if body:
                body.prop(active_settings_preset, "export_unused_images")
                body.prop(active_settings_preset, "export_unused_textures")

class MSFS2024_PT_export_shapekeys(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Shape Keys"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw_header(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)

        self.layout.label(icon="SHAPEKEY_DATA")
        self.layout.prop(active_settings_preset, "export_morph", text="")

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        
        layout.active = active_settings_preset.export_morph

        layout.prop(active_settings_preset, "export_morph_normal")
        col = layout.column()
        col.active = active_settings_preset.export_morph_normal
        col.prop(active_settings_preset, "export_morph_tangent")

        if active_settings_preset.enable_msfs_extension:
            return

        if bpy.app.version >= (4, 2, 0) and not active_settings_preset.enable_msfs_extension:
            header, body = layout.panel("MSFS2024_PT_export_optimize_shapekeys", default_closed=True)
            header.label(text="Optimize Shape Keys")
            if not body:
                return
            col = body.column()
            col.prop(active_settings_preset, "export_try_sparse_sk")
            col = body.column()
            col.active = active_settings_preset.export_try_sparse_sk
            col.prop(active_settings_preset, "export_try_omit_sparse_sk")

class MSFS2024_PT_export_armature(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Armature"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return (
            bpy.app.version >= (3, 3, 0)
            and context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier
        )

    def draw_header(self, context: bpy.types.Context):
        self.layout.label(icon="ARMATURE_DATA")

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.active = active_settings_preset.export_skins

        if bpy.app.version >= (3, 6, 0) :
            # Export rest position is always enabled when using msfs extension
            sub_layout = layout.row()
            sub_layout.prop(active_settings_preset, "export_rest_position_armature")
            sub_layout.enabled = not active_settings_preset.enable_msfs_extension

        if bpy.app.version >= (3, 3, 0):
            row = layout.row()
            row.active = active_settings_preset.export_force_sampling
            row.prop(active_settings_preset, "export_def_bones")
            if (
                active_settings_preset.export_force_sampling is False
                and active_settings_preset.export_def_bones is True
            ):
                layout.label(text="Export only deformation bones is not possible when not sampling animation")

            if bpy.app.version >= (4, 2, 0):
                layout.prop(active_settings_preset, "export_armature_object_remove")

            if bpy.app.version >= (3, 6, 0):
                layout.prop(active_settings_preset, "export_hierarchy_flatten_bones")

class MSFS2024_PT_export_skinning(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Skinning"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw_header(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)

        self.layout.label(icon="MOD_SKIN")
        self.layout.prop(active_settings_preset, "export_skins", text="")

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        layout.active = active_settings_preset.export_skins

        if bpy.app.version >= (4, 2, 0):
            layout.prop(active_settings_preset, "export_influence_nb")

        if not active_settings_preset.enable_msfs_extension:
            layout.prop(active_settings_preset, "export_all_influences")

class MSFS2024_PT_export_Lighting(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Lighting"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        active_settings_preset = MSFS2024_PT_export_settings_panels.get_active_multi_exporter_settings(context)
        
        return (
            context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier
            and bpy.app.version >= (3, 6, 0)
            and not active_settings_preset.enable_msfs_extension
        )

    def draw(self, context: bpy.types.Context):
        if bpy.app.version < (3, 6, 0):
            return

        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.prop(active_settings_preset, "export_import_convert_lighting_mode")

class MSFS2024_PT_export_geometry_compression(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Compression"
    bl_parent_id = "MSFS2024_PT_export_geometry"
    bl_options = {'DEFAULT_CLOSED'}

    register_order = 1 # Register after MSFS2024_PT_export_geometry class

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_draco_available = gltf2_io_draco_compression_extension.dll_exists(quiet=True)

    @classmethod
    def poll(cls, context: bpy.types.Context):
        active_settings_preset = MSFS2024_PT_export_settings_panels.get_active_multi_exporter_settings(context)

        return (
            context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier
            and active_settings_preset.export_draco_mesh_compression_enable
        )

    def draw_header(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        self.layout.prop(active_settings_preset, "export_draco_mesh_compression_enable", text="")

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.active = active_settings_preset.export_draco_mesh_compression_enable
        layout.prop(active_settings_preset, "export_draco_mesh_compression_level")

        col = layout.column(align=True)
        col.prop(active_settings_preset, "export_draco_position_quantization", text="Quantize Position")
        col.prop(active_settings_preset, "export_draco_normal_quantization", text="Normal")
        col.prop(active_settings_preset, "export_draco_texcoord_quantization", text="Tex Coord")
        col.prop(active_settings_preset, "export_draco_color_quantization", text="Color")
        col.prop(active_settings_preset, "export_draco_generic_quantization", text="Generic")

class MSFS2024_PT_export_animation(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Animation"
    bl_parent_id = "MSFS2024_PT_MultiExporter"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier

    def draw_header(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)

        self.layout.label(icon="ANIM")
        self.layout.prop(active_settings_preset, "export_animations", text="")

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.active = active_settings_preset.export_animations

        if bpy.app.version >= (3, 6, 0):                
            row = layout.row()
            row.prop(active_settings_preset, 'export_animation_mode')

            if active_settings_preset.export_animation_mode == "ACTIVE_ACTIONS":
                layout.prop(active_settings_preset, 'export_nla_strips_merged_animation_name')

            row = layout.row()
            row.active = (
                active_settings_preset.export_force_sampling
                and active_settings_preset.export_animation_mode in ['ACTIONS', 'ACTIVE_ACTIONS']
            )
            row.prop(active_settings_preset, 'export_bake_animation')

            if active_settings_preset.export_animation_mode == "SCENE":
                layout.prop(active_settings_preset, 'export_anim_scene_split_object')
        else:
            layout.prop(active_settings_preset, "export_current_frame")
            layout.prop(active_settings_preset, "export_frame_range")
            layout.prop(active_settings_preset, "export_frame_step")
            layout.prop(active_settings_preset, "export_force_sampling")
            
            row = layout.row()
            row.prop(active_settings_preset, "export_nla_strips")

            if (
                active_settings_preset.export_nla_strips is False
                and bpy.app.version >= (3, 3, 0)
            ):
                layout.prop(active_settings_preset, "export_nla_strips_merged_animation_name")

            layout.prop(active_settings_preset, "export_optimize_animation_size")
            if bpy.app.version >= (3, 3, 0):
                layout.prop(active_settings_preset, "export_anim_single_armature")
            else:
                layout.prop(active_settings_preset, 'export_def_bones')

class MSFS2024_PT_export_animation_notes(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Notes"
    bl_parent_id = "MSFS2024_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    register_order = 1 #Register after MSFS2024_PT_export_animation class

    @classmethod
    def poll(cls, context: bpy.types.Context):
        active_settings_preset = MSFS2024_PT_export_settings_panels.get_active_multi_exporter_settings(context)

        return (
            context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier
            and bpy.app.version >= (3, 6, 0)
            and active_settings_preset.export_animation_mode in ["NLA_TRACKS", "SCENE"]
        )

    def draw(self, context: bpy.types.Context):
        if bpy.app.version < (3, 6, 0):
            return

        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        if active_settings_preset.export_animation_mode == "SCENE":
            layout.label(text="Scene mode uses full bake mode:")
            layout.label(text="- sampling is active")
            layout.label(text="- baking all objects is active")
            layout.label(text="- Using scene frame range")
        elif active_settings_preset.export_animation_mode == "NLA_TRACKS":
            layout.label(text="Track mode uses full bake mode:")
            layout.label(text="- sampling is active")
            layout.label(text="- baking all objects is active")

class MSFS2024_PT_export_animation_ranges(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Rest & Ranges"
    bl_parent_id = "MSFS2024_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    register_order = 1 #After MSFS2024_PT_export_animation register
    @classmethod
    def poll(cls, context: bpy.types.Context):
        return (
            context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier
            and bpy.app.version >= (3, 6, 0)
        )

    def draw(self, context: bpy.types.Context):
        if bpy.app.version < (3, 6, 0):
            return
        
        active_settings_preset = self.get_active_multi_exporter_settings(context)

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.prop(active_settings_preset, 'export_current_frame')
        row = layout.row()
        row.active = active_settings_preset.export_animation_mode in ['ACTIONS', 'ACTIVE_ACTIONS', 'NLA_TRACKS']
        row.prop(active_settings_preset, 'export_frame_range')
        layout.prop(active_settings_preset, 'export_anim_slide_to_zero')
        row = layout.row()
        row.active = active_settings_preset.export_animation_mode in ['ACTIONS', 'ACTIVE_ACTIONS', 'NLA_TRACKS']
        layout.prop(active_settings_preset, 'export_negative_frame')

class MSFS2024_PT_export_animation_armature(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Armature"
    bl_parent_id = "MSFS2024_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    register_order = 1 #Register after MSFS2024_PT_export_animation class

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return (
            context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier
            and bpy.app.version >= (3, 6, 0)
        )

    def draw(self, context: bpy.types.Context):
        if bpy.app.version < (3, 6, 0):
            return
        
        active_settings_preset = self.get_active_multi_exporter_settings(context)

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.active = active_settings_preset.export_animations

        layout.prop(active_settings_preset, 'export_anim_single_armature')
        layout.prop(active_settings_preset, 'export_reset_pose_bones')

class MSFS2024_PT_export_animation_shapekeys(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Shape keys Animation"
    bl_parent_id = "MSFS2024_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return (
            context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier
            and bpy.app.version >= (3, 6, 0)
        )

    def draw_header(self, context: bpy.types.Context):
        if bpy.app.version < (3, 6, 0):
            return

        active_settings_preset = self.get_active_multi_exporter_settings(context)

        self.layout.active = (
            active_settings_preset.export_animations
            and active_settings_preset.export_morph
        )
        self.layout.prop(active_settings_preset, "export_morph_animation", text="")

    def draw(self, context: bpy.types.Context):
        if bpy.app.version < (3, 6, 0):
            return
        
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.active = active_settings_preset.export_animations
        layout.prop(active_settings_preset, "export_morph_reset_sk_data")

class MSFS2024_PT_export_animation_sampling(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Sampling Animations"
    bl_parent_id = "MSFS2024_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return (
            context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier
            and bpy.app.version >= (3, 6, 0)
        )

    def draw_header(self, context: bpy.types.Context):
        if bpy.app.version < (3, 6, 0):
            return

        active_settings_preset = self.get_active_multi_exporter_settings(context)

        self.layout.active = (
            active_settings_preset.export_animations
            and active_settings_preset.export_animation_mode in ['ACTIONS', 'ACTIVE_ACTIONS']
        )
        self.layout.prop(active_settings_preset, "export_force_sampling", text="")

    def draw(self, context: bpy.types.Context):
        if bpy.app.version < (3, 6, 0):
            return
        
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.active = active_settings_preset.export_animations
        layout.prop(active_settings_preset, 'export_frame_step')

class MSFS2024_PT_export_animation_optimize(bpy.types.Panel, MSFS2024_PT_export_settings_panels):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Optimize Animations"
    bl_parent_id = "MSFS2024_PT_export_animation"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return (
            context.scene.msfs_multi_exporter_current_tab == constants.Tabs.SETTINGS.identifier
            and bpy.app.version >= (3, 6, 0)
        )

    def draw(self, context: bpy.types.Context):
        active_settings_preset = self.get_active_multi_exporter_settings(context)
        
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        layout.active = active_settings_preset.export_animations

        layout.prop(active_settings_preset, "export_optimize_animation_size")

        row = layout.row()
        row.prop(active_settings_preset, "export_optimize_animation_keep_anim_armature")

        row = layout.row()
        row.prop(active_settings_preset, "export_optimize_animation_keep_anim_object")

        if bpy.app.version >= (4, 2, 0):
            row = layout.row()
            row.prop(active_settings_preset, "export_optimize_disable_viewport")

# endregion
def init_setting_presets():
    """
    Make sure that msfs_multi_exporter_settings_presets contains 
    one default setting preset.
    """
    settings_presets = bpy.context.scene.msfs_multi_exporter_settings_presets
    if len(settings_presets) <= 0:
        default_settings_preset = settings_presets.add()
        default_settings_preset.name = "Default"

def get_setting_presets_items(self, context: bpy.types.Context)->list[tuple[str, str, str]]:
    init_setting_presets()
    settings_presets = context.scene.msfs_multi_exporter_settings_presets  
    enum_items = []
    for settings_preset in settings_presets:
        data = str(settings_preset.name)
        item = (data, data, data)
        enum_items.append(item)
    return enum_items

def register():

    bpy.types.Scene.msfs_multi_exporter_settings_presets = bpy.props.CollectionProperty( # type: ignore
        type=MSFS2024_MultiExporterSettings
    )
    
    bpy.types.Scene.msfs_multi_exporter_settings_presets_enum = bpy.props.EnumProperty( # type: ignore
        name="Settings Presets",
        items=get_setting_presets_items
    )

    bpy.types.Scene.msfs_background_export = bpy.props.BoolProperty( # type: ignore
        name="Export In Background", 
        description=(
            "Export in a separate background process, allowing you\n"
            "to continue working in Blender.\n"
            "WARNING: This setting is global and common to all export presets"
        ),
        default=True,
    )

def unregister():
    try:
        del bpy.types.Scene.msfs_multi_exporter_settings_presets # type: ignore
        del bpy.types.Scene.msfs_multi_exporter_settings_presets_enum # type: ignore
        del bpy.types.Scene.msfs_background_export # type: ignore
    except:
        pass
