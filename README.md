# Telnyx provider for Hermes Agent

Vendor-maintained [Hermes Agent](https://github.com/NousResearch/hermes-agent)
model-provider plugin for
[Telnyx AI inference](https://developers.telnyx.com/docs/inference/getting-started).

- OpenAI-compatible chat completions at `https://api.telnyx.com/v2/ai/openai`
  (streaming, tool calling, usage on the final chunk).
- Live model catalog from the authenticated `/models` endpoint, filtered to
  text-generation models: open-weight models hosted on Telnyx GPU
  infrastructure (Kimi, GLM, MiniMax, Qwen, Llama) plus proxied frontier
  routes.
- Curated offline fallback models when the live catalog is unreachable.

Maintained by Telnyx. This package intentionally lives outside the
hermes-agent tree and registers through the documented external
model-provider plugin surface (`providers.register_provider`).

## Compatibility

- Hermes Agent `>=0.21.4` (Python 3.11–3.13). Hermes `0.21.1` added flat
  provider discovery and switching, but `0.21.4` is the first release that
  correctly normalizes the Telnyx catalog's per-million-token prices.
- CI guards the `0.21.1` host-capability floor and the minimum fully
  supported release (`0.21.4`) from exact release commits.

## Install

```bash
hermes plugins install team-telnyx/hermes-inference-provider
```

The installer prompts for `TELNYX_API_KEY` (masked) and saves it to
`$HERMES_HOME/.env` (default: `~/.hermes/.env`). Hermes discovers the
provider directly from the installer's flat plugin directory; no manual
move is required.

Note: the installer's "Enable now?" prompt does not gate model providers —
activation is picking the provider (`hermes model` or `--provider telnyx`).

Until the catalog entry is merged, install from the GitHub repository as
shown above. Afterwards the catalog name is enough:

```bash
hermes plugins install telnyx-provider
```

Create an API key at <https://portal.telnyx.com/#/app/api-keys>.

**Restart any long-running `hermes gateway` after installing** — provider
discovery runs once per process.

## Use

```bash
hermes model                                      # interactive picker → Telnyx
hermes chat --provider telnyx -m moonshotai/Kimi-K3
hermes chat -q "hello" --provider telnyx -m zai-org/GLM-5.2
```

Inside an interactive session:

```text
/model moonshotai/Kimi-K3 --provider telnyx
```

## Models

The model list comes from the authenticated live catalog
(`GET /v2/ai/openai/models`), filtered to text-generation tasks. When the
live fetch fails, Hermes falls back to this curated, tool-call-verified
list:

- `moonshotai/Kimi-K3`
- `moonshotai/Kimi-K2.6`
- `zai-org/GLM-5.2`
- `MiniMaxAI/MiniMax-M3-MXFP8`

Current catalog and pricing: [Telnyx model docs](https://developers.telnyx.com/docs/inference/models).

## Known constraints

- **No default output cap.** Combining `max_tokens` /
  `max_completion_tokens` with function tools trips Telnyx error 10015 on
  hosted models, and no catalog metadata predicts which models are
  affected. The profile therefore never volunteers a cap; only an explicit
  user `agent.max_tokens` sends one, and it may still be rejected by some
  models.
- **`/models` requires auth.** Anonymous requests get a 401; without a key
  the picker shows the curated fallback list.
- **Catalog pricing is per-1M-token** (`pricing.unit == "1M_tokens"`).
  Supported Hermes releases normalize the current catalog rates. A
  provider-neutral upstream change is tracking explicit recognition of this
  unit spelling instead of relying on rate-magnitude inference.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| 401 from the API | Check `TELNYX_API_KEY` in `~/.hermes/.env`; create a key in the Telnyx portal. |
| Provider missing from `hermes model` | Confirm `hermes plugins list` shows `telnyx-provider`, then restart the process/gateway. Hermes 0.21.4 or newer is required. |
| Model list looks stale or short | Live catalog fetch failed (network/auth) — Hermes is showing the curated fallback list. |
| Long-running gateway doesn't see the plugin | Restart it; providers register once per process. |

## Update / remove

```bash
hermes plugins update telnyx-provider
hermes plugins remove telnyx-provider
```

## Development

```bash
HERMES_AGENT_REPO=/path/to/hermes-agent python -m pytest tests -q
```

Tests need a hermes-agent checkout on `PYTHONPATH` (the conftest handles
it) and nothing else beyond `pytest` + `pyyaml`; the default suite makes
no network calls.

Before a release, validate every exposed model against the authenticated
Telnyx catalog and Hermes pricing normalization:

```bash
TELNYX_LIVE_TESTS=1 HERMES_AGENT_REPO=/path/to/hermes-agent \
  python -m pytest tests/test_live_pricing.py -q
```

## Security

Report vulnerabilities through this repository's GitHub Security
Advisories ("Report a vulnerability"). Do not open public issues for
security reports.

## License

[MIT](LICENSE)
