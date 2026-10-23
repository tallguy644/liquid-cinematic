# Feed SceneColor proper screen UVs: ViewportUV + RefractOffset.
import unreal
mel = unreal.MaterialEditingLibrary
mat = unreal.load_asset("/Game/DrainingLiquid/M_DrainingLiquid")
out = []
shade = sc = None
for e in mel.get_material_expressions(mat):
    n = e.get_class().get_name()
    if n == "MaterialExpressionCustom" and "DL_Shade" in e.get_editor_property("description"):
        shade = e
    if n == "MaterialExpressionSceneColor":
        sc = e
out.append("found shade=%s scene=%s" % (shade is not None, sc is not None))
try:
    out.append("input_mode before: %s" % sc.get_editor_property("input_mode"))
except Exception as ex:
    out.append("no input_mode: %s" % ex)
sp = mel.create_material_expression(mat, unreal.MaterialExpressionScreenPosition, -400, 320)
add = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -250, 320)
ok_a = any(mel.connect_material_expressions(sp, o, add, "A") for o in ["ViewportUV", ""])
ok_b = mel.connect_material_expressions(shade, "RefractOffset", add, "B")
ok_c = any(mel.connect_material_expressions(add, "", sc, i) for i in ["UVs", "UV", "Input"])
out.append("links A=%s B=%s C=%s" % (ok_a, ok_b, ok_c))
mel.recompile_material(mat)
unreal.EditorAssetLibrary.save_loaded_asset(mat)
out.append("saved")
p = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + "liquid_fix_log.txt"
open(p, "w").write("\n".join(out))
