# Security policy

## Supported versions

Only the latest commit on the `main` branch is supported during the pre-alpha stage.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use the repository's
**Security > Report a vulnerability** private-advisory form. If private advisories are not yet
enabled on a fork, contact the repository owner through the GitHub profile without including
exploit details, credentials, private prompts, or datasets in the first message.

Never include model API keys, raw private prompts, credentials, or personal datasets in a
report. Generated programs are untrusted and must not be executed outside the sandbox.

The 0.4.x research preview is intended for trusted local operators. It must not be exposed
directly to the public Internet or used as a hostile multi-tenant execution service.
