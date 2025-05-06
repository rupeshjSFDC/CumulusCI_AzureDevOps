import re
from typing import Optional, Tuple
from urllib.parse import ParseResult, urlparse

from cumulusci.utils.git import EMPTY_URL_MESSAGE


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
