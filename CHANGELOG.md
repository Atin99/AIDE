# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added

- Added baseline repository docs:
  - `README.md`
  - `CONTRIBUTING.md`
  - `CHANGELOG.md`
- Added baseline runtime ML model artifacts to `ml/models` for out-of-the-box prediction support.

### Changed

- Interactive Composition Editor now defaults to full 42-domain sweep.
- Fast subset mode is now explicitly opt-in with clearer labeling.
- Fast subset slider now defaults to a broader coverage when enabled.

### Fixed

- Reduced risk of silently excluding low-weight domains during close-composition comparisons by showing explicit warning when subset mode is active.
