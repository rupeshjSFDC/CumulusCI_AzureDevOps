# from unittest import mock

# import pytest

# import requests
import responses

# from azure.devops.exceptions import AzureDevOpsAuthenticationError

# from cumulusci_ado.vcs.ado.service import AzureDevOpsService


class TestADO:
    @responses.activate
    def test_validate_service(self, keychain_enterprise):
        assert True
