<!-- Assembled by coding-standards setup.sh — do not edit above the PROJECT-SPECIFIC marker -->

# AGENTS.md

Instructions for OpenAI Codex CLI.

## Environment

- Runs in a sandboxed container with an isolated filesystem.
- Network access may be restricted — do not assume external services are reachable.
- No interactive commands; all operations must be non-interactive and scriptable.

## Behavior

- Read project structure first (`ls`, read key files) before making any changes.
- Apply language-specific conventions by detecting file extensions.
- Run tests after implementation; do not mark a task complete if tests fail.
- Follow TDD for bug fixes and new features: write the failing test first.

## Approval Mode

**Suggest mode (default):** Explain the planned change before editing any file. Wait for confirmation.

**Auto mode:** Make changes directly with atomic commits and Conventional Commits messages (`type(scope): subject`). Each commit must represent one logical change.

## Constraints

- Do not modify generated files, lock files, or CI configuration unless explicitly requested.
- Do not add new dependencies without explaining why and listing alternatives considered.
- Make minimal changes — touch only the files required to satisfy the task.
- No secrets or credentials in any file; check before committing config files.
- If sync-standards reports customized files, pending updates are in `.standards-pending/`. See `.standards/docs/reference/merge-standards-prompt.md` to merge.

## Architecture

Dependencies point inward only: Domain ← Application ← Infrastructure ← Apps.

- **Domain:** Pure business logic. No external dependencies. Entities, value objects.
- **Application:** Orchestrates domain. Defines use cases and repository interfaces.
- **Infrastructure:** Implements interfaces. Handles DB, APIs, file systems.
- **Apps:** Entry points (CLI, web, workers). Depends on all inner layers.

SOLID principles mandatory. Violations require justification in code comments.
Validate inputs at boundaries. Fail fast; reject invalid state immediately.
Define typed custom errors in Domain. No generic exceptions.
Use structured logging with request ID, user ID, and operation context.
Secondary/derived subsystems (mirrors, indexes, sync, telemetry) are best-effort and error-isolated — a failure there must never break the primary write path.
When you catch-and-degrade, preserve and surface the original cause; never swallow it behind a generic "failed" message.

## Testing

TDD is mandatory. Red → Green → Refactor. Write failing tests before implementation code.
Coverage enforced in CI — blocks merge if violated:

- Domain / Core: 100%
- Application / Shell: 95%+
- Infrastructure: 95%+

Every bug fix must include a regression test.
Meet coverage with real tests — never add dead/unreachable branches to hit a number. For genuinely untestable boundaries (real filesystem/keychain/native APIs), keep the boundary thin, push logic into pure testable units, and flag the residual manual-verification step explicitly.
Run the build (e.g. `tsc -b`), not just typecheck — a narrow typecheck config often excludes test files and the project references that the full build compiles, so the build catches errors typecheck misses.
Mirror source structure: `src/domain/user.py` → `tests/domain/test_user.py`
Use descriptive test names: `test_should_raise_error_when_email_is_invalid`
Visual/snapshot baselines: regenerate via a CI dispatch job, never commit from a local run — rendered pixels are environment-specific and local baselines drift from CI.

## Security

P0/P1 block merge. P2 are warnings.

P0 (Critical): Never build SQL from user input — use parameterized queries. Never pass user input to `eval()`, `exec()`, `system()`. Never commit credentials. Never deserialize untrusted data via native serialization. Never ship default credentials. Verify auth on every request.

P1 (High): Encode all HTML output. No `innerHTML` with untrusted data. Validate URLs; block SSRF to internal IPs. Enable CSRF on state-changing endpoints. Secure cookie attributes (`Secure`, `HttpOnly`, `SameSite`). Regenerate session IDs after login. Use cryptographically secure random for tokens. Run dependency CVE scanning in CI. Enforce HTTPS/TLS. Configure CSP, HSTS, X-Content-Type-Options, X-Frame-Options. Never log passwords, tokens, or PII.

P2 (Warning): Missing rate limiting. Verbose errors in production. Unpinned dependencies. Missing encryption at rest.

Secrets scanning: run `git-secrets`, `truffleHog`, or `detect-secrets` in CI.
Add `.env` to `.gitignore`. Provide `.env.example` with placeholder values only.

## Naming Conventions

Use verbose, descriptive names. Avoid abbreviations. Functions are verbs. Classes are nouns.
Boolean variables: `is_`, `has_`, `should_`, `can_` prefixes.
Comments explain "why", never "what".

Python: `snake_case` variables/functions/modules, `PascalCase` classes, `UPPER_SNAKE_CASE` constants, `_leading_underscore` private.
JavaScript/TypeScript: `camelCase` variables/functions, `PascalCase` classes/components/types, `kebab-case` files/dirs, `UPPER_SNAKE_CASE` constants.
Java/Kotlin: `camelCase` methods/variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants, reverse-domain lowercase packages.
Ruby: `snake_case` methods/variables/files, `PascalCase` classes/modules, `?` suffix predicates, `!` suffix dangerous methods.
Rust/Zig: `snake_case` functions/variables, `PascalCase` types/structs/enums, `UPPER_SNAKE_CASE` constants.
Go: `camelCase` unexported identifiers, `PascalCase` exported functions/types/constants; `ALL_CAPS` not used (Go uses `PascalCase` for exported constants); short lowercase package names without underscores.
Elixir: `snake_case` functions/variables/atoms/files, `PascalCase` modules/aliases; `UPPER_SNAKE_CASE` not used (use module attributes `@name` instead); `?` suffix for predicates, `!` suffix for raising variants.

## Git Workflow

Conventional Commits: `type(scope): subject` — types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`.
Subject: imperative mood, ≤50 characters, no period.
Branch naming: `type/description` in kebab-case (e.g., `feature/user-authentication`, `fix/email-validation`).
One task = one branch = one PR. Work is not done until a PR exists. Prefer small, independently mergeable PRs, sequenced/stacked deliberately.
Feature branches from `main`. No direct pushes to `main`. Require one approval; all CI checks must pass.
PR merge loop: run the full local gate (`make ci`) first → open PR → wait for the automated reviewer → address every finding → all checks green (a partial pass is a fail) → squash-merge + delete branch. Never merge on a partial pass or before the automated review runs.
Run `gh pr create` from the feature worktree (or pass `--head`); the cwd's branch is what it opens.
Stacked PRs: retarget dependents to `main` before merging+deleting a base branch, or the dependents get closed.
Delete branches immediately after merge. Keep fewer than 10 active branches.
Never commit: secrets, build artifacts, `node_modules/`, `.env`, IDE files, OS files.
Always commit lock files (`package-lock.json`, `Gemfile.lock`, `Cargo.lock`, `uv.lock`).

## Documentation

Document all public APIs with language-standard formats (JSDoc, docstrings, rustdoc, JavaDoc, YARD). Include parameters, return values, errors, and examples.
Comments explain "why", never "what". Self-documenting code preferred.
Every package and app must have a README: purpose, installation, usage, configuration, development.
Create an ADR in `docs/adr/` for decisions affecting structure, dependencies, or significant technical choices.
Maintain `CHANGELOG.md` (Keep a Changelog format); update it for every user-facing change in a PR — UNLESS the project uses release automation (semantic-release, release-please, Changesets). With automation, release notes are generated (from Conventional Commits for commit-driven tools, or from per-PR changeset fragments for Changesets): do NOT hand-edit a shared `## [Unreleased]` block per PR (it causes merge conflicts under parallel work); rely on the generated notes or changeset fragments.
Track all work as GitHub Issues. Every `TODO`/`FIXME` must reference an issue: `# TODO(#42): description`.

<!-- BEGIN PROJECT-SPECIFIC — DO NOT EDIT THIS LINE -->

<!-- Add project-specific instructions below this line. This section is preserved across re-assembly. -->

## OpenSCAD native prototype
- The user's implementation authorization enables direct changes, dependency installation, public repository creation, pushes and PRs. Never merge automatically.
- Keep Dust3D checkouts untouched. Preserve upstream OpenSCAD history, reference sources, fixtures, licenses and formatting.
- Native engine targets require HEADLESS=ON and NULLGL=ON. Never link Qt/OpenGL. Export fast CSG leaves and Boolean operations; a final mesh alone is not preview parity.
- Use Swift 6 strict concurrency, SwiftUI, Metal and SwiftPM. Main-actor presentation; isolated portable worker for compilation. Copy and validate worker output before presentation.
- Follow TDD. Measure new boundary coverage separately from inherited engine coverage. Run make ci and inspect actual rendered UI; document unverified behavior honestly.
- See docs/adr/0001-native-preview.md, docs/acceptance.md and docs/coding-standards-audit.md.

## Portable native OpenSCAD core
- The user authorizes direct implementation, tools/dependency installation, implementation-branch pushes and PR creation. Never merge automatically.
- Preserve upstream history, Qt reference application, regression fixtures and licenses. Do not edit any Dust3D checkout.
- Native preview requires HEADLESS=ON and NULLGL=ON. Preserve fast-preview CSG leaves and operations. A final Boolean mesh is not equivalent.
- Preserve upstream C++17, identifiers and .clang-format. Format only new adapter files. Use RAII, bounds/finite checks, bounded input and caught exceptions at the process boundary.
- One compilation request per worker process isolates globals, buffers and cancellation. No in-process concurrency or borrowed-pointer guarantees are implied.
- Follow TDD. Run python3 native/tests/test_preview.py build-native/openscad-preview-worker. Instrument new boundary coverage separately from inherited engine coverage.
- See native/README.md, native/cpp-standards.md and native/coding-standards-audit.md. Apple UI and renderer belong in dalbrecht/openscad-apple.
