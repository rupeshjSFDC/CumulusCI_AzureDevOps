# cumulusci-azure-devops

A plugin for [CumulusCI](https://github.com/SFDO-Tooling/CumulusCI) supporting Azure DevOps integration.

## Features

- Integrates Azure DevOps pipelines with CumulusCI
- Provides tasks and utilities for Azure DevOps automation

## Installation

### Recommended Installation (with conflict checking)

For the best experience, use our custom installation script that checks for conflicts:

```bash
# Download and run the installation script
curl -O https://raw.githubusercontent.com/jorgesolebur/CumulusCI_AzureDevOps/main/install.py
python install.py
```

### Manual Installation via pipx (recommended)

```bash
pipx install cumulusci-plus-azure-devops
```

### Manual Installation via pip

```bash
pip install cumulusci-plus-azure-devops
```

### Important Notes

- **Conflict Warning**: This package is designed to work with `cumulusci-plus` (version 5.0.0+), not the original `cumulusci` package. Having both installed may cause conflicts.
- **pipx vs pip**: We recommend using `pipx` for CLI tools as it provides better isolation and prevents dependency conflicts.
- **Dependencies**: All required dependencies (including `cumulusci-plus`, `azure-devops`, etc.) are automatically installed.
- **CLI Tools**: After installation, you'll have access to `cumulusci-ado` and `cci-ado` commands for plugin management.

## Usage

### Plugin Management Commands

After installation, you can use these commands to manage the plugin:

```bash
# Check plugin installation status
cumulusci-ado status

# Show version information
cumulusci-ado version

# Get help
cumulusci-ado help

# Short alias versions
cci-ado status
cci-ado version
cci-ado help
```

### CumulusCI Integration

Add the plugin to your `cumulusci.yml`:

```yaml
plugins:
  azure_devops:
    path: cumulusci_ado
```

Or use via the CumulusCI CLI if installed as a package. The plugin will automatically integrate with CumulusCI when installed.

## Development

- Requires Python 3.11+
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines (if available)

## License

GNU General Public License v3.0

## Links

- [CumulusCI](https://github.com/SFDO-Tooling/CumulusCI)
- [Azure DevOps Python API](https://github.com/microsoft/azure-devops-python-api)
