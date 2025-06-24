from packaging import version

from cumulusci_ado import __version__


def test_version_format():
    """Test that the version string is in a valid format."""
    # This will raise an exception if the version is not valid
    parsed_version = version.parse(__version__)
    assert isinstance(parsed_version, version.Version)


def test_version_comparison():
    """Test that version comparison works correctly."""
    current_version = version.parse(__version__)
    older_version = version.parse("0.0.1")
    newer_version = version.parse("9.9.9")

    assert current_version > older_version
    assert current_version < newer_version


def test_version_components():
    """Test that version components can be accessed."""
    parsed_version = version.parse(__version__)
    assert hasattr(parsed_version, "major")
    assert hasattr(parsed_version, "minor")
    assert hasattr(parsed_version, "micro")
