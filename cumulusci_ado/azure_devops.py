from cumulusci.plugins import PluginBase


class AzureDevOpsPlugin(PluginBase):
    name = "Azure DevOps Plugin"
    api_name = "azure_devops"
    description = "Plugin for Azure DevOps integration"
    priority = 1
    version = "1.0"
    author = "Rupesh J"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
