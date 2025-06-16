from packaging import version


def test_plugin_entry_point():
    """Test that the plugin is properly registered as an entry point."""
    from importlib.metadata import entry_points

    # Get all cumulusci plugins
    plugins = entry_points().select(group="cumulusci.plugins")

    # Find our plugin
    ado_plugin = next((ep for ep in plugins if ep.name == "azure_devops"), None)
    assert ado_plugin is not None
    assert ado_plugin.value == "cumulusci_ado.azure_devops:AzureDevOpsPlugin"


def test_packaging_version_works():
    """Test that packaging version works correctly."""
    v1 = version.parse("1.0.0")
    v2 = version.parse("2.0.0")
    assert v2 > v1
    assert hasattr(v1, "major")
    assert hasattr(v1, "minor")
    assert hasattr(v1, "micro")
