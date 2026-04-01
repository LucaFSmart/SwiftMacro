"""Tests for the GitHub Releases update checker."""
import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError


def _make_urlopen_mock(tag_name="v1.1.0", html_url="https://github.com/releases/v1.1.0"):
    """Return a context-manager-compatible mock for urllib.request.urlopen."""
    payload = json.dumps({"tag_name": tag_name, "html_url": html_url}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_update_available_when_newer_version():
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", return_value=_make_urlopen_mock("v1.1.0")):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is True
    assert url == "https://github.com/releases/v1.1.0"


def test_no_update_when_same_version():
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", return_value=_make_urlopen_mock("v1.0.0")):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_no_update_when_older_version():
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", return_value=_make_urlopen_mock("v0.9.0")):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_no_update_on_network_error():
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", side_effect=URLError("no network")):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_no_update_on_malformed_json():
    from swiftmacro.updater import check_for_update
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"not-json"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_no_update_on_missing_tag_name():
    from swiftmacro.updater import check_for_update
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"html_url": "https://example.com"}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_no_update_on_http_404():
    from swiftmacro.updater import check_for_update
    with patch(
        "urllib.request.urlopen",
        side_effect=HTTPError("url", 404, "Not Found", {}, None),
    ):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_tag_without_v_prefix():
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", return_value=_make_urlopen_mock("1.1.0")):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is True


def test_no_update_two_digit_minor():
    """Integer comparison: 1.10.0 > 1.9.0 must be True (not False via string sort)."""
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", return_value=_make_urlopen_mock("v1.10.0")):
        available, url = check_for_update("owner/repo", "1.9.0")
    assert available is True, "1.10.0 must be newer than 1.9.0"
