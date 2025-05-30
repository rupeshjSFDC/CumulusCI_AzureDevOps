from cumulusci.plugins import PluginBase
from cumulusci.vcs.vcs_source import VCSSource

VCSSource.register(
    "azure_devops", "cumulusci_ado.vcs.ado.source.azure_devops.ADOSource"
)

# from cumulusci_ado.vcs.ado.dependencies.resolvers import VCS_AZURE_DEVOPS, ADO_RESOLVER_CLASSES
# from cumulusci.core.dependencies.base import update_resolver_classes
# update_resolver_classes(VCS_AZURE_DEVOPS, ADO_RESOLVER_CLASSES)


class AzureDevOpsPlugin(PluginBase):
    name = "Azure DevOps Plugin"
    api_name = "azure_devops"
    description = "Plugin for Azure DevOps integration"
    priority = 1
    version = "1.0"
    author = "Rupesh J"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
