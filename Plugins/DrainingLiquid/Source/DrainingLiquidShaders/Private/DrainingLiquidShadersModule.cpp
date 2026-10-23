// Maps the plugin's Shaders folder so Custom material nodes can include
//   /DrainingLiquidShaders/DrainingLiquid.ush
// Must load at PostConfigInit (before shaders compile), so it lives in its own tiny module.

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "ShaderCore.h"

class FDrainingLiquidShadersModule : public IModuleInterface
{
public:
	virtual void StartupModule() override
	{
		static const FString VirtualPath = TEXT("/DrainingLiquidShaders");
		if (AllShaderSourceDirectoryMappings().Contains(VirtualPath))
		{
			return;
		}
		const TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("DrainingLiquid"));
		if (Plugin.IsValid())
		{
			AddShaderSourceDirectoryMapping(VirtualPath, FPaths::Combine(Plugin->GetBaseDir(), TEXT("Shaders")));
		}
	}
};

IMPLEMENT_MODULE(FDrainingLiquidShadersModule, DrainingLiquidShaders)
