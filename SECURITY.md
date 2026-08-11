# Security Policy

ANNEX handles user-generated content, AI model interaction, and personal accounts.
Security is a first-class requirement, not an afterthought. This policy explains how
vulnerabilities are reported and what security standards every contribution must meet.

## Supported versions

| Version | Supported |
|---|---|
| `main` (development) | ✅ Latest — receives fixes immediately |
| `0.x` (pre-release) | ✅ Only the most recent patch |
| `1.0.0+` (planned) | ✅ Latest stable + previous minor |

During pre-release (`0.x`), only the most recent release is patched. Once ANNEX
reaches 1.0.0, we will support the latest minor release and the previous one for
security fixes.

## Reporting a vulnerability

**Do not open a public issue for a security vulnerability.** Doing so exposes users
before a fix exists.

Instead:

1. **Use GitHub's private vulnerability reporting** (Security tab → *Report a
   vulnerability*) for this repository, **or**
2. If private reporting is unavailable, open a **confidential** issue marked
   `[SECURITY]` and reach out to the maintainers with a pointer to it.

### What to include

- Affected component(s) and version or commit.
- A minimal, step-by-step reproduction.
- Impact assessment: what an attacker can gain, and under which conditions.
- A proposed fix, if you have one (do not include exploit code in the report body).

### What happens next

1. **Acknowledgment** — maintainers confirm receipt within **48 hours**.
2. **Triage** — severity is assessed (CVSS) and a fix plan is agreed.
3. **Fix & release** — a patched version is released; the fix is coordinated with
   downstream users where relevant.
4. **Disclosure** — once a fix is shipped (or after **90 days** without a fix),
   the vulnerability is disclosed with credit to the reporter unless they request
   anonymity.

We operate a coordinated-disclosure model: **no public disclosure before a fix.**

## Security engineering requirements

Every contribution must respect these requirements. See
[CONTRIBUTING.md](./CONTRIBUTING.md) for the contribution workflow.

| Concern | Requirement |
|---|---|
| **Secrets management** | Credentials live in environment variables / secret manager only. Never commit keys, tokens, or service accounts. |
| **Authentication** | Firebase Auth tokens verified server-side on every request; JWT validation with proper issuer/audience checks and expiry. |
| **Authorization (RBAC)** | Every endpoint enforces role/permission checks in the service layer, never only in the UI. |
| **Rate limiting** | Auth, AI-analysis, and public endpoints are rate limited (Redis-backed). |
| **Input validation** | All inputs validated server-side with strict schemas; reject unknown fields. |
| **SQL injection** | SQL is never constructed by string interpolation; database access goes through the repository layer (parameterized queries / Supabase client). |
| **Prompt injection** | LLM prompts treat model output and user content as untrusted; the project's guard layer sanitizes and delimits untrusted content. |
| **CSRF / XSS** | State-changing APIs require proper token/CSRF handling; all rendered content is escaped; no `innerHTML` with untrusted data. |
| **Storage** | Supabase Storage objects use signed URLs with short expiry; bucket policies enforce least privilege. |
| **Dependencies** | Lockfiles are committed; CI runs vulnerability scanning on every change. |

## Security checklist for PRs

- [ ] No secrets, credentials, or personal data introduced or logged.
- [ ] New endpoints validate input and enforce authorization.
- [ ] New prompts apply prompt-injection guards.
- [ ] Sensitive operations are rate limited.
- [ ] Tests cover the security-sensitive code path.

## Scope

This policy covers the ANNEX source code and official infrastructure. It does not
cover third-party services configured by end users or forks of the project.

## Acknowledgements

We are grateful to every researcher who reports responsibly. Reporters of verified
vulnerabilities will be publicly credited (unless they prefer not to be).
