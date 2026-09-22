"""Opt-in release gate against the authenticated Telnyx model catalog.

Run with ``TELNYX_LIVE_TESTS=1`` and ``TELNYX_API_KEY`` set. Normal CI skips
this test because catalog contents and credentials are external release inputs.
"""

from __future__ import annotations

import json
import os
import urllib.request
from decimal import Decimal

import pytest

_LIVE = os.environ.get("TELNYX_LIVE_TESTS") == "1"
_KEY = os.environ.get("TELNYX_API_KEY", "").strip()
pytestmark = pytest.mark.skipif(
    not (_LIVE and _KEY),
    reason="set TELNYX_LIVE_TESTS=1 and TELNYX_API_KEY for the live release gate",
)

_TOLERANCE = Decimal("1e-12")
_FIELDS = {
    "input_cost_per_million": ("prompt", "input", "input_cost_per_token", "prompt_token_cost"),
    "output_cost_per_million": ("completion", "output", "output_cost_per_token", "completion_token_cost"),
    "cache_read_cost_per_million": ("cache_read", "cached_prompt", "input_cache_read", "cache_read_cost_per_token"),
    "cache_write_cost_per_million": ("cache_write", "cache_creation", "input_cache_write", "cache_write_cost_per_token"),
    "request_cost": ("request", "request_cost"),
}
_RAW_RATE_FIELDS = {alias for aliases in _FIELDS.values() for alias in aliases}


def _live_catalog(base_url: str) -> list[dict]:
    from hermes_cli.urllib_security import open_credentialed_url

    request = urllib.request.Request(
        base_url.rstrip("/") + "/models",
        headers={
            "Authorization": f"Bearer {_KEY}",
            "Accept": "application/json",
            "User-Agent": "hermes-telnyx-provider-release-check",
        },
    )
    with open_credentialed_url(request, timeout=30) as response:
        payload = json.loads(response.read().decode())
    rows = payload if isinstance(payload, list) else payload.get("data", [])
    return [row for row in rows if isinstance(row, dict)]


def _decimal(value):
    return None if value in (None, "") else Decimal(str(value))


def _pricing_mapping(value):
    """Find the catalog's unit-tagged pricing object without pinning its nesting."""
    if isinstance(value, dict):
        normalized = {str(key).lower(): item for key, item in value.items()}
        if "unit" in normalized and any(
            normalized.get(field) not in (None, "") for field in _RAW_RATE_FIELDS
        ):
            return normalized
        for item in value.values():
            found = _pricing_mapping(item)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _pricing_mapping(item)
            if found is not None:
                return found
    return None


def test_every_exposed_model_matches_the_live_telnyx_pricing(telnyx_profile):
    """Every live picker row either preserves its published rate or stays explicitly unpriced."""
    from agent.usage_pricing import get_pricing_entry

    rows = _live_catalog(telnyx_profile.base_url)
    exposed = set(telnyx_profile.fetch_models(api_key=_KEY, timeout=30) or [])
    expected_exposed = {
        row["id"]
        for row in rows
        if "id" in row
        and (
            "task" not in row
            or str(row["task"]).strip().lower().replace(" ", "-")
            == "text-generation"
        )
    }
    assert exposed == expected_exposed

    for row in rows:
        model_id = row.get("id")
        if model_id not in exposed:
            continue
        raw = _pricing_mapping(row)
        entry = get_pricing_entry(
            model_id,
            provider="telnyx",
            base_url=telnyx_profile.base_url,
            api_key=_KEY,
        )
        if not isinstance(raw, dict) or not any(
            raw.get(field) not in (None, "") for field in _RAW_RATE_FIELDS
        ):
            assert entry is None, f"{model_id}: host invented pricing absent from Telnyx catalog"
            continue

        assert str(raw.get("currency", "USD")).upper() == "USD", model_id
        assert str(raw.get("unit", "")).strip().lower() == "1m_tokens", model_id
        assert entry is not None, f"{model_id}: published Telnyx pricing was dropped"
        for entry_field, aliases in _FIELDS.items():
            expected = next(
                (_decimal(raw[alias]) for alias in aliases if raw.get(alias) not in (None, "")),
                None,
            )
            actual = _decimal(getattr(entry, entry_field))
            if expected is None:
                assert actual is None, f"{model_id}: unexpected {entry_field}={actual}"
            else:
                assert actual is not None, f"{model_id}: missing {entry_field}"
                assert abs(actual - expected) <= _TOLERANCE, (
                    f"{model_id}: {entry_field}={actual}, Telnyx={expected}"
                )
