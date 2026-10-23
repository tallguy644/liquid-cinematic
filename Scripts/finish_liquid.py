# Second pass: fixes refraction hookup and finishes level, camera and sequence.
import os, traceback, unreal
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else
     "C:/Users/Chris/Downloads/LiquidCinematic/Scripts", "setup_liquid.py")).read().split("# ----------------------------------------------------------------------------- run")[0])

LOG_PATH = LOG_PATH.replace("liquid_setup_log.txt", "liquid_finish_log.txt")


def fix_refraction():
    mat = unreal.load_asset(ROOT + "/M_DrainingLiquid")
    shade = sc = None
    for e in unreal.MaterialEditingLibrary.get_material_expressions(mat) if hasattr(unreal.MaterialEditingLibrary, "get_material_expressions") else []:
        n = e.get_class().get_name()
        if n == "MaterialExpressionCustom" and "DL_Shade" in e.get_editor_property("description"):
            shade = e
        if n == "MaterialExpressionSceneColor":
            sc = e
    if shade is None or sc is None:
        # fall back: find by iterating the material's expression collection
        try:
            exprs = mat.get_editor_property("expressions")
        except Exception:
            exprs = []
        for e in exprs:
            n = e.get_class().get_name()
            if n == "MaterialExpressionCustom" and "DL_Shade" in e.get_editor_property("description"):
                shade = e
            if n == "MaterialExpressionSceneColor":
                sc = e
    if shade is None or sc is None:
        log("refraction fix: could not locate nodes (shade=%s scene=%s)" % (shade, sc))
        return
    ok = False
    for o in ["RefractOffset"]:
        for i in ["Offset Fraction", "OffsetFraction", "Offset", "Input", "UV", "UVs"]:
            if mel.connect_material_expressions(shade, o, sc, i):
                log("refraction linked via SceneColor[%s]" % i)
                ok = True
                break
        if ok:
            break
    if not ok:
        # coordinates mode: UV = ViewportUV + offset
        try:
            sc.set_editor_property("input_mode", unreal.MaterialSceneAttributeInputMode.COORDINATES)
        except Exception as e:
            log("  input_mode: %s" % e)
        sp = mel.create_material_expression(mat, unreal.MaterialExpressionScreenPosition, -400, 300)
        add = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -250, 300)
        link(sp, ["ViewportUV", ""], add, "A")
        link(shade, "RefractOffset", add, "B")
        for i in ["UV", "UVs", "Input", "Coordinates", ""]:
            if mel.connect_material_expressions(add, "", sc, i):
                log("refraction linked via screen UV into SceneColor[%s]" % i)
                ok = True
                break
    if not ok:
        log("refraction still unlinked (liquid will look un-refracted)")
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)


def finish_level():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
    glass = actors.get("Glass")
    liquid = actors.get("DrainingLiquid")
    if liquid is None or glass is None:
        log("missing actors: glass=%s liquid=%s" % (glass, liquid))
        return None, None
    liquid.set_editor_property("glass_collection", unreal.load_asset(ROOT + "/MPC_DrainingLiquid"))
    liquid.set_editor_property("start_fill", 0.85)
    liquid.set_editor_property("vortex_core_radius", 0.8)
    liquid.set_editor_property("vortex_depth", 2.5)
    liquid.set_editor_property("wave_length", 2.0)
    liquid.attach_to_actor(glass, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                           unreal.AttachmentRule.KEEP_WORLD, False)

    if "Table" not in actors:
        table = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -2))
        table.set_actor_label("Table")
        table.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
        table.set_actor_scale3d(unreal.Vector(1.2, 0.8, 0.04))

    cam = actors.get("ShotCamera")
    if cam is None:
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
    log("level actors finished")
    les.save_current_level()
    log("level saved")
    return liquid, cam


def run():
    try:
        fix_refraction()
    except Exception:
        log("REFRACTION FIX FAILED:\n" + traceback.format_exc())
    try:
        liquid, cam = finish_level()
        if liquid is not None:
            build_sequence(liquid, cam)
        try:
            unreal.EditorLevelLibrary.pilot_level_actor(cam) if False else None
        except Exception:
            pass
    except Exception:
        log("FINISH FAILED:\n" + traceback.format_exc())
    eal.save_directory(ROOT)
    log("DONE")
    flush_log()


run()
