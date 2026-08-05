"""Contract tests for the Telnyx provider profile.

Pins the profile's contract without going live: identity, catalog-ID model
defaults, the load-bearing ``default_max_tokens=None`` (Telnyx error 10015
rejects an output cap combined with function tools on hosted models), the
task-filtered ``fetch_models`` override, and the plugin manifest shape.
"""

from __future__ import annotations

import io
import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


class TestTelnyxIdentity:
    def test_core_fields(self, telnyx_profile):
        p = telnyx_profile
        assert p.name == "telnyx"
        assert p.auth_type == "api_key"
        assert p.base_url == "https://api.telnyx.com/v2/ai/openai"
        assert "TELNYX_API_KEY" in p.env_vars

    def test_display_metadata_present(self, telnyx_profile):
        # Picker copy stays non-empty rather than pinning exact wording.
        assert telnyx_profile.display_name
        assert telnyx_profile.description
        assert telnyx_profile.signup_url.startswith("https://")

    def test_no_partner_attribution_headers(self, telnyx_profile):
        assert "HTTP-Referer" not in telnyx_profile.default_headers
        assert "X-Title" not in telnyx_profile.default_headers


class TestTelnyxMaxTokensContract:
    def test_no_default_output_cap(self, telnyx_profile):
        """Telnyx error 10015 rejects max_tokens + function tools on all
        hosted models, and no catalog metadata predicts which models are
        affected. The profile must never volunteer a cap — only an explicit
        user ``agent.max_tokens`` may send one."""
        assert telnyx_profile.default_max_tokens is None
        assert telnyx_profile.get_max_tokens("moonshotai/Kimi-K3") is None


class TestTelnyxModelDefaults:
    """Defaults must be live catalog IDs (``org/model`` form)."""

    def test_aux_model_is_catalog_id(self, telnyx_profile):
        aux = telnyx_profile.default_aux_model
        assert aux and "/" in aux, aux

    def test_fallback_models_are_catalog_ids(self, telnyx_profile):
        assert telnyx_profile.fallback_models, "expected curated fallbacks"
        for model in telnyx_profile.fallback_models:
            assert "/" in model, model


class TestRegistration:
    def test_last_writer_wins_under_canonical_name(self, plugin_module):
        """``register_provider`` is last-writer-wins; after (idempotent)
        re-registration the registry must serve this package's instance."""
        import providers

        providers.get_provider_profile("telnyx")  # force lazy discovery first
        providers.register_provider(plugin_module.telnyx)
        assert providers.get_provider_profile("telnyx") is plugin_module.telnyx


@contextmanager
def _fake_models_response(rows, seen_requests=None):
    payload = json.dumps({"data": rows}).encode()

    @contextmanager
    def _fake_open(req, timeout=None):
        if seen_requests is not None:
            seen_requests.append(req)
        yield io.BytesIO(payload)

    with patch("hermes_cli.urllib_security.open_credentialed_url", _fake_open):
        yield


class TestTelnyxFetchModels:
    def test_filters_to_text_generation_both_spellings(self, telnyx_profile):
        """The catalog labels hosted models ``text-generation`` and proxied
        frontier routes ``text generation`` (with a space) — both must pass;
        non-text tasks must not reach the chat picker; taskless rows pass so
        a payload-shape change cannot silently empty the picker."""
        rows = [
            {"id": "moonshotai/Kimi-K3", "task": "text-generation"},
            {"id": "openai/gpt-5", "task": "text generation"},
            {"id": "some/embedder", "task": "embedding"},
            {"id": "some/reranker", "task": "rerank"},
            {"id": "future/no-task-field"},
        ]
        with _fake_models_response(rows):
            got = telnyx_profile.fetch_models(api_key="test-key")
        assert got == ["moonshotai/Kimi-K3", "openai/gpt-5", "future/no-task-field"]

    def test_auth_header_only_when_key_present(self, telnyx_profile):
        seen: list = []
        with _fake_models_response([], seen_requests=seen):
            telnyx_profile.fetch_models(api_key="test-key")
            telnyx_profile.fetch_models()
        with_key, without_key = seen
        assert with_key.get_header("Authorization") == "Bearer test-key"
        assert without_key.get_header("Authorization") is None

    def test_base_url_override_is_respected(self, telnyx_profile):
        seen: list = []
        with _fake_models_response([], seen_requests=seen):
            telnyx_profile.fetch_models(
                api_key="test-key", base_url="https://proxy.example/v9/"
            )
        assert seen[0].full_url == "https://proxy.example/v9/models"

    def test_fetch_failure_returns_none(self, telnyx_profile):
        @contextmanager
        def _boom(req, timeout=None):
            raise OSError("connection refused")
            yield  # pragma: no cover

        with patch("hermes_cli.urllib_security.open_credentialed_url", _boom):
            assert telnyx_profile.fetch_models(api_key="test-key") is None


class TestManifest:
    def _manifest(self):
        with open(PACKAGE_ROOT / "plugin.yaml", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_kind_and_name(self):
        manifest = self._manifest()
        assert manifest["kind"] == "model-provider"
        assert manifest["name"] == "telnyx-provider"
        assert manifest["manifest_version"] == 1
        assert isinstance(manifest["version"], str) and manifest["version"]

    def test_requires_env_declares_secret_key(self):
        manifest = self._manifest()
        entries = {e["name"]: e for e in manifest["requires_env"]}
        key = entries["TELNYX_API_KEY"]
        # `secret: true` makes the installer use the masked prompt.
        assert key["secret"] is True
        assert key["url"].startswith("https://portal.telnyx.com")
