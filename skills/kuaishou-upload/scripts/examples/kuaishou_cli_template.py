from __future__ import annotations

import shlex
import subprocess


def run_command(command: list[str]) -> None:
    print("Running:", " ".join(shlex.quote(part) for part in command))
    subprocess.run(command, check=True)


def main() -> None:
    account = "account_a"
    # account_name is user-defined. One account_name maps to one account file.
    # You can prepare multiple account names and run them in parallel.

    commands = [
        ["sau", "kuaishou", "login", "--account", account],
        ["sau", "kuaishou", "check", "--account", account],
        [
            "sau",
            "kuaishou",
            "upload-video",
            "--account",
            account,
            "--file",
            "videos/demo.mp4",
            "--title",
            "Kuaishou video from Python",
            "--desc",
            "Kuaishou video description from Python",
            "--tags",
            "cli,video",
            "--thumbnail",
            "videos/demo.png",
            "--headless",
        ],
        [
            "sau",
            "kuaishou",
            "upload-note",
            "--account",
            account,
            "--images",
            "videos/1.png",
            "videos/2.png",
            "videos/3.png",
            "--title",
            "Kuaishou note title from Python",
            "--note",
            "Kuaishou note from Python",
            "--tags",
            "cli,note",
            "--headless",
        ],
    ]

    for command in commands:
        run_command(command)


if __name__ == "__main__":
    main()
