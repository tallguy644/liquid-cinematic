# LiquidCinematic

Unreal Engine 5.8 project for a cinematic of liquid draining out of a glass.

## What's inside

- **Plugins/DrainingLiquid** — C++ plugin with a parametric draining-liquid actor and HLSL shader (Beer–Lambert absorption, meniscus, ripples, drain whirlpool, slosh, wet glass). Keyframe one value, `DrainProgress` 0 → 1. See its README for details.
- **Content/Maps/LiquidShot** — level with the glass, liquid and shot camera.
- **Content/DrainingLiquid** — liquid material `M_DrainingLiquid`, `MI_Water_Clear`, glass material `M_Glass`, `MPC_DrainingLiquid`, and the 12 s sequence `LS_Drain`.
- **Scripts/** — editor Python that builds all of the above from scratch (`setup_liquid.py`, then `finish_liquid.py` and `fix_refraction.py`).

## Open it

1. Clone, then double-click `LiquidCinematic.uproject` (needs Visual Studio with *Game development with C++*).
2. Click **Yes** when asked to rebuild modules.
3. Open `Content/Maps/LiquidShot`, then `LS_Drain` in Sequencer and scrub.

Render with Movie Render Queue using Lumen (not the Path Tracer).
