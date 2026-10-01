# CleanC integration with Ziqva AppCenter

Status: implementation awaits the backend source and deployment configuration.
CleanC currently has a website link, not an authenticated AppCenter session.
User decision: all application features require login, including GUI and CLI.
Only login, login retry, and application exit remain available without a session.

## Architecture

CleanC is a distributed Windows desktop client. It opens the system browser for
login. The confidential OAuth client runs on the backend that owns
https://zumo.ziqva.com/login-callback. The client secret and OAuth refresh tokens
stay on that server. No shared client secret may be bundled in the EXE.

CleanC receives an opaque, revocable application session through a short-lived
single-use handoff bound to a random secret held by the initiating desktop
instance. Browser callback state alone must not authorize desktop session pickup.
Desktop session credentials are stored using Windows DPAPI, never plaintext.
The backend persists sessions and login transactions with expiry and atomic
single-use consumption; it must work across multiple processes and restarts.

## Tasks and acceptance criteria

1. Configuration and OAuth helper: load the supplied issuer, client ID, exact
   redirect URI, scopes and server-held secret; HTTPS timeouts, no credential
   logging, bounded JSON responses, explicit error handling.
2. Login initiation: create cryptographically random state and transaction
   credentials; bind state to the initiating transaction; enforce expiry, polling
   limits and one active transaction per attempt. Use PKCE S256 only after
   verifying server support; PKCE does not turn a distributed EXE into a
   confidential client.
3. Callback: validate state, reject missing/duplicate parameters and replay,
   exchange code server-side, retrieve userinfo and expose only required profile
   fields. Obtain a stable user identifier from the provider; display name or
   email alone must not serve as an unverified account-linking key.
4. Sessions: issue an opaque application session to the bound desktop instance;
   hash session credentials at rest on the backend, encrypt provider tokens and
   persist desktop credentials with DPAPI. Never put bearer tokens in browser URLs.
5. Refresh and expiry: verify the provider's refresh-token grant contract before
   implementation; serialize refresh, handle rotation and revoked credentials,
   use returned expires_in and clear expired local sessions.
6. Logout: revoke access and refresh tokens using the provider's actual client
   authentication requirements; invalidate the backend session and local DPAPI
   storage; perform browser logout only with a provider-approved return URI.
   Report revocation failures without presenting them as successful global logout.
7. GUI and guards: login/logout controls, account display, asynchronous network
   work and actionable errors. Login is mandatory. Enforce access consistently
   in both GUI and CLI entry points, including scan, cleanup, storage exploration
   and process-control operations. Restore a valid persisted session on startup;
   expired or revoked sessions return to login. Recheck authorization before
   starting destructive work. Define network-failure behavior explicitly so
   cached profile information alone cannot unlock operations.

## Inputs still required

- Backend repository/path, framework, database and deployment access/configuration.
- Ownership/routing of the registered zumo.ziqva.com callback for this client.
- Actual client secret configured privately on the server.
- Confirmed refresh grant, PKCE support, stable user ID, revocation authentication
  and allowed logout redirect contract.

## Validation

Test successful login, denied consent, invalid/expired/replayed state, handoff
theft/replay, provider/network errors, simultaneous refresh, token rotation,
expiry, logout failures, DPAPI persistence and guards. Run an end-to-end login
against the deployed backend, then rebuild and smoke-test the portable EXE.

References: https://www.rfc-editor.org/rfc/rfc8252.html and
https://www.rfc-editor.org/rfc/rfc6749.html.
