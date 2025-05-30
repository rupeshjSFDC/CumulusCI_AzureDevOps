import logging
from abc import ABC
from typing import List, Optional, Type

import cumulusci.core.dependencies.base as base_dependency
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.exceptions import DependencyResolutionError, VcsNotFoundError
from cumulusci.vcs.base import AbstractRepo
from pydantic import AnyUrl, root_validator, validator

logger = logging.getLogger(__name__)

VCS_AZURE_DEVOPS = "azure_devops"


def _validate_azure_devops_parameters(values):
    assert values.get("url") or values.get(
        "azure_devops"
    ), "Must specify `azure_devops` or `url`"

    return values


def _sync_azure_devops_and_url(values):
    # If only azure_devops is provided, set url to azure_devops
    if values.get("azure_devops") and not values.get("url"):
        values["url"] = values["azure_devops"]
    # If only url is provided, set azure_devops to url
    elif values.get("url") and not values.get("azure_devops"):
        values["azure_devops"] = values["url"]
    return values


class ADODependencyPin(base_dependency.VcsDependencyPin):
    """Model representing a request to pin an Azure DevOps dependency to a specific tag"""

    azure_devops: str

    @root_validator(pre=True)
    def sync_vcs_and_url(cls, values):
        return _sync_azure_devops_and_url(values)

    @property
    def vcsTagResolver(self):
        from cumulusci_ado.vcs.ado.dependencies.azure_devops_resolvers import (  # Circular imports
            ADOTagResolver,
        )

        raise ADOTagResolver


ADODependencyPin.update_forward_refs()


class BaseADODependency(base_dependency.BaseVcsDynamicDependency, ABC):
    """Base class for dynamic dependencies that reference an Azure DevOps repo."""

    pin_class = ADODependencyPin
    vcs: str = VCS_AZURE_DEVOPS
    azure_devops: Optional[AnyUrl] = None

    @root_validator
    def check_complete(cls, values):
        return _validate_azure_devops_parameters(values)

    @root_validator(pre=True)
    def sync_vcs_and_url(cls, values):
        return _sync_azure_devops_and_url(values)


class ADODynamicSubfolderDependency(
    base_dependency.VcsDynamicSubfolderDependency, BaseADODependency
):
    """A dependency expressed by a reference to a subfolder of a ADO repo, which needs
    to be resolved to a specific ref. This is always an unmanaged dependency."""

    @property
    def unmanagedVcsDependency(self) -> Type["UnmanagedADORefDependency"]:
        """A human-readable description of the dependency."""
        return UnmanagedADORefDependency


class ADODynamicDependency(base_dependency.VcsDynamicDependency, BaseADODependency):
    """A dependency expressed by a reference to a ADO repo, which needs
    to be resolved to a specific ref and/or package version."""

    def _flatten_unpackaged(
        self,
        repo: AbstractRepo,
        subfolder: str,
        skip: List[str],
        managed: bool,
        namespace: Optional[str],
    ) -> List[base_dependency.StaticDependency]:
        """Locate unmanaged dependencies from a repository subfolder (such as unpackaged/pre or unpackaged/post)"""
        unpackaged = []
        try:
            contents = repo.directory_contents(
                subfolder, return_as=dict, ref=(self.ref or "")
            )
        except VcsNotFoundError:
            contents = None

        if contents:
            for dirname in sorted(contents.keys()):
                this_subfolder = f"{subfolder}/{dirname}"
                if this_subfolder in skip:
                    continue

                unpackaged.append(
                    UnmanagedADORefDependency(
                        azure_devops=self.azure_devops,
                        ref=self.ref or "",
                        subfolder=this_subfolder,
                        unmanaged=not managed,
                        namespace_inject=namespace if namespace and managed else None,
                        namespace_strip=namespace
                        if namespace and not managed
                        else None,
                    )
                )

        return unpackaged

    def flatten(self, context: BaseProjectConfig) -> List[base_dependency.Dependency]:
        """Find more dependencies based on repository contents.

        Includes:
        - dependencies from cumulusci.yml
        - subfolders of unpackaged/pre
        - the contents of src, if this is not a managed package
        - subfolders of unpackaged/post
        """
        if not self.is_resolved:
            raise DependencyResolutionError(
                f"Dependency {self} is not resolved and cannot be flattened."
            )

        deps = []

        context.logger.info(
            f"Collecting dependencies from ADO repo {self.azure_devops}"
        )
        repo = get_repo(self.azure_devops, context)

        package_config = get_remote_project_config(repo, self.ref)
        _, namespace = get_package_data(package_config)

        # Parse upstream dependencies from the repo's cumulusci.yml
        # These may be unresolved or unflattened; if so, `get_static_dependencies()`
        # will manage them.
        dependencies = package_config.project__dependencies
        if dependencies:
            deps.extend([parse_dependency(d) for d in dependencies])
            if None in deps:
                raise DependencyResolutionError(
                    f"Unable to flatten dependency {self} because a transitive dependency could not be parsed."
                )

        # Check for unmanaged flag on a namespaced package
        managed = bool(namespace and not self.unmanaged)

        # Look for subfolders under unpackaged/pre
        # unpackaged/pre is always deployed unmanaged, no namespace manipulation.
        deps.extend(
            self._flatten_unpackaged(
                repo, "unpackaged/pre", self.skip, managed=False, namespace=None
            )
        )

        if not self.package_dependency:
            if managed:
                # We had an expectation of finding a package version and did not.
                raise DependencyResolutionError(
                    f"Could not find latest release for {self}"
                )

            # Deploy the project, if unmanaged.
            deps.append(
                UnmanagedADORefDependency(
                    azure_devops=self.azure_devops,
                    ref=self.ref or "",
                    unmanaged=self.unmanaged,
                    namespace_inject=self.namespace_inject,
                    namespace_strip=self.namespace_strip,
                )
            )
        else:
            deps.append(self.package_dependency)

        # We always inject the project's namespace into unpackaged/post metadata if managed
        deps.extend(
            self._flatten_unpackaged(
                repo,
                "unpackaged/post",
                self.skip,
                managed=managed,
                namespace=namespace,
            )
        )

        return deps

    @property
    def description(self):
        unmanaged = " (unmanaged)" if self.unmanaged else ""
        loc = f" @{self.tag or self.ref}" if self.ref or self.tag else ""
        return f"{self.azure_devops}{unmanaged}{loc}"


class UnmanagedADORefDependency(base_dependency.UnmanagedDependency):
    """Static dependency on unmanaged metadata in a specific ADO ref and subfolder."""

    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None

    # or
    azure_devops: Optional[AnyUrl] = None

    # and
    ref: str

    # for backwards compatibility only; currently unused
    filename_token: Optional[str] = None
    namespace_token: Optional[str] = None

    @root_validator
    def validate(cls, values):
        return _validate_azure_devops_parameters(values)

    def _get_zip_src(self, context):
        repo = get_repo(self.azure_devops, context)

        # We don't pass `subfolder` to download_extract_azure_devops_from_repo()
        # because we need to get the whole ref in order to
        # correctly handle any permutation of MDAPI/SFDX format,
        # with or without a subfolder specified.

        # install() will take care of that for us.
        return download_extract_azure_devops_from_repo(
            repo,
            ref=self.ref,
        )

    @property
    def name(self):
        subfolder = (
            f"/{self.subfolder}" if self.subfolder and self.subfolder != "src" else ""
        )
        return f"Deploy {self.azure_devops}{subfolder}"

    @property
    def description(self):
        subfolder = (
            f"/{self.subfolder}" if self.subfolder and self.subfolder != "src" else ""
        )

        return f"{self.azure_devops}{subfolder} @{self.ref}"
