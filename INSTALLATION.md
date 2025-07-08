# CumulusCI Plus Azure DevOps - Installation Guide

## Overview

This guide explains how to properly install `cumulusci-plus-azure-devops` and addresses common concerns about dependency management and potential conflicts.

## Understanding Dependency Installation

### How pipx Handles Dependencies

When you install a package with pipx, it **automatically installs all dependencies** listed in the package's `dependencies` array. This includes:

- `cumulusci-plus>=5.0.0`
- `azure-devops`
- `requests`
- `humanfriendly`
- `distro`
- `packaging>=23.0`

### Why Dependencies Might Seem Missing

If you think dependencies aren't being installed, it might be because:

1. **Isolated Environment**: pipx installs packages in isolated virtual environments, so dependencies aren't visible globally
2. **Network Issues**: Installation failed due to connectivity problems
3. **Package Conflicts**: Conflicting packages prevented proper installation
4. **Outdated pipx**: Using an old version of pipx

## Installation Methods

### Method 1: Recommended Installation (with conflict checking)

Use our custom installation script that performs pre-installation checks:

```bash
# Download and run the installation script
curl -O https://raw.githubusercontent.com/jorgesolebur/CumulusCI_AzureDevOps/main/install.py
python install.py
```

This script will:

- ✅ Check if pipx is available
- ✅ Detect conflicting packages
- ✅ Warn about potential conflicts
- ✅ Guide you through resolution steps
- ✅ Install the package with all dependencies

### Method 2: Direct pipx Installation

```bash
pipx install cumulusci-plus-azure-devops
```

### Method 3: pip Installation (not recommended for CLI tools)

```bash
pip install cumulusci-plus-azure-devops
```

## Conflict Prevention

### The Problem

This package is designed to work with `cumulusci-plus` (the next-generation CumulusCI), not the original `cumulusci` package. Having both installed can cause:

- Import conflicts
- Command name collisions
- Dependency version conflicts
- Unexpected behavior

### Our Solutions

#### 1. Runtime Conflict Detection

The package includes runtime checks that warn users if conflicts are detected:

```python
# This runs automatically when you import the package
WARNING: Both 'cumulusci' and 'cumulusci-plus' packages are detected.
This may cause conflicts. Please use 'cumulusci-plus' instead of 'cumulusci'.
Consider uninstalling 'cumulusci' with: pip uninstall cumulusci
```

#### 2. Pre-installation Checks

Our custom installation script checks for:

- Global installations of conflicting packages
- Existing pipx installations of conflicting packages
- Missing prerequisites

#### 3. Clear Documentation

This guide and the README clearly explain the relationship between packages and recommended installation methods.

## Troubleshooting

### "Dependencies not installed" Error

If you get this error:

1. **Check pipx environment**:

   ```bash
   pipx list
   # Should show cumulusci-plus-azure-devops with its dependencies
   ```

2. **Verify installation**:

   ```bash
   pipx run cumulusci-plus-azure-devops --help
   ```

3. **Reinstall if needed**:
   ```bash
   pipx uninstall cumulusci-plus-azure-devops
   pipx install cumulusci-plus-azure-devops
   ```

### Conflict Resolution

If you have conflicting packages:

1. **Remove conflicting packages**:

   ```bash
   # Remove global installation
   pip uninstall cumulusci

   # Remove pipx installation
   pipx uninstall cumulusci
   ```

2. **Clean reinstall**:
   ```bash
   pipx install cumulusci-plus-azure-devops
   ```

### Verification

After installation, verify everything works:

```bash
# Check installation
pipx list | grep cumulusci

# Test the package
pipx run cumulusci-plus-azure-devops --help

# Check for conflicts (should show no warnings)
python -c "import cumulusci_ado; print('Installation successful!')"
```

## Technical Details

### Why These Approaches Work

1. **pipx Isolation**: Each package gets its own virtual environment, preventing most conflicts
2. **Runtime Checks**: Early detection of conflicts when they do occur
3. **Clear Dependencies**: Explicit dependency specification in `pyproject.toml`
4. **User Education**: Clear documentation about proper installation methods

### Limitations

- **Cannot prevent installation**: Python packaging standards don't support pre-installation hooks
- **Runtime detection only**: Conflicts are detected after installation, not prevented
- **User cooperation required**: Users must follow recommendations to avoid conflicts

## Best Practices

1. **Use pipx for CLI tools**: Better isolation than pip
2. **Use our installation script**: Includes conflict checking
3. **Keep packages updated**: Regular updates prevent compatibility issues
4. **Follow migration guides**: When switching between package versions
5. **Report issues**: Help us improve conflict detection

## Support

If you encounter issues:

1. Check this guide first
2. Look at the main README.md
3. Open an issue on GitHub with:
   - Your operating system
   - Python version
   - Installation method used
   - Error messages
   - Output of `pipx list`
