# Tints the water so it reads on camera, and auto-plays LS_Drain when you press Play.
import unreal
out = []
mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary

mi = unreal.load_asset("/Game/DrainingLiquid/MI_Water_Clear")
for name, v in [("Absorption", (0.28, 0.07, 0.025, 0)),      # blue-green tint over ~7 cm
                ("ScatterColor", (0.05, 0.35, 0.45, 0)),
                ("FoamColor", (0.92, 0.96, 1.0, 0)),
                ("Optics", (0.05, 0.02, 0.35, 0.25))]:      # refract, rough, foam rough, murk
    ok = mel.set_material_instance_vector_parameter_value(mi, name, unreal.LinearColor(*v))
    out.append("%s set=%s" % (name, ok))
mel.update_material_instance(mi)
eal.save_loaded_asset(mi)

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
seq = unreal.load_asset("/Game/DrainingLiquid/LS_Drain")
lsa = None
for a in eas.get_all_level_actors():
    if a.get_class().get_name() == "LevelSequenceActor":
        lsa = a
if lsa is None:
    lsa = eas.spawn_actor_from_class(unreal.LevelSequenceActor, unreal.Vector(0, 0, 50))
    lsa.set_actor_label("LS_Drain_Player")
lsa.set_sequence(seq)
ps = lsa.get_editor_property("playback_settings")
ps.set_editor_property("auto_play", True)
lc = unreal.MovieSceneSequenceLoopCount()
lc.set_editor_property("value", -1)
ps.set_editor_property("loop_count", lc)
lsa.set_editor_property("playback_settings", ps)
out.append("sequence actor auto-play + loop set")

unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
out.append("level saved")
p = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "liquid_visible_log.txt"
open(p, "w").write("\n".join(out))
