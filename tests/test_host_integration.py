"""Cold-install proof against a real hermes-agent tree.

Copies this package into ``$HERMES_HOME/plugins/telnyx-provider``
inside a temporary home, then asserts in a fresh subprocess (clean module
state — how a real ``hermes`` process starts) that flat plugin discovery
registers the provider across every host resolution path.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from conftest import HERMES_REPO, PACKAGE_ROOT

_SNIPPET = """
import providers
from hermes_cli.providers import get_provider, resolve_provider_full
from hermes_cli.models_catalog_static import CANONICAL_PROVIDERS

profile = providers.get_provider_profile("telnyx")
assert profile is not None, "telnyx not discovered from the user plugins dir"
assert profile.base_url == "https://api.telnyx.com/v2/ai/openai"
assert profile.default_max_tokens is None
assert profile.fallback_models, "curated fallbacks missing"
assert "telnyx" in [p.name for p in providers.list_providers()]
assert get_provider("telnyx").source == "plugin-profile"
assert resolve_provider_full("telnyx").source == "plugin-profile"
assert "telnyx" in [p.slug for p in CANONICAL_PROVIDERS]
# Provenance: the registered instance must come from the *user* plugin dir
# (module `_hermes_user_provider_<dir>`), not a bundled tree.
assert type(profile).__module__.startswith("_hermes_user_provider_"), (
    type(profile).__module__
)
print("cold-install-ok")
"""


def test_cold_discovery_from_user_plugins_dir(tmp_path):
    home = tmp_path / "hermes-home"
    target = home / "plugins" / "telnyx-provider"
    target.parent.mkdir(parents=True)
    shutil.copytree(
        PACKAGE_ROOT,
        target,
        ignore=shutil.ignore_patterns(
            ".git", ".github", "tests", "__pycache__", ".pytest_cache"
        ),
    )

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HERMES_HOME": str(home),
        "PYTHONPATH": str(HERMES_REPO),
    }
    result = subprocess.run(
        [sys.executable, "-c", _SNIPPET],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "cold-install-ok" in result.stdout
