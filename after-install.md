# Telnyx provider — final steps

1. **Move the plugin into the model-provider directory** (current Hermes
   installs plugins into `~/.hermes/plugins/`, but model providers are
   discovered from `~/.hermes/plugins/model-providers/`):

   `mv ~/.hermes/plugins/telnyx-provider ~/.hermes/plugins/model-providers/`

2. **Set your API key** (skip if you entered it during install): add
   `TELNYX_API_KEY=...` to `~/.hermes/.env`. Create a key at
   https://portal.telnyx.com/#/app/api-keys

3. **Restart any running `hermes gateway`** — providers register once per
   process.

4. **Pick a model:**

   `hermes model` (interactive picker), or
   `hermes chat --provider telnyx -m moonshotai/Kimi-K3`

Note: the "Enable now?" toggle does not apply to model providers —
selecting the provider is what activates it.
