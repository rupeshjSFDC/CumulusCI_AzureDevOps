import abc
from typing import Any, List, Optional

from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.resolvers import (
    AbstractReleaseTagResolver,
    AbstractTagResolver,
    AbstractUnmanagedHeadResolver,
    AbstractVcsCommitStatusPackageResolver,
    AbstractVcsReleaseBranchResolver,
    DependencyResolutionStrategy,
    update_resolver_classes,
)
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.utils.git import get_feature_branch_name
from cumulusci.vcs.bootstrap import find_repo_feature_prefix

from cumulusci_ado.vcs.ado.adapter import ADOBranch, ADORepository
from cumulusci_ado.vcs.ado.dependencies.ado_dependencies import (
    VCS_ADO,
    BaseADODependency,
    get_ado_repo,
)


class ADOTagResolver(AbstractTagResolver):
    """Resolver that identifies a ref by a specific ADO tag."""

    name = "ADO Tag Resolver"
    vcs = VCS_ADO

    def get_repo(self, context: BaseProjectConfig, url: Optional[str]) -> ADORepository:
        """Get the ADO repository for the given URL."""
        return get_ado_repo(context, url)


class ADOReleaseTagResolver(AbstractReleaseTagResolver):
    """Resolver that identifies a ref by finding the latest ADO release."""

    name = "ADO Release Resolver"
    vcs = VCS_ADO

    def get_repo(self, context: BaseProjectConfig, url: Optional[str]) -> ADORepository:
        """Get the ADO repository for the given URL."""
        return get_ado_repo(context, url)


class ADOBetaReleaseTagResolver(ADOReleaseTagResolver):
    """Resolver that identifies a ref by finding the latest ADO release, including betas."""

    name = "ADO Release Resolver (Betas)"
    include_beta = True


class ADOUnmanagedHeadResolver(AbstractUnmanagedHeadResolver):
    """Resolver that identifies a ref by finding the latest commit on the main branch."""

    name = "ADO Unmanaged Resolver"
    vcs = VCS_ADO

    def get_repo(self, context: BaseProjectConfig, url: Optional[str]) -> ADORepository:
        """Get the ADO repository for the given URL."""
        return get_ado_repo(context, url)


class ADOReleaseBranchCommitStatusResolver(AbstractVcsReleaseBranchResolver):
    """Resolver that identifies a ref by finding a beta 2GP package version
    in a commit status on a `feature/NNN` release branch."""

    name = "ADO Release Branch Commit Status Resolver"
    commit_status_context = "2gp_context"
    commit_status_default = "Build Feature Test Package"
    branch_offset_start = 0
    branch_offset_end = 1

    def get_repo(self, context: BaseProjectConfig, url: Optional[str]) -> ADORepository:
        """Get the ADO repository for the given URL."""
        return get_ado_repo(context, url)


class ADOReleaseBranchUnlockedResolver(AbstractVcsReleaseBranchResolver):
    """Resolver that identifies a ref by finding an unlocked package version
    in a commit status on a `feature/NNN` release branch."""

    name = "ADO Release Branch Unlocked Commit Status Resolver"
    commit_status_context = "unlocked_context"
    commit_status_default = "Build Unlocked Test Package"
    branch_offset_start = 0
    branch_offset_end = 1

    def get_repo(self, context: BaseProjectConfig, url: Optional[str]) -> ADORepository:
        """Get the ADO repository for the given URL."""
        return get_ado_repo(context, url)


class ADOPreviousReleaseBranchCommitStatusResolver(AbstractVcsReleaseBranchResolver):
    """Resolver that identifies a ref by finding a beta 2GP package version
    in a commit status on a `feature/NNN` release branch that is earlier
    than the matching local release branch."""

    name = "ADO Previous Release Branch Commit Status Resolver"
    commit_status_context = "2gp_context"
    commit_status_default = "Build Feature Test Package"
    branch_offset_start = 1
    branch_offset_end = 3

    def get_repo(self, context: BaseProjectConfig, url: Optional[str]) -> ADORepository:
        """Get the ADO repository for the given URL."""
        return get_ado_repo(context, url)


class ADOPreviousReleaseBranchUnlockedResolver(AbstractVcsReleaseBranchResolver):
    """Resolver that identifies a ref by finding an unlocked package version
    in a commit status on a `feature/NNN` release branch that is earlier
    than the matching local release branch."""

    name = "ADO Previous Release Branch Unlocked Commit Status Resolver"
    commit_status_context = "unlocked_context"
    commit_status_default = "Build Unlocked Test Package"
    branch_offset_start = 1
    branch_offset_end = 3

    def get_repo(self, context: BaseProjectConfig, url: Optional[str]) -> ADORepository:
        """Get the ADO repository for the given URL."""
        return get_ado_repo(context, url)


class AbstractADOExactMatchCommitStatusResolver(
    AbstractVcsCommitStatusPackageResolver, abc.ABC
):
    """Abstract base class for resolvers that identify a ref by finding a package version
    in a commit status on a branch whose name matches the local branch."""

    def get_repo(self, context: BaseProjectConfig, url: Optional[str]) -> ADORepository:
        """Get the ADO repository for the given URL."""
        return get_ado_repo(context, url)

    def get_branches(
        self,
        dep: BaseADODependency,
        context: BaseProjectConfig,
    ) -> List[ADOBranch]:
        repo = self.get_repo(context, dep.url)
        if not repo:
            raise DependencyResolutionError(
                f"Unable to access ADO repository for {dep.url}"
            )

        try:
            remote_branch_prefix = find_repo_feature_prefix(repo)
        except Exception:
            context.logger.info(
                f"Could not find feature branch prefix or commit-status context for {repo.clone_url}. Unable to resolve package."
            )
            return []

        # Attempt exact match
        try:
            branch = get_feature_branch_name(
                context.repo_branch or "", context.project__git__prefix_feature
            )
            release_branch = repo.branch(f"{remote_branch_prefix}{branch}")
        except Exception:
            context.logger.info(f"Exact-match branch not found for {repo.clone_url}.")
            return []

        return [release_branch]


class ADOExactMatch2GPResolver(AbstractADOExactMatchCommitStatusResolver):
    """Resolver that identifies a ref by finding a 2GP package version
    in a commit status on a branch whose name matches the local branch."""

    name = "ADO Exact-Match Commit Status Resolver"
    commit_status_context = "2gp_context"
    commit_status_default = "Build Feature Test Package"


class ADOExactMatchUnlockedCommitStatusResolver(
    AbstractADOExactMatchCommitStatusResolver
):
    """Resolver that identifies a ref by finding an unlocked package version
    in a commit status on a branch whose name matches the local branch."""

    name = "ADO Exact-Match Unlocked Commit Status Resolver"
    commit_status_context = "unlocked_context"
    commit_status_default = "Build Unlocked Test Package"


class AbstractADODefaultBranchCommitStatusResolver(
    AbstractVcsCommitStatusPackageResolver, abc.ABC
):
    """Abstract base class for resolvers that identify a ref by finding a beta package version
    in a commit status on the repo's default branch."""

    def get_repo(self, context: BaseProjectConfig, url: Optional[str]) -> ADORepository:
        """Get the ADO repository for the given URL."""
        return get_ado_repo(context, url)

    def get_branches(
        self,
        dep: BaseADODependency,
        context: BaseProjectConfig,
    ) -> List[ADOBranch]:
        repo = self.get_repo(context, dep.url)

        return [repo.branch(repo.default_branch)]


class ADODefaultBranch2GPResolver(AbstractADODefaultBranchCommitStatusResolver):
    name = "ADO Default Branch Commit Status Resolver"
    commit_status_context = "2gp_context"
    commit_status_default = "Build Feature Test Package"


class ADODefaultBranchUnlockedCommitStatusResolver(
    AbstractADODefaultBranchCommitStatusResolver
):
    name = "ADO Default Branch Unlocked Commit Status Resolver"
    commit_status_context = "unlocked_context"
    commit_status_default = "Build Unlocked Test Package"


ADO_RESOLVER_CLASSES: dict[str, type[Any]] = {
    DependencyResolutionStrategy.STATIC_TAG_REFERENCE: ADOTagResolver,
    DependencyResolutionStrategy.COMMIT_STATUS_EXACT_BRANCH: ADOExactMatch2GPResolver,
    DependencyResolutionStrategy.COMMIT_STATUS_RELEASE_BRANCH: ADOReleaseBranchCommitStatusResolver,
    DependencyResolutionStrategy.COMMIT_STATUS_PREVIOUS_RELEASE_BRANCH: ADOPreviousReleaseBranchCommitStatusResolver,
    DependencyResolutionStrategy.COMMIT_STATUS_DEFAULT_BRANCH: ADODefaultBranch2GPResolver,
    DependencyResolutionStrategy.BETA_RELEASE_TAG: ADOBetaReleaseTagResolver,
    DependencyResolutionStrategy.RELEASE_TAG: ADOReleaseTagResolver,
    DependencyResolutionStrategy.UNMANAGED_HEAD: ADOUnmanagedHeadResolver,
    DependencyResolutionStrategy.UNLOCKED_EXACT_BRANCH: ADOExactMatchUnlockedCommitStatusResolver,
    DependencyResolutionStrategy.UNLOCKED_RELEASE_BRANCH: ADOReleaseBranchUnlockedResolver,
    DependencyResolutionStrategy.UNLOCKED_PREVIOUS_RELEASE_BRANCH: ADOPreviousReleaseBranchUnlockedResolver,
    DependencyResolutionStrategy.UNLOCKED_DEFAULT_BRANCH: ADODefaultBranchUnlockedCommitStatusResolver,
}

update_resolver_classes(VCS_ADO, ADO_RESOLVER_CLASSES)
