import types
from unittest import mock

import pytest

import cumulusci_ado.utils.common.artifacttool_updater as updater


# --- Mock Classes ---
class MockRelease:
    def __init__(
        self,
        uri="http://example.com/tool.zip",
        name="ArtifactTool",
        rid="osx-x64",
        version="1.0.0",
    ):
        self.uri = uri
        self.name = name
        self.rid = rid
        self.version = version


class MockClient:
    def __init__(self, release=None):
        self._release = release or MockRelease()
        self.called = False

    def get_clienttool_release(self, *args, **kwargs):
        self.called = True
        return self._release


# --- Fixtures ---
@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    monkeypatch.setenv("AZURE_DEVOPS_EXT_ARTIFACTTOOL_OVERRIDE_PATH", "", raising=False)
    monkeypatch.setenv("AZURE_DEVOPS_EXT_ARTIFACTTOOL_OVERRIDE_URL", "", raising=False)
    monkeypatch.setenv(
        "AZURE_DEVOPS_EXT_ARTIFACTTOOL_OVERRIDE_VERSION", "", raising=False
    )
    yield


@pytest.fixture
def mock_spinner():
    with mock.patch("humanfriendly.Spinner") as spinner:
        spinner.return_value.__enter__.return_value = mock.Mock(step=mock.Mock())
        yield spinner


@pytest.fixture
def mock_uuid():
    with mock.patch("uuid.uuid4", return_value="mock-uuid"):
        yield


@pytest.fixture
def mock_platform():
    with mock.patch("platform.system", return_value="Darwin"), mock.patch(
        "platform.machine", return_value="arm64"
    ):
        yield


@pytest.fixture
def mock_distro():
    with mock.patch("distro.id", return_value="ubuntu"), mock.patch(
        "distro.version", return_value="20.04"
    ):
        yield


# --- Tests ---
def test_get_latest_artifacttool_override(monkeypatch):
    monkeypatch.setenv(updater.ARTIFACTTOOL_OVERRIDE_PATH_ENVKEY, "/tmp/tool")
    atu = updater.ArtifactToolUpdater()
    assert atu.get_latest_artifacttool("org") == "/tmp/tool"


def test_get_latest_artifacttool_normal(monkeypatch):
    monkeypatch.delenv(updater.ARTIFACTTOOL_OVERRIDE_PATH_ENVKEY, raising=False)
    atu = updater.ArtifactToolUpdater()
    with mock.patch.object(atu, "_get_artifacttool", return_value="/tmp/realtool") as m:
        assert atu.get_latest_artifacttool("org") == "/tmp/realtool"
        m.assert_called_once()


def test__get_artifacttool_override_url(monkeypatch, mock_uuid):
    monkeypatch.setenv(
        updater.ARTIFACTTOOL_OVERRIDE_URL_ENVKEY, "http://custom.com/tool.zip"
    )
    atu = updater.ArtifactToolUpdater()
    with mock.patch("os.path.exists", return_value=False), mock.patch(
        "cumulusci_ado.utils.common.artifacttool_updater._update_artifacttool"
    ) as upd:
        path = atu._get_artifacttool("org")
        assert "mock-uuid" in path
        upd.assert_called_once()


def test__get_artifacttool_release_exists(monkeypatch, mock_uuid):
    monkeypatch.delenv(updater.ARTIFACTTOOL_OVERRIDE_URL_ENVKEY, raising=False)
    atu = updater.ArtifactToolUpdater()
    with mock.patch(
        "cumulusci_ado.utils.common.artifacttool_updater._get_current_release",
        return_value=("http://x.com", "relid"),
    ):
        with mock.patch("os.path.exists", return_value=True):
            assert atu._get_artifacttool("org") == updater._compute_release_dir("relid")


def test__get_artifacttool_update(monkeypatch, mock_uuid):
    atu = updater.ArtifactToolUpdater()
    with mock.patch(
        "cumulusci_ado.utils.common.artifacttool_updater._get_current_release",
        return_value=("http://x.com", "relid"),
    ):
        with mock.patch("os.path.exists", side_effect=[False, False]):
            with mock.patch(
                "cumulusci_ado.utils.common.artifacttool_updater._update_artifacttool"
            ) as upd:
                path = atu._get_artifacttool("org")
                assert "relid" in path
                upd.assert_called_once()


def test__get_artifacttool_exception(monkeypatch):
    atu = updater.ArtifactToolUpdater()

    def raise_exc(*a, **kw):
        raise Exception("fail")

    with mock.patch(
        "cumulusci_ado.utils.common.artifacttool_updater._get_current_release",
        side_effect=raise_exc,
    ):
        with pytest.raises(updater.CumulusCIFailure):
            atu._get_artifacttool("org")


def test__update_artifacttool_normal(mock_spinner, mock_uuid):
    with mock.patch("os.path.isdir", return_value=True), mock.patch(
        "os.listdir", return_value=["old1", "old2"]
    ), mock.patch("os.path.join", side_effect=lambda *a: "/".join(a)), mock.patch(
        "shutil.rmtree"
    ), mock.patch(
        "requests.get"
    ) as req, mock.patch(
        "zipfile.ZipFile"
    ) as zf, mock.patch(
        "os.makedirs"
    ), mock.patch(
        "os.path.exists", side_effect=[False, False, False]
    ), mock.patch(
        "os.stat", return_value=types.SimpleNamespace(st_mode=0o755)
    ), mock.patch(
        "os.chmod"
    ), mock.patch(
        "os.rename"
    ), mock.patch(
        "time.sleep"
    ):
        # Setup mocks
        req.return_value.headers = {"Content-Length": "10"}
        req.return_value.iter_content = lambda chunk_size: [b"12345", b"67890"]
        zf.return_value.extractall = mock.Mock()
        updater._update_artifacttool("http://x.com", "relid")
        zf.assert_called()


def test__update_artifacttool_release_exists(mock_spinner, mock_uuid):
    with mock.patch("os.path.isdir", return_value=True), mock.patch(
        "os.listdir", return_value=[]
    ), mock.patch("os.path.join", side_effect=lambda *a: "/".join(a)), mock.patch(
        "shutil.rmtree"
    ), mock.patch(
        "requests.get"
    ) as req, mock.patch(
        "zipfile.ZipFile"
    ) as zf, mock.patch(
        "os.makedirs"
    ), mock.patch(
        "os.path.exists", side_effect=[False, True]
    ), mock.patch(
        "os.stat", return_value=types.SimpleNamespace(st_mode=0o755)
    ), mock.patch(
        "os.chmod"
    ), mock.patch(
        "os.rename"
    ), mock.patch(
        "time.sleep"
    ):
        req.return_value.headers = {"Content-Length": "10"}
        req.return_value.iter_content = lambda chunk_size: [b"12345", b"67890"]
        zf.return_value.extractall = mock.Mock()
        updater._update_artifacttool("http://x.com", "relid")
        zf.assert_called()


def test__update_artifacttool_extract_exception(mock_spinner, mock_uuid):
    with mock.patch("os.path.isdir", return_value=True), mock.patch(
        "os.listdir", return_value=[]
    ), mock.patch("os.path.join", side_effect=lambda *a: "/".join(a)), mock.patch(
        "shutil.rmtree"
    ), mock.patch(
        "requests.get"
    ) as req, mock.patch(
        "zipfile.ZipFile"
    ) as zf, mock.patch(
        "os.makedirs"
    ), mock.patch(
        "os.path.exists", side_effect=[False, False, False]
    ), mock.patch(
        "os.stat", return_value=types.SimpleNamespace(st_mode=0o755)
    ), mock.patch(
        "os.chmod"
    ), mock.patch(
        "os.rename"
    ), mock.patch(
        "time.sleep"
    ):
        req.return_value.headers = {"Content-Length": "10"}
        req.return_value.iter_content = lambda chunk_size: [b"12345", b"67890"]
        zf.return_value.extractall.side_effect = Exception("fail")
        with mock.patch("logging.Logger.error") as logerr:
            updater._update_artifacttool("http://x.com", "relid")
            logerr.assert_called()


def test__update_artifacttool_rename_retries(mock_spinner, mock_uuid):
    with mock.patch("os.path.isdir", return_value=True), mock.patch(
        "os.listdir", return_value=[]
    ), mock.patch("os.path.join", side_effect=lambda *a: "/".join(a)), mock.patch(
        "shutil.rmtree"
    ), mock.patch(
        "requests.get"
    ) as req, mock.patch(
        "zipfile.ZipFile"
    ) as zf, mock.patch(
        "os.makedirs"
    ), mock.patch(
        "os.path.exists", side_effect=[False, False, False]
    ), mock.patch(
        "os.stat", return_value=types.SimpleNamespace(st_mode=0o755)
    ), mock.patch(
        "os.chmod"
    ), mock.patch(
        "os.rename", side_effect=[Exception("fail")] * 9 + [None]
    ), mock.patch(
        "time.sleep"
    ):
        req.return_value.headers = {"Content-Length": "10"}
        req.return_value.iter_content = lambda chunk_size: [b"12345", b"67890"]
        zf.return_value.extractall = mock.Mock()
        updater._update_artifacttool("http://x.com", "relid")
        zf.assert_called()


def test__get_current_release_darwin_arm(monkeypatch, mock_platform, mock_distro):
    client = MockClient()
    uri, relid = updater._get_current_release(client, None)
    assert uri == client._release.uri
    assert relid == updater._compute_id(client._release)


def test__get_current_release_windows_arm(monkeypatch, mock_distro):
    with mock.patch("platform.system", return_value="Windows"), mock.patch(
        "platform.machine", return_value="ARM64"
    ):
        client = MockClient()
        uri, relid = updater._get_current_release(client, None)
        assert uri == client._release.uri
        assert relid == updater._compute_id(client._release)


def test__get_current_release_none(monkeypatch, mock_platform, mock_distro):
    client = MockClient(release=None)
    client.get_clienttool_release = lambda *a, **k: None
    uri, relid = updater._get_current_release(client, None)
    assert uri is None and relid is None


def test__mkdir_if_not_exist_new(monkeypatch):
    with mock.patch("os.makedirs") as makedirs:
        updater._mkdir_if_not_exist("/tmp/newdir")
        makedirs.assert_called_once()


def test__mkdir_if_not_exist_exists(monkeypatch):
    with mock.patch("os.makedirs", side_effect=OSError), mock.patch(
        "os.path.isdir", return_value=True
    ):
        updater._mkdir_if_not_exist("/tmp/existdir")


def test__mkdir_if_not_exist_fail(monkeypatch):
    with mock.patch("os.makedirs", side_effect=OSError), mock.patch(
        "os.path.isdir", return_value=False
    ):
        with pytest.raises(OSError):
            updater._mkdir_if_not_exist("/tmp/faildir")


def test__compute_id():
    rel = MockRelease(name="foo", rid="bar", version="baz")
    assert updater._compute_id(rel) == "foo_bar_baz"


def test__compute_artifacttool_root(monkeypatch):
    monkeypatch.setattr(updater, "AZ_DEVOPS_GLOBAL_CONFIG_DIR", "/tmp/conf")
    root = updater._compute_artifacttool_root()
    assert root.endswith("cli/tools/artifacttool")


def test__compute_release_dir(monkeypatch):
    monkeypatch.setattr(updater, "_compute_artifacttool_root", lambda: "/tmp/root")
    assert updater._compute_release_dir("relid") == "/tmp/root/relid"
