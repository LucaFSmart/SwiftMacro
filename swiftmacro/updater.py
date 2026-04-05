"""GitHub Releases update checker."""
from __future__ import annotations

import json
import urllib.request

from packaging.version import Version


def check_for_update(repo: str, current_version: str) -> tuple[bool, str]:
    """
    Check GitHub Releases API for a newer version.

    Returns (update_available, release_html_url).
    Returns (False, "") on any network, HTTP, or parse error — never raises.

    Args:
        repo: GitHub repository in "owner/name" form (e.g. "alice/SwiftMacro")
        current_version: Semver string of the running app (e.g. "1.0.0")
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "SwiftMacro-updater"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        tag = data["tag_name"].lstrip("v")
        html_url = data.get("html_url", "")
        if Version(tag) > Version(current_version):
            return True, html_url
        return False, ""
    except Exception as exc:
        from swiftmacro.log import get_logger
        get_logger("updater").info("Update check failed: %s", exc)
        return False, ""
