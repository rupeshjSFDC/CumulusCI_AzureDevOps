import logging
import re
from typing import Optional, Tuple
from urllib.parse import ParseResult, urlparse

import colorama
from cumulusci.core.exceptions import CumulusCIFailure
from cumulusci.utils.git import EMPTY_URL_MESSAGE

from cumulusci_ado.utils.common.artifacttool import ArtifactToolInvoker
from cumulusci_ado.utils.common.artifacttool_updater import ArtifactToolUpdater
from cumulusci_ado.utils.common.external_tool import (
    ProgressReportingExternalToolInvoker,
)

logger = logging.getLogger(__name__)


def parse_repo_url(
    url: str,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Parses a given URI into Owner, Repo Name, Host and Project

    Parameters
    ----------
    url: str
        A Azure URI. Examples: ["https://user@dev.azure.com/[org|user]/project/_git/repo", "git@ssh.dev.azure.com:v3/[user|org]/project/repo"]
    Returns
    -------
    Tuple: (Optional[str], Optional[str], Optional[str], Optional[str])
        Returns (owner, name, host, project)
    """
    if not url:
        raise ValueError(EMPTY_URL_MESSAGE)

    formatted_url = f"ssh://{url}" if url.startswith("git") else url
    parse_result: ParseResult = urlparse(formatted_url)

    host: Optional[str] = parse_result.hostname

    url_parts = re.split("/|@|:", parse_result.path.rstrip("/").lstrip("/"))
    url_parts = list(filter(None, url_parts))

    name: Optional[str] = url_parts[-1]
    if name.endswith(".git"):
        name = name[:-4]

    owner: Optional[str] = url_parts[0]
    project: Optional[str] = url_parts[1] if len(url_parts) > 1 else None

    return (owner, name, host, project)


def publish_package(
    client_tool,
    feed,
    name,
    version,
    path,
    description=None,
    scope="organization",
    organization=None,
    project=None,
    detect=None,
):
    """Publish a package to a feed.
    :param scope: Scope of the feed: 'project' if the feed was created in a project, and 'organization' otherwise.
    :type scope: str
    :param feed: Name or ID of the feed.
    :type feed: str
    :param name: Name of the package, e.g. 'foo-package'.
    :type name: str
    :param version: Version of the package, e.g. '1.0.0'.
    :type version: str
    :param description: Description of the package.
    :type description: str
    :param path: Directory containing the package contents.
    :type path: str
    """
    colorama.init()  # Needed for humanfriendly spinner to display correctly

    if scope == "project":
        if project is None:
            raise CumulusCIFailure("--scope 'project' requires a value in --project")
    else:
        if project is not None:
            raise CumulusCIFailure(
                "--scope 'project' is required when specifying a value in --project"
            )

    artifact_tool = ArtifactToolInvoker(
        client_tool, ProgressReportingExternalToolInvoker(), ArtifactToolUpdater()
    )
    return artifact_tool.publish_universal(
        organization, project, feed, name, version, description, path
    )


def download_package(
    client_tool,
    feed,
    name,
    version,
    path,
    file_filter=None,
    scope="organization",
    organization=None,
    project=None,
    detect=None,
):
    """Download a package.
    :param scope: Scope of the feed: 'project' if the feed was created in a project, and 'organization' otherwise.
    :type scope: str
    :param feed: Name or ID of the feed.
    :type feed: str
    :param name: Name of the package, e.g. 'foo-package'.
    :type name: str
    :param version: Version of the package, e.g. 1.0.0.
    :type version: str
    :param path: Directory to place the package contents.
    :type path: str
    :param file_filter: Wildcard filter for file download.
    :type file_filter: str
    """
    colorama.init()  # Needed for humanfriendly spinner to display correctly

    if scope == "project":
        if project is None:
            raise CumulusCIFailure("--scope 'project' requires a value in --project")
    else:
        if project is not None:
            raise CumulusCIFailure(
                "--scope 'project' is required when specifying a value in --project"
            )

    artifact_tool = ArtifactToolInvoker(
        client_tool, ProgressReportingExternalToolInvoker(), ArtifactToolUpdater()
    )
    return artifact_tool.download_universal(
        organization, project, feed, name, version, path, file_filter
    )
