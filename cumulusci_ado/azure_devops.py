from cumulusci.core.utils import import_global
from cumulusci.plugins.plugin_base import PluginBase
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
    """Plugin for Azure DevOps integration."""

    plugin_config_file = "cumulusci_plugin.yml"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def initialize(self) -> None:
        """Initialize the plugin."""
        super().initialize()
        # Add any additional initialization here

    def teardown(self) -> None:
        """Tear down the plugin."""
        super().teardown()
        # Add any additional cleanup here
