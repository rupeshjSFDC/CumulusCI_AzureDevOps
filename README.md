# cumulusci-azure-devops

A plugin for [CumulusCI](https://github.com/SFDO-Tooling/CumulusCI) supporting Azure DevOps integration.

## Features

- Integrates Azure DevOps pipelines with CumulusCI
- Provides tasks and utilities for Azure DevOps automation

## Installation

```bash
pip install cumulusci-azure-devops
```

## Usage

Add the plugin to your `cumulusci.yml`:

```yaml
plugins:
  cciplus_ado:
    path: cciplus_ado
```

Or use via the CumulusCI CLI if installed as a package.

## Development

- Requires Python 3.11+
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines (if available)

## License

GNU General Public License v3.0

## Links

- [CumulusCI](https://github.com/SFDO-Tooling/CumulusCI)
- [Azure DevOps Python API](https://github.com/microsoft/azure-devops-python-api)
