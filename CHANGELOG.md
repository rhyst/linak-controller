# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] - 2025-xx-xx

### Breaking

If using the http or tcp server the JSON payload should now be a `command` object and not a `config` object:

```bash
# HTTP
curl -X POST http://127.0.0.1:9123 --data '{"key": "move_to", "value": 640}'

# TCP
echo '{"key": "move_to", "value": 640}' | nc -w 1 127.0.0.1 9123
```

### Changed

- Refactor global config and command to fix [100](https://github.com/rhyst/linak-controller/issues/100) and [85](https://github.com/rhyst/linak-controller/issues/85)

### Fixed 

- Server port argument [99](https://github.com/rhyst/linak-controller/pull/99) by @gomi-source
- Allow using FIFO as config file [101](https://github.com/rhyst/linak-controller/pull/101) by @jayrhynas


## [1.2.0] - 2024-12-03

### Added 

- Added http endpoint in addition to web socket endpoint in server mode

### Changes

- Added support for Python 3.13
- Update bleak dependency

## [1.1.1] - 2023-12-01

### Changed

- Removed redundant move to method

### Fixed

- Configurable move command period should allow float [76](https://github.com/rhyst/linak-controller/pull/76) by @tomsb
- Fixed "ValueError: Characteristic notifications already started" [77](https://github.com/rhyst/linak-controller/issues/77)

## [1.1.0] - 2023-11-03

### Added

- Configurable move command period (relating to [48](https://github.com/rhyst/linak-controller/issues/48))

### Changed

- Removed redundant move timeout config

## [1.0.3] - 2023-11-01

### Added

- Docker recipe by @voruti

### Fixed

- Fixed stuttering issues [48](https://github.com/rhyst/linak-controller/issues/48) by @tomsb

## [1.0.2] - 2023-10-31

### Changed

- Copy config from old config location if it exists and new one does not

### Fixed

- Swapped `|` operator for `Union` in `gatt.py` to fix python 3.8 compatibility

## [1.0.1] - 2023-10-31

### Changed

- Added `idasen-controller` as a script to maintain some backwards compatibility

## [1.0.0] - 2023-10-31

Rename `idasen-controller` to `linak-controller`.

---

This package was previously named `idasen-controller`

## [2.2.0] - 2023-10-31

Final release of `idasen-controller` to point at renamed packaged `linak-controller`.

## [2.1.0] - 2023-10-31

### Added

- Add setting a user ID on first connection to support DPG1C and DPG1M
- Allow fetching base height from desk by setting config value to null

### Changed

- Python version changed to >=3.8 <3.13 to satisfy dependencies
- Bleak updated to 0.21.1
- Refactor into seperate files and helper classes
- Removed `print-exceptions` option
- Removed max height option as it was unused
- Removed movement range option as it was unused

## [2.0.2] - 2023-03-13

### Changed

- Update aiohttp dependency to 3.8.4
- Update bleak dependency to 0.19.5
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
