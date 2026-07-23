# Changelog

All notable changes to this project are documented here.

## [0.2] - 2026-07-23

### Added

- 63-case endpoint quality, security, robustness, performance, UX and data checklist.
- GitHub issue forms, pull request template and Dependabot configuration.
- Regression coverage for browser API header merging.

### Changed

- Demo credentials use PBKDF2-HMAC-SHA256 hashes with per-user salts.
- State migration removes legacy plaintext password fields.
- Audit logs redact sensitive fields before persistence.
- Unknown API paths return a consistent 404 response.
- Documentation reflects the PythonAnywhere deployment and current security model.

### Fixed

- Custom fetch options no longer overwrite Authorization or CSRF headers.
- Invalid DOCX input types return a controlled client error.

## [0.1] - 2026-07-01

- Initial authenticated project management release.
