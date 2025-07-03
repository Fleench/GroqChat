"""Simple self updater used by the server and CLI.

This script pulls the latest versions of selected files from the
GitHub repository and overwrites the local copies.  It is intentionally
minimal so that it can be run from both the web UI and the command line.
"""

import os
import subprocess
import sys
import requests

from typing import Optional


# Base URL to the raw files in the repository
GITHUB_REPO_URL = "https://raw.githubusercontent.com/Fleench/GroqChat/main/"

# Files that should be refreshed when an update is triggered.  The
# paths are relative to the repository root.
LOCAL_FILE_PATHS = [
    "logic.py",
    "server.py",
    "static/index.html",
    "static/app.js",
    # Include this script so it stays up to date as well
    "update.py",
    # Keep dependencies in sync
    "requirements.txt",
]


def fetch_file_from_github(file_path: str) -> Optional[bytes]:
    """Retrieve the latest version of ``file_path`` from GitHub."""

    url = f"{GITHUB_REPO_URL}{file_path}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Failed to fetch {file_path}: {exc}")
        return None
    return response.content


def update_local_file(file_path: str) -> bool:
    """Overwrite ``file_path`` with the version fetched from GitHub."""

    fetched_file = fetch_file_from_github(file_path)
    if fetched_file is None:
        print(f"Skipped updating {file_path}")
        return False
    with open(file_path, "wb") as f:
        f.write(fetched_file)
    return True


def update_all_files() -> None:
    """Update each file listed in ``LOCAL_FILE_PATHS``."""

    for file_path in LOCAL_FILE_PATHS:
        if update_local_file(file_path):
            print(f"Updated {file_path}")


def install_requirements() -> None:
    """Install dependencies listed in ``requirements.txt``."""

    req_file = "requirements.txt"
    if not os.path.exists(req_file):
        return
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_file],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Failed to install dependencies: {exc}")


if __name__ == "__main__":
    # When executed directly, update the files and notify the user.
    update_all_files()
    install_requirements()
    print("Update complete!")
