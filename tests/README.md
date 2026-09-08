# Backend Integration Tests

Run from the repository root, with the backend requirements installed:

```powershell
python -m pip install pytest
python -B -m pytest tests -q -p no:cacheprovider
```

`pytest` is the additional test dependency; `httpx` is already in the backend requirements. No backend or frontend dependency files are changed by this suite.

Each test uses a separate temporary SQLite database selected through `DATABASE_URL`. Clients use FastAPI's in-process `TestClient`, including cookie sessions and CSRF tokens obtained from `/api/auth/me`. Application socket connections and SMTP connections are blocked; only the Windows standard library's internal asyncio socketpair connection is permitted. Development email tokens exercise verification and reset without sending email.

Educator setup promotes an otherwise normally registered account directly in the temporary database. All authorization, membership, assignment, award, and redemption assertions go through HTTP. This does not add a public role-selection mechanism.

The suite imports `investolingo_backend.create_app`, the factory re-exported by `aether_backend`, avoiding the CLI's eagerly constructed global app. Missing backend modules or factories are setup errors, not skipped tests.

Production HTTP behavior is checked by injecting a production-mode `Config` with temporary SQLite and no SMTP, using HTTPS URLs and a trusted Origin header. The route guards, cookies, and token handling are not mocked. A separate test checks that normal production configuration rejects SQLite. This suite does not claim to test PostgreSQL deployment or SMTP delivery.
