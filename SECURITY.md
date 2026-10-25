# Security policy

Please report security-sensitive issues privately using the GitHub repository's
**Report a vulnerability** workflow if available, or contact a repository
maintainer without including confidential data in a public issue.

The supported release will be the latest maintained PyPI version. This
repository currently contains unreleased modernization work.

## Threat model

- Bundled data are generated at build time from audited, numeric WHO/CDC CSV.
- The installed wheel only includes non-executable fixed-format LMS binary
  resources, with an explicit format version and linked source SHA-256.
- User-supplied table overrides are strictly parsed as bounded CSV numbers.
- No `eval`, `exec`, pickle/marshal deserialization or downloaded-code
  execution is used for reference loading.
- Trusted custom `GrowthTable` subclasses are Python code and should never
  be loaded from untrusted sources.
- Live network verification is an opt-in maintenance operation, never part of
  growth-score evaluation.
- PyPI publication uses protected GitHub environments and short-lived OIDC
  credentials with signed attestations.

Scientific correctness and adverse interpretations are separate safety
considerations; report suspected reference or formula errors even if they are
not traditional software security vulnerabilities.
