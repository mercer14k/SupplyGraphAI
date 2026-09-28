# Security policy

The 0.1 line is an experimental local-first analytical demo, not an internet-facing multi-tenant service. Keep bindings on loopback. See `docs/security.md` for the implemented threat model and remaining deployment controls.

Do not post secrets, private supply data or exploit payloads in a public issue. For a vulnerability in a published repository, use GitHub's private vulnerability reporting if the maintainer has enabled it. If unavailable, open an issue asking for a private reporting channel without sensitive details. No response-time or enterprise support guarantee is implied.

Supported scope: latest main branch and the current 0.1 release. Reproduce using synthetic data, identify the affected version and describe the trust boundary crossed. Dependency advisories are checked in CI; third-party runtime/model issues should also be reported upstream.
