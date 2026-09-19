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
import math
from mathutils import Color
import bpy

from .utils.msfs_utils import MSFS2024_Enum_Properties

class MSFS2024LightPropertiesEnum(MSFS2024_Enum_Properties):
    """
        Enum describing the parameters of lights contains Tuples of:
        ( 
            The name that appears in the UI, 
            Default Value, 
            attribute name of the property, 
            name that appear in the extension when it's exported/imported
        )
    """

    ## Parameters
    LIGHTTYPE = "Light Type", "NONE", "msfs_light_type", None
    LIGHT_TEMPERATURE = "Kelvin", 6500, "msfs_light_temperature", None
    LIGHT_TEMPERATURE_PREVIEW = "Kelvin Preview", [1.0, 1.0, 1.0], "msfs_light_temperature_preview", None 
    USE_LIGHT_TEMPERATURE = "Use Kelvin", False, "msfs_light_use_temperature", None
    LIGHTCOLOR = "RGB", [1.0, 1.0, 1.0], "msfs_light_color", "color"
    LIGHTINTENSITY = "Intensity (cd)", 10000.0, "msfs_light_intensity", "intensity"
    LIGHTDAYTIMEINTENSITY = "Daytime Intensity Override (cd)", 10000.0, "msfs_light_daytime_intensity", "daytime_intensity"
    HASLIGHTSYMMETRY = "Has symmetry", False, "msfs_light_has_symmetry", "has_symmetry"
    LIGHTDAYNIGHTCYCLE = "Day/Night Cycle", False, "msfs_light_day_night_cycle", "day_night_cycle"
    LIGHTFLASHFREQUENCY = "Frequency (1/min)", 0.0, "msfs_light_flash_frequency", "flash_frequency"
    LIGHTFLASHDURATION = "Duration (s)", 0.2, "msfs_light_flash_duration", "flash_duration"
    LIGHTFLASHPHASE = "Phase (s)", 0.0, "msfs_light_flash_phase", "flash_phase"
    LIGHTROTATIONPHASE = "Rotation Phase", 0.0, "msfs_light_rotation_phase", "rotation_phase"
    LIGHTROTATIONSPEED = "Rotation Speed (RPM)", 0.0, "msfs_light_rotation_speed", "rotation_speed"
    LIGHTRANDOMPHASE = "Random Phase", True, "msfs_light_random_phase", "random_phase"
    LIGHTCONEANGLE = "Cone Angle", 45.0, "msfs_light_cone_angle", "cone_angle"
    LIGHTSHAPE = "Shape", "point", "msfs_light_shape_type", "shape_type"
    LIGHTSOURCERADIUS = "Source Radius (cm)", 50.0, "msfs_light_source_radius", "source_radius"
    LIGHTINNERANGLE = "Inner Angle", 0.0, "msfs_light_inner_angle", "inner_cone_angle"
    LIGHTOUTERANGLE = "Outer Angle", 160.0, "msfs_light_outer_angle", "outer_cone_angle"
    LIGHTCHANNELEXTERIOR = "Exterior", True, "msfs_light_channel_exterior", "channel_exterior"
    LIGHTCHANNELINTERIOR = "Interior", True, "msfs_light_channel_interior", "channel_interior"
    FLARE_ENABLED = "Lens Flare", True, "msfs_light_lens_flare", "flare_enabled"
    FLARE_ONLY = "Flare Only", False, "msfs_light_flare_only", "flare_only"


def sync_blender_params(self, context):
    """
    Set Blender light params in order to match
    engine rendering.
    """
    msfs_light_properties = None
    if isinstance(self, bpy.types.Light):
        msfs_light_properties = self.msfs_light_properties
    elif isinstance(self, MSFS2024LightProperties):
        msfs_light_properties = self

    if not msfs_light_properties:
        return

    msfs_light_properties: MSFS2024LightProperties
    light_data = msfs_light_properties.get_active_light_data()
    if light_data is None:
        return
    light_type = light_data.msfs_light_type
    if light_type == "streetLight":
        msfs_light_properties.set_street_light(light_data)
    elif light_type == "advancedLight":
        msfs_light_properties.set_advanced_light(light_data)
    elif light_type == "skyPortalLight":
        msfs_light_properties.set_skyportal_light(light_data)


class MSFS2024LightProperties(bpy.types.PropertyGroup):
    # region Common Light Methods
    def get_active_light_data(self):

        if isinstance(self, bpy.types.Light):
            return self

        light_data = self.id_data
        if not light_data:
            return None

        if not isinstance(light_data, bpy.types.Light):
            return None

        return light_data

    @staticmethod
    def set_change_attr(obj, attrib_name, value):
        """
        Only set Prop if value is different.
        Prevents unecessary assignment and viewport redraw.
        """
        old_value = getattr(obj, attrib_name, None)
        if old_value == value:
            return
        setattr(obj, attrib_name, value)

    @staticmethod
    def temperatureToColor(temperature):
        # Temperature to CIE 1960
        u = (
            (0.860117757 + 0.000154118254 * temperature + 0.000000128641212 * temperature * temperature)
            / (1.0 + 0.000842420235 * temperature + 0.000000708145163 * temperature * temperature)
        )
        v = (
            (0.317398726 + 0.0000422806245 * temperature + 0.0000000420481691 * temperature * temperature)
            / (1.0 - 0.0000289741816 * temperature + 0.000000161456053 * temperature * temperature)
        )

        # CIE to xyY
        xx = 3.0 * u / (2.0 * u - 8.0 * v + 4.0)
        yy = 2.0 * v / (2.0 * u - 8.0 * v + 4.0)
        Y = 1.0

        # xyY to XYZ
        X = xx * Y / yy
        Z = (1.0 - xx - yy) * Y / yy

        # XYZ to RGB (color primaries and white point from sRGB)
        R = 3.2404542 * X - 1.5371385 * Y - 0.4985314 * Z
        G = - 0.9692660 * X + 1.8760108 * Y + 0.0415560 * Z
        B = 0.0556434 * X - 0.2040259 * Y + 1.0572252 * Z

        # Normalize
        m = B
        if R > G and R > B:
            m = R

        if R <= G and G > B:
            m = G

        R /= m
        G /= m
        B /= m

        if R < 0: R = 0
        if G < 0: G = 0
        if B < 0: B = 0

        #convert to linear
        R=math.pow(R,2.2)
        G=math.pow(G,2.2)
        B=math.pow(B,2.2)

        return [R, G, B]

    @staticmethod
    def update_light_color(light_data):
        use_light_temperature = getattr(
            light_data.msfs_light_properties,
            MSFS2024LightPropertiesEnum.USE_LIGHT_TEMPERATURE.attribute_name(),
        )
        new_light_color = None
        if not use_light_temperature:

            new_light_color = getattr(
                light_data.msfs_light_properties,
                MSFS2024LightPropertiesEnum.LIGHTCOLOR.attribute_name(),
            )

        else:
            temperature = getattr(
                light_data.msfs_light_properties,
                MSFS2024LightPropertiesEnum.LIGHT_TEMPERATURE.attribute_name(),
            )

            new_light_color = Color(MSFS2024LightProperties.temperatureToColor(temperature))

            # Use [] operator to set attrib
            # It prevents infinite recursion with properties update calls
            light_data.msfs_light_properties[
                MSFS2024LightPropertiesEnum.LIGHTCOLOR.attribute_name()
            ] = new_light_color

            # Set color preview for UI Feedback
            setattr(
                light_data.msfs_light_properties,
                MSFS2024LightPropertiesEnum.LIGHT_TEMPERATURE_PREVIEW.attribute_name(),
                new_light_color,
            )

        MSFS2024LightProperties.set_change_attr(light_data, "color", new_light_color)

    @staticmethod
    def set_custom_distance(light_data, distance):
        """
        Set light cutoff distance
        """
        light_data.use_custom_distance = True
        light_data.cutoff_distance = distance

    @staticmethod
    def update_light_intensity(light_data):

        intensity = getattr(
            light_data.msfs_light_properties,
            MSFS2024LightPropertiesEnum.LIGHTINTENSITY.attribute_name(),
        )

        intensity = intensity * 4 * math.pi / 683  # cd to Watt
        distance = min(intensity / 3, 200)
        MSFS2024LightProperties.set_custom_distance(light_data, distance)
        intensity *= 10  # Compensate game exposure
        # Multiply lm/steradian by 4Pi to obtain total lumen as it was emitted in all direction
        MSFS2024LightProperties.set_change_attr(light_data, "energy", intensity)

    def switch_blender_light_type(self, light_data, type):
        """
        Switch blender light type and return light_data
        """
        MSFS2024LightProperties.set_change_attr(light_data, "type", type)
        # Force light Data refresh after type setup
        light_data = self.get_active_light_data()
        return light_data

    # endregion

    # region StreeLight

    def update_cone_angle(self, light_data):

        light_type = light_data.msfs_light_type
        if light_type == "streetLight":

            cone_angle = getattr(
                light_data.msfs_light_properties,
                MSFS2024LightPropertiesEnum.LIGHTCONEANGLE.attribute_name(),
            )
            if cone_angle <= 180:
                light_data = self.switch_blender_light_type(light_data, "SPOT")
                cone_angle = math.radians(cone_angle)
                light_data.spot_size = cone_angle
            else:
                # Switch to point since spot doesn't go over 180 angle
                light_data = self.switch_blender_light_type(light_data, "POINT")

    def update_flare_only(self, light_data):
        flare_only = getattr(
            light_data.msfs_light_properties,
            MSFS2024LightPropertiesEnum.FLARE_ONLY.attribute_name(),
        )
        if not flare_only:
            return
        # Switch to point light without energy
        light_data = self.switch_blender_light_type(light_data, "POINT")

        MSFS2024LightProperties.set_change_attr(light_data, "energy", 0)
        MSFS2024LightProperties.set_change_attr(light_data, "shadow_soft_size", 0.5)

    def set_street_light(self, light_data):
        # Setup Spot
        light_data = self.switch_blender_light_type(light_data, "SPOT")
        MSFS2024LightProperties.set_change_attr(light_data, "shadow_soft_size", 0)
        MSFS2024LightProperties.set_change_attr(light_data, "spot_blend", 1)
        MSFS2024LightProperties.set_change_attr(light_data, "use_shadow", False)

        MSFS2024LightProperties.update_light_color(light_data)
        MSFS2024LightProperties.update_light_intensity(light_data)
        self.update_cone_angle(light_data)
        self.update_flare_only(light_data)

    # endregion

    # region AdvancedLight and SkyportalLight
    @staticmethod
    def _update_spot_blend(light_data):
        inner_angle = getattr(
            light_data.msfs_light_properties,
            MSFS2024LightPropertiesEnum.LIGHTINNERANGLE.attribute_name(),
        )
        outer_angle = getattr(
            light_data.msfs_light_properties,
            MSFS2024LightPropertiesEnum.LIGHTOUTERANGLE.attribute_name(),
        )
        if outer_angle <= 0:
            light_data.spot_size = math.radians(1)
            return

        # Clamp outer angle because blend is not visible at 180°
        outer_angle = min(outer_angle, 179)

        inner_angle = min(inner_angle, outer_angle)

        outer_angle = math.radians(outer_angle)
        inner_angle = math.radians(inner_angle)

        light_data.spot_size = outer_angle

        # Pythagorean Trigonometric
        outer_opposite_distance = math.sin(outer_angle * 0.5)
        inner_opposite_distance = math.sin(inner_angle * 0.5)
        # Blend corresponds to amount of space that the inner cone should occupy inside the outer cone.
        # Subtracting the area of the smaller circle from the area of the larger one instead.
        outer_circle_area = math.pow(outer_opposite_distance, 2)
        inner_circle_area = math.pow(inner_opposite_distance, 2)
        blend = (outer_circle_area - inner_circle_area) / outer_circle_area
        MSFS2024LightProperties.set_change_attr(light_data, "spot_blend", blend)

    def update_inner_outer_angle(self, light_data, switch_to_point = False):
        """
        Inner outer angle for best visual fidelity.
        Can switch to point light when spot angle > 180
        """
        light_data: bpy.types.Light

        outer_angle = getattr(
            light_data.msfs_light_properties,
            MSFS2024LightPropertiesEnum.LIGHTOUTERANGLE.attribute_name(),
        )

        if switch_to_point and outer_angle >= 180 :
            light_data = self.switch_blender_light_type(light_data, "POINT")

        else :
            # Switch to point since spot doesn't go over 180 angle
            light_data = self.switch_blender_light_type(light_data, "SPOT")   
            MSFS2024LightProperties._update_spot_blend(light_data)

    def set_advanced_light(self, light_data):

        light_data = self.switch_blender_light_type(light_data, "SPOT")
        shape = getattr(
            light_data.msfs_light_properties,
            MSFS2024LightPropertiesEnum.LIGHTSHAPE.attribute_name(),
        )
        if shape == "point":
            MSFS2024LightProperties.set_change_attr(
                light_data,
                "shadow_soft_size",
                0
            )
        else:
            radius = getattr(
                light_data.msfs_light_properties,
                MSFS2024LightPropertiesEnum.LIGHTSOURCERADIUS.attribute_name(),
            )
            radius_meter = radius / 100
            MSFS2024LightProperties.set_change_attr(
                light_data, 
                "shadow_soft_size", 
                radius_meter
            )

        MSFS2024LightProperties.set_change_attr(light_data, "spot_blend", 1)
        MSFS2024LightProperties.set_change_attr(light_data, "use_shadow", False)

        MSFS2024LightProperties.update_light_color(light_data)
        MSFS2024LightProperties.update_light_intensity(light_data)
        self.update_inner_outer_angle(light_data, switch_to_point=True)

    def set_skyportal_light(self, light_data):
        """
        Not rendered in evee. We use a spotlight with no energy 
        to visualize gizmo.
        """
        light_data = self.switch_blender_light_type(light_data, "SPOT")

        # Set light shape, important for extension export
        MSFS2024LightProperties.set_change_attr(
            light_data.msfs_light_properties, 
            MSFS2024LightPropertiesEnum.LIGHTSHAPE.attribute_name(), 
            "disc"
        )

        radius = getattr(
            light_data.msfs_light_properties,
            MSFS2024LightPropertiesEnum.LIGHTSOURCERADIUS.attribute_name(),
        )
        radius_meter = radius / 100

        MSFS2024LightProperties.set_change_attr(
            light_data, 
            "shadow_soft_size", 
            radius_meter
        )

        MSFS2024LightProperties.set_change_attr(light_data, "use_shadow", False)

        MSFS2024LightProperties.set_change_attr(light_data, "energy", 0)
        # Set cutoff distance to 0 to remove useless distance preview
        MSFS2024LightProperties.set_change_attr(light_data, "use_custom_distance", True)
        MSFS2024LightProperties.set_change_attr(light_data, "cutoff_distance", 0)

        self.update_inner_outer_angle(light_data, switch_to_point=False)

    # endregion

    msfs_light_use_temperature: bpy.props.BoolProperty(
        name=MSFS2024LightPropertiesEnum.USE_LIGHT_TEMPERATURE.property_name(),
        default=MSFS2024LightPropertiesEnum.USE_LIGHT_TEMPERATURE.default_value(),
        update=sync_blender_params
    ) # type: ignore

    msfs_light_temperature: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHT_TEMPERATURE.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHT_TEMPERATURE.default_value(),
        min=1000.0,
        max=10000,
        update=sync_blender_params,
        subtype = "TEMPERATURE",
        step=100
    ) # type: ignore

    msfs_light_temperature_preview: bpy.props.FloatVectorProperty(
        name=MSFS2024LightPropertiesEnum.LIGHT_TEMPERATURE_PREVIEW.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHT_TEMPERATURE_PREVIEW.default_value(),
        min=0,
        max=1,
        subtype="COLOR",
        size=3
    ) # type: ignore

    msfs_light_color: bpy.props.FloatVectorProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTCOLOR.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTCOLOR.default_value(),
        min=0,
        max=1,
        subtype="COLOR",
        size=3,
        update=sync_blender_params
    )  # type: ignore

    msfs_light_intensity: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTINTENSITY.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTINTENSITY.default_value(),
        soft_max=1000000,
        step=100,
        update=sync_blender_params
    )  # type: ignore

    msfs_light_daytime_intensity: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTDAYTIMEINTENSITY.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTDAYTIMEINTENSITY.default_value(),
        soft_max=1000000,
        step=100
    )  # type: ignore

    msfs_light_has_symmetry: bpy.props.BoolProperty(
        name=MSFS2024LightPropertiesEnum.HASLIGHTSYMMETRY.property_name(),
        default=MSFS2024LightPropertiesEnum.HASLIGHTSYMMETRY.default_value(),
        description=("Enable Light Symmetry.\n"
                     "INFO : Light Symmetry preview not supported in Evee")
    )  # type: ignore

    msfs_light_flash_frequency: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTFLASHFREQUENCY.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTFLASHFREQUENCY.default_value(),
        min=0.0
    )  # type: ignore

    msfs_light_flash_duration: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTFLASHDURATION.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTFLASHDURATION.default_value(),
        min=0.0
    )  # type: ignore

    msfs_light_flash_phase: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTFLASHPHASE.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTFLASHPHASE.default_value()
    )  # type: ignore

    msfs_light_rotation_speed: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTROTATIONSPEED.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTROTATIONSPEED.default_value()
    )  # type: ignore

    msfs_light_rotation_phase: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTROTATIONPHASE.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTROTATIONPHASE.default_value()
    )  # type: ignore

    msfs_light_random_phase: bpy.props.BoolProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTRANDOMPHASE.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTRANDOMPHASE.default_value()
    )  # type: ignore

    msfs_light_day_night_cycle: bpy.props.BoolProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTDAYNIGHTCYCLE.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTDAYNIGHTCYCLE.default_value(),
        description="Set this value to 'true' if you want the light to be visible at night only."
    )  # type: ignore

    msfs_light_cone_angle: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTCONEANGLE.property_name(),
        min = 0,
        max = 360,
        default=MSFS2024LightPropertiesEnum.LIGHTCONEANGLE.default_value(),
        description="This value sets the cone angle of the light.",
        update=sync_blender_params
    )  # type: ignore

    msfs_light_shape_type: bpy.props.EnumProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTSHAPE.property_name(),
        description="Shape of the light",
        items=(
            ("point", "Point", ""),
            ("sphere", "Sphere", ""),
            ("disc", "Disc", "")
        ),
        default=MSFS2024LightPropertiesEnum.LIGHTSHAPE.default_value(),
        update=sync_blender_params
        
    )  # type: ignore

    msfs_light_source_radius: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTSOURCERADIUS.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTSOURCERADIUS.default_value(),
        min=1.0,
        update=sync_blender_params,
        description=("Light source radius.\n"
                     "INFO : Disc Source Radius preview not supported in Evee")
    )  # type: ignore

    msfs_light_inner_angle: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTINNERANGLE.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTINNERANGLE.default_value(),
        min = 0,
        max = 360,
        update=sync_blender_params
    )  # type: ignore

    msfs_light_outer_angle: bpy.props.FloatProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTOUTERANGLE.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTOUTERANGLE.default_value(),
        min = 0,
        max = 360,
        update=sync_blender_params
    )  # type: ignore

    msfs_light_channel_exterior: bpy.props.BoolProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTCHANNELEXTERIOR.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTCHANNELEXTERIOR.default_value()
    )  # type: ignore

    msfs_light_channel_interior: bpy.props.BoolProperty(
        name=MSFS2024LightPropertiesEnum.LIGHTCHANNELINTERIOR.property_name(),
        default=MSFS2024LightPropertiesEnum.LIGHTCHANNELINTERIOR.default_value()
    )  # type: ignore

    msfs_light_lens_flare: bpy.props.BoolProperty(
        name=MSFS2024LightPropertiesEnum.FLARE_ENABLED.property_name(),
        default=MSFS2024LightPropertiesEnum.FLARE_ENABLED.default_value(),
        description=("Enable light lens flare.\n"
                     "INFO : Lens Flare preview not supported in Evee")
    )  # type: ignore

    msfs_light_flare_only: bpy.props.BoolProperty(
        name=MSFS2024LightPropertiesEnum.FLARE_ONLY.property_name(),
        default=MSFS2024LightPropertiesEnum.FLARE_ONLY.default_value(),
        update=sync_blender_params,
        description=("Enable light without energy, only flare.\n"
                     "INFO : Flare preview not supported in Evee")
    )  # type: ignore


class MSFS2024AddLight(bpy.types.Operator):
    bl_idname = "msfs2024.add_light"
    bl_label = "Add MSFS2024 Light"
    bl_options = {"REGISTER", "UNDO"}

    msfs_light_type: bpy.props.StringProperty(default="streetLight") # type: ignore

    @staticmethod
    def _get_default_name(msfs_light_type: str) -> str:
        """Get default name for each msfs_light_type

        Args:
            msfs_light_type: bpy.types.Light.msfs_light_type

        Returns:
            Default Name
        """
        name = "Light"
        if msfs_light_type == "streetLight":
            name = "MSFS2024 Street Light"
        elif msfs_light_type == "advancedLight":
            name = "MSFS2024 Advanced Light"
        elif msfs_light_type == "skyPortalLight":
            name = "MSFS2024 SkyPortal Light"
        return name

    @staticmethod
    def force_update_msfs_properties(light_data: bpy.types.Light):
        """
        Force msfs_properties update.
        """
        if light_data.msfs_light_type == "NONE":
            return

        light_data.msfs_light_type = light_data.msfs_light_type

    @staticmethod
    def _create_light_data(msfs_light_type: str) -> bpy.types.Light:
        name = MSFS2024AddLight._get_default_name(msfs_light_type)

        light_data = bpy.data.lights.new(
            name=name,
            type="POINT"
        )
        light_data.name = name

        setattr(
            light_data,
            MSFS2024LightPropertiesEnum.LIGHTTYPE.attribute_name(),
            msfs_light_type,
        )
        setattr(
            light_data.msfs_light_properties,
            MSFS2024LightPropertiesEnum.LIGHTINTENSITY.attribute_name(),
            MSFS2024LightPropertiesEnum.LIGHTINTENSITY.default_value(),
        )

        return light_data

    @staticmethod
    def create_light_object(msfs_light_type: str) -> bpy.types.Object:
        """
        Create a light object without using bpy.ops.
        Faster, does not require context switching

        Parameters:
            msfs_light_type (str): Type of MSFS light.

        Returns:
            bpy.types.Object: The created light object.
        """
        light_data = MSFS2024AddLight._create_light_data(
            msfs_light_type=msfs_light_type
        )
        light_object = bpy.data.objects.new(light_data.name, light_data)
        return light_object

    def add_light(self, context, position = [0,0,0]):
        light_obj = self.create_light_object(self.msfs_light_type)
        
        bpy.context.collection.objects.link(light_obj)

        # Deselect all objects and select the new light
        for obj in bpy.context.view_layer.objects:
            obj.select_set(False)  # Deselect all objects

        light_obj.location = position
        # Set new light as active
        bpy.context.view_layer.objects.active = light_obj
        light_obj.select_set(True)  # Select the new light

        return light_obj

    def execute(self, context):
        self.add_light(context, position=context.scene.cursor.location)
        return {"FINISHED"}

class MSFS2024LightsAddMenu(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_msfs_lights2024_add_menu"
    bl_label = "Microsoft Flight Simulator 2024 Lights"

    def draw(self, context):
        add_fast_light_op = self.layout.operator(
            MSFS2024AddLight.bl_idname,
            text="Fast Light",
            icon="LIGHT_POINT"
        )
        add_fast_light_op.msfs_light_type = "streetLight"

        add_advanced_light_op = self.layout.operator(
            MSFS2024AddLight.bl_idname,
            text="Advanced Light",
            icon="LIGHT_POINT"
        )
        add_advanced_light_op.msfs_light_type = "advancedLight"

        add_skyportal_light_op = self.layout.operator(
            MSFS2024AddLight.bl_idname,
            text="Sky Portal Light",
            icon="LIGHT_POINT"
        )
        add_skyportal_light_op.msfs_light_type = "skyPortalLight"

#####################################################
class MSFS2024_PT_LightProperties(bpy.types.Panel):
    bl_label = "MSFS2024 Light Parameters"
    bl_idname = "LIGHT_PT_msfs2024_light_properties"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):

        return context.active_object is not None and context.active_object.type == 'LIGHT'     

    def draw_color(self, context, prop, layout):
        box = layout.box()
        box.label(text="Color")
        box.prop(prop, MSFS2024LightPropertiesEnum.USE_LIGHT_TEMPERATURE.attribute_name())

        use_light_temperature = getattr(
            prop,
            MSFS2024LightPropertiesEnum.USE_LIGHT_TEMPERATURE.attribute_name()
        )

        if use_light_temperature:
            row = box.row()
            row.prop(prop, MSFS2024LightPropertiesEnum.LIGHT_TEMPERATURE.attribute_name())
            row = row.row()
            row.enabled = False
            row.scale_x = 0.5
            row.prop(
                prop,
                MSFS2024LightPropertiesEnum.LIGHT_TEMPERATURE_PREVIEW.attribute_name(),
                text="",
            )

        else:
            row = box.row(heading=MSFS2024LightPropertiesEnum.LIGHTCOLOR.property_name())
            row.prop(
                prop,
                MSFS2024LightPropertiesEnum.LIGHTCOLOR.attribute_name(),
                text=""
            )

    def draw_fast_light_properties(self, context, prop, layout):
        self.draw_color(context, prop, layout)

        box = layout.box()
        box.label(text="Power")
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTINTENSITY.attribute_name())
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTDAYNIGHTCYCLE.attribute_name())
        if not getattr(prop, MSFS2024LightPropertiesEnum.LIGHTDAYNIGHTCYCLE.attribute_name()):
            box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTDAYTIMEINTENSITY.attribute_name())

        box = layout.box()
        box : bpy.types.UILayout
        box.label(text="Distribution")
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTCONEANGLE.attribute_name())

        sub_row = box.row(align=True)    
        sub_row.prop(prop, MSFS2024LightPropertiesEnum.HASLIGHTSYMMETRY.attribute_name())

        box = layout.box()
        box.label(text="Animation")
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTFLASHFREQUENCY.attribute_name())
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTFLASHDURATION.attribute_name())
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTFLASHPHASE.attribute_name())
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTROTATIONSPEED.attribute_name())
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTROTATIONPHASE.attribute_name())
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTRANDOMPHASE.attribute_name())

        box = layout.box()
        box.label(text="Lens Flare")
        box.prop(prop, MSFS2024LightPropertiesEnum.FLARE_ENABLED.attribute_name())
        if getattr(prop, MSFS2024LightPropertiesEnum.FLARE_ENABLED.attribute_name()):
            box.prop(prop, MSFS2024LightPropertiesEnum.FLARE_ONLY.attribute_name())

    def draw_advanced_light_properties(self, context, prop, layout):
        self.draw_color(context, prop, layout)

        box = layout.box()
        box.label(text="Power")
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTINTENSITY.attribute_name())

        box = layout.box()
        box.label(text="Shape")
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTSHAPE.attribute_name())
        light_shape = getattr(prop,MSFS2024LightPropertiesEnum.LIGHTSHAPE.attribute_name())

        if not light_shape == "point":
            box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTSOURCERADIUS.attribute_name())

        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTINNERANGLE.attribute_name())
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTOUTERANGLE.attribute_name())

        box = layout.box()
        box.label(text="Channels")
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTCHANNELEXTERIOR.attribute_name())
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTCHANNELINTERIOR.attribute_name())

        box = layout.box()
        box.label(text="Lens Flare")
        box.prop(prop, MSFS2024LightPropertiesEnum.FLARE_ENABLED.attribute_name())

    def draw_skyportal_light_properties(self, context, prop, layout):
        box = layout.box()

        box.label(text="Shape")
        box.label(text="Skyportal Preview is not supported in Evee", icon="INFO")
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTSOURCERADIUS.attribute_name())
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTINNERANGLE.attribute_name())
        box.prop(prop, MSFS2024LightPropertiesEnum.LIGHTOUTERANGLE.attribute_name())

    def draw(self, context):
        layout = self.layout
        active_object = context.object

        if active_object.type != 'LIGHT':
            return

        blender_light = active_object.data
        if blender_light is None:
            return

        prop = blender_light.msfs_light_properties

        layout.prop(blender_light, "msfs_light_type")

        if blender_light.msfs_light_type == "streetLight":
            self.draw_fast_light_properties(context, prop, layout)
        elif blender_light.msfs_light_type == "advancedLight":
            self.draw_advanced_light_properties(context, prop, layout)
        elif blender_light.msfs_light_type == "skyPortalLight":
            self.draw_skyportal_light_properties(context, prop, layout)

#####################################################
def draw_menu(self, context):
    self.layout.menu(menu=MSFS2024LightsAddMenu.bl_idname, icon="OUTLINER_DATA_LIGHT")


def force_update_all_lights():

    for light_data in bpy.data.lights:
        MSFS2024AddLight.force_update_msfs_properties(light_data)

def register():
    bpy.types.Light.msfs_light_type = bpy.props.EnumProperty(
        name="Type",
        description="Type of light to add",
        items=(("NONE", "Disabled", ""),
               ("streetLight", "MSFS2024 Street Light", ""),
               ("advancedLight", "MSFS2024 Advanced Light", ""),
               ("skyPortalLight", "MSFS2024 Sky Portal Light", "")
               ),
        default="NONE",
        update=sync_blender_params
    )
    bpy.types.VIEW3D_MT_add.append(draw_menu)

    bpy.types.Light.msfs_light_properties = bpy.props.PointerProperty(type=MSFS2024LightProperties)

def unregister():
    
    bpy.types.VIEW3D_MT_add.remove(draw_menu)
    try:
        del bpy.types.Light.msfs_light_type
        del bpy.types.Light.msfs_light_properties
    except :
        pass
