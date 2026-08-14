# Security Policy

## Supported versions

The project is under active development and has not shipped a stable
release yet. Security fixes are applied to `main` and backported to the
latest release tag when one exists.

| Version | Supported |
| ------- | --------- |
| `main`  | ✅ Yes    |
| Latest release | ✅ Yes |
| Older releases | ❌ No |

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Report them
privately so they can be fixed before disclosure.

- **Preferred:** use GitHub's private vulnerability reporting on the
  repository: **Security → Report a vulnerability**. If you do not see it,
  email the maintainer using the contact in your GitHub profile.
- Include as much of the following as possible:
  - A description of the vulnerability and the impact.
  - Steps to reproduce (or a minimal proof-of-concept).
  - Affected component(s) and versions.
  - Any suggested fix, if you have one.

### What happens next

1. Acknowledgment within **48 hours** of the report.
2. A fix is prepared, reviewed and released as soon as possible
   (critical issues targeted within 7 days).
3. A public advisory is published after the fix ships.

We ask that you do not disclose the issue publicly until a fix has been
released.

## Security scope

Things we care about in this project:

- Secrecy of `OPENROUTER_API_KEY`, `FIREBASE_PRIVATE_KEY` and any other
  secrets (see `.env.example`). Never commit real keys.
- Firebase token verification and per-user authorization.
- Per-user rate limiting that is currently disabled or bypassable.
- Prompt injection / prompt-leak risks through user chat input.
- Any path that reads files or network input (LeetCode GraphQL client,
  RAG knowledge base).

## Good practices for contributors

- Never commit `.env` files or real secrets.
- Sign your commits with GPG or SSH keys.
- Run `pre-commit` and the CI suite (`ruff`, `mypy`, `pytest`,
  frontend `lint`/`build`) before pushing.
