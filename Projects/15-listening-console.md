# Social Media Listening Tools ("Listening Console") — Multi-platform social listening & reply console

> **Status**: Active Development
> **Last Updated**: 2026-09-11

## Business Context
- **Client**: internal / own tool
- **Status**: active
- **Priority**: medium
- **Revenue Model**: not yet decided
- **Deployed**: No

## Overview
- **Root**: `Downloads/Social Media Listening Tools/Social Media Listening Tools`
- **Not to be confused with** [12-social-listening](./12-social-listening.md) — the R&D build at
  `Desktop/Codex Lure/project/RND DayThree/...` on Laravel 13. Same idea, **separate codebase**.
- **Stack**: Laravel 12 + PHP 8.2+ + Inertia 3.3 + Vue 3.5 + AdminLTE 4 + Bootstrap 5.3 + ApexCharts, Vite 8
- **Type**: social listening / monitoring console
- **Auth**: session (single operator; **single-tenant, one account per platform** — `social_accounts` has a
  unique index on `social_platform_id` and no `user_id` column, recorded as OQ-01)
- **Database**: MySQL, `listening_console`
- **Registered in CS**: 2026-09-11. **Not bound** — no `.coresentinel/` in the repo, so no context packs
  or gate ledger. `coresentinel init` would bind it.

## Overview — what it does
Six platform connectors behind one provider contract (`app/Services/Social/`): **x, youtube, facebook,
instagram, threads, linkedin**. Keyword/hashtag discovery feeds a mentions queue; Live Search is the
operator's one-off query; some platforms support replying. Credentials are entered per platform in
Settings and stored **encrypted** (`social_credentials.secrets`, `encrypted:array`), never in `.env` —
only non-secret host/version config lives in `config/services.php`.

## Key Patterns
- **One HTTP door per vendor.** `Meta\MetaClient` centralises Meta's error format for Facebook,
  Instagram and Threads; each provider does its own normalisation. Error codes map to typed
  exceptions whose *retry policy* is the point (`CredentialExpired` / `RateLimited` /
  `PermissionDenied` / `ProviderUnavailable`).
- **Capability by interface, not by list.** `SupportsLiveSearch`, `SupportsHashtagDiscovery`,
  `SupportsMentionReplies` — `ProviderRegistry` resolves on `instanceof`, so no caller keeps a list
  of which platforms can do what.
- **`ProviderRegistry` is the only place a credential is decrypted.** One file to audit.
- Both entries under *Third-Party Grants & Token Lifecycles* in
  [Pattern Library](../11-pattern-library.md) came from this project.

## Completed
1. Six providers, discovery + Live Search + mentions queue + reply dispatch
2. YouTube channel OAuth (`YouTubeOAuthService`) — the only full OAuth flow in the app
3. **Threads connection settled (2026-09-11)** — scope/expiry/user-id read from
   `debug_token`, plus `threads:refresh-token` scheduled daily. Branch `feat/threads-connection`.

## Remaining
- **Threads OAuth** — the operator still pastes the first token by hand; `app_id` / `app_secret`
  are collected and **unused** until an authorize→code→exchange flow exists.
- **First live Verify against a real Threads app.** Everything is tested against fakes; this
  project holds no approved Threads grant, so the `debug_token` path is unproven in anger.
- `MentionReplyTest` ×2 failing on `main` ("Not a valid Inertia response") — pre-existing,
  reproduced on a clean tree 2026-09-11, **not yet diagnosed**.
- Facebook/Instagram capability rows still marked `RequiresVerification` in `Platforms.php`.

## Anti-Patterns (This Project)
- **A settings field wired to the wrong store.** See the entry of that name in
  [55-self-evolution.md](../55-self-evolution.md). `keyword_search_granted` was read from settings
  by the provider and displayed from credentials by the screen, so it rendered blank forever while
  governing whether Threads search saw the public web. One missing `'store' => 'setting'`.
- **Never trust a Meta 200.** Threads `keyword_search` returns success with a near-empty array when
  `threads_keyword_search` was not approved. Instagram and Facebook forbid writing to content found
  by searching; Threads does not. These differences are per-platform and must not be generalised.
- Meta's own docs are inconsistent on host: OAuth pages use `graph.threads.com`, token and search
  pages use `graph.threads.net`. **Both work** (their Overview says so). Kept in config as
  `META_THREADS_HOST` so the inconsistency lives in one place.

## Work Log
### 2026-09-11 — Threads connection (T2)
- `debug_token` read-back: real scope list, `expires_at`, `user_id`. Meta's answer overrules the
  operator's assertion, with a test asserting exactly that.
- `ThreadsTokenService` + `threads:refresh-token` (daily 03:15) for the 60-day expiry.
- Fixed the dead `keyword_search_granted` control; added `granted_scopes` and `token_expires_at`
  readonly rows.
- No migration — discovered facts go to `social_accounts.settings`, user id to `external_id`.
- 59 tests in area, 318 across the suite. `coresentinel review` APPROVED, secret scan clean.
