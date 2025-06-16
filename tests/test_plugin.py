from cumulusci_ado.azure_devops import AzureDevOpsPlugin


def test_plugin_initialization():
    """Test that the plugin initializes correctly."""
    plugin = AzureDevOpsPlugin()
    assert plugin.name == "Azure DevOps Plugin"
    assert plugin.api_name == "azure_devops"
    assert plugin.description == "Plugin for Azure DevOps integration"
    assert plugin.priority == 1
    assert plugin.version == "1.0"
    assert plugin.author == "Rupesh J"
    assert plugin.plugin_config_file == "cumulusci_ado_plugin.yml"


def test_plugin_entry_point():
    """Test that the plugin is properly registered as an entry point."""
    from importlib.metadata import entry_points

    # Get all cumulusci plugins
    plugins = entry_points().select(group="cumulusci.plugins")

    # Find our plugin
    ado_plugin = next((ep for ep in plugins if ep.name == "azure_devops"), None)
    assert ado_plugin is not None
    assert ado_plugin.value == "cumulusci_ado.azure_devops:AzureDevOpsPlugin"


def test_plugin_initialization_method():
    """Test that the plugin's initialize method works."""
    plugin = AzureDevOpsPlugin()
    # This should not raise any exceptions
    plugin.initialize()
    assert plugin.plugin_project_config is not None
    assert "azure_devops" in plugin.plugin_project_config
    assert "api_version" in plugin.plugin_project_config["azure_devops"]
