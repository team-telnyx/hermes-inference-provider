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

- Hermes Agent (Python 3.11–3.13), validated against
  `NousResearch/hermes-agent@ae6c2e57e` (main, 2026-08-05). CI re-validates
  weekly against current `main`.
- Release candidates track hermes-agent `main`. The stable `v0.1.0` release
  will pin the first released Hermes version that routes
  `kind: model-provider` installs automatically (upstream change in
  progress).

## Install

Hermes discovers external model providers from
`$HERMES_HOME/plugins/model-providers/` (default:
`~/.hermes/plugins/model-providers/`).

### Option A — Hermes installer + one move

```bash
hermes plugins install team-telnyx/hermes-inference-provider
mv ~/.hermes/plugins/telnyx-provider ~/.hermes/plugins/model-providers/
```

The installer prompts for `TELNYX_API_KEY` (masked) and saves it to
`~/.hermes/.env`. The `mv` is needed because current Hermes clones every
plugin into `~/.hermes/plugins/`, while model-provider discovery scans the
`model-providers/` subdirectory; once the upstream routing change lands,
the `mv` step disappears.

Note: the installer's "Enable now?" prompt does not gate model providers —
activation is picking the provider (`hermes model` or `--provider telnyx`).

### Option B — plain git clone

```bash
mkdir -p ~/.hermes/plugins/model-providers
git clone https://github.com/team-telnyx/hermes-inference-provider \
  ~/.hermes/plugins/model-providers/telnyx
```

Then set `TELNYX_API_KEY` in `~/.hermes/.env`, or let `hermes model` prompt
for it.

Create an API key at <https://portal.telnyx.com/#/app/api-keys>.

**Restart any long-running `hermes gateway` after installing** — provider
discovery runs once per process.

## Use

```bash
hermes model                                      # interactive picker → Telnyx
hermes chat --provider telnyx -m moonshotai/Kimi-K3
hermes -z "hello" --provider telnyx -m zai-org/GLM-5.2
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
  Cost tracking that reads live catalog pricing needs a host that honors
  the tagged unit; until the upstream integration change lands, treat
  in-app cost figures for Telnyx as unavailable rather than authoritative.
- **In-session `/model … --provider telnyx` switching** needs the upstream
  resolver change (current Hermes resolves that path against models.dev +
  built-in overlays only). Until it lands, pick Telnyx via `hermes model`
  or pass `--provider telnyx` at launch — both work today.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| 401 from the API | Check `TELNYX_API_KEY` in `~/.hermes/.env`; create a key in the Telnyx portal. |
| Provider missing from `hermes model` | Confirm the plugin directory is under `~/.hermes/plugins/model-providers/`, then restart the process/gateway. |
| Model list looks stale or short | Live catalog fetch failed (network/auth) — Hermes is showing the curated fallback list. |
| Long-running gateway doesn't see the plugin | Restart it; providers register once per process. |
| `/model <model> --provider telnyx` says unknown provider | Current-host limitation (see Known constraints); use `hermes model` or launch with `--provider telnyx`. |

## Update / remove

```bash
git -C ~/.hermes/plugins/model-providers/telnyx pull   # update
rm -rf ~/.hermes/plugins/model-providers/telnyx        # remove
```

## Development

```bash
HERMES_AGENT_REPO=/path/to/hermes-agent python -m pytest tests -q
```

Tests need a hermes-agent checkout on `PYTHONPATH` (the conftest handles
it) and nothing else beyond `pytest` + `pyyaml`; they make no network
calls.

## Security

Report vulnerabilities through this repository's GitHub Security
Advisories ("Report a vulnerability"). Do not open public issues for
security reports.

## License

[MIT](LICENSE)
