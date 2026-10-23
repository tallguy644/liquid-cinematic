# Draining Liquid — UE5 plugin

A Sequencer-driven liquid that drains out of a container and holds up in close-ups. You keyframe **one value**, `DrainProgress` from 0 to 1. The plugin derives everything else from it:

- **Level** follows a real gravity-drain curve (Torricelli). It drops fast at first and slows near the end. A linear keyframe is the main reason drains look fake.
- **Colour depth** uses Beer–Lambert absorption over the true distance light travels through the liquid. It is darker through the middle, clearer at the edges, and the last thin layer goes nearly clear.
- **Meniscus line** where the liquid climbs the glass.
- **Surface** is reconstructed exactly at the waterline, with fine ripples. The ripples get stronger while draining.
- **Whirlpool** forms over the drain as the liquid gets shallow, with rotating spiral arms and an aerated core.
- **Underside** shows a silvery total-internal-reflection band when the camera is below the waterline.
- **Slosh** tilts the surface and wobbles it with a damped spring when the container moves.
- **Wet glass** (optional) shows a film trailing the waterline, rivulets, beaded droplets and a residue ring at the starting level.

Everything is deterministic: scrubbing in Sequencer matches the Movie Render Queue output.

---

## 1. Install

1. Copy the `DrainingLiquid` folder into `YourProject/Plugins/`.
2. Your project needs to be a C++ project. If it is Blueprint-only, use **Tools → New C++ Class → None → Create**, then close the editor.
3. Right-click the `.uproject` → **Generate Visual Studio project files**, then build. Or just open the project and accept the rebuild prompt.
4. Enable the **Draining Liquid** plugin if it isn't already enabled.

## 2. Make the interior mesh (in Blender or similar)

1. Duplicate the glass and delete the outer shell, keeping only the inner wall and inner bottom.
2. Cap the top so the mesh is watertight.
3. **Flip normals so they face outward**, toward the glass.
4. Shrink it about 0.05 cm (Alt+S in Blender) so it doesn't z-fight with the glass.
5. Put the pivot at the bottom centre and keep the container's up axis as +Z.
6. You don't need extra subdivisions, because the clipping is done per pixel.
7. In Unreal, **disable Nanite** on this mesh. Translucent materials can't use Nanite, so Unreal would fall back to a coarse mesh.

## 3. Build the material `M_DrainingLiquid`

Material settings:

- **Blend Mode:** Translucent
- **Shading Model:** Default Lit
- **Two Sided:** on
- **Translucency → Lighting Mode:** Surface ForwardShading
- **Tangent Space Normal:** off (under Advanced)
- **Refraction:** none. The refraction is done manually below, which allows proper per-channel tinting.
- **Opacity:** constant 1
- **Specular:** 0.25 (water has F0 ≈ 0.02)

### Parameters

The actor fills these in for you, so their defaults don't matter. Create them as **Vector Parameters** with these exact names:

`DL_PlaneOrigin`, `DL_PlaneNormal`, `DL_AxisOrigin`, `DL_AxisDir`, `DL_DrainPoint`, `DL_Shape`, `DL_Waves`, `DL_Vortex`, `DL_Spiral`

### Look parameters

These belong to you; tweak them in a Material Instance.

| Name | Type | Clear water | Tea / whiskey | Juice / milky |
|---|---|---|---|---|
| `Absorption` (1/cm) | Vector | 0.0045, 0.0015, 0.0008 | 0.05, 0.12, 0.30 | 0.02, 0.06, 0.25 |
| `ScatterColor` | Vector | — | 0.4, 0.15, 0.03 | 0.9, 0.5, 0.1 |
| `FoamColor` | Vector | 0.9, 0.9, 0.9 | 0.85, 0.75, 0.6 | 1, 0.95, 0.85 |
| `Optics` (Refract, Rough, FoamRough, Murk) | Vector | 0.04, 0.02, 0.35, 0 | 0.04, 0.03, 0.4, 0.15 | 0.03, 0.08, 0.4, 0.8 |

> The most common cause of fake-looking water is making it too blue. Real clear water in a glass is almost colourless. Let the refraction, the meniscus and the reflections sell it.

### Custom node 1 — `DL_Liquid`

- **Output Type:** Float 3
- **Include File Paths:** `/DrainingLiquidShaders/DrainingLiquid.ush`

Inputs, each with what to connect:

| Input | Connect |
|---|---|
| WorldPos | Absolute World Position |
| CamPos | Camera Position |
| TwoSided | TwoSidedSign |
| VertexN | VertexNormalWS |
| SceneThick | SceneDepth − PixelDepth |
| GameTime | Time |
| PlaneO | `DL_PlaneOrigin` (RGB) |
| PlaneN | `DL_PlaneNormal` (RGB) |
| AxisO | `DL_AxisOrigin` (RGB) |
| AxisD | `DL_AxisDir` (RGB) |
| DrainP | `DL_DrainPoint` (RGB) |
| Shape | `DL_Shape` (RGBA) |
| Waves | `DL_Waves` (RGBA) |
| Vortex | `DL_Vortex` (RGBA) |
| Spiral | `DL_Spiral` (RGBA) |

Additional Outputs, all Float 1: `Thickness`, `Foam`, `Rim`, `Underside`.

Code:

```hlsl
return DL_Liquid(WorldPos, CamPos, TwoSided, VertexN, SceneThick, GameTime,
                 PlaneO, PlaneN, AxisO, AxisD, DrainP, Shape, Waves, Vortex, Spiral,
                 Thickness, Foam, Rim, Underside);
```

### Custom node 2 — `DL_Shade`

- **Output Type:** Float 3
- **Include File Paths:** the same `.ush`

Inputs:

| Input | Connect |
|---|---|
| N | DL_Liquid main output |
| ViewN | TransformVector (World → View) of that same output |
| WorldPos | Absolute World Position |
| CamPos | Camera Position |
| Thick | DL_Liquid `Thickness` output |
| FoamIn | DL_Liquid `Foam` output |
| RimIn | DL_Liquid `Rim` output |
| Under | DL_Liquid `Underside` output |
| Absorption | `Absorption` parameter |
| ScatterColor | `ScatterColor` parameter |
| FoamColor | `FoamColor` parameter |
| Optics | `Optics` parameter (RGBA) |

Additional Outputs:

- `Transmittance` (Float 3)
- `RefractOffset` (Float 2)
- `Rough` (Float 1)

Code:

```hlsl
return DL_Shade(N, ViewN, WorldPos, CamPos, Thick, FoamIn, RimIn, Under,
                Absorption, ScatterColor, FoamColor, Optics,
                Transmittance, RefractOffset, Rough);
```

### Final wiring

- **Base Color** ← DL_Shade main output
- **Roughness** ← DL_Shade `Rough`
- **Normal** ← DL_Liquid main output
- **Emissive Color** ← `SceneColor` node (Offset Fraction ← `RefractOffset`).RGB × `Transmittance`

Then create a Material Instance of this material. That instance is the one you assign to the actor.

## 4. Optional — wet glass

1. Create a **Material Parameter Collection** `MPC_DrainingLiquid` with these parameters:
   - Scalars: `DL_SurfaceH`, `DL_WetTopH`, `DL_StartH`, `DL_Radius`
   - Vectors: `DL_AxisOrigin`, `DL_AxisDir`
2. In your glass material, add a Custom node with **Output Type Float 1** and the same include path.
   - Inputs:
     - `WorldPos`
     - `AxisO`, `AxisD`, `Radius`, `SurfaceH`, `WetTopH`, `StartH` — Collection Parameter nodes from the MPC
     - `GameTime` — Time
     - `FilmFade` (≈ 1.5), `DropSize` (≈ 0.25), `RingWidth` (≈ 0.08) — constants
   - Additional Outputs: `Drops`, `Ring` (Float 1)
   - Code:

```hlsl
float Wet; DL_GlassWet(WorldPos, AxisO, AxisD, Radius, SurfaceH, WetTopH, StartH, GameTime,
                        FilmFade, DropSize, RingWidth, Wet, Drops, Ring);
return Wet;
```

3. Use the outputs in the glass material:
   - Add `Drops × 0.25 + Wet × 0.04 + Ring × 0.12` to the glass Opacity.
   - Add `Drops × 0.15` to the glass refraction.
   - Tint by the liquid colour × `Ring` for residue.
4. Set the glass mesh **Translucency Sort Priority = 1** so it draws on top of the liquid (the liquid uses 0).
   - If your glass has a modelled inner surface, split the back/inner faces into a separate mesh at priority −1. Otherwise they draw over the liquid.

## 5. Use it

1. Place **Draining Liquid** in the level and attach it to your container actor. This makes slosh follow the container's animation.
2. Set these on the actor:
   - `InteriorMesh`
   - `LiquidMaterial` (your Material Instance)
   - `GlassCollection` (optional)
   - `DrainOffset` (where the hole is)
3. Bottles, flasks and other shapes that change width: add a **RadiusProfile** float curve. X is normalized height (0–1); Y is the interior radius in cm.
4. In your Level Sequence, add the actor and key **DrainProgress** 0 → 1 with **linear** tangents. Key `VortexOverride` or `WaveAmplitude` too if you want direct control.
5. In Movie Render Queue:
   - Anti-aliasing: Temporal Samples ≥ 8.
   - Engine Warm Up Count ≥ 32, so slosh settles.
   - In the post process volume, under Lumen Reflections, turn on **High Quality Translucency Reflections**.

### Limitations

- **This is a camera-ray technique, so render with Lumen, not the Path Tracer.** The Path Tracer traces secondary rays the trick can't follow.
- **The vortex is shading only.** It's great for a whirlpool over a drain, but it can't show a deep air funnel.
- **This approach suits liquid that leaves through a hole.** If the liquid pours out by tipping, or you need splashes, use a baked simulation (see below).
- **Keep the container within a few km of the world origin.** Custom nodes use float precision.

## When to use a real simulation instead

| Situation | Best route |
|---|---|
| Bottom drain, level drops, whirlpool | **This plugin** — fully art-directable and cheap. |
| Pouring out, tipping, splashing, glugging | **Niagara Fluids 3D FLIP** in-engine. Enable the *Niagara Fluids* and *Niagara Sim Caching* plugins, start from a 3D FLIP liquid template, use the container as collision, then cache the sim and play it from a Sequencer cache track so renders are repeatable. |
| Hero close-up, maximum realism | **Offline sim → Alembic → Geometry Cache.** Use Houdini FLIP, Blender + FLIP Fluids, or JangaFX LiquiGen, then play it with a Geometry Cache track. You can reuse the absorption / meniscus shading ideas from `DL_Shade` on the imported mesh. |
