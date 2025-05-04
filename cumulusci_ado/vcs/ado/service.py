import logging

from azure.devops.connection import Connection
from azure.devops.exceptions import AzureDevOpsAuthenticationError
from cumulusci.vcs.base import VCSService
from msrest.authentication import BasicAuthentication

logger = logging.getLogger(__name__)


class AzureDevOpsService(VCSService):
    service_type = "azure_devops"
    # _repo: ADORepository
    # github: GitHub

    @classmethod
    def validate_service(cls, options: dict, keychain) -> dict:
        personal_access_token = options["token"]
        organization_url = options["organization_url"]

        cls.validate_duplicate_service(keychain, organization_url)

        try:
            connection = cls._authenticate(personal_access_token, organization_url)
            core_client = connection.clients.get_core_client()
            base_url = core_client.config.base_url
            assert organization_url in base_url, f"https://{organization_url}"
        except AttributeError as e:
            raise AzureDevOpsAuthenticationError(f"Authentication Error. ({str(e)})")
        except Exception as e:
            raise AzureDevOpsAuthenticationError(f"Authentication Error. ({str(e)})")

        return options

    @classmethod
    def validate_duplicate_service(cls, keychain, organization_url):
        """Check if the service is already configured in the keychain."""
        services = keychain.get_services_for_type(cls.service_type)
        if not services:
            return True

        hosts = [service.organization_url for service in services]
        if hosts.count(organization_url) > 1:
            raise AzureDevOpsAuthenticationError(
                f"More than one Azure Devops service configured for domain {organization_url}."
            )
        return True

    @staticmethod
    def _authenticate(token: str, org_url: str):
        organization_url = f"https://{org_url}"
        # Create a connection to the org
        credentials = BasicAuthentication("", token)
        connection = Connection(base_url=organization_url, creds=credentials)

        # Get a client (the "core" client provides access to projects, teams, etc)
        connection.authenticate()

        return connection

    @classmethod
    def get_azure_api_connection(cls, service_config, session=None):
        return cls._authenticate(service_config.token, service_config.organization_url)
