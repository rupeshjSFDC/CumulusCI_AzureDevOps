#!/usr/bin/env python3
"""
Custom installation script for cumulusci-plus-azure-devops
This script performs pre-installation checks and guides users through the installation process.
"""

import json
import subprocess
import sys


def run_command(cmd, capture_output=True, check=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture_output, text=True, check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        return e


def check_pipx_available():
    """Check if pipx is available."""
    result = run_command("pipx --version", check=False)
    if result.returncode != 0:
        print("❌ pipx is not installed or not available in PATH")
        print("Please install pipx first:")
        print("  pip install pipx")
        print("  pipx ensurepath")
        return False
    print(f"✅ pipx is available: {result.stdout.strip()}")
    return True


def check_conflicting_packages():
    """Check for conflicting packages in the system."""
    print("🔍 Checking for conflicting packages...")

    # Check if cumulusci is installed globally
    result = run_command("pip list | grep cumulusci", check=False)
    if result.returncode == 0 and "cumulusci" in result.stdout:
        print("❌ CONFLICT DETECTED: 'cumulusci' package is installed globally")
        print("This may cause conflicts with 'cumulusci-plus-azure-devops'")
        print("\nRecommended actions:")
        print("1. Uninstall the conflicting package:")
        print("   pip uninstall cumulusci")
        print("2. Then run this installer again")

        response = input("\nDo you want to continue anyway? (y/N): ")
        if response.lower() != "y":
            print("Installation cancelled.")
            return False
        print("⚠️  Continuing with installation despite conflicts...")

    # Check pipx list for existing installations
    result = run_command("pipx list --json", check=False)
    if result.returncode == 0:
        try:
            pipx_data = json.loads(result.stdout)
            for venv_name, venv_info in pipx_data.get("venvs", {}).items():
                if "cumulusci" in venv_name and "azure-devops" not in venv_name:
                    print(f"❌ CONFLICT DETECTED: '{venv_name}' is installed via pipx")
                    print("This may cause conflicts with 'cumulusci-plus-azure-devops'")
                    print("\nRecommended action:")
                    print(f"   pipx uninstall {venv_name}")

                    response = input("\nDo you want to continue anyway? (y/N): ")
                    if response.lower() != "y":
                        print("Installation cancelled.")
                        return False
                    print("⚠️  Continuing with installation despite conflicts...")
        except json.JSONDecodeError:
            print("⚠️  Could not parse pipx list output")

    print("✅ No major conflicts detected")
    return True


def install_package():
    """Install the package using pipx."""
    print("\n🚀 Installing cumulusci-plus-azure-devops...")

    # Install the package
    result = run_command(
        "pipx install cumulusci-plus-azure-devops", capture_output=False
    )

    if result.returncode == 0:
        print("✅ Installation completed successfully!")
        print("\nNext steps:")
        print("1. Verify installation: pipx list | grep cumulusci")
        print("2. Check plugin status: cumulusci-ado status")
        print("3. Or use the shorter alias: cci-ado status")
        print("4. Get help: cumulusci-ado help")
        return True
    else:
        print("❌ Installation failed!")
        print("Please check the error messages above and try again.")
        return False


def main():
    """Main installation function."""
    print("🔧 CumulusCI Plus Azure DevOps Installation Script")
    print("=" * 50)

    # Check prerequisites
    if not check_pipx_available():
        sys.exit(1)

    # Check for conflicts
    if not check_conflicting_packages():
        sys.exit(1)

    # Install the package
    if not install_package():
        sys.exit(1)

    print("\n🎉 Installation complete!")


if __name__ == "__main__":
    main()
