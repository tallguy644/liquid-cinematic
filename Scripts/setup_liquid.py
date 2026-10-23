# Builds the draining-liquid demo shot inside LiquidCinematic.
# Run from the editor console:  py "<project>/Scripts/setup_liquid.py"
# Writes a report to <project>/Saved/liquid_setup_log.txt

import os
import traceback
import unreal

ROOT = "/Game/DrainingLiquid"
INCLUDE = "/DrainingLiquidShaders/DrainingLiquid.ush"
LOG_PATH = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "liquid_setup_log.txt")

log_lines = []


def log(msg):
    msg = str(msg)
    log_lines.append(msg)
    unreal.log("[LiquidSetup] " + msg)


def flush_log():
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
    except Exception as e:
        unreal.log_warning("could not write log: %s" % e)


mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def fresh_asset(name, cls, factory):
    path = "%s/%s" % (ROOT, name)
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    return tools.create_asset(name, ROOT, cls, factory)


def expr(mat, cls, x, y, **props):
    e = mel.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def link(a, a_out, b, b_in):
    """Connect trying a few pin-name spellings; log if none works."""
    outs = a_out if isinstance(a_out, (list, tuple)) else [a_out]
    ins = b_in if isinstance(b_in, (list, tuple)) else [b_in]
    for o in outs:
        for i in ins:
            if mel.connect_material_expressions(a, o, b, i):
                return True
    log("  !! failed link %s[%s] -> %s[%s]" % (a.get_class().get_name(), outs, b.get_class().get_name(), ins))
    return False


def to_prop(a, a_out, prop):
    outs = a_out if isinstance(a_out, (list, tuple)) else [a_out]
    for o in outs:
        if mel.connect_material_property(a, o, prop):
            return True
    log("  !! failed property link %s[%s] -> %s" % (a.get_class().get_name(), outs, prop))
    return False


MAIN_OUT = ["", "return", "Return"]


def custom_node(mat, x, y, code, in_names, extra_outs, out_type):
    c = expr(mat, unreal.MaterialExpressionCustom, x, y)
    c.set_editor_property("code", code)
    c.set_editor_property("output_type", out_type)
    ins = []
    for n in in_names:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", n)
        ins.append(ci)
    c.set_editor_property("inputs", ins)
    outs = []
    for n, t in extra_outs:
        co = unreal.CustomOutput()
        co.set_editor_property("output_name", n)
        co.set_editor_property("output_type", t)
        outs.append(co)
    c.set_editor_property("additional_outputs", outs)
    c.set_editor_property("include_file_paths", [INCLUDE])
    return c


def vec_param(mat, name, x, y, value=(0, 0, 0, 0), rgba=False):
    p = expr(mat, unreal.MaterialExpressionVectorParameter, x, y)
    p.set_editor_property("parameter_name", name)
    p.set_editor_property("default_value", unreal.LinearColor(*value))
    if not rgba:
        return p, ""
    ap = expr(mat, unreal.MaterialExpressionAppendVector, x + 220, y)
    link(p, "", ap, "A")
    link(p, "A", ap, "B")
    return ap, ""


F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
F2 = unreal.CustomMaterialOutputType.CMOT_FLOAT2
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3


# ----------------------------------------------------------------------------- liquid material
def build_liquid_material():
    mat = fresh_asset("M_DrainingLiquid", unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("tangent_space_normal", False)
    try:
        mat.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    except Exception as e:
        log("  lighting mode not set: %s" % e)

    wp = expr(mat, unreal.MaterialExpressionWorldPosition, -1800, -600)
    cam = expr(mat, unreal.MaterialExpressionCameraPositionWS, -1800, -500)
    tss = expr(mat, unreal.MaterialExpressionTwoSidedSign, -1800, -400)
    vn = expr(mat, unreal.MaterialExpressionVertexNormalWS, -1800, -300)
    sd = expr(mat, unreal.MaterialExpressionSceneDepth, -1800, -200)
    pd = expr(mat, unreal.MaterialExpressionPixelDepth, -1800, -100)
    thick = expr(mat, unreal.MaterialExpressionSubtract, -1600, -150)
    link(sd, "", thick, "A")
    link(pd, "", thick, "B")
    tm = expr(mat, unreal.MaterialExpressionTime, -1800, 0)

    params = {}
    y = 100
    for name, rgba in [("DL_PlaneOrigin", False), ("DL_PlaneNormal", False), ("DL_AxisOrigin", False),
                       ("DL_AxisDir", False), ("DL_DrainPoint", False), ("DL_Shape", True),
                       ("DL_Waves", True), ("DL_Vortex", True), ("DL_Spiral", True)]:
        params[name] = vec_param(mat, name, -1900, y, (0, 0, 1, 0), rgba)
        y += 110

    liq = custom_node(
        mat, -1100, -200,
        "return DL_Liquid(WorldPos, CamPos, TwoSided, VertexN, SceneThick, GameTime,\n"
        "                 PlaneO, PlaneN, AxisO, AxisD, DrainP, Shape, Waves, Vortex, Spiral,\n"
        "                 Thickness, Foam, Rim, Underside);",
        ["WorldPos", "CamPos", "TwoSided", "VertexN", "SceneThick", "GameTime",
         "PlaneO", "PlaneN", "AxisO", "AxisD", "DrainP", "Shape", "Waves", "Vortex", "Spiral"],
        [("Thickness", F1), ("Foam", F1), ("Rim", F1), ("Underside", F1)], F3)
    liq.set_editor_property("description", "DL_Liquid")

    link(wp, "", liq, "WorldPos")
    link(cam, "", liq, "CamPos")
    link(tss, "", liq, "TwoSided")
    link(vn, "", liq, "VertexN")
    link(thick, "", liq, "SceneThick")
    link(tm, "", liq, "GameTime")
    for pin, pname in [("PlaneO", "DL_PlaneOrigin"), ("PlaneN", "DL_PlaneNormal"), ("AxisO", "DL_AxisOrigin"),
                       ("AxisD", "DL_AxisDir"), ("DrainP", "DL_DrainPoint"), ("Shape", "DL_Shape"),
                       ("Waves", "DL_Waves"), ("Vortex", "DL_Vortex"), ("Spiral", "DL_Spiral")]:
        node, out = params[pname]
        link(node, out, liq, pin)

    # look parameters (clear water defaults)
    absorb, _ = vec_param(mat, "Absorption", -900, 300, (0.0045, 0.0015, 0.0008, 0))
    scatter, _ = vec_param(mat, "ScatterColor", -900, 420, (0.6, 0.75, 0.8, 0))
    foamc, _ = vec_param(mat, "FoamColor", -900, 540, (0.9, 0.9, 0.9, 0))
    optics, _ = vec_param(mat, "Optics", -1100, 660, (0.04, 0.02, 0.35, 0.0), rgba=True)

    xf = expr(mat, unreal.MaterialExpressionTransform, -800, -350)
    try:
        xf.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
        xf.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_VIEW)
    except Exception as e:
        log("  transform node props: %s" % e)
    link(liq, MAIN_OUT, xf, ["", "Input"])

    shade = custom_node(
        mat, -500, -100,
        "return DL_Shade(N, ViewN, WorldPos, CamPos, Thick, FoamIn, RimIn, Under,\n"
        "                Absorption, ScatterColor, FoamColor, Optics,\n"
        "                Transmittance, RefractOffset, Rough);",
        ["N", "ViewN", "WorldPos", "CamPos", "Thick", "FoamIn", "RimIn", "Under",
         "Absorption", "ScatterColor", "FoamColor", "Optics"],
        [("Transmittance", F3), ("RefractOffset", F2), ("Rough", F1)], F3)
    shade.set_editor_property("description", "DL_Shade")

    link(liq, MAIN_OUT, shade, "N")
    link(xf, "", shade, "ViewN")
    link(wp, "", shade, "WorldPos")
    link(cam, "", shade, "CamPos")
    link(liq, "Thickness", shade, "Thick")
    link(liq, "Foam", shade, "FoamIn")
    link(liq, "Rim", shade, "RimIn")
    link(liq, "Underside", shade, "Under")
    link(absorb, "", shade, "Absorption")
    link(scatter, "", shade, "ScatterColor")
    link(foamc, "", shade, "FoamColor")
    link(optics, "", shade, "Optics")

    sc = expr(mat, unreal.MaterialExpressionSceneColor, -100, 200)
    link(shade, "RefractOffset", sc, ["Offset Fraction", "OffsetFraction"])
    mask = expr(mat, unreal.MaterialExpressionComponentMask, 100, 200, r=True, g=True, b=True, a=False)
    link(sc, "", mask, "")
    emis = expr(mat, unreal.MaterialExpressionMultiply, 300, 200)
    link(mask, "", emis, "A")
    link(shade, "Transmittance", emis, "B")

    one = expr(mat, unreal.MaterialExpressionConstant, 300, 350, r=1.0)
    spec = expr(mat, unreal.MaterialExpressionConstant, 300, 420, r=0.25)

    to_prop(shade, MAIN_OUT, unreal.MaterialProperty.MP_BASE_COLOR)
    to_prop(shade, "Rough", unreal.MaterialProperty.MP_ROUGHNESS)
    to_prop(liq, MAIN_OUT, unreal.MaterialProperty.MP_NORMAL)
    to_prop(emis, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    to_prop(one, "", unreal.MaterialProperty.MP_OPACITY)
    to_prop(spec, "", unreal.MaterialProperty.MP_SPECULAR)

    mel.layout_material_expressions(mat)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    log("material M_DrainingLiquid built (%d expressions)" % mel.get_num_material_expressions(mat))

    mi = fresh_asset("MI_Water_Clear", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, mat)
    eal.save_loaded_asset(mi)
    log("material instance MI_Water_Clear created")
    return mat, mi


# ----------------------------------------------------------------------------- parameter collection
def build_mpc():
    mpc = fresh_asset("MPC_DrainingLiquid", unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    scalars = []
    for n, v in [("DL_SurfaceH", 0.0), ("DL_WetTopH", 0.0), ("DL_StartH", 0.0), ("DL_Radius", 1.0)]:
        s = unreal.CollectionScalarParameter()
        s.set_editor_property("parameter_name", n)
        s.set_editor_property("default_value", v)
        scalars.append(s)
    vectors = []
    for n, v in [("DL_AxisOrigin", (0, 0, 0, 0)), ("DL_AxisDir", (0, 0, 1, 0))]:
        p = unreal.CollectionVectorParameter()
        p.set_editor_property("parameter_name", n)
        p.set_editor_property("default_value", unreal.LinearColor(*v))
        vectors.append(p)
    mpc.set_editor_property("scalar_parameters", scalars)
    mpc.set_editor_property("vector_parameters", vectors)
    eal.save_loaded_asset(mpc)
    log("MPC_DrainingLiquid created")
    return mpc


# ----------------------------------------------------------------------------- glass material
def build_glass_material(mpc):
    mat = fresh_asset("M_Glass", unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    try:
        mat.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    except Exception:
        pass

    base = expr(mat, unreal.MaterialExpressionConstant3Vector, 200, -300, constant=unreal.LinearColor(0.92, 0.95, 0.96, 1))
    rough = expr(mat, unreal.MaterialExpressionConstant, 200, -200, r=0.03)
    spec = expr(mat, unreal.MaterialExpressionConstant, 200, -150, r=0.6)
    fres = expr(mat, unreal.MaterialExpressionFresnel, -400, -50)
    base_op = expr(mat, unreal.MaterialExpressionLinearInterpolate, -150, -50)
    a = expr(mat, unreal.MaterialExpressionConstant, -400, -150, r=0.05)
    b = expr(mat, unreal.MaterialExpressionConstant, -400, -100, r=0.45)
    link(a, "", base_op, "A")
    link(b, "", base_op, "B")
    link(fres, "", base_op, "Alpha")
    opacity_src = base_op

    if mpc is not None:
        def coll(name, x, y, vector=False):
            c = expr(mat, unreal.MaterialExpressionCollectionParameter, x, y)
            c.set_editor_property("collection", mpc)
            c.set_editor_property("parameter_name", name)
            if not vector:
                return c
            m = expr(mat, unreal.MaterialExpressionComponentMask, x + 200, y, r=True, g=True, b=True, a=False)
            link(c, "", m, "")
            return m

        wet = custom_node(
            mat, -500, 250,
            "float Wet; DL_GlassWet(WorldPos, AxisO, AxisD, Radius, SurfaceH, WetTopH, StartH, GameTime,\n"
            "                       FilmFade, DropSize, RingWidth, Wet, Drops, Ring);\nreturn Wet;",
            ["WorldPos", "AxisO", "AxisD", "Radius", "SurfaceH", "WetTopH", "StartH", "GameTime",
             "FilmFade", "DropSize", "RingWidth"],
            [("Drops", F1), ("Ring", F1)], F1)
        link(expr(mat, unreal.MaterialExpressionWorldPosition, -1100, 100), "", wet, "WorldPos")
        link(coll("DL_AxisOrigin", -1100, 180, True), "", wet, "AxisO")
        link(coll("DL_AxisDir", -1100, 260, True), "", wet, "AxisD")
        link(coll("DL_Radius", -1100, 340), "", wet, "Radius")
        link(coll("DL_SurfaceH", -1100, 400), "", wet, "SurfaceH")
        link(coll("DL_WetTopH", -1100, 460), "", wet, "WetTopH")
        link(coll("DL_StartH", -1100, 520), "", wet, "StartH")
        link(expr(mat, unreal.MaterialExpressionTime, -1100, 580), "", wet, "GameTime")
        link(expr(mat, unreal.MaterialExpressionConstant, -1100, 640, r=1.5), "", wet, "FilmFade")
        link(expr(mat, unreal.MaterialExpressionConstant, -1100, 700, r=0.25), "", wet, "DropSize")
        link(expr(mat, unreal.MaterialExpressionConstant, -1100, 760, r=0.08), "", wet, "RingWidth")

        # opacity += Drops*0.25 + Wet*0.04 + Ring*0.12
        def scaled(out_name, k, y):
            m = expr(mat, unreal.MaterialExpressionMultiply, -150, y)
            link(wet, out_name, m, "A")
            link(expr(mat, unreal.MaterialExpressionConstant, -300, y + 40, r=k), "", m, "B")
            return m
        s1 = scaled("Drops", 0.25, 200)
        s2 = scaled(MAIN_OUT, 0.04, 300)
        s3 = scaled("Ring", 0.12, 400)
        add1 = expr(mat, unreal.MaterialExpressionAdd, 50, 100)
        link(base_op, "", add1, "A")
        link(s1, "", add1, "B")
        add2 = expr(mat, unreal.MaterialExpressionAdd, 150, 200)
        link(add1, "", add2, "A")
        link(s2, "", add2, "B")
        add3 = expr(mat, unreal.MaterialExpressionAdd, 250, 300)
        link(add2, "", add3, "A")
        link(s3, "", add3, "B")
        sat = expr(mat, unreal.MaterialExpressionSaturate, 350, 300)
        link(add3, "", sat, "")
        opacity_src = sat

    to_prop(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    to_prop(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    to_prop(spec, "", unreal.MaterialProperty.MP_SPECULAR)
    to_prop(opacity_src, "", unreal.MaterialProperty.MP_OPACITY)
    mel.layout_material_expressions(mat)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    log("material M_Glass built")
    return mat


# ----------------------------------------------------------------------------- level + actors
def build_level(liquid_mi, glass_mat, mpc):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    made = False
    for tpl in ["/Engine/Maps/Templates/Template_Default", "/Engine/Maps/Templates/OpenWorld"]:
        try:
            if eal.does_asset_exist("/Game/Maps/LiquidShot"):
                eal.delete_asset("/Game/Maps/LiquidShot")
            if les.new_level_from_template("/Game/Maps/LiquidShot", tpl):
                log("level created from template %s" % tpl)
                made = True
                break
        except Exception as e:
            log("  template %s failed: %s" % (tpl, e))
    if not made:
        les.new_level("/Game/Maps/LiquidShot")
        eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 300), unreal.Rotator(0, -40, -30))
        eas.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 200))
        eas.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
        log("empty level created with basic lights")

    cyl = unreal.load_asset("/Engine/BasicShapes/Cylinder")
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")

    # table top so the glass has something to sit on (top surface at z = 0)
    table = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -2))
    table.set_actor_label("Table")
    table.static_mesh_component.set_static_mesh(cube)
    table.set_actor_scale3d(unreal.Vector(1.2, 0.8, 0.04))
    wood = unreal.load_asset("/Engine/EngineMaterials/WorldGridMaterial")
    if wood:
        table.static_mesh_component.set_material(0, wood)

    # glass: 8 cm wide, 14 cm tall, base at z = 0
    glass = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 7))
    glass.set_actor_label("Glass")
    smc = glass.static_mesh_component
    smc.set_static_mesh(cyl)
    smc.set_material(0, glass_mat)
    smc.set_editor_property("translucency_sort_priority", 1)
    smc.set_editor_property("cast_shadow", False)
    glass.set_actor_scale3d(unreal.Vector(0.08, 0.08, 0.14))

    # liquid: interior 7.4 cm wide, from z = 1 (thick glass base) to z = 14
    liquid = eas.spawn_actor_from_class(unreal.DrainingLiquidActor, unreal.Vector(0, 0, 7.5))
    liquid.set_actor_label("DrainingLiquid")
    liquid.set_actor_scale3d(unreal.Vector(0.074, 0.074, 0.13))
    liquid.set_editor_property("interior_mesh", cyl)
    liquid.set_editor_property("liquid_material", liquid_mi)
    if mpc is not None:
        liquid.set_editor_property("glass_collection", mpc)
    liquid.set_editor_property("start_fill", 0.85)
    liquid.set_editor_property("vortex_core_radius", 0.8)
    liquid.set_editor_property("vortex_depth", 2.5)
    liquid.set_editor_property("wave_length", 2.0)
    liquid.attach_to_actor(glass, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                           unreal.AttachmentRule.KEEP_WORLD, False)
    log("glass + DrainingLiquid actor placed")

    # camera
    cam_loc = unreal.Vector(-26.0, -9.0, 13.0)
    look = unreal.MathLibrary.find_look_at_rotation(cam_loc, unreal.Vector(0, 0, 6.0))
    cam = eas.spawn_actor_from_class(unreal.CineCameraActor, cam_loc, look)
    cam.set_actor_label("ShotCamera")
    cc = cam.get_cine_camera_component()
    try:
        cc.set_editor_property("current_focal_length", 50.0)
        fs = cc.get_editor_property("focus_settings")
        fs.set_editor_property("manual_focus_distance", 28.0)
        cc.set_editor_property("focus_settings", fs)
        cc.set_editor_property("current_aperture", 2.8)
    except Exception as e:
        log("  camera settings: %s" % e)
    log("camera placed")

    les.save_current_level()
    log("level saved to /Game/Maps/LiquidShot")
    return liquid, cam


# ----------------------------------------------------------------------------- sequence
def build_sequence(liquid, cam):
    seq = fresh_asset("LS_Drain", unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    fps = 24
    length = 12 * fps
    seq.set_display_rate(unreal.FrameRate(fps, 1))
    seq.set_playback_start(0)
    seq.set_playback_end(length)

    b = seq.add_possessable(liquid)
    track = b.add_track(unreal.MovieSceneFloatTrack)
    track.set_property_name_and_path("DrainProgress", "DrainProgress")
    sec = track.add_section()
    sec.set_range(0, length)
    ch = sec.get_all_channels()[0]
    lin = unreal.MovieSceneKeyInterpolation.LINEAR
    ch.add_key(unreal.FrameNumber(1 * fps), 0.0, interpolation=lin)
    ch.add_key(unreal.FrameNumber(11 * fps), 1.0, interpolation=lin)
    log("DrainProgress keyed 0 -> 1 from 1s to 11s")

    try:
        cb = seq.add_possessable(cam)
        try:
            cut = seq.add_track(unreal.MovieSceneCameraCutTrack)
        except Exception:
            cut = seq.add_master_track(unreal.MovieSceneCameraCutTrack)
        cs = cut.add_section()
        cs.set_range(0, length)
        bid = unreal.MovieSceneObjectBindingID()
        bid.set_editor_property("guid", cb.get_id())
        cs.set_camera_binding_id(bid)
        log("camera cut track added")
    except Exception as e:
        log("  camera cut skipped: %s" % e)

    eal.save_loaded_asset(seq)
    log("sequence LS_Drain saved")
    try:
        unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(seq)
    except Exception:
        pass


# ----------------------------------------------------------------------------- run
def main():
    if not eal.does_directory_exist(ROOT):
        eal.make_directory(ROOT)
    steps_ok = True
    liquid_mi = glass_mat = mpc = None
    try:
        _, liquid_mi = build_liquid_material()
    except Exception:
        steps_ok = False
        log("LIQUID MATERIAL FAILED:\n" + traceback.format_exc())
    try:
        mpc = build_mpc()
    except Exception:
        log("MPC FAILED (wet glass disabled):\n" + traceback.format_exc())
        mpc = None
    try:
        glass_mat = build_glass_material(mpc)
    except Exception:
        log("GLASS MATERIAL FAILED:\n" + traceback.format_exc())
    if liquid_mi is not None:
        try:
            liquid, cam = build_level(liquid_mi, glass_mat, mpc)
            build_sequence(liquid, cam)
        except Exception:
            steps_ok = False
            log("LEVEL/SEQUENCE FAILED:\n" + traceback.format_exc())
    eal.save_directory(ROOT)
    log("DONE" if steps_ok else "DONE WITH ERRORS")
    flush_log()


main()
