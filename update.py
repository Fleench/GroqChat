import requests
import os

# Set the GitHub repository URL
GITHUB_REPO_URL = "https://raw.githubusercontent.com/your-username/your-repo-name/main/"

# Set the local file paths
LOCAL_FILE_PATHS = [
    "logic.py",
    "server.py",
    "static/index.html",
    "static/app.js",
    "update.py"  # Add the update script itself to the list
]

# Function to fetch the latest file from GitHub
def fetch_file_from_github(file_path):
    url = f"{GITHUB_REPO_URL}{file_path}"
    response = requests.get(url)
    return response.content

# Function to update the local file
def update_local_file(file_path):
    fetched_file = fetch_file_from_github(file_path)
    with open(file_path, "wb") as f:
        f.write(fetched_file)

# Function to update all local files
def update_all_files():
    for file_path in LOCAL_FILE_PATHS:
        update_local_file(file_path)
        print(f"Updated {file_path}")

# Run the update script
if __name__ == "__main__":
    update_all_files()
    print("Update complete!")
