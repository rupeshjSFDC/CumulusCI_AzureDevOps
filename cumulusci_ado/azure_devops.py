from cumulusci.core.utils import import_global
from cumulusci.plugins import PluginBase
from cumulusci.vcs.vcs_source import VCSSource

import_global("cumulusci_ado.vcs.ado.service.AzureDevOpsService")

VCSSource.register(
    "azure_devops", "cumulusci_ado.vcs.ado.source.azure_devops.ADOSource"
)

from cumulusci_ado.vcs.ado.dependencies.ado_dependencies import VCS_ADO as dep
from cumulusci_ado.vcs.ado.dependencies.ado_resolvers import VCS_ADO as res

assert (
    dep == res
), "VCS_ADO must match in dependencies and resolvers. (Assertion done to load the ado dependencies and resolvers correctly)"


class AzureDevOpsPlugin(PluginBase):
    name = "Azure DevOps Plugin"
    api_name = "azure_devops"
    description = "Plugin for Azure DevOps integration"
    priority = 1
    version = "1.0"
    author = "Rupesh J"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
