using UnrealBuildTool;

public class LiquidCinematicTarget : TargetRules
{
	public LiquidCinematicTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("LiquidCinematic");
	}
}
