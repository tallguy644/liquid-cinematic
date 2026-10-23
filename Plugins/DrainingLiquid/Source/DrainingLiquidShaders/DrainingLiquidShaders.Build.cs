using UnrealBuildTool;

public class DrainingLiquidShaders : ModuleRules
{
	public DrainingLiquidShaders(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PrivateDependencyModuleNames.AddRange(new string[] { "Core", "Projects", "RenderCore" });
	}
}
