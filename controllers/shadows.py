from typing import List, Dict
import numpy as np
import random
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian, HDRISkyboxLibrarian
from tdw.output_data import OutputData, Transforms
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset
from tdw_physics.util import get_args


class _Sector:
    """
    A sector has two points.

    A "sub-sector" is the circle defined by one of these points and RADIUS.
    """

    RADIUS = 0.5

    def __init__(self, c_0: Dict[str, float], c_1: Dict[str, float]):
        """
        :param c_0: Center of a subsector.
        :param c_1: Center of a subsector.
        """
        self.c_0 = TDWUtils.vector3_to_array(c_0)
        self.c_1 = TDWUtils.vector3_to_array(c_1)

    def get_p_0(self) -> Dict[str, float]:
        """
        :return: A position in the c_0 sub-sector.
        """

        return TDWUtils.array_to_vector3(TDWUtils.get_random_point_in_circle(center=self.c_0, radius=self.RADIUS))

    def get_p_1(self) -> Dict[str, float]:
        """
        :return: A position in the c_1 sub-sector.
        """

        return TDWUtils.array_to_vector3(TDWUtils.get_random_point_in_circle(center=self.c_1, radius=self.RADIUS))


class Shadows(RigidbodiesDataset):
    """
    Move a ball to and from areas with different lighting.

    Use HDRI skyboxes and visual materials (for the ball) to change the lighting per trial.
    """

    _BALL_SCALE = 0.5
    _BALL_MATERIALS = ["aluminium_brushed", "aluminium_clean", "alien_rock_coral_formation", "alien_soil_acid_puddles",
                       "aluminium_foil", "antique_bronze_darkened", "bull_leather_large_worn",
                       "bull_leather_medium_grain", "bull_leather_medium_worn", "car_metallic_fabric_cover_crumpled",
                       "car_synthetic_net", "chrome_v_shiny", "chrome2", "concrete", "concrete_raw_eroded",
                       "copper_brushed", "cotton_canvas_washed_out", "cotton_check_black", "cotton_fabric_printed",
                       "cotton_hot_orange", "cotton_linen_woven_shorn_brush", "cotton_mercerised_grey",
                       "cotton_natural_rough", "dmd_metallic_fine", "dmls_cobalt_chrome_rough", "dmls_silver_sanded",
                       "fabric_vinyl_heavy", "fabric_carpet_grey", "fabric_felt", "glass_clear", "gold_clean",
                       "gold_leaf_fine", "iron_anvil_rusty", "iron_bumped", "iron_rusty", "kevlar_plain_weave",
                       "lamb_leather", "leather_bull", "leather_fine_grain", "leather_fine_grain_pebbled",
                       "leather_pebbled", "linen_burlap_irregular", "linen_viscose_classic_pattern",
                       "linen_viscose_woven_cloth", "linen_woven", "marble_anemone_grey", "marble_crema_valencia",
                       "marble_green", "marble_griotte", "metal_brushed_copper", "metal_cast", "metal_grater",
                       "metal_iron_damaged", "metal_molten_drop_3d_print", "metal_round_mesh_layered",
                       "metal_sandblasted", "metal_steel_galvanized_spangle", "military_camouflage",
                       "nappa_leather_pill_quilt", "nappa_leather_switch_quilt", "nappa_leather_worn",
                       "plaster_facade_grey", "plastic_diamond_grid_grain", "plastic_dot_recessed_grain",
                       "plastic_grain", "plastic_stripes", "plastic_vinyl_glossy_green", "plastic_vinyl_glossy_blue",
                       "plastic_vinyl_glossy_gray", "plastic_vinyl_glossy_green", "plastic_vinyl_glossy_light_gray",
                       "plastic_vinyl_glossy_orange", "plastic_vinyl_glossy_red", "plastic_vinyl_glossy_white",
                       "plastic_vinyl_glossy_yellow", "plastic_weave", "polyester_acrylic_nylon_canvas_thick_yarn",
                       "polyester_check_interlock_pattern", "polyester_fabric_charmeuse",
                       "polyester_hexagon_pattern_knit", "polyester_honeycomb_mesh_back",
                       "polyester_lycra_hydrosoft_weave", "polyester_softshell_brushed", "porous_stone_mesh_concretion",
                       "printed_cotton_rough", "printed_cotton_shirt", "rainbow_anodized_metal", "roughcast_troweled",
                       "rusty_metal", "slate_raw", "slate_rockery", "sls_titanium", "sls_titanium_honeycomb_pattern",
                       "sls_titanium_square_pattern", "spandex_printed_fabric", "square_padded_wall",
                       "stone_cellular_concretion", "stone_mountain_grey", "synthetic_boldweave_ball",
                       "synthetic_fabric_knit", "synthetic_flipflop_topstitch_diamond", "synthetic_quilted",
                       "taurillon_leather_medium_worn", "thin_bamboo_blinds", "tiles_hexagon_bees_dirty",
                       "travertine_persian_vein", "wicker_weave", "wood_american_cherry", "wood_beech_honey",
                       "wool_tartan_multicolored"]

    # These sectors have different lighting at each point, e.g. c_0 is more shadowed than c_1.
    SECTORS = [_Sector(c_0={"x": 0.5, "y": 0, "z": 0}, c_1={"x": -0.5, "y": 0, "z": 0}),
               _Sector(c_0={"x": 0, "y": 0, "z": 3}, c_1={"x": -1.2, "y": 0, "z": 3.7}),
               _Sector(c_0={"x": 0, "y": 0, "z": -3}, c_1={"x": -1.2, "y": 0, "z": -3.7}),
               _Sector(c_0={"x": 2.15, "y": 0, "z": -2.6}, c_1={"x": 4, "y": 0, "z": -3}),
               _Sector(c_0={"x": 2.15, "y": 0, "z": 2.6}, c_1={"x": 4, "y": 0, "z": 3}),
               _Sector(c_0={"x": -2.15, "y": 0, "z": 2.6}, c_1={"x": -4, "y": 0, "z": 3}),
               _Sector(c_0={"x": -2.15, "y": 0, "z": -2.6}, c_1={"x": -4, "y": 0, "z": -3})]

    def __init__(self, port: int = 1071):
        super().__init__(port=port)

        # Cache the ball data.
        self._ball = ModelLibrarian("models_flex.json").get_record("sphere")
        self._ball_id = 0

        # The position the ball starts in and the position the ball is directed at.
        self._p0: Dict[str, float] = {}
        self._p1: Dict[str, float] = {}

        # Cache the skybox records.
        skybox_lib = HDRISkyboxLibrarian()
        self._skyboxes: List[str] = [r.name for r in skybox_lib.records if r.sun_intensity >= 0.8]

    def get_scene_initialization_commands(self) -> List[dict]:
        return [self.get_add_scene(scene_name="box_room_2018"),
                {"$type": "set_aperture",
                 "aperture": 4.8},
                {"$type": "set_focus_distance",
                 "focus_distance": 1.25},
                {"$type": "set_post_exposure",
                 "post_exposure": 0.4},
                {"$type": "set_ambient_occlusion_intensity",
                 "intensity": 0.175},
                {"$type": "set_ambient_occlusion_thickness_modifier",
                 "thickness": 3.5}]

    def get_trial_initialization_commands(self) -> List[dict]:
        # Select a random sector.
        sector: _Sector = random.choice(self.SECTORS)
        # Decide where the ball will go and in which direction.
        if random.random() < 0.5:
            self._p0 = sector.get_p_0()
            self._p1 = sector.get_p_1()
        else:
            self._p0 = sector.get_p_1()
            self._p1 = sector.get_p_0()

        commands = []
        # Add the ball.
        mass = random.uniform(1, 4)
        commands.extend(self.add_physics_object(record=self._ball,
                                                position=self._p0,
                                                rotation=TDWUtils.VECTOR3_ZERO,
                                                o_id=self._ball_id,
                                                mass=mass,
                                                dynamic_friction=random.uniform(0, 0.1),
                                                static_friction=random.uniform(0, 0.1),
                                                bounciness=random.uniform(0, 0.1)))
        # Scale the ball and apply a force and a spin.
        commands.extend([{"$type": "scale_object",
                          "scale_factor": {"x": self._BALL_SCALE, "y": self._BALL_SCALE, "z": self._BALL_SCALE},
                          "id": self._ball_id},
                         {"$type": "rotate_object_by",
                          "angle": random.uniform(30, 45),
                          "id": self._ball_id,
                          "axis": "pitch",
                          "is_world": True},
                         {"$type": "apply_force_magnitude_to_object",
                          "magnitude": random.uniform(0.01, 0.03),
                          "id": self._ball_id},
                         {"$type": "object_look_at_position",
                          "position": self._p1,
                          "id": self._ball_id},
                         {"$type": "apply_force_magnitude_to_object",
                          "magnitude": random.uniform(5.2 * mass, 8 * mass),
                          "id": self._ball_id}])
        # Set a random material.
        commands.extend(TDWUtils.set_visual_material(self, self._ball.substructure, self._ball_id,
                                                     random.choice(self._BALL_MATERIALS)))

        # Set a random skybox and rotate it for variable lighting.
        commands.extend([self.get_add_hdri_skybox(skybox_name=random.choice(self._skyboxes)),
                         {"$type": "rotate_hdri_skybox_by",
                          "angle": random.uniform(0, 360)}])

        # Teleport the avatar such that it can see both points.
        d0 = TDWUtils.get_distance(self._p0, self._p1)
        p_med = np.array([(self._p0["x"] + self._p1["x"]) / 2, 0, (self._p0["z"] + self._p1["z"]) / 2])
        p_cen = np.array([0, 0, 0])
        a_pos = p_med + ((p_cen - p_med) / np.abs(np.linalg.norm(p_cen - p_med)) * (d0 + random.uniform(0.3, 0.4)))
        a_pos[1] = random.uniform(0.3, 0.6)
        commands.extend([{"$type": "teleport_avatar_to",
                          "position": TDWUtils.array_to_vector3(a_pos)},
                         {"$type": "look_at_position",
                          "position": TDWUtils.array_to_vector3(p_med)}])
        return commands

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return [{"$type": "focus_on_object",
                 "object_id": self._ball_id,
                 "use_centroid": True}]

    def get_field_of_view(self) -> float:
        return 68

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        for r in resp[:-1]:
            r_id = OutputData.get_data_type_id(r)
            # If the ball reaches or overshoots the destination, the trial is done.
            if r_id == "tran":
                t = Transforms(r)
                d0 = TDWUtils.get_distance(TDWUtils.array_to_vector3(t.get_position(0)), self._p0)
                d1 = TDWUtils.get_distance(self._p0, self._p1)
                d2 = TDWUtils.get_distance(TDWUtils.array_to_vector3(t.get_position(0)), self._p1)
                return d2 <= 0.01 or d0 >= d1
        return False


if __name__ == "__main__":
    args = get_args("shadows")
    td = Shadows()
    td.run(num=args.num, output_dir=args.dir, temp_path=args.temp)
