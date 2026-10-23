#include "DrainingLiquidActor.h"

#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Curves/CurveFloat.h"
#include "Engine/StaticMesh.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialParameterCollection.h"

namespace DrainingLiquid
{
	// Liquid material (vector parameters)
	static const FName P_PlaneOrigin(TEXT("DL_PlaneOrigin"));
	static const FName P_PlaneNormal(TEXT("DL_PlaneNormal"));
	static const FName P_AxisOrigin(TEXT("DL_AxisOrigin"));
	static const FName P_AxisDir(TEXT("DL_AxisDir"));
	static const FName P_DrainPoint(TEXT("DL_DrainPoint"));
	static const FName P_Shape(TEXT("DL_Shape"));
	static const FName P_Waves(TEXT("DL_Waves"));
	static const FName P_Vortex(TEXT("DL_Vortex"));
	static const FName P_Spiral(TEXT("DL_Spiral"));

	// Glass Material Parameter Collection
	static const FName C_SurfaceH(TEXT("DL_SurfaceH"));
	static const FName C_WetTopH(TEXT("DL_WetTopH"));
	static const FName C_StartH(TEXT("DL_StartH"));
	static const FName C_Radius(TEXT("DL_Radius"));
	static const FName C_AxisOrigin(TEXT("DL_AxisOrigin"));
	static const FName C_AxisDir(TEXT("DL_AxisDir"));

	static constexpr float Gravity = 980.f;          // cm/s^2
	static constexpr float TeleportDistance = 200.f; // cm per frame = camera cut / snap, not motion

	static FLinearColor ToColor(const FVector& V, float W = 0.f)
	{
		return FLinearColor(float(V.X), float(V.Y), float(V.Z), W);
	}
}

ADrainingLiquidActor::ADrainingLiquidActor()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostUpdateWork; // after Sequencer and attachments have moved things

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;

	LiquidMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LiquidMesh"));
	LiquidMesh->SetupAttachment(Root);
	LiquidMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	LiquidMesh->CastShadow = false;
	LiquidMesh->bAffectDistanceFieldLighting = false;
	LiquidMesh->TranslucencySortPriority = 0; // keep the glass ABOVE this (e.g. 1) so it draws on top
}

void ADrainingLiquidActor::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);

	LiquidMesh->SetStaticMesh(InteriorMesh);

	LiquidMID = nullptr;
	if (InteriorMesh && LiquidMaterial)
	{
		LiquidMID = UMaterialInstanceDynamic::Create(LiquidMaterial, this);
		for (int32 i = 0; i < LiquidMesh->GetNumMaterials(); ++i)
		{
			LiquidMesh->SetMaterial(i, LiquidMID);
		}
	}

	if (InteriorMesh)
	{
		const FBox B = InteriorMesh->GetBoundingBox();
		const FVector Size = B.GetSize();
		LocalCenter = B.GetCenter();
		LocalBottomZ = float(B.Min.Z);
		LocalTopZ = float(B.Max.Z);
		LocalRadius = 0.5f * float(FMath::Min(Size.X, Size.Y));
	}

	Slope = SlopeVel = FVector2D::ZeroVector;
	PrevLocation = LiquidMesh->GetComponentLocation();
	PrevVelocity = FVector::ZeroVector;
	HistoryFrames = 1;

	PushParameters();
}

void ADrainingLiquidActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	UpdateSlosh(DeltaSeconds);
	PushParameters();
}

float ADrainingLiquidActor::FillAtProgress(float Progress) const
{
	const float P = FMath::Clamp(Progress, 0.f, 1.f);
	return StartFill * FMath::Pow(1.f - P, DrainCurveExponent);
}

float ADrainingLiquidActor::GetCurrentFill() const
{
	return FillOverride >= 0.f ? FMath::Clamp(FillOverride, 0.f, 1.f) : FillAtProgress(DrainProgress);
}

float ADrainingLiquidActor::ComputeDrainActivity() const
{
	// Smooth 0..1 "is it draining right now" — deterministic, so scrubbing Sequencer looks identical to the render.
	if (FillOverride >= 0.f)
	{
		return 0.f;
	}
	return FMath::SmoothStep(0.f, 0.03f, DrainProgress) * (1.f - FMath::SmoothStep(0.97f, 1.f, DrainProgress));
}

float ADrainingLiquidActor::ComputeVortex(float Fill) const
{
	if (VortexOverride >= 0.f)
	{
		return VortexOverride;
	}
	const float Onset = FMath::Max(VortexOnsetFill, 0.01f);
	const float Grow = 1.f - FMath::SmoothStep(Onset * 0.3f, Onset, Fill); // stronger as it gets shallow
	const float Collapse = FMath::SmoothStep(0.f, 0.03f, Fill);              // breaks up in the last few %
	return VortexMaxStrength * Grow * Collapse * ComputeDrainActivity();
}

void ADrainingLiquidActor::UpdateSlosh(float Dt)
{
	const FVector Loc = LiquidMesh->GetComponentLocation();

	if (!bEnableSlosh || Dt <= KINDA_SMALL_NUMBER)
	{
		PrevLocation = Loc;
		if (!bEnableSlosh)
		{
			Slope = SlopeVel = FVector2D::ZeroVector;
		}
		return;
	}

	const FVector Delta = Loc - PrevLocation;
	const bool bTeleport = Delta.SizeSquared() > FMath::Square(DrainingLiquid::TeleportDistance);
	const FVector Vel = bTeleport ? FVector::ZeroVector : Delta / Dt;
	FVector Acc = (HistoryFrames >= 2 && !bTeleport) ? (Vel - PrevVelocity) / Dt : FVector::ZeroVector;
	Acc = Acc.GetClampedToMaxSize(5000.0);

	PrevLocation = Loc;
	PrevVelocity = Vel;
	HistoryFrames = bTeleport ? 1 : HistoryFrames + 1;

	// In the container's accelerating frame the free surface settles perpendicular to (g - a),
	// so its slope is -a_horizontal / g. A damped spring chases that target -> slosh.
	const FVector2D Target(-Acc.X / DrainingLiquid::Gravity, -Acc.Y / DrainingLiquid::Gravity);
	const double Omega = 2.0 * PI * FMath::Max(SloshFrequency, 0.05f);
	const double K = Omega * Omega;
	const double C = 2.0 * SloshDamping * Omega;

	const int32 Steps = FMath::Clamp(FMath::CeilToInt(Dt * 240.f), 1, 32);
	const double H = double(Dt) / Steps;
	for (int32 i = 0; i < Steps; ++i)
	{
		const FVector2D Accel = (Target - Slope) * K - SlopeVel * C;
		SlopeVel += Accel * H;
		Slope += SlopeVel * H;
	}

	if (Slope.Size() > MaxSlope)
	{
		Slope = Slope.GetSafeNormal() * MaxSlope;
		SlopeVel *= 0.5;
	}
}

void ADrainingLiquidActor::PushParameters()
{
	using namespace DrainingLiquid;

	const float Fill = GetCurrentFill();
	LiquidMesh->SetVisibility(InteriorMesh != nullptr && Fill > 1e-4f);

	if (!InteriorMesh)
	{
		return;
	}

	const FTransform& Xf = LiquidMesh->GetComponentTransform();
	const FVector Scale = Xf.GetScale3D().GetAbs();
	const float Height = LocalTopZ - LocalBottomZ;
	const float SurfaceLocalZ = LocalBottomZ + Fill * Height;

	const FVector AxisO = Xf.TransformPosition(FVector(LocalCenter.X, LocalCenter.Y, LocalBottomZ));
	const FVector AxisD = Xf.GetUnitAxis(EAxis::Z);
	const FVector PlaneO = Xf.TransformPosition(FVector(LocalCenter.X, LocalCenter.Y, SurfaceLocalZ));
	const FVector PlaneN = FVector(-Slope.X, -Slope.Y, 1.0).GetSafeNormal(); // gravity-aligned + slosh
	const FVector DrainP = Xf.TransformPosition(FVector(LocalCenter.X + DrainOffset.X, LocalCenter.Y + DrainOffset.Y, SurfaceLocalZ));

	const float RadiusLocal = RadiusProfile ? RadiusProfile->GetFloatValue(Fill) : LocalRadius;
	const float RadiusWS = FMath::Max(RadiusLocal - RadiusInset, 0.f) * float(FMath::Min(Scale.X, Scale.Y));

	const float Activity = ComputeDrainActivity();
	const float Vortex = ComputeVortex(Fill);
	const float WaveAmp = WaveAmplitude * (1.f + DrainTurbulence * Activity);

	if (LiquidMID)
	{
		LiquidMID->SetVectorParameterValue(P_PlaneOrigin, ToColor(PlaneO));
		LiquidMID->SetVectorParameterValue(P_PlaneNormal, ToColor(PlaneN));
		LiquidMID->SetVectorParameterValue(P_AxisOrigin, ToColor(AxisO));
		LiquidMID->SetVectorParameterValue(P_AxisDir, ToColor(AxisD));
		LiquidMID->SetVectorParameterValue(P_DrainPoint, ToColor(DrainP));
		LiquidMID->SetVectorParameterValue(P_Shape, FLinearColor(RadiusWS, MeniscusHeight, EdgeFoamWidth, bFlipSurfaceNormal ? -1.f : 1.f));
		LiquidMID->SetVectorParameterValue(P_Waves, FLinearColor(WaveLength, WaveAmp, WaveSpeed, 0.f));
		LiquidMID->SetVectorParameterValue(P_Vortex, FLinearColor(Vortex, VortexCoreRadius, VortexDepth, float(SpiralArms)));
		LiquidMID->SetVectorParameterValue(P_Spiral, FLinearColor(SpiralTightness, SpiralSpin, 0.f, 0.f));
	}

	if (GlassCollection)
	{
		// Heights are measured along the container axis from the bottom, in world cm.
		auto AlongAxis = [&](float LocalZ) { return (LocalZ - LocalBottomZ) * float(Scale.Z); };

		const float WetFill = FillOverride >= 0.f ? Fill : FMath::Max(FillAtProgress(DrainProgress - WetFilmLag), Fill);

		UKismetMaterialLibrary::SetScalarParameterValue(this, GlassCollection, C_SurfaceH, AlongAxis(SurfaceLocalZ));
		UKismetMaterialLibrary::SetScalarParameterValue(this, GlassCollection, C_WetTopH, AlongAxis(LocalBottomZ + WetFill * Height));
		UKismetMaterialLibrary::SetScalarParameterValue(this, GlassCollection, C_StartH, AlongAxis(LocalBottomZ + StartFill * Height));
		UKismetMaterialLibrary::SetScalarParameterValue(this, GlassCollection, C_Radius, RadiusWS);
		UKismetMaterialLibrary::SetVectorParameterValue(this, GlassCollection, C_AxisOrigin, ToColor(AxisO));
		UKismetMaterialLibrary::SetVectorParameterValue(this, GlassCollection, C_AxisDir, ToColor(AxisD));
	}
}
