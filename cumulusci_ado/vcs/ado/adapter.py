from typing import Optional, Union

from azure.devops.connection import Connection
from azure.devops.exceptions import AzureDevOpsClientError
from azure.devops.v7_0.git.git_client import GitClient
from azure.devops.v7_0.git.models import (
    GitAnnotatedTag,
    GitObject,
    GitRef,
    GitRepository,
    TeamProjectReference,
)
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.vcs.models import (
    AbstractBranch,
    AbstractComparison,
    AbstractGitTag,
    AbstractPullRequest,
    AbstractRef,
    AbstractRepo,
    AbstractRepoCommit,
)


class ADORef(AbstractRef):
    ref: GitRef
    sha: Optional[str]
    type: Optional[str]

    def __init__(self, ref: GitRef, **kwargs) -> None:
        super().__init__(ref, **kwargs)
        self.sha = self.ref.object_id
        self.type = "tag"


class ADOTag(AbstractGitTag):
    ref: Optional[GitRef]

    def __init__(self, tag: object, **kwargs) -> None:
        super().__init__(tag, **kwargs)
        self.ref = kwargs.get("ref", None)
        self.sha: Optional[str] = self.ref.sha if self.ref else None


class ADOComparison(AbstractComparison):
    def get_comparison(self) -> None:
        """Gets the comparison object for the current base and head."""
        # self.comparison = self.repo.repo.compare_commits(self.base, self.head)
        return None

    @property
    def files(self) -> list:
        # return (
        #     self.comparison.files if self.comparison and self.comparison.files else []
        # )
        return []

    @property
    def behind_by(self) -> int:
        """Returns the number of commits the head is behind the base."""
        # return (
        #     self.comparison.behind_by
        #     if self.comparison and self.comparison.behind_by
        #     else 0
        # )
        return 0

    @classmethod
    def compare(cls, repo: AbstractRepo, base: str, head: str) -> "ADOComparison":
        comparison = ADOComparison(repo, base, head)
        comparison.get_comparison()
        return comparison


class ADOCommit(AbstractRepoCommit):
    """ADO comparison object for comparing commits."""

    pass


class ADOBranch(AbstractBranch):
    repo: "ADORepository"

    def __init__(self, repo: "ADORepository", branch_name: str, **kwargs) -> None:
        super().__init__(repo, branch_name, **kwargs)
        self.repo = repo

    def get_branch(self) -> None:
        # try:
        #     self.branch = self.repo.repo.branch(self.name)
        # except github3.exceptions.NotFoundError:
        #     message = f"Branch {self.name} not found"
        #     raise GithubApiNotFoundError(message)
        return

    @classmethod
    def branches(cls, git_repo: AbstractRepo) -> list["ADOBranch"]:
        """Fetches all branches from the given repository"""
        # try:
        #     branches = git_repo.repo.branches()
        #     return [
        #         ADOBranch(git_repo, branch.name, branch=branch)
        #         for branch in branches
        #     ]
        # except github3.exceptions.NotFoundError:
        #     raise GithubApiNotFoundError("Could not find branches on ADO")
        return []


class ADOPullRequest(AbstractPullRequest):
    """ADO pull request object for creating and managing pull requests."""

    @classmethod
    def pull_requests(
        cls,
        git_repo: AbstractRepo,
        state=None,
        head=None,
        base=None,
        sort="created",
        direction="desc",
        number=-1,
        etag=None,
    ) -> list["ADOPullRequest"]:
        """Fetches all pull requests from the repository."""
        # try:
        #     pull_requests = git_repo.repo.pull_requests(
        #         state=state,
        #         head=head,
        #         base=base,
        #         sort=sort,
        #         direction=direction,
        #         number=number,
        #         etag=etag,
        #     )
        #     return [
        #         ADOPullRequest(repo=git_repo, pull_request=pull_request)
        #         for pull_request in pull_requests
        #     ]
        # except github3.exceptions.NotFoundError:
        #     raise GithubApiNotFoundError("Could not find pull requests on ADO")
        return []

    @classmethod
    def create_pull(
        cls,
        git_repo: AbstractRepo,
        title: str,
        base: str,
        head: str,
        body: Optional[str] = None,
        maintainer_can_modify: Optional[bool] = False,
    ) -> "ADOPullRequest":
        """Creates a pull request on the given repository."""
        # try:
        #     pull_request = git_repo.repo.create_pull(
        #         title,
        #         base,
        #         head,
        #         body=body,
        #         maintainer_can_modify=maintainer_can_modify,
        #     )
        #     return ADOPullRequest(repo=git_repo, pull_request=pull_request)
        # except github3.exceptions.NotFoundError:
        #     raise GithubApiNotFoundError("Could not create pull request on ADO")
        return ADOPullRequest()

    @property
    def number(self) -> int:
        """Gets the pull request number."""
        # return self.pull_request.number if self.pull_request else None
        return 0

    @property
    def base_ref(self) -> str:
        """Gets the base reference of the pull request."""
        # return self.pull_request.base.ref if self.pull_request else ""
        return ""

    @property
    def head_ref(self) -> str:
        """Gets the head reference of the pull request."""
        # return self.pull_request.head.ref if self.pull_request else ""
        return ""


class ADORepository(AbstractRepo):

    project_config: BaseProjectConfig
    connection: Connection
    git_client: GitClient
    repo: GitRepository
    project: Optional[TeamProjectReference]

    def __init__(
        self, connection: Connection, config: BaseProjectConfig, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.connection = connection
        self.project_config = config
        self.service_type = kwargs.get("service_type", "azure_devops")
        self.git_client = self.connection.clients.get_git_client()
        self.repo = self.git_client.get_repository(
            self.project_config.repo_name, self.project_config.repo_name
        )  # TODO Get project Name.
        self.project = self.repo.project

    @property
    def project_id(self) -> Optional[str]:
        """Returns the project ID of the repository."""
        if self.project is None:
            raise ValueError("Project is not set. Cannot access its ID.")
        return self.project.id

    def get_ref_for_tag(self, tag_name: str) -> Optional[ADORef]:
        """Gets a Reference object for the tag with the given name"""
        try:
            refs: list[GitRef] = self.git_client.get_refs(
                self.repo.id, self.project_id, filter=f"tags/{tag_name}"
            )
            if len(refs) > 1:
                return ADORef(ref=refs[0])

        except Exception as e:
            raise AzureDevOpsClientError(
                f"Could not find reference for 'tags/{tag_name}' on ADO. Error: {str(e)}"
            )
        return None

    def get_tag_by_ref(self, ref: ADORef, tag_name: Optional[str] = None) -> ADOTag:
        """Fetches a tag by reference, name from the given repository"""
        try:
            return ADOTag(tag=None, ref=ref)
        except Exception as e:
            msg = f"Could not find tag '{tag_name}' with SHA {ref.sha} on ADO"
            if ref.type != "tag":
                msg += f"\n{tag_name} is not an annotated tag."
            msg += f"\nError: {str(e)}"
            raise AzureDevOpsClientError(msg)

    def create_tag(
        self, tag_name: str, message: str, sha: str, obj_type: str, tagger: dict = {}
    ) -> ADOTag:
        # Create a tag on the given repository

        clone_tag = GitAnnotatedTag()
        clone_tag.message = message
        clone_tag.name = tag_name

        clone_tag.tagged_object = GitObject()
        clone_tag.tagged_object.object_id = sha

        tag = self.git_client.create_annotated_tag(
            clone_tag, self.project_id, self.repo.id
        )

        return ADOTag(tag=tag)

    def branch(self, branch_name) -> ADOBranch:
        # # Fetches a branch from the given repository
        # return ADOBranch(self, branch_name)
        return ADOBranch(self, "")

    def branches(self) -> list[ADOBranch]:
        # # Fetches all branches from the given repository
        # return ADOBranch.branches(self)
        return []

    def compare_commits(self, branch_name: str, commit: str) -> ADOComparison:
        # # Compares the given branch with the given commit
        # return ADOComparison.compare(self, branch_name, commit)
        return ADOComparison(self, "", "")

    def merge(self, base: str, head: str, message: str = "") -> Union[ADOCommit, None]:
        # Merges the given base and head with the specified message
        # try:
        #     commit = self.repo.merge(base, head, message)
        #     git_commit = ADOCommit(commit=commit)
        #     return git_commit
        # except ADOError as e:
        #     if e.code != http.client.CONFLICT:
        #         raise
        # except NotFoundError:
        #     raise GithubApiNotFoundError(
        #         f"Could not find base {base} or head {head} for merge on ADO"
        #     )
        pass

    def pull_requests(
        self,
        state: Optional[str] = None,
        head: Optional[str] = None,
        base: Optional[str] = None,
        sort: Optional[str] = "created",
        direction: Optional[str] = "desc",
        number: Optional[int] = -1,
        etag: Optional[str] = None,
    ) -> list[ADOPullRequest]:
        """Fetches all pull requests from the given repository"""
        # return ADOPullRequest.pull_requests(
        #     self,
        #     state=state,
        #     head=head,
        #     base=base,
        #     sort=sort,
        #     direction=direction,
        #     number=number,
        #     etag=etag,
        # )
        return []

    def create_pull(
        self,
        title: str,
        base: str,
        head: str,
        body: Optional[str] = None,
        maintainer_can_modify: Optional[bool] = None,
        options: dict = {},
    ) -> Union[ADOPullRequest, None]:
        """Creates a pull request on the given repository"""
        # try:
        #     pull_request = ADOPullRequest.create_pull(
        #         self,
        #         title,
        #         base,
        #         head,
        #         body=body,
        #         maintainer_can_modify=maintainer_can_modify,
        #     )
        #     return pull_request
        # except github3.exceptions.UnprocessableEntity as e:
        #     error_msg = options.get(
        #         "error_message",
        #         f"Error creating pull request to merge {head} into {base}",
        #     )
        #     self.logger.error(f"{error_msg}:\n{e.response.text}")
        # except Exception as e:
        #     self.logger.error(f"An unexpected error occurred: {str(e)}")
        return None
