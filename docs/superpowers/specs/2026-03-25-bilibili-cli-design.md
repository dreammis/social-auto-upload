# Bilibili CLI Design

Date: 2026-03-25

## Summary

This design adds a `bilibili` platform branch under `sau` with the same user-facing shape as the existing `douyin` and `kuaishou` commands.

The key constraint is that users should not need to install `biliup` manually. The project will treat `biliup` as an internal runtime dependency:

- `sau bilibili ...` is the public entrypoint
- the program auto-downloads `biliup` when missing
- the program checks GitHub Releases on each run
- when a newer upstream release exists, the program auto-updates first and then continues

This design intentionally keeps the wrapper thin. It reuses the current Bilibili uploader semantics already present in the repository instead of inventing a brand-new parameter model.

## Goals

- Keep the user-facing CLI consistent with `sau douyin ...` and `sau kuaishou ...`
- Hide `biliup` installation from users
- Reuse current project concepts such as account files, `VideoZoneTypes`, scheduled publish, and existing example semantics
- Avoid over-abstracting the Bilibili integration

## Non-Goals

- Do not vendor `biliup` binaries into the repository
- Do not pin or maintain a local release manifest in the first version
- Do not add note/image publishing for Bilibili in the first version
- Do not redesign the existing Bilibili uploader domain model beyond what is needed for CLI integration

## Existing Project Context

The repository already has native Bilibili support:

- `uploader/bilibili_uploader/main.py` wraps `biliup.plugins.bili_webup`
- `examples/upload_video_to_bilibili.py` uses existing upload semantics
- `utils/constant.py` already defines `VideoZoneTypes`

The current local upload model is centered on:

- `file`
- `title`
- `desc`
- `tid`
- `tags`
- `dtime`

This design keeps that shape for the first CLI version.

## User-Facing CLI

### Supported commands

- `sau bilibili login`
- `sau bilibili check`
- `sau bilibili upload-video`

### Command contract

#### `sau bilibili login`

Purpose:

- ensure `biliup` is present and up to date
- trigger Bilibili login through `biliup`
- store account data using the project account-file convention

First version behavior:

- if `biliup` is missing, auto-download latest release
- if upstream has a newer release, auto-update first
- then invoke the login flow

#### `sau bilibili check`

Purpose:

- ensure `biliup` is present and up to date
- validate whether the configured Bilibili account is usable

First version behavior:

- combines local account-file presence with a practical `biliup`-based validation path
- keeps output simple and aligned with other platforms:
  - `valid`
  - `invalid`

#### `sau bilibili upload-video`

Purpose:

- ensure `biliup` is present and up to date
- upload one Bilibili video using the current repository semantics

First version parameters:

- `--account` required
- `--file` required
- `--title` required
- `--desc` required
- `--tid` required
- `--tags` optional
- `--schedule` optional

Decision:

- `tid` is required in v1
- this matches the current project model and avoids guessing a default zone

## Runtime Dependency Strategy

### Chosen strategy

`biliup` is not committed into this repository and is not a user-managed prerequisite.

Instead, `sau bilibili ...` automatically manages it at runtime:

1. locate local `biliup`
2. query upstream GitHub Release state
3. if missing or outdated, download latest release
4. replace local runtime copy
5. continue current command

### Why this strategy

- keeps repository size small
- removes manual installation burden from users
- preserves a single public entrypoint through `sau`
- avoids `git submodule`, which is not useful for release assets

### Trade-off accepted

This design intentionally accepts upstream instability risk:

- every run checks for updates
- a new upstream release may change CLI behavior
- the wrapper must therefore stay thin and resilient

This trade-off was explicitly accepted in exchange for lower maintenance overhead.

## Storage and Resolution

The implementation should use a local runtime tool cache instead of shipping binaries in git.

The exact cache directory can remain implementation-defined, but it should satisfy:

- writable by the current user
- reusable across commands
- isolated from source-controlled files

The resolver should be responsible for:

- discovering the current OS
- choosing the correct upstream release asset
- downloading and replacing the executable
- returning the resolved executable path

## Thin Wrapper Architecture

The wrapper should stay minimal and split responsibilities into only a few pieces:

### 1. Resolver

Responsibilities:

- check whether `biliup` exists locally
- query upstream release metadata
- download/update executable when needed
- return executable path

### 2. Runner

Responsibilities:

- invoke the resolved `biliup` executable
- collect exit code, stdout, and stderr
- convert obvious process failures into project-friendly runtime errors

### 3. CLI adapter in `sau_cli.py`

Responsibilities:

- parse `sau bilibili ...` arguments
- map them to the Bilibili runtime invocation
- keep help text consistent with existing platform subcommands

No deeper abstraction layers are required in v1.

## Mapping to Existing Project Concepts

The wrapper should align with existing repository behavior instead of inventing a second Bilibili model.

### Account files

The Bilibili branch should use the same account alias concept as other platforms:

- user passes `--account <name>`
- the project resolves the corresponding account file path

### Categories

`tid` remains a first-class parameter.

The existing `VideoZoneTypes` enum should stay reusable for:

- examples
- documentation
- future helper utilities

### Scheduling

`--schedule` should follow the same `sau` convention already used by other platforms:

- no `--schedule` means immediate publish
- providing `--schedule` means scheduled publish

The internal translation to Bilibili-specific runtime arguments happens inside the adapter layer.

## Error Handling

The wrapper should prefer simple, direct failure modes:

- download failure: clearly state that `biliup` auto-download failed
- update failure: clearly state that the latest release could not be prepared
- login failure: surface `biliup` login failure with project context
- check failure: return `invalid`
- upload failure: return non-zero and show the upstream error summary

The wrapper should not attempt to over-normalize all upstream error text in v1.

## Documentation Impact

When implemented, the following documentation should be updated:

- `README.md`
- `docs/CLI.md`
- install/update documentation
- a Bilibili skill similar to the Douyin/Kuaishou skills
- Bilibili example scripts

The user-facing messaging should consistently say:

- users interact with `sau bilibili ...`
- `biliup` is prepared automatically by the program

## Testing Strategy

Minimum verification expected once implemented:

- `sau bilibili login --account <name>`
- `sau bilibili check --account <name>`
- `sau bilibili upload-video ...`
- missing-runtime path triggers auto-download
- existing-runtime path reuses local binary
- outdated-runtime path updates before executing

Manual verification is acceptable for first integration because upstream login and upload are external-platform behaviors.

## Recommended Implementation Order

1. add `bilibili` subcommands to `sau_cli.py`
2. add a minimal resolver that can fetch/update `biliup`
3. add a minimal runner for subprocess execution
4. wire `login/check/upload-video`
5. update docs, examples, and skill definitions

## Final Decisions

- Public entrypoint stays `sau bilibili ...`
- First version supports `login`, `check`, and `upload-video`
- `tid` is required
- `biliup` is auto-downloaded
- every run checks GitHub Releases
- if a newer release exists, auto-update first and continue
- wrapper remains intentionally thin
