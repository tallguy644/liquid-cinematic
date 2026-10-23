using UnrealBuildTool;

public class LiquidCinematic : ModuleRules
{
	public LiquidCinematic(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
	}
}
