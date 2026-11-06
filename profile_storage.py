"""Prepare a new private browser profile without altering existing sessions.

Chrome may be using an existing directory. Leave its permissions and contents
untouched until an operator can safely close the corresponding window.
"""
from pathlib import Path


def ensure_private_profile_dir(root: Path, name: str) -> Path:
    root = Path(root)
    if not name or Path(name).name != name or name in {".", ".."}:
        raise ValueError("invalid browser profile name")
    if root.is_symlink():
        raise RuntimeError("browser profile parent must not be a symlink")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("invalid browser profile parent")

    profile = root / name
    try:
        # For a new directory, 0700 is independent of the caller's umask.
        # Existing directories are never chmod'ed while Chrome may be using them.
        profile.mkdir(mode=0o700)
    except FileExistsError:
        if profile.is_symlink() or not profile.is_dir():
            raise RuntimeError("browser profile is not a real directory")
    return profile
