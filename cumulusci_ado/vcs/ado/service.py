from typing import Optional

import requests
from azure.devops.connection import Connection
from azure.devops.exceptions import AzureDevOpsAuthenticationError
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.vcs.base import VCSService
from msrest.authentication import BasicAuthentication

from cumulusci_ado.vcs.ado import ADORepository


class AzureDevOpsService(VCSService):
    service_type: str = "azure_devops"
    _repo: Optional[ADORepository] = None

    def __init__(self, config: BaseProjectConfig, name: Optional[str] = None, **kwargs):
        """Initializes the ADO service with the given project configuration.
        Args:
            config (BaseProjectConfig): The configuration for the ADO service.
            name (str): The name or alias of the VCS service.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(config, name, **kwargs)
        # Set azure variables
        self.connection = self.__class__.get_api_connection(self.service_config)
        self.core_client = self.connection.clients.get_core_client()

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
    def _authenticate(
        token: str, org_url: str, session: Optional[requests.Session] = None
    ) -> Connection:
        organization_url = f"https://{org_url}"

        credentials = BasicAuthentication("", token)
        if session:
            credentials.signed_session(session)
        connection = Connection(base_url=organization_url, creds=credentials)

        # Get a client (the "core" client provides access to projects, teams, etc)
        connection.authenticate()

        return connection

    @classmethod
    def get_api_connection(
        cls, service_config, session: Optional[requests.Session] = None
    ) -> Connection:
        return cls._authenticate(
            service_config.token, service_config.organization_url, session
        )

    def get_repository(self) -> Optional[ADORepository]:
        """Returns the GitHub repository."""
        if self._repo is None:
            self._repo = ADORepository(
                self.connection,
                self.config,
                logger=self.logger,
                service_type=self.service_type,
                service_config=self.service_config,
            )
        return self._repo
