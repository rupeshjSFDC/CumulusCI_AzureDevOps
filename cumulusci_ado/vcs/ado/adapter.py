import time
from datetime import UTC, datetime
from re import Pattern
from typing import Optional, Union

from azure.devops.connection import Connection
from azure.devops.exceptions import AzureDevOpsClientError, AzureDevOpsServiceError
from azure.devops.v7_0.git.git_client import GitClient
from azure.devops.v7_0.git.models import (
    GitAnnotatedTag,
    GitBaseVersionDescriptor,
    GitBranchStats,
    GitCommit,
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
    AbstractRelease,
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
    tag: GitAnnotatedTag

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sha = self.tag.object_id or "" if self.tag else ""

    @property
    def message(self) -> str:
        """Gets the message of the tag."""
        return self.tag.message or "" if self.tag else ""


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
    """ADO commit object for representing a commit in the repository."""

    commit: GitCommit

    def get_statuses(self, context: str, regex_match: Pattern[str]) -> Optional[str]:
        # TODO: Implement the logic to get the status of the commit
        # for status in self.commit.status().statuses:
        #     if status.state == "success" and status.context == context:
        #         match = regex_match.search(status.description)
        #         if match:
        #             return match.group(1)
        return None


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

    @property
    def title(self) -> str:
        """Gets the pull request title."""
        return self.pull_request.title or ""

    @property
    def merged_at(self) -> datetime:
        """Gets the merged date of the short pull request."""
        return self.pull_request.closed_date or datetime.now(UTC)


class Release:
    @property
    def tag_name(self) -> str:
        """Gets the tag name of the release."""
        return self.tag_name or ""

    @property
    def body(self) -> str:
        """Gets the body of the release."""
        return self.body or ""

    @property
    def prerelease(self) -> bool:
        """Checks if the release is a pre-release."""
        return self.prerelease or False

    @property
    def name(self) -> str:
        """Gets the name of the release."""
        return self.name or ""

    @property
    def html_url(self) -> str:
        """Gets the HTML URL of the release."""
        return self.html_url or ""

    @property
    def created_at(self) -> datetime:
        """Gets the creation date of the release."""
        return self.created_at or datetime.now(UTC)

    @property
    def draft(self) -> bool:
        """Checks if the release is a draft."""
        return self.draft or False


class ADORelease(AbstractRelease):
    """Azure DevOps release object for creating and managing releases."""

    release: "Release"

    @property
    def tag_name(self) -> str:
        """Gets the tag name of the release."""
        return self.release.tag_name if self.release else ""

    @property
    def body(self) -> Union[str, None]:
        """Gets the body of the release."""
        return self.release.body if self.release else None

    @property
    def prerelease(self) -> bool:
        """Checks if the release is a pre-release."""
        return self.release.prerelease if self.release else False

    @property
    def name(self) -> str:
        """Gets the name of the release."""
        return self.release.name if self.release else ""

    @property
    def html_url(self) -> str:
        """Gets the HTML URL of the release."""
        return self.release.html_url if self.release else ""

    @property
    def created_at(self) -> Optional[datetime]:
        """Gets the creation date of the release."""
        return self.release.created_at if self.release else None

    @property
    def draft(self) -> bool:
        """Checks if the release is a draft."""
        return self.release.draft if self.release else False


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
        self._service_config = kwargs.get("service_config")
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

    @property
    def service_config(self):
        if not self._service_config and self.project_config.keychain is not None:
            self._service_config = self.project_config.keychain.get_service(
                self.service_type
            )
        return self._service_config

    @property
    def owner_login(self) -> str:
        """Returns the owner login of the repository."""
        # TODO: Implement the logic to get the owner login from ADO
        # return self.repo.owner.login if self.repo else ""
        return ""

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

    def get_commit(self, commit_sha: str) -> ADOCommit:
        """Given a SHA1 hash, retrieve a Commit object from the REST API."""
        # TODO: Implement the logic to get the commit from ADO
        # try:
        #     commit = self.repo.commit(commit_sha)
        #     return ADOCommit(commit=commit)
        # except (NotFoundError, UnprocessableEntity):
        #     # GitHub returns 422 for nonexistent commits in at least some circumstances.
        #     raise GithubApiNotFoundError(
        #         f"Could not find commit {commit_sha} on GitHub"
        #     )
        return ADOCommit()

    def release_from_tag(self, tag_name: str) -> ADORelease:
        """Fetches a release from the given tag name."""
        # TODO: Implement the logic to fetch a release from ADO
        # try:
        #     release: Release = self.repo.release_from_tag(tag_name)
        # except NotFoundError:
        #     message = f"Release for {tag_name} not found"
        #     raise GithubApiNotFoundError(message)
        return ADORelease()

    def default_branch(self) -> Optional[ADOBranch]:
        """Returns the default branch of the repository."""
        # TODO: Implement the logic to get the default branch from ADO
        # return ADOBranch(self, self.repo.default_branch) if self.repo else None
        return ADOBranch(self, "")

    def archive(self, format: str, zip_content: Union[str, object], ref=None) -> bytes:
        """Archives the repository content as a zip file."""
        # TODO: Implement the logic to archive the repository content
        # try:
        #     archive = self.repo.archive(format, zip_content, ref)
        #     return archive
        # except NotFoundError:
        #     raise GithubApiNotFoundError(
        #         f"Could not find archive for {zip_content} for service {self.service_type}"
        #     )
        return b""

    def full_name(self) -> str:
        """Returns the full name of the repository."""
        # return self.repo.full_name if self.repo else ""
        # TODO: Implement the logic to get the full name of the repository
        return ""

    def create_release(
        self,
        tag_name: str,
        name: str = "",
        body: str = "",
        draft: bool = False,
        prerelease: bool = False,
    ) -> ADORelease:
        """Creates a release on the given repository."""
        # TODO: Implement the logic to create a release on ADO
        # try:
        #     release = self.repo.create_release(
        #         tag_name, name=name, body=body, draft=draft, prerelease=prerelease
        #     )
        #     return GitHubRelease(release=release)
        # except NotFoundError:
        #     raise GithubApiNotFoundError(
        #         f"Could not create release for {tag_name} on GitHub"
        #     )
        return ADORelease()

    def releases(self) -> list[ADORelease]:
        """Fetches all releases from the given repository."""
        # TODO: Implement the logic to fetch all releases from ADO
        # try:
        #     releases = self.repo.releases()
        #     return [GitHubRelease(release=release) for release in releases]
        # except NotFoundError:
        #     raise GithubApiNotFoundError("Could not find releases on GitHub")
        # except UnprocessableEntity:
        #     raise GithubApiNotFoundError(
        #         "Could not find releases on GitHub. Check if the repository is archived."
        #     )
        # except GitHubError as e:
        #     if e.code == http.client.UNAUTHORIZED:
        #         raise GithubApiNotFoundError(
        #             "Could not find releases on GitHub. Check your authentication."
        #         )
        #     else:
        #         raise GithubApiNotFoundError(
        #             f"Could not find releases on GitHub: {e.message}"
        #         )
        # except Exception as e:
        #     raise GithubApiNotFoundError(
        #         f"An unexpected error occurred while fetching releases: {str(e)}"
        #     )
        return []

    def latest_release(self) -> Optional[ADORelease]:
        """Fetches the latest release from the given repository."""
        # TODO: Implement the logic to fetch the latest release from ADO
        # release = self.repo.latest_release()
        # if release:
        #     return GitHubRelease(release=release)
        return None

    def has_issues(self) -> bool:
        """Checks if the repository has issues enabled."""
        # TODO: Implement the logic to check if issues are enabled on ADO
        # return self.repo.has_issues() if self.repo else False
        return False

    def get_pull_requests_by_commit(self, commit_sha) -> list[ADOPullRequest]:
        """Fetches all pull requests associated with the given commit SHA."""
        # TODO: Implement the logic to fetch pull requests by commit SHA
        # endpoint = (
        #     self.github.session.base_url
        #     + f"/repos/{self.repo.owner.login}/{self.repo.name}/commits/{commit_sha}/pulls"
        # )
        # response = self.github.session.get(
        #     endpoint, headers={"Accept": "application/vnd.github.groot-preview+json"}
        # )
        # json_list = safe_json_from_response(response)

        # for json in json_list:
        #     json["body_html"] = ""
        #     json["body_text"] = ""

        # pull_requests = [
        #     GitHubPullRequest(
        #         repo=self.repo, pull_request=ShortPullRequest(json, self.github)
        #     )
        #     for json in json_list
        # ]
        # return pull_requests
        return []

    def get_pr_issue_labels(self, pull_request: ADOPullRequest) -> list[str]:
        """Fetches all labels associated with the given pull request."""
        # TODO: Implement the logic to fetch labels from ADO
        # issue: ShortIssue = self.repo.issue(pull_request.number)
        # labels: ShortLabel = issue.labels()
        # return [label.name for label in labels] if labels else []
        return []
