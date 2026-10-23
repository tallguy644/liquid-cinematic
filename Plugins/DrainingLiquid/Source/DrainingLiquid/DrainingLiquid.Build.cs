using UnrealBuildTool;

public class DrainingLiquid : ModuleRules
{
	public DrainingLiquid(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
	}
}
