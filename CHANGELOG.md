# Changelog

All notable changes to this project will be documented in this file.

## [1.0.6] - 2021-03-30

### Changed

- Changed check for pickling connection to `IS_LINUX` after confirmation that you cannot pickle OSX bluetooth connection objects.

## [1.0.5] - 2021-02-11

### Changed

- Fix `--scan-timeout` flag.

## [1.0.4] - 2021-02-11

### Changed

- Ensure mac addresses are upper case because apparently this matters on some devices.

## [1.0.3] - 2021-02-11

### Changed

- Fix to prevent the script from hiding connection errors on subsequent failed attempts.

## [1.0.2] - 2021-01-27

No changes, just a reupload to fix bad Pypi upload of 1.0.1.

## [1.0.1] - 2021-01-27

### Added

- This changelog.

### Changed

- Script will retry connection if it fails with a pickled connection. This will help in situations where the adapter name changes for example.

## [1.0.0] - 2021-01-27

### Added

- Initial pip release.
