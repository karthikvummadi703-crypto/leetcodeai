# Contributing

Thanks for your interest in LeetCode Guidance AI! Here's how to get
started, what we expect from contributions, and how to keep the project
healthy.

## Code of conduct

Please read and follow our
[Code of Conduct](CODE_OF_CONDUCT.md). Harassment of any kind will not be
tolerated.

## Project overview

- `backend/` — FastAPI + Python 3.13 (RAG, agent, LeetCode catalog +
  GraphQL client, MCP server).
- `frontend/` — React 19 + Vite + TypeScript + Tailwind.
- See [README.md](README.md) and `docs/` for architecture and API docs.

## Development setup

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env      # macOS/Linux: cp .env.example .env
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
copy .env.example .env.local     # set Firebase web keys
npm run dev
```

## Running checks

Every change should pass the same suite that CI runs:

```bash
# Backend (from backend/)
ruff check .          # lint
mypy app              # type checking
pytest -q             # tests

# Frontend (from frontend/)
npm run lint
npm run build
```

You can also install the pre-commit hooks so checks run automatically:

```bash
pre-commit install
```

## Commit conventions

We follow **Conventional Commits** — this powers automated releases via
release-please.

```
feat: add offline search for the problem catalog
fix(backend): handle rate limit 429s without dropping the stream
docs: document the MCP server usage
chore(deps): bump uvicorn to 0.34
```

Prefixes we use: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
`test`, `build`, `ci`, `chore`, `revert`.

- **Sign your commits** (GPG or SSH). Unverified commits are still
  accepted, but signed history is appreciated.
- Write descriptive commit bodies; avoid `Update file.py` messages.

## Branches and PRs

1. Create a branch off `main` (`feature/xyz` or `fix/xyz`).
2. Make focused changes and keep them small enough to review.
3. Add or update tests for backend changes.
4. Push and open a pull request against `main`.
5. Respond to review comments promptly.

## Reporting issues

- **Bugs:** include the steps to reproduce, expected vs actual behaviour,
  and the versions you used.
- **Feature requests:** explain the problem you're trying to solve, not
  just the feature you want.
- **Security issues:** use the process in [SECURITY.md](SECURITY.md) —
  do not open a public issue.

## Releases

Releases are created automatically by release-please from Conventional
Commits on `main`. `feat:` bumps minor, `fix:` bumps patch, and `BREAKING
CHANGE:` bumps major. No manual release steps are needed.
