import abc
import itertools
from typing import Callable, Iterable, List, Optional, Tuple, Union

from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.base import (
    AbstractResolver,
    Dependency,
    DependencyPin,
    DependencyResolutionStrategy,
    DynamicDependency,
    StaticDependency,
)
from cumulusci.core.dependencies.dependencies import (
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
    parse_dependencies,
    parse_pins,
)
from cumulusci.core.exceptions import CumulusCIException, DependencyResolutionError
from cumulusci.core.github import (  # find_latest_release,
    find_repo_feature_prefix,
    get_version_id_from_commit,
)
from cumulusci.core.versions import PackageType
from cumulusci.utils.git import (
    construct_release_branch_name,
    get_feature_branch_name,
    get_release_identifier,
    is_release_branch_or_child,
)
from cumulusci.vcs.bootstrap import find_latest_release

from cumulusci_ado.vcs.ado.dependencies.azure_devops import (  # get_package_data,; get_package_details_from_tag,; get_remote_project_config,; get_repo,
    VCS_AZURE_DEVOPS,
    BaseADODependency,
)


class ADOTagResolver(AbstractResolver):
    """Resolver that identifies a ref by a specific ADO tag."""

    name = "ADO Tag Resolver"

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, BaseADODependency) and dep.tag is not None

    def resolve(
        self, dep: BaseADODependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        # TODO: try:
        #     # Find the azure devops release corresponding to this tag.
        #     repo = get_repo(dep.azure_devops, context)
        #     release = repo.release_from_tag(dep.tag)
        #     tag = repo.tag(repo.ref(f"tags/{release.tag_name}").object.sha)
        #     ref = tag.object.sha
        #     package_config = get_remote_project_config(repo, ref)
        #     package_name, namespace = get_package_data(package_config)
        #     version_id, package_type = get_package_details_from_tag(tag)

        #     install_unmanaged = (
        #         dep.is_unmanaged  # We've been told to use this dependency unmanaged
        #         or not (
        #             # We will install managed if:
        #             namespace  # the package has a namespace
        #             or version_id  # or is a non-namespaced Unlocked Package
        #         )
        #     )

        #     if install_unmanaged:
        #         return ref, None
        #     else:
        #         if package_type is PackageType.SECOND_GEN:
        #             package_dep = PackageVersionIdDependency(
        #                 version_id=version_id,
        #                 version_number=release.name,
        #                 package_name=package_name,
        #             )
        #         else:
        #             package_dep = PackageNamespaceVersionDependency(
        #                 namespace=namespace,
        #                 version=release.name,
        #                 package_name=package_name,
        #                 version_id=version_id,
        #             )

        #         return (ref, package_dep)
        # except NotFoundError:
        #     raise DependencyResolutionError(f"No release found for tag {dep.tag}")
        return (None, None)


class ADOReleaseTagResolver(AbstractResolver):
    """Resolver that identifies a ref by finding the latest ADO release."""

    name = "ADO Release Resolver"
    include_beta = False

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, BaseADODependency)

    def resolve(
        self, dep: BaseADODependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        repo = dep.repo
        release = find_latest_release(repo, include_beta=self.include_beta)
        if release:
            tag = repo.tag(repo.ref(f"tags/{release.tag_name}").object.sha)
            version_id, package_type = get_package_details_from_tag(tag)

            ref = tag.object.sha
            package_config = get_remote_project_config(repo, ref)
            package_name, namespace = get_package_data(package_config)

            install_unmanaged = (
                dep.is_unmanaged  # We've been told to use this dependency unmanaged
                or not (
                    # We will install managed if:
                    namespace  # the package has a namespace
                    or version_id  # or is a non-namespaced Unlocked Package
                )
            )

            if install_unmanaged:
                return ref, None
            else:
                if package_type is PackageType.SECOND_GEN:
                    package_dep = PackageVersionIdDependency(
                        version_id=version_id,
                        version_number=release.name,
                        package_name=package_name,
                    )
                else:
                    package_dep = PackageNamespaceVersionDependency(
                        namespace=namespace,
                        version=release.name,
                        package_name=package_name,
                        version_id=version_id,
                    )
                return (ref, package_dep)

        return (None, None)


class ADOBetaReleaseTagResolver(ADOReleaseTagResolver):
    """Resolver that identifies a ref by finding the latest ADO release, including betas."""

    name = "ADO Release Resolver (Betas)"
    include_beta = True


class ADOUnmanagedHeadResolver(AbstractResolver):
    """Resolver that identifies a ref by finding the latest commit on the main branch."""

    name = "ADO Unmanaged Resolver"

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, BaseADODependency)

    def resolve(
        self, dep: BaseADODependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        # TODO: repo = get_repo(dep.azure_devops, context)
        # return (repo.branch(repo.default_branch).commit.sha, None)
        return (None, None)


class AbstractADOCommitStatusPackageResolver(AbstractResolver, abc.ABC):
    """Abstract base class for resolvers that use commit statuses to find packages."""

    commit_status_context = ""
    commit_status_default = ""

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return self.is_valid_repo_context(context) and isinstance(
            dep, BaseADODependency
        )

    def is_valid_repo_context(self, context: BaseProjectConfig) -> bool:
        return bool(context.repo_branch and context.project__git__prefix_feature)

    @abc.abstractmethod
    def get_branches(
        self,
        dep: BaseADODependency,
        context: BaseProjectConfig,
    ) -> List:  # List[Branch]
        ...

    def resolve(
        self, dep: BaseADODependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        branches = self.get_branches(dep, context)

        # We know `repo` is not None because `get_branches()` will raise in that case.

        # TODO: repo = context.get_repo_from_url(dep.azure_devops)
        # remote_context = get_remote_context(
        #     repo, self.commit_status_context, self.commit_status_default
        # )
        # for branch in branches:
        #     version_id, commit = locate_commit_status_package_id(
        #         repo,
        #         branch,
        #         remote_context,
        #     )

        #     if version_id and commit:
        #         context.logger.info(
        #             f"{self.name} located package version {version_id} on branch {branch.name} on {repo.clone_url} at commit {branch.commit.sha}"
        #         )
        #         package_config = get_remote_project_config(repo, commit.sha)
        #         package_name, _ = get_package_data(package_config)

        #         return commit.sha, PackageVersionIdDependency(
        #             version_id=version_id, package_name=package_name
        #         )

        # context.logger.warn(
        #     f"{self.name} did not locate package package version on {repo.clone_url}."
        # )
        return (None, None)


class AbstractADOReleaseBranchResolver(AbstractADOCommitStatusPackageResolver, abc.ABC):
    """Abstract base class for resolvers that use commit statuses on release branches to find refs."""

    branch_offset_start = 0
    branch_offset_end = 0

    def is_valid_repo_context(self, context: BaseProjectConfig) -> bool:
        return bool(
            super().is_valid_repo_context(context)
            and is_release_branch_or_child(
                context.repo_branch, context.project__git__prefix_feature  # type: ignore
            )
        )

    def get_branches(
        self,
        dep: BaseADODependency,
        context: BaseProjectConfig,
    ) -> List:  # List[Branch]
        # release_id = get_release_id(context)
        # repo = context.get_repo_from_url(dep.azure_devops)
        # if not repo:
        #     raise DependencyResolutionError(
        #         f"Unable to access ADO repository for {dep.azure_devops}"
        #     )

        # try:
        #     remote_branch_prefix = find_repo_feature_prefix(repo)
        # except Exception:
        #     context.logger.info(
        #         f"Could not find feature branch prefix or commit-status context for {repo.clone_url}. Unable to resolve packages."
        #     )
        #     return []

        # # We will check at least the release branch corresponding to our release id.
        # # We may be configured to check backwards on release branches.
        # release_branches = []
        # for i in range(self.branch_offset_start, self.branch_offset_end):
        #     remote_matching_branch = construct_release_branch_name(
        #         remote_branch_prefix, str(release_id - i)
        #     )
        #     try:
        #         release_branches.append(repo.branch(remote_matching_branch))
        #     except NotFoundError:
        #         context.logger.info(f"Remote branch {remote_matching_branch} not found")
        #         pass

        # return release_branches
        return []  # Placeholder for actual branch retrieval logic


class ADOReleaseBranchCommitStatusResolver(AbstractADOReleaseBranchResolver):
    """Resolver that identifies a ref by finding a beta 2GP package version
    in a commit status on a `feature/NNN` release branch."""

    name = "ADO Release Branch Commit Status Resolver"
    commit_status_context = "2gp_context"
    commit_status_default = "Build Feature Test Package"
    branch_offset_start = 0
    branch_offset_end = 1


class ADOReleaseBranchUnlockedResolver(AbstractADOReleaseBranchResolver):
    """Resolver that identifies a ref by finding an unlocked package version
    in a commit status on a `feature/NNN` release branch."""

    name = "ADO Release Branch Unlocked Commit Status Resolver"
    commit_status_context = "unlocked_context"
    commit_status_default = "Build Unlocked Test Package"
    branch_offset_start = 0
    branch_offset_end = 1


class ADOPreviousReleaseBranchCommitStatusResolver(AbstractADOReleaseBranchResolver):
    """Resolver that identifies a ref by finding a beta 2GP package version
    in a commit status on a `feature/NNN` release branch that is earlier
    than the matching local release branch."""

    name = "ADO Previous Release Branch Commit Status Resolver"
    commit_status_context = "2gp_context"
    commit_status_default = "Build Feature Test Package"
    branch_offset_start = 1
    branch_offset_end = 3


class ADOPreviousReleaseBranchUnlockedResolver(AbstractADOReleaseBranchResolver):
    """Resolver that identifies a ref by finding an unlocked package version
    in a commit status on a `feature/NNN` release branch that is earlier
    than the matching local release branch."""

    name = "ADO Previous Release Branch Unlocked Commit Status Resolver"
    commit_status_context = "unlocked_context"
    commit_status_default = "Build Unlocked Test Package"
    branch_offset_start = 1
    branch_offset_end = 3


class AbstractADOExactMatchCommitStatusResolver(
    AbstractADOCommitStatusPackageResolver, abc.ABC
):
    """Abstract base class for resolvers that identify a ref by finding a package version
    in a commit status on a branch whose name matches the local branch."""

    def get_branches(
        self,
        dep: BaseADODependency,
        context: BaseProjectConfig,
    ) -> List:  # List[Branch]
        repo = context.get_repo_from_url(dep.azure_devops)
        if not repo:
            raise DependencyResolutionError(
                f"Unable to access ADO repository for {dep.azure_devops}"
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
            # TODO: branch = get_feature_branch_name(
            #     context.repo_branch, context.project__git__prefix_feature
            # )
            # release_branch = repo.branch(f"{remote_branch_prefix}{branch}")
            release_branch = ""
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
    AbstractADOCommitStatusPackageResolver, abc.ABC
):
    """Abstract base class for resolvers that identify a ref by finding a beta package version
    in a commit status on the repo's default branch."""

    def get_branches(
        self,
        dep: BaseADODependency,
        context: BaseProjectConfig,
    ) -> List:  # List[Branch]
        repo = context.get_repo_from_url(dep.azure_devops)

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


ADO_RESOLVER_CLASSES = {
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
