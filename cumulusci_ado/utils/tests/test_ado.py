from typing import Optional

import pytest

from cumulusci_ado.utils.ado import (  # Replace .your_module with the actual module name
    EMPTY_URL_MESSAGE,
    parse_repo_url,
)


class TestParseRepoUrl:
    """
    Test suite for the parse_repo_url function.
    """

    @pytest.mark.parametrize(
        "url, expected_owner, expected_name, expected_host, expected_project",
        [
            # HTTPS URLS
            (
                "https://user@dev.azure.com/myorg/myproject/_git/myrepo",
                "myorg",
                "myrepo",
                "dev.azure.com",
                "myproject",
            ),
            (
                "https://dev.azure.com/myorg/myproject/_git/myrepo.git",
                "myorg",
                "myrepo",
                "dev.azure.com",
                "myproject",
            ),
            (
                "https://my-user@dev.azure.com/another-org/another-project/_git/another-repo",
                "another-org",
                "another-repo",
                "dev.azure.com",
                "another-project",
            ),
            (  # HTTPS URL without explicit user in the host part
                "https://dev.azure.com/solo-user/project-name/_git/repo-name",
                "solo-user",
                "repo-name",
                "dev.azure.com",
                "project-name",
            ),
            (  # HTTPS URL with a different username format if applicable (though Azure typically uses org)
                "https://username@dev.azure.com/orgname/projectname/_git/reponame.git",
                "orgname",
                "reponame",
                "dev.azure.com",
                "projectname",
            ),
            # SSH URLS
            (
                "git@ssh.dev.azure.com:v3/myorg/myproject/myrepo",
                "myorg",
                "myrepo",
                "ssh.dev.azure.com",
                "myproject",
            ),
            (
                "git@ssh.dev.azure.com:v3/myorg/myproject/myrepo.git",
                "myorg",
                "myrepo",
                "ssh.dev.azure.com",
                "myproject",
            ),
            (
                "git@ssh.dev.azure.com:v3/another-org/project-x/repo-y",
                "another-org",
                "repo-y",
                "ssh.dev.azure.com",
                "project-x",
            ),
            (  # SSH URL with a user instead of org (if this is a valid Azure DevOps pattern)
                "git@ssh.dev.azure.com:v3/username/projectname/reponame",
                "username",
                "reponame",
                "ssh.dev.azure.com",
                "projectname",
            ),
            (  # SSH URL without .git and with hyphens in names
                "git@ssh.dev.azure.com:v3/hyphen-org/hyphen-project/hyphen-repo",
                "hyphen-org",
                "hyphen-repo",
                "ssh.dev.azure.com",
                "hyphen-project",
            ),
            # Edge cases based on implementation details
            (  # URL with trailing slash (though your function handles rstrip)
                "https://user@dev.azure.com/myorg/myproject/_git/myrepo/",
                "myorg",
                "myrepo",
                "dev.azure.com",
                "myproject",
            ),
            (  # URL with leading slash in path (though your function handles lstrip for path parts)
                "ssh://git@ssh.dev.azure.com:v3/myorg/myproject/myrepo",  # Simulating how formatted_url would look
                "myorg",
                "myrepo",
                "ssh.dev.azure.com",
                "myproject",
            ),
        ],
    )
    def test_valid_repo_urls(
        self,
        url: str,
        expected_owner: str,
        expected_name: str,
        expected_host: str,
        expected_project: Optional[str],
    ):
        """
        Tests parse_repo_url with various valid Azure DevOps URLs.

        Args:
            url: The Azure DevOps URL to parse.
            expected_owner: The expected owner (organization or user).
            expected_name: The expected repository name.
            expected_host: The expected host.
            expected_project: The expected project name.
        """
        owner, name, host, project = parse_repo_url(url)
        assert owner == expected_owner, f"Owner mismatch for URL: {url}"
        assert name == expected_name, f"Repo name mismatch for URL: {url}"
        assert host == expected_host, f"Host mismatch for URL: {url}"
        assert project == expected_project, f"Project mismatch for URL: {url}"

    def test_empty_url(self):
        """
        Tests that parse_repo_url raises a ValueError for an empty URL string.
        """
        with pytest.raises(ValueError) as excinfo:
            parse_repo_url("")
        assert (
            str(excinfo.value) == EMPTY_URL_MESSAGE
        ), "ValueError message mismatch for empty URL"

    def test_none_url(self):
        """
        Tests that parse_repo_url raises a ValueError for a None URL (if not caught by type hints earlier).
        """
        with pytest.raises(
            ValueError
        ) as excinfo:  # Assuming None would also result in the EMPTY_URL_MESSAGE
            parse_repo_url(None)  # type: ignore
        assert (
            str(excinfo.value) == EMPTY_URL_MESSAGE
        ), "ValueError message mismatch for None URL"

    @pytest.mark.parametrize(
        "url, expected_owner, expected_name, expected_host, expected_project",
        [
            (
                "git@ssh.dev.azure.com:v3/justowner",
                "justowner",  # owner
                "justowner",  # name will also be justowner
                "ssh.dev.azure.com",  # host
                None,  # project
            ),
        ],
    )
    def test_urls_with_potentially_none_project(
        self,
        url: str,
        expected_owner: str,
        expected_name: Optional[str],
        expected_host: str,
        expected_project: Optional[str],
    ):
        """
        Tests URLs that might result in 'project' being None based on the parsing logic.
        Note: These might be malformed Azure DevOps URLs but test the code path.
        """
        owner, name, host, project = parse_repo_url(url)
        assert owner == expected_owner, f"Owner mismatch for URL: {url}"
        assert name == expected_name, f"Repo name mismatch for URL: {url}"
        assert host == expected_host, f"Host mismatch for URL: {url}"
        assert project == expected_project, f"Project mismatch for URL: {url}"
