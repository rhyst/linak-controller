# Changelog

All notable changes to this project will be documented in this file.

## [Unrelease]

### Changed

- Update aiohttp dependency
- Use poetry for dependency management
- Removed old options from RECIPES.md

## [2.0.1] - 2022-07-27

### Fixed

- Removed unnecessary unsubscribe command that was leftover from previous refactor and causing a `bleak.exc.BleakDBusError: [org.bluez.Error.Failed] No notify session started` error.

## [2.0.0] - 2022-03-08

### Changed

- Replaced `--sit/--stand` commands with a more configurable list of favourites that can be actived with `--move-to <favourite-name>`

## [1.1.0] - 2022-03-08

### Added

- Client/server mode now prints heights on the client as well as the server

### Changed

- Updated to use the REFERENCE_INPUT characteristic which allows you to specify a height to move to. Makes the movement accurate to the millimetre and greatly simplifies code. Inspired by this project: https://github.com/pfilipp/idasen-controller

## [1.0.8] - 2022-01-07

### Added

- Add options allowing configuring base height and movement range (via PR from subraizada3)

### Changed

- Remove redundant scanning code when connecting which should improve time to connection
- Remove pickling code as that was an attempt to speed up the redundant scanning process

### Fixed

- More compatible shebang (via PR from subraizada3)

## [1.0.7] - 2022-01-07

### Changed

- Remove unneeded depenedencies which will hopefully make windows installs a bit smoother.

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
