using UnrealBuildTool;

public class LiquidCinematicEditorTarget : TargetRules
{
	public LiquidCinematicEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("LiquidCinematic");
	}
}
