from cumulusci.core.exceptions import VcsException, VcsNotFoundError


class ADOException(VcsException):
    """Raise for errors related to ADO"""

    pass


class ADOApiNotFoundError(VcsNotFoundError):
    pass
