"""Simple self updater used by the server and CLI.

This script pulls the latest versions of selected files from the
GitHub repository and overwrites the local copies.  It is intentionally
minimal so that it can be run from both the web UI and the command line.
"""

import os
import requests


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
]


def fetch_file_from_github(file_path: str) -> bytes:
    """Retrieve the latest version of ``file_path`` from GitHub."""

    url = f"{GITHUB_REPO_URL}{file_path}"
    response = requests.get(url)
    return response.content


def update_local_file(file_path: str) -> None:
    """Overwrite ``file_path`` with the version fetched from GitHub."""

    fetched_file = fetch_file_from_github(file_path)
    with open(file_path, "wb") as f:
        f.write(fetched_file)


def update_all_files() -> None:
    """Update each file listed in ``LOCAL_FILE_PATHS``."""

    for file_path in LOCAL_FILE_PATHS:
        update_local_file(file_path)
        print(f"Updated {file_path}")


if __name__ == "__main__":
    # When executed directly, update the files and notify the user.
    update_all_files()
    print("Update complete!")
