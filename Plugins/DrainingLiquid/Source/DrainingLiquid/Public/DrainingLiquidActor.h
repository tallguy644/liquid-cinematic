#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DrainingLiquidActor.generated.h"

class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UMaterialParameterCollection;
class UCurveFloat;

/**
 * Liquid inside a container that drains for cinematics.
 * Attach to your container, then keyframe DrainProgress 0 -> 1 in Sequencer.
 * Level, drain curve, vortex, ripples, slosh and the wet glass are all derived from it.
 */
UCLASS(Blueprintable, meta = (DisplayName = "Draining Liquid"),
	hidecategories = (Input, Collision, Replication, HLOD, Physics, Networking, LOD, Cooking))
class DRAININGLIQUID_API ADrainingLiquidActor : public AActor
{
	GENERATED_BODY()

public:
	ADrainingLiquidActor();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void Tick(float DeltaSeconds) override;
	virtual bool ShouldTickIfViewportsOnly() const override { return true; }

	/** 0 = empty, 1 = full to the top of InteriorMesh. */
	UFUNCTION(BlueprintPure, Category = "Liquid")
	float GetCurrentFill() const;

	// ------------------------------------------------------------------ Setup

	/** Closed, watertight mesh of the container's INTERIOR, normals facing outward (toward the glass). Disable Nanite on it. */
	UPROPERTY(EditAnywhere, Category = "Liquid|Setup")
	TObjectPtr<UStaticMesh> InteriorMesh;

	/** Material instance of M_DrainingLiquid (see README). */
	UPROPERTY(EditAnywhere, Category = "Liquid|Setup")
	TObjectPtr<UMaterialInterface> LiquidMaterial;

	/** Optional MPC_DrainingLiquid: drives wet film, droplets and residue ring on the glass material. */
	UPROPERTY(EditAnywhere, Category = "Liquid|Setup")
	TObjectPtr<UMaterialParameterCollection> GlassCollection;

	/** Optional: interior radius (cm, mesh space) by normalized height (X: 0 = bottom, 1 = top). Leave empty for straight walls. */
	UPROPERTY(EditAnywhere, Category = "Liquid|Setup")
	TObjectPtr<UCurveFloat> RadiusProfile;

	/** Pulls the surface edge in slightly so it never pokes through the glass (cm). */
	UPROPERTY(EditAnywhere, Category = "Liquid|Setup", meta = (ClampMin = "0"))
	float RadiusInset = 0.05f;

	/** Drain hole position relative to the mesh centre, local XY (cm). */
	UPROPERTY(EditAnywhere, Category = "Liquid|Setup")
	FVector2D DrainOffset = FVector2D::ZeroVector;

	/** Tick if the top surface looks lit from underneath on your engine version. */
	UPROPERTY(EditAnywhere, Category = "Liquid|Setup")
	bool bFlipSurfaceNormal = false;

	// ------------------------------------------------------------------ Drain (keyframe in Sequencer)

	/** 0 = not started, 1 = fully drained. Key this with LINEAR tangents; the physics curve is applied for you. */
	UPROPERTY(EditAnywhere, Interp, BlueprintReadWrite, Category = "Liquid|Drain", meta = (ClampMin = "0", ClampMax = "1", UIMin = "0", UIMax = "1"))
	float DrainProgress = 0.f;

	/** Fill level before draining starts (fraction of the interior height). */
	UPROPERTY(EditAnywhere, Interp, BlueprintReadWrite, Category = "Liquid|Drain", meta = (ClampMin = "0", ClampMax = "1"))
	float StartFill = 0.85f;

	/** 2 = gravity drain through a bottom hole (Torricelli: fast at first, slowing as pressure drops). 1 = linear. */
	UPROPERTY(EditAnywhere, Category = "Liquid|Drain", meta = (ClampMin = "1", ClampMax = "4"))
	float DrainCurveExponent = 2.f;

	/** >= 0 sets the fill directly (0..1) and ignores DrainProgress. */
	UPROPERTY(EditAnywhere, Interp, BlueprintReadWrite, Category = "Liquid|Drain")
	float FillOverride = -1.f;

	/** How far behind the waterline (in DrainProgress) the wet film on the glass trails. */
	UPROPERTY(EditAnywhere, Interp, Category = "Liquid|Drain", meta = (ClampMin = "0", ClampMax = "1"))
	float WetFilmLag = 0.12f;

	// ------------------------------------------------------------------ Vortex

	UPROPERTY(EditAnywhere, Interp, Category = "Liquid|Vortex", meta = (ClampMin = "0"))
	float VortexMaxStrength = 1.f;

	/** The whirlpool starts forming once the fill drops below this. */
	UPROPERTY(EditAnywhere, Category = "Liquid|Vortex", meta = (ClampMin = "0.01", ClampMax = "1"))
	float VortexOnsetFill = 0.35f;

	/** >= 0 overrides the automatic vortex strength (key it for full control). */
	UPROPERTY(EditAnywhere, Interp, Category = "Liquid|Vortex")
	float VortexOverride = -1.f;

	UPROPERTY(EditAnywhere, Category = "Liquid|Vortex", meta = (ClampMin = "0.01"))
	float VortexCoreRadius = 1.5f;

	UPROPERTY(EditAnywhere, Category = "Liquid|Vortex", meta = (ClampMin = "0"))
	float VortexDepth = 4.f;

	UPROPERTY(EditAnywhere, Category = "Liquid|Vortex", meta = (ClampMin = "1", ClampMax = "8"))
	int32 SpiralArms = 3;

	UPROPERTY(EditAnywhere, Category = "Liquid|Vortex")
	float SpiralTightness = 6.f;

	/** Negative spins the other way. */
	UPROPERTY(EditAnywhere, Category = "Liquid|Vortex")
	float SpiralSpin = 5.f;

	// ------------------------------------------------------------------ Surface

	UPROPERTY(EditAnywhere, Interp, Category = "Liquid|Surface", meta = (ClampMin = "0.1"))
	float WaveLength = 4.f;

	UPROPERTY(EditAnywhere, Interp, Category = "Liquid|Surface", meta = (ClampMin = "0"))
	float WaveAmplitude = 0.03f;

	UPROPERTY(EditAnywhere, Category = "Liquid|Surface")
	float WaveSpeed = 6.f;

	/** Ripple boost while draining (multiplier on WaveAmplitude). */
	UPROPERTY(EditAnywhere, Category = "Liquid|Surface", meta = (ClampMin = "0"))
	float DrainTurbulence = 2.f;

	/** Height of the bright line where liquid climbs the glass (cm). */
	UPROPERTY(EditAnywhere, Category = "Liquid|Surface", meta = (ClampMin = "0"))
	float MeniscusHeight = 0.15f;

	UPROPERTY(EditAnywhere, Category = "Liquid|Surface", meta = (ClampMin = "0"))
	float EdgeFoamWidth = 0.3f;

	// ------------------------------------------------------------------ Slosh

	/** Surface tilts and wobbles when the container moves. */
	UPROPERTY(EditAnywhere, Category = "Liquid|Slosh")
	bool bEnableSlosh = true;

	UPROPERTY(EditAnywhere, Category = "Liquid|Slosh", meta = (ClampMin = "0.05"))
	float SloshFrequency = 1.6f;

	UPROPERTY(EditAnywhere, Category = "Liquid|Slosh", meta = (ClampMin = "0", ClampMax = "1"))
	float SloshDamping = 0.12f;

	UPROPERTY(EditAnywhere, Category = "Liquid|Slosh", meta = (ClampMin = "0"))
	float MaxSlope = 0.4f;

protected:
	UPROPERTY(VisibleAnywhere, Category = "Liquid")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, Category = "Liquid")
	TObjectPtr<UStaticMeshComponent> LiquidMesh;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> LiquidMID;

private:
	float FillAtProgress(float Progress) const;
	float ComputeVortex(float Fill) const;
	float ComputeDrainActivity() const;
	void UpdateSlosh(float DeltaSeconds);
	void PushParameters();

	FVector LocalCenter = FVector::ZeroVector;
	float LocalBottomZ = 0.f;
	float LocalTopZ = 100.f;
	float LocalRadius = 10.f;

	FVector2D Slope = FVector2D::ZeroVector;
	FVector2D SlopeVel = FVector2D::ZeroVector;
	FVector PrevLocation = FVector::ZeroVector;
	FVector PrevVelocity = FVector::ZeroVector;
	int32 HistoryFrames = 0;
};
