import logging
from abc import ABC
from typing import Optional, Type

import cumulusci.core.dependencies.base as base_dependency
from cumulusci.core.dependencies.dependencies import (
    add_dependency_class,
    add_dependency_pin_class,
)
from cumulusci.core.exceptions import DependencyResolutionError
from pydantic import root_validator
from pydantic.networks import AnyUrl

from cumulusci_ado.vcs.ado.adapter import ADORepository
from cumulusci_ado.vcs.ado.exceptions import ADOApiNotFoundError

logger = logging.getLogger(__name__)

VCS_ADO = "azure_devops"


def get_ado_repo(project_config, url) -> ADORepository:
    from cumulusci_ado.vcs.ado.service import AzureDevOpsService, VCSService

    vcs_service: Optional[VCSService] = AzureDevOpsService.get_service_for_url(
        project_config, url
    )

    if vcs_service is None:
        raise DependencyResolutionError(f"Could not find a ADO service for URL: {url}")

    try:
        repo = vcs_service.get_repository(options={"repository_url": url})
        if not repo:
            raise ADOApiNotFoundError(f"Get ADO Repository found None. {url}")
        return repo
    except ADOApiNotFoundError as e:
        raise DependencyResolutionError(
            f"Could not find a ADO repository at {url}: {e}"
        )


def _validate_ado_parameters(values):
    assert values.get("url") or values.get(
        "azure_devops"
    ), "Must specify `azure_devops`"

    return values


def _sync_ado_and_url(values):
    # If only ado is provided, set url to ado
    if values.get("azure_devops") and not values.get("url"):
        values["url"] = values["azure_devops"]
    # If only url is provided, set ado to url
    elif values.get("url") and not values.get("azure_devops"):
        values["azure_devops"] = values["url"]
    return values


class ADODependencyPin(base_dependency.VcsDependencyPin):
    """Model representing a request to pin an ADO dependency to a specific tag"""

    azure_devops: str

    @property
    def vcsTagResolver(self):  # -> Type["AbstractTagResolver"]:
        from cumulusci_ado.vcs.ado.dependencies.ado_resolvers import (  # Circular imports
            ADOTagResolver,
        )

        return ADOTagResolver

    @root_validator(pre=True)
    def sync_vcs_and_url(cls, values):
        """Defined vcs should be assigned to url"""
        return _sync_ado_and_url(values)


ADODependencyPin.update_forward_refs()


class BaseADODependency(base_dependency.BaseVcsDynamicDependency, ABC):
    """Base class for dynamic dependencies that reference an ADO repo."""

    azure_devops: Optional[AnyUrl] = None
    vcs: str = VCS_ADO
    pin_class = ADODependencyPin

    @root_validator
    def validate_ado_parameters(cls, values):
        return _validate_ado_parameters(values)

    @root_validator(pre=True)
    def sync_vcs_and_url(cls, values):
        """Defined vcs should be assigned to url"""
        return _sync_ado_and_url(values)


class ADODynamicSubfolderDependency(
    BaseADODependency, base_dependency.VcsDynamicSubfolderDependency
):
    """A dependency expressed by a reference to a subfolder of a ADO repo, which needs
    to be resolved to a specific ref. This is always an unmanaged dependency."""

    @property
    def unmanagedVcsDependency(self) -> Type["UnmanagedADORefDependency"]:
        """A human-readable description of the dependency."""
        return UnmanagedADORefDependency


class ADODynamicDependency(BaseADODependency, base_dependency.VcsDynamicDependency):
    """A dependency expressed by a reference to a ADO repo, which needs
    to be resolved to a specific ref and/or package version."""

    @property
    def unmanagedVcsDependency(self) -> Type["UnmanagedADORefDependency"]:
        """A human-readable description of the dependency."""
        return UnmanagedADORefDependency

    def get_repo(self, context, url) -> Optional["ADORepository"]:
        return get_ado_repo(context, url)


class UnmanagedADORefDependency(base_dependency.UnmanagedVcsDependency):
    """Static dependency on unmanaged metadata in a specific ADO ref and subfolder."""

    azure_devops: Optional[AnyUrl] = None

    def get_repo(self, context, url) -> Optional["ADORepository"]:
        return get_ado_repo(context, url)

    @root_validator
    def validate(cls, values):
        return _validate_ado_parameters(values)

    @root_validator(pre=True)
    def sync_vcs_and_url(cls, values):
        """Defined vcs should be assigned to url"""

        return _sync_ado_and_url(values)


add_dependency_class(UnmanagedADORefDependency)
add_dependency_class(ADODynamicDependency)
add_dependency_class(ADODynamicSubfolderDependency)

add_dependency_pin_class(ADODependencyPin)
