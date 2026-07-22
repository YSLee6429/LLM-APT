# M3 Evaluation Workspace Completion

Version `0.4.0` completes the open-source local research preview defined by M3. It exposes the
M2 evaluation kernel through an authenticated, project-oriented website while preserving the
trusted-Oracle, isolated-Runner, and public/private evidence boundaries.

## Delivered scope

1. Local authentication uses PBKDF2-SHA256 password hashes and HMAC-SHA256 signed, expiring bearer
   tokens. Roles are `admin`, `guest`, `reviewer`, `researcher`, and `viewer`. Login attempts are
   rate-limited, and guest identities receive shorter-lived, non-reusable sessions.
2. Projects organize research work without claiming commercial tenant isolation. Existing
   experiment, candidate, and report UUIDs can be linked without rewriting immutable evidence.
3. Model profiles record provider, model, revision, description, and tags independently of API
   credentials.
4. The dashboard aggregates experiment and candidate states, report verdicts, and stable failures.
5. Evidence review reads only public projections; hidden inputs, generated source, raw responses,
   actual output bytes, and Runner artifact tokens remain private.
6. Reports export deterministic JSON, Markdown, or CSV representations of the public projection.
7. The React website includes login, dashboard, projects and profiles, experiment/candidate index,
   evidence review/export, the problem validation lab, live readiness, responsive navigation, and
   light/dark themes.

## Local operation

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1
docker compose up -d --build
docker compose ps
```

Open `http://localhost:3000`. Read the generated administrator credentials from the local `.env`.
The file is ignored by Git and must never be published. External model calls remain disabled by
default.

## Acceptance baseline

- Python: Ruff, strict MyPy, Pytest, and coverage threshold.
- Frontend: ESLint, strict TypeScript, Vitest, and production Vite build.
- Database: Alembic `20260721_0004 (head)`.
- Deployment: eight Docker Compose services healthy.
- Browser path: login, dashboard, projects, evidence index, and report export.

The actual counts and IDs are recorded in `docs/acceptance/M3_FINAL_ACCEPTANCE.md` and the delivery
log. These values are evidence for this build, not general claims about external model quality.

## Explicit research-preview boundary

M3 is complete for a controlled local research environment and is released under Apache-2.0.
The current implementation is not a multi-tenant public
service and does not provide quotas, billing, enterprise identity federation, gVisor per-job
isolation, Kubernetes deployment, or long-term compliance retention. Those capabilities remain
M4 future work and are not represented as implemented.
