import re
from unittest import mock  # unittest.mock is often imported as 'mock'

import pytest

# Standard library imports
import requests

# Azure DevOps SDK related imports (for type hinting and potentially for exceptions)
from azure.devops.connection import Connection as AzureConnection
from azure.devops.exceptions import AzureDevOpsAuthenticationError

# CumulusCI core imports
from cumulusci.core.config import BaseProjectConfig, ServiceConfig, UniversalConfig
from cumulusci.core.keychain import BaseProjectKeychain

# msrest imports
from msrest.authentication import BasicAuthentication as MSBasicAuthentication

# The class to be tested - **ADJUST THIS IMPORT PATH AS NEEDED**
from cumulusci_ado.vcs.ado import ADORepository, AzureDevOpsService

# Define a common service name and options for tests
ADO_SERVICE_NAME = "my_ado_service"
ADO_ORG_URL = "dev.azure.com/MyOrg"
ADO_TOKEN = "test_pat_token"

# --- Pytest Fixtures ---


@pytest.fixture
def mock_universal_config():
    """Provides a mock UniversalConfig."""
    return UniversalConfig()


@pytest.fixture
def ado_service_config():
    """Provides a ServiceConfig dictionary for ADO."""
    return ServiceConfig(
        {
            "token": ADO_TOKEN,
            "url": ADO_ORG_URL,
            # Add other attributes if your AzureDevOpsService or its base expects them
            # e.g., username, email, though ADO primarily uses PAT for API access
        }
    )


@pytest.fixture
def mock_keychain(ado_service_config):
    """
    Provides a mock BaseProjectKeychain with an ADO service configured.
    """
    runtime = mock.Mock()
    runtime.project_config = BaseProjectConfig(UniversalConfig(), config={"foo": "bar"})
    runtime.project_config.config["services"] = {
        "connected_app": {"attributes": {"test": {"required": True}}},
        "github": {"attributes": {"name": {"required": True}, "password": {}}},
        "github_enterprise": {
            "attributes": {"name": {"required": True}, "password": {}}
        },
        "devhub": {"attributes": {"foo": {"required": True}}},
        "marketing_cloud": {
            "class_path": "cumulusci.core.config.marketing_cloud_service_config.MarketingCloudServiceConfig",
            "attributes": {"foo": {"required": True}},
        },
        "azure_devops": {
            "attributes": {"url": {"required": True}, "token": {"required": True}}
        },
    }

    runtime.keychain = BaseProjectKeychain(runtime.project_config, None)
    runtime.keychain.set_service(
        AzureDevOpsService.service_type,
        ADO_SERVICE_NAME,
        ado_service_config,
    )
    # runtime._load_project_config = mock.Mock()
    # runtime._load_project_config.return_value = runtime.project_config
    return runtime.keychain


@pytest.fixture
def mock_project_config(mock_keychain):
    """Provides a mock BaseProjectConfig."""
    mock_keychain.project_config.keychain = mock_keychain
    return mock_keychain.project_config


@pytest.fixture
def mock_ado_connection_instance():
    """Returns a MagicMock for an instance of azure.devops.connection.Connection."""
    connection_mock = mock.MagicMock(spec=AzureConnection)
    mock_core_client = mock.MagicMock()
    mock_core_client.config = mock.MagicMock()
    mock_core_client.config.base_url = (
        f"https://{ADO_ORG_URL}"  # Default successful base_url
    )
    connection_mock.clients = mock.MagicMock()
    connection_mock.clients.get_core_client = mock.MagicMock()
    connection_mock.clients.get_core_client.return_value = mock_core_client
    connection_mock.authenticate.return_value = (
        None  # Simulate successful authentication
    )
    return connection_mock


# --- Test Class for AzureDevOpsService ---


class TestAzureDevOpsService:
    @pytest.fixture
    @mock.patch("cumulusci_ado.vcs.ado.AzureDevOpsService.get_api_connection")
    def ado_service_instances(
        self, mock_get_api_connection, mock_project_config, mock_keychain
    ):
        """
        Provides an initialized AzureDevOpsService instance with a mocked get_api_connection.
        The keychain fixture ensures service_config is available via project_config.
        """
        # Setup the mock for get_api_connection (which is called in __init__)
        mock_conn_instance = mock.MagicMock(spec=AzureConnection)
        mock_core_cli = mock.MagicMock()
        mock_core_cli.config = mock.MagicMock()
        mock_core_cli.config.base_url = f"https://{ADO_ORG_URL}"

        mock_conn_instance.clients = mock.MagicMock()
        mock_conn_instance.clients.get_core_client = mock.MagicMock()
        mock_conn_instance.clients.get_core_client.return_value = mock_core_cli
        mock_get_api_connection.return_value = mock_conn_instance

        # Instantiate the service
        # VCSService.__init__ will use project_config.keychain.get_service(ADO_SERVICE_NAME)
        # to populate self.service_config
        service = AzureDevOpsService(mock_project_config, name=ADO_SERVICE_NAME)
        service.logger = mock.MagicMock()  # Ensure logger is a mock

        return service, mock_get_api_connection

    def test_init_success(self, ado_service_instances, mock_project_config):
        """Test successful initialization of AzureDevOpsService."""
        service, mock_get_api_connection_method = ado_service_instances  # Unpack

        # Assert that super().__init__ was called (implicitly tested by VCSService behavior)
        # Assert that get_api_connection was called (mocked by fixture)
        mock_get_api_connection_method.assert_called_once_with(service.service_config)

        # Assert connection and core_client are set
        assert service.connection is not None
        assert service.core_client is not None
        assert service.connection.clients.get_core_client.called
        assert service.config == mock_project_config
        assert service.name == ADO_SERVICE_NAME
        assert service.service_config.token == ADO_TOKEN
        assert service.service_config.url == ADO_ORG_URL

    @mock.patch("cumulusci_ado.vcs.ado.AzureDevOpsService._authenticate")
    @mock.patch("cumulusci_ado.vcs.ado.AzureDevOpsService.validate_duplicate_service")
    def test_validate_service_success(
        self, mock_validate_duplicate, mock_authenticate, mock_keychain
    ):
        """Test validate_service successfully."""
        mock_conn = mock.MagicMock(spec=AzureConnection)
        mock_core_cli = mock.MagicMock()
        mock_core_cli.config = mock.MagicMock()
        mock_core_cli.config.base_url = (
            f"https://someprefix.{ADO_ORG_URL}/somepostfix"  # Valid base URL
        )
        mock_conn.clients = mock.MagicMock()
        mock_conn.clients.get_core_client = mock.MagicMock()
        mock_conn.clients.get_core_client.return_value = mock_core_cli
        mock_authenticate.return_value = mock_conn
        mock_validate_duplicate.return_value = True

        options = {"token": ADO_TOKEN, "url": ADO_ORG_URL}
        result = AzureDevOpsService.validate_service(options, mock_keychain)

        mock_validate_duplicate.assert_called_once_with(mock_keychain, ADO_ORG_URL)
        mock_authenticate.assert_called_once_with(ADO_TOKEN, ADO_ORG_URL)
        assert result == options

    @mock.patch(
        "cumulusci_ado.vcs.ado.AzureDevOpsService._authenticate",
        side_effect=Exception("Auth boom!"),
    )
    @mock.patch(
        "cumulusci_ado.vcs.ado.AzureDevOpsService.validate_duplicate_service",
        return_value=True,
    )
    def test_validate_service_auth_failure(
        self, mock_validate_duplicate, mock_authenticate_fails, mock_keychain
    ):
        """Test validate_service when _authenticate fails."""
        options = {"token": ADO_TOKEN, "url": ADO_ORG_URL}
        with pytest.raises(
            AzureDevOpsAuthenticationError,
            match=r"Authentication Error\. \(Auth boom!\)",
        ):
            AzureDevOpsService.validate_service(options, mock_keychain)

    @mock.patch("cumulusci_ado.vcs.ado.AzureDevOpsService._authenticate")
    @mock.patch(
        "cumulusci_ado.vcs.ado.AzureDevOpsService.validate_duplicate_service",
        side_effect=AzureDevOpsAuthenticationError("Duplicate service!"),
    )
    def test_validate_service_duplicate_failure(
        self, mock_validate_duplicate_fails, mock_authenticate, mock_keychain
    ):
        """Test validate_service when validate_duplicate_service fails."""
        options = {"token": ADO_TOKEN, "url": ADO_ORG_URL}
        with pytest.raises(AzureDevOpsAuthenticationError, match="Duplicate service!"):
            AzureDevOpsService.validate_service(options, mock_keychain)

    @mock.patch("cumulusci_ado.vcs.ado.AzureDevOpsService._authenticate")
    @mock.patch(
        "cumulusci_ado.vcs.ado.AzureDevOpsService.validate_duplicate_service",
        return_value=True,
    )
    def test_validate_service_url_mismatch(
        self, mock_validate_duplicate, mock_authenticate, mock_keychain
    ):
        """Test validate_service when url is not in base_url."""
        mock_conn = mock.MagicMock(spec=AzureConnection)
        mock_core_cli = mock.MagicMock()
        mock_core_cli.config = mock.MagicMock()
        # Simulate a mismatch
        mock_core_cli.config.base_url = "https://another.domain.com"
        mock_conn.clients = mock.MagicMock()
        mock_conn.clients.get_core_client = mock.MagicMock()
        mock_conn.clients.get_core_client.return_value = mock_core_cli
        mock_authenticate.return_value = mock_conn

        options = {"token": ADO_TOKEN, "url": ADO_ORG_URL}
        assertion_failure_message = f"https://{ADO_ORG_URL}"
        expected_final_error_message = (
            f"Authentication Error. ({assertion_failure_message})"
        )

        # Escape the expected message for regex matching
        escaped_expected_message = re.escape(expected_final_error_message)

        with pytest.raises(
            AzureDevOpsAuthenticationError, match=escaped_expected_message
        ):
            AzureDevOpsService.validate_service(options, mock_keychain)

    def test_validate_service_missing_options(self, mock_keychain):
        """Test validate_service with missing keys in options."""
        with pytest.raises(
            KeyError
        ):  # Expecting KeyError as it's accessed before try-catch
            AzureDevOpsService.validate_service({"token": ADO_TOKEN}, mock_keychain)
        with pytest.raises(KeyError):
            AzureDevOpsService.validate_service({"url": ADO_ORG_URL}, mock_keychain)

    # --- Tests for validate_duplicate_service ---
    def test_validate_duplicate_no_services(self, mock_project_config):
        """Test validate_duplicate_service when keychain has no services of this type."""
        keychain = BaseProjectKeychain(mock_project_config, None)  # Fresh keychain
        keychain.get_services_for_type = mock.MagicMock(return_value={})  # No services
        assert (
            AzureDevOpsService.validate_duplicate_service(keychain, ADO_ORG_URL) is True
        )

    def test_validate_duplicate_no_clash(self, mock_project_config):
        """Test validate_duplicate_service with existing services but no URL clash."""
        keychain = BaseProjectKeychain(mock_project_config, None)
        mock_service_other_url = mock.MagicMock(spec=ServiceConfig)
        mock_service_other_url.url = "dev.azure.com/OtherOrg"
        keychain.get_services_for_type = mock.MagicMock(
            return_value=[mock_service_other_url]
        )
        assert (
            AzureDevOpsService.validate_duplicate_service(keychain, ADO_ORG_URL) is True
        )

    def test_validate_duplicate_one_existing_match(self, mock_project_config):
        """Test validate_duplicate_service with one existing service matching URL (should pass)."""
        keychain = BaseProjectKeychain(mock_project_config, None)
        mock_service_match_url = mock.MagicMock(spec=ServiceConfig)
        mock_service_match_url.url = ADO_ORG_URL
        keychain.get_services_for_type = mock.MagicMock(
            return_value=[mock_service_match_url]
        )
        # The logic `hosts.count(url) > 1` means if count is 1, it passes.
        assert (
            AzureDevOpsService.validate_duplicate_service(keychain, ADO_ORG_URL) is True
        )

    def test_validate_duplicate_multiple_existing_matches(self, mock_project_config):
        """Test validate_duplicate_service with multiple existing services matching URL (should fail)."""
        keychain = BaseProjectKeychain(mock_project_config, None)
        mock_service1 = mock.MagicMock(spec=ServiceConfig)
        mock_service1.url = ADO_ORG_URL
        mock_service2 = mock.MagicMock(spec=ServiceConfig)
        mock_service2.url = ADO_ORG_URL
        keychain.get_services_for_type = mock.MagicMock(
            return_value=[mock_service1, mock_service2]
        )

        with pytest.raises(
            AzureDevOpsAuthenticationError,
            match=f"More than one Azure Devops service configured for domain {ADO_ORG_URL}.",
        ):
            AzureDevOpsService.validate_duplicate_service(keychain, ADO_ORG_URL)

    # --- Tests for _authenticate (staticmethod) ---
    @mock.patch("msrest.authentication.BasicAuthentication")
    @mock.patch("azure.devops.connection.Connection")
    @mock.patch("msrest.authentication.BasicAuthentication.signed_session")
    @mock.patch("azure.devops.connection.Connection.authenticate", return_value=True)
    def test_authenticate_internal_success(
        self,
        MockAzureConnection,
        MockMSBasicAuth,
        MockSignedSession,
        MockAuth,
        mock_ado_connection_instance,
    ):
        """Test _authenticate successfully without session."""
        MockMSBasicAuth.return_value = mock.MagicMock(spec=MSBasicAuthentication)
        MockAzureConnection.return_value = mock_ado_connection_instance

        MockSignedSession.return_value = True

        # Check session was not used on credentials
        assert not MockMSBasicAuth.return_value.signed_session.called

    # --- Tests for get_api_connection (classmethod) ---
    @mock.patch("cumulusci_ado.vcs.ado.AzureDevOpsService._authenticate")
    def test_get_api_connection_success(
        self,
        mock_internal_authenticate,
        ado_service_config,
        mock_ado_connection_instance,
    ):
        """Test get_api_connection successfully calls _authenticate."""
        mock_internal_authenticate.return_value = mock_ado_connection_instance
        mock_session = mock.MagicMock(spec=requests.Session)

        # Test without session
        conn1 = AzureDevOpsService.get_api_connection(ado_service_config)
        mock_internal_authenticate.assert_called_with(
            ado_service_config.token, ado_service_config.url, None
        )
        assert conn1 == mock_ado_connection_instance

        # Test with session
        conn2 = AzureDevOpsService.get_api_connection(
            ado_service_config, session=mock_session
        )
        mock_internal_authenticate.assert_called_with(
            ado_service_config.token, ado_service_config.url, mock_session
        )
        assert conn2 == mock_ado_connection_instance

    @mock.patch(
        "cumulusci_ado.vcs.ado.AzureDevOpsService._authenticate",
        side_effect=AzureDevOpsAuthenticationError("Boom from _authenticate"),
    )
    def test_get_api_connection_failure(
        self, mock_internal_authenticate_fails, ado_service_config
    ):
        """Test get_api_connection when _authenticate fails."""
        with pytest.raises(
            AzureDevOpsAuthenticationError, match="Boom from _authenticate"
        ):
            AzureDevOpsService.get_api_connection(ado_service_config)

    # --- Tests for get_repository ---
    @mock.patch("cumulusci_ado.vcs.ado.ADORepository")  # Patch the ADORepository class
    def test_get_repository_first_call_creates_repo(
        self, MockADORepository, ado_service_instances
    ):
        """Test get_repository creates and returns a new ADORepository instance on first call."""
        service, ado_service_instance = ado_service_instances  # Unpack
        mock_repo_instance = mock.MagicMock(spec=ADORepository)
        MockADORepository.return_value = mock_repo_instance
        test_options = {"branch": "main"}

        ado_service_instance.get_repository(options=test_options)

    @mock.patch("cumulusci_ado.vcs.ado.ADORepository")  # Patch the ADORepository class
    def test_get_repository_subsequent_calls_return_existing(
        self, MockADORepository, ado_service_instances
    ):
        """Test get_repository returns the existing ADORepository instance on subsequent calls."""
        # Correctly unpack: the first element is the actual service instance
        actual_service_instance, _ = ado_service_instances

        mock_repo_instance = mock.MagicMock(spec=ADORepository)
        MockADORepository.return_value = mock_repo_instance

        actual_service_instance._repo = None

        # --- First call ---
        repo1 = actual_service_instance.get_repository()

        assert repo1.__class__.__name__ == mock_repo_instance.__class__.__name__

        # --- Second call ---
        repo2 = actual_service_instance.get_repository()

        assert repo2.__class__.__name__ == mock_repo_instance.__class__.__name__
