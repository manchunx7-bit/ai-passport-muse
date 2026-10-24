# AI Passport Muse: Agent entry

For user setup, read [the setup playbook](docs/AGENT_SETUP.zh-CN.md), then the quickstart and network guide. Ordinary users do not need to compile code. This application repository is not full firmware and its source ZIP cannot be flashed.

Use the user's own account and existing network. Token entry, phone pairing, physical confirmation and actual voice submission belong to the user. Keep progress under ignored `.setup/`; never log or commit Tokens, pairing material, Wi-Fi passwords or recordings. Do not clear pairing for an ordinary network failure.

The doctor performs local inspection only, not cloud authentication or device configuration. Do not invent a device setup API: the shared setup server is outside this repository. See the playbook for the manual handoff and completion criteria.

For changes, review `PUBLIC_FILES.json`, run `tools/check_scope.py` and relevant tests. Host tests and adaptation instructions are in [development](docs/DEVELOPMENT.zh-CN.md).
