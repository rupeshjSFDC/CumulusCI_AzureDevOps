import time
from typing import Optional, Union

from azure.devops.connection import Connection
from azure.devops.exceptions import AzureDevOpsClientError, AzureDevOpsServiceError
from azure.devops.v7_0.git.git_client import GitClient
from azure.devops.v7_0.git.models import (
    GitAnnotatedTag,
    GitBaseVersionDescriptor,
    GitBranchStats,
    GitCommitDiffs,
    GitObject,
    GitPullRequest,
    GitPullRequestCompletionOptions,
    GitPullRequestSearchCriteria,
    GitRef,
    GitRepository,
    GitTargetVersionDescriptor,
    GitVersionDescriptor,
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

from cumulusci_ado.utils.ado import parse_repo_url


class ADORef(AbstractRef):
    ref: GitRef
    sha: Optional[str]
    type: Optional[str]

    def __init__(self, ref: GitRef, **kwargs) -> None:
        super().__init__(ref, **kwargs)
        self.sha = self.ref.object_id
        self.type = "tag"


class ADOTag(AbstractGitTag):
    tag: Optional[GitAnnotatedTag]

    def __init__(self, tag: GitAnnotatedTag, **kwargs) -> None:
        super().__init__(tag, **kwargs)
        self.sha: Optional[str] = self.tag.object_id if self.tag else None


class ADOComparison(AbstractComparison):
    repo: "ADORepository"
    commit_diffs: GitCommitDiffs

    def get_comparison(self) -> None:
        """Gets the comparison object for the current base and head."""
        # self.comparison = self.repo.repo.compare_commits(self.base, self.head)
        base_version_descriptor = GitBaseVersionDescriptor(
            self.base,
            version_type="commit",
            base_version=self.base,
            base_version_type="commit",
        )

        target_version_descriptor: GitTargetVersionDescriptor = (
            GitTargetVersionDescriptor(
                self.head,
                version_type="branch",
                target_version=self.head,
                target_version_type="branch",
            )
        )
        try:
            self.commit_diffs = self.repo.git_client.get_commit_diffs(
                self.repo.id,
                self.repo.project_id,
                top=10,
                base_version_descriptor=base_version_descriptor,
                target_version_descriptor=target_version_descriptor,
            )

            return
        except AzureDevOpsServiceError as e:
            e.message = f"Failed to get commit diffs: {e.message}"
            raise AzureDevOpsServiceError(e)
        except Exception as ex:
            message = f"Unexpected error during getting commit diffs: {str(ex)}"
            raise Exception(message)

    @property
    def files(self) -> list:
        return self.commit_diffs.changes or []

    @property
    def behind_by(self) -> int:
        """Returns the number of commits the head is behind the base."""
        return self.commit_diffs.behind_count or 0

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
    branch: Optional[GitBranchStats]

    def __init__(self, repo: "ADORepository", branch_name: str, **kwargs) -> None:
        super().__init__(repo, branch_name, **kwargs)

    def get_branch(self) -> None:
        try:
            self.branch = self.repo.git_client.get_branch(
                self.repo.id, self.name, self.repo.project_id
            )
        except AzureDevOpsServiceError as e:
            e.message = f"Branch {self.name} not found. {e.message}"
            raise AzureDevOpsServiceError(e)

    @classmethod
    def branches(cls, ado_repo: "ADORepository") -> list["ADOBranch"]:
        """Fetches all branches from the given repository"""
        source_branch: Optional[str] = ado_repo.options.get("source_branch", None)

        try:
            if ado_repo.repo is None:
                raise ValueError("Repository is not set. Cannot access its branches.")

            base_version_descriptor = GitVersionDescriptor(
                source_branch, "none", "branch"
            )
            branches: list[GitBranchStats] = ado_repo.git_client.get_branches(
                ado_repo.repo.id, ado_repo.project_id, base_version_descriptor
            )
            return [
                ADOBranch(
                    repo=ado_repo,
                    branch_name=(branch.name if branch.name else ""),
                    branch=branch,
                )
                for branch in branches
            ]
        except AzureDevOpsServiceError as e:
            e.message = f"Failed to get branches: {e.message}"
            raise AzureDevOpsServiceError(e)
        except Exception as ex:
            message = f"Unexpected error when getting branches: {str(ex)}"
            raise Exception(message)


class ADOPullRequest(AbstractPullRequest):
    """ADO pull request object for creating and managing pull requests."""

    pull_request: GitPullRequest
    repo: "ADORepository"
    options: dict

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.options = kwargs.get("options", {})

    @classmethod
    def pull_requests(
        cls,
        repo: "ADORepository",
        state: Optional[str] = None,
        head: Optional[str] = None,
        base: Optional[str] = None,
        sort: Optional[str] = "creationDate",
        direction: Optional[str] = "desc",
        number: Optional[int] = -1,
        etag: Optional[str] = None,
    ) -> list["ADOPullRequest"]:
        """Fetches all pull requests from the repository."""
        try:
            search_criteria = GitPullRequestSearchCriteria(
                source_ref_name=f"refs/heads/{base}",
                status="open",
                repository_id=repo.id,
                source_repository_id=repo.id,
            )
            pull_requests = repo.git_client.get_pull_requests(
                repo.id, search_criteria, repo.project_id
            )

            pull_requests.sort(
                key=lambda p: getattr(p, sort or "pull_request_id", "pull_request_id"),
                reverse=(direction == "desc"),
            )

            return [
                ADOPullRequest(repo=repo, pull_request=pull_request)
                for pull_request in pull_requests
            ]
        except AzureDevOpsServiceError as e:
            e.message = f"Failed to get pull requests: {e.message}"
            raise AzureDevOpsServiceError(e)
        except Exception as ex:
            message = f"Unexpected error during getting pull requests: {str(ex)}"
            raise Exception(message)

    @classmethod
    def create_pull(
        cls,
        repo: "ADORepository",
        title: str,
        base: str,
        head: str,
        body: Optional[str] = None,
        maintainer_can_modify: Optional[bool] = False,
        options: Optional[dict] = {},
    ) -> "ADOPullRequest":
        """Creates a pull request on the given repository."""

        try:
            pull_request = GitPullRequest(
                source_ref_name=f"refs/heads/{base}",
                target_ref_name=f"refs/heads/{head}",
                title=title,
                description=body,
            )

            created_pr = repo.git_client.create_pull_request(
                git_pull_request_to_create=pull_request,
                repository_id=repo.id,
                project=repo.project_id,
            )

            repo.logger.info(
                f"Pull request created: #{created_pr.pull_request_id} - {created_pr.title}"
            )

            return ADOPullRequest(repo=repo, pull_request=pull_request, options=options)
        except AzureDevOpsServiceError as e:
            e.message = f"Failed to create pull request: {e.message}"
            raise AzureDevOpsServiceError(e)
        except Exception as ex:
            message = f"Unexpected error during PR creation: {str(ex)}"
            raise Exception(message)

    @property
    def number(self) -> int:
        """Gets the pull request number."""
        return self.pull_request.pull_request_id or 0

    @property
    def base_ref(self) -> str:
        """Gets the base reference of the pull request."""
        return self.pull_request.source_ref_name or ""

    @property
    def head_ref(self) -> str:
        """Gets the head reference of the pull request."""
        return self.pull_request.target_ref_name or ""

    def can_auto_merge(self) -> bool:
        """
        Waits until the pull request has completed merge checks or timeout hits.
        """
        self.repo.logger.debug("Waiting for PR auto-merge check...")
        start_time = time.time()
        timeout = self.options.get("retry_timeout", 100)
        interval = self.options.get("retry_interval", 10)

        while time.time() - start_time < timeout:
            self.reload()

            if self.pull_request.merge_status == "succeeded":
                self.repo.logger.info("Pull request can be automatically merged.")
                return True

            if self.pull_request.merge_status in ("conflicts", "failure"):
                self.repo.logger.info(
                    f"Merge status resolved: {self.pull_request.merge_status}"
                )
                return False

            self.repo.logger.info(
                f"Current merge status: {self.pull_request.merge_status}. Retrying in {interval} seconds..."
            )
            time.sleep(interval)

        self.repo.logger.warning(
            f"Pull request cannot be auto-merged. Merge status: {self.pull_request.merge_status}"
        )
        return False

    def reload(self) -> None:
        """Reloads the pull request object."""
        try:
            # Check if the PR can be auto-merged
            self.pull_request = self.repo.git_client.get_pull_request(
                repository_id=self.repo.id,
                pull_request_id=self.number,
                project=self.repo.project_id,
            )

        except AzureDevOpsServiceError as e:
            e.message = f"Failed to get pull request status: {e.message}"
            raise AzureDevOpsServiceError(e)
        except Exception as ex:
            message = f"Unexpected error during PR status check: {str(ex)}"
            raise Exception(message)

    def merge(self) -> None:
        """Merges the pull request."""

        # Set PR to auto-complete and bypass rules
        completion_options = GitPullRequestCompletionOptions(
            delete_source_branch=self.options.get(
                "completion_opts_delete_source_branch", False
            ),
            merge_strategy=self.options.get(
                "completion_opts_merge_strategy", "squash"
            ),  # 'noFastForward', 'rebase', 'rebaseMerge', etc.
            bypass_policy=self.options.get("completion_opts_bypass_policy", False),
            bypass_reason=self.options.get(
                "completion_opts_bypass_reason", "Automated bypass for CI/CD pipeline"
            ),
        )

        self.update(completion_options=completion_options)

    def update(
        self,
        completion_options: Optional[GitPullRequestCompletionOptions] = None,
        status: Optional[str] = None,
    ) -> None:

        self.pull_request.auto_complete_set_by = self.pull_request.created_by

        if completion_options:
            self.pull_request.completion_options = completion_options

        if status:
            self.pull_request.status = status

        try:
            updated_pr = self.repo.git_client.update_pull_request(
                git_pull_request_to_update=self.pull_request,
                repository_id=self.repo.id,
                pull_request_id=self.number,
                project=self.repo.project_id,
            )
            self.repo.logger.info(
                f"Pull request #{updated_pr.pull_request_id} updated successfully."
            )
        except AzureDevOpsServiceError as e:
            e.message = f"Failed to update pull request #{self.number}: {e.message}"
            raise AzureDevOpsServiceError(e)
        except Exception as ex:
            message = f"Unexpected error during PR update: {str(ex)}"
            raise Exception(message)


class ADORepository(AbstractRepo):

    project_config: BaseProjectConfig
    connection: Connection
    git_client: GitClient
    repo: Optional[GitRepository]
    project: Optional[TeamProjectReference]

    def __init__(
        self, connection: Connection, config: BaseProjectConfig, **kwargs
    ) -> None:
        """Initializes the repository object."""
        super().__init__(**kwargs)
        self.connection = connection
        self.project_config = config
        self.service_type = kwargs.get("service_type", "azure_devops")
        self.repo = None
        self.project = None

    def _init_repo(self) -> None:
        self.git_client = self.connection.clients.get_git_client()

        if self.project_config.repo_url:
            _, repo_name, _, project = parse_repo_url(self.project_config.repo_url)
            self.repo = self.git_client.get_repository(repo_name, project)
            self.project = self.repo.project if self.repo else None

    @property
    def id(self) -> Optional[str]:
        """Returns the ID of the repository."""
        if self.repo is None:
            raise ValueError("Repository is not set. Cannot access its ID.")
        return self.repo.id

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
                self.id,
                self.project_id,
                filter=f"tags/{tag_name}",
                include_statuses=True,
                latest_statuses_only=True,
                peel_tags=True,
            )

        except Exception as e:
            raise AzureDevOpsClientError(
                f"Could not find reference for 'tags/{tag_name}' on ADO. Error: {str(e)}"
            )

        if len(refs) > 1:
            raise AzureDevOpsClientError(f"More than one tag found for {tag_name}.")

        if len(refs) == 0:
            raise AzureDevOpsClientError(f"Could not find tag {tag_name}.")

        ref = refs[0]

        if ref.peeled_object_id is None:
            msg = f"Could not find tag '{tag_name}' with SHA {ref.object_id} on ADO."
            msg += f"\n{tag_name} is not an annotated tag."
            raise AzureDevOpsClientError(msg)

        return ADORef(ref=ref)

    def get_tag_by_ref(self, ref: ADORef, tag_name: Optional[str] = None) -> ADOTag:
        """Fetches a tag by reference, name from the given repository"""
        try:
            annotatedTag: GitAnnotatedTag = self.git_client.get_annotated_tag(
                self.project_id, self.id, ref.sha
            )

        except Exception as e:
            msg = f"Could not find tag '{tag_name}' with SHA {ref.sha} on ADO"
            if ref.type != "tag":
                msg += f"\n{tag_name} is not an annotated tag."
            msg += f"\nError: {str(e)}"
            raise AzureDevOpsClientError(msg)

        if annotatedTag is None:
            raise AzureDevOpsClientError("Annotated Tag not found.")

        return ADOTag(tag=annotatedTag)

    def create_tag(
        self, tag_name: str, message: str, sha: str, obj_type: str, tagger: dict = {}
    ) -> ADOTag:
        # Create a tag on the given repository

        clone_tag = GitAnnotatedTag()
        clone_tag.message = message
        clone_tag.name = tag_name

        clone_tag.tagged_object = GitObject()
        clone_tag.tagged_object.object_id = sha

        try:
            tag = self.git_client.create_annotated_tag(
                clone_tag, self.project_id, self.id
            )
        except Exception as e:
            self.logger.error(f"Error: Clone tag {e}")
            raise AzureDevOpsClientError(f"Could not create tag {tag_name} on ADO.")

        return ADOTag(tag=tag)

    def branch(self, branch_name) -> ADOBranch:
        # # Fetches a branch from the given repository
        return ADOBranch(self, branch_name)

    def branches(self) -> list[ADOBranch]:
        # # Fetches all branches from the given repository
        return ADOBranch.branches(self)

    def compare_commits(self, branch_name: str, commit: str) -> ADOComparison:
        # # Compares the given branch with the given commit
        return ADOComparison.compare(self, branch_name, commit)

    def merge(
        self, base: str, head: str, message: str = ""
    ) -> Union[ADOPullRequest, None]:

        body = (
            message + "\nThis pull request was automatically generated because "
            "an automated merge hit a merge conflict"
        )
        created_pr: ADOPullRequest = self.create_pull(
            base=base,
            head=head,
            body=body,
            title=f"Automerge {head} into {base}",
            options=self.options,
        )

        if created_pr.can_auto_merge() is True:
            created_pr.merge()
        elif not (self.options.get("create_pull_request_on_conflict")):
            created_pr.update(status="abandoned")
        else:
            self.logger.info(f"Merge conflict on branch {base}: Pull request created")
        return created_pr

    def pull_requests(
        self,
        state: Optional[str] = None,
        head: Optional[str] = None,
        base: Optional[str] = None,
        sort: Optional[str] = "createdDate",
        direction: Optional[str] = "desc",
        number: Optional[int] = -1,
        etag: Optional[str] = None,
    ) -> list[ADOPullRequest]:
        """Fetches all pull requests from the given repository"""
        return ADOPullRequest.pull_requests(
            self,
            state=state,
            head=head,
            base=base,
            sort=sort,
            direction=direction,
            number=number,
            etag=etag,
        )

    def create_pull(
        self,
        title: str,
        base: str,
        head: str,
        body: Optional[str] = None,
        maintainer_can_modify: Optional[bool] = None,
        options: Optional[dict] = {},
    ) -> ADOPullRequest:
        """Creates a pull request on the given repository"""
        if options:
            self.options.update(options)

        pull_request = ADOPullRequest.create_pull(
            self,
            title,
            base,
            head,
            body=body,
            maintainer_can_modify=maintainer_can_modify,
            options=self.options,
        )
        return pull_request
