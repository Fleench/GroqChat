# Repository Guide

## Web UI Layout

The web interface served by `server.py` is defined in `static/index.html` and `static/app.js`. It consists of several regions:

- **Side bar** – Contains the chat manager with the **New Chat** button, directory tabs, list of chats and archive controls. The command bar with **Update Key** and **Update Server** buttons is also in this area.
- **Command bar** – Located inside the sidebar, this bar provides the form to update the API key and the button to restart/update the server.
- **Message area** – Displays user and assistant messages for the current chat.
- **Message bar** – The input field and **Send** button used to submit a message.
- **Model bar** – Part of the header that exposes the conversation summary and the system prompt fields.

## File Overview

- **`cli.py`** – Command line interface for chatting with the Groq API. Handles history files, prompt management and various chat commands.
- **`logic.py`** – Shared helper functions and defaults used by the CLI and the web server. Implements reading/writing chat files, exporting chats and prompt management.
- **`server.py`** – FastAPI application that exposes REST endpoints for the web UI. Serves `static/` files and processes chat requests, file management and update actions.
- **`update.py`** – Simple updater that pulls the latest versions of certain files from the GitHub repository and restarts the server.
- **`static/index.html`** – HTML structure and inline CSS for the web interface.
- **`static/app.js`** – Front‑end JavaScript to load chats, send messages and update the page dynamically.
- **`promt.txt`** – Default text used as the system prompt if no other prompt is configured.
- **`requirements.txt`** – Python dependencies required for running the web server and updater.
- **`README.md`** – Usage instructions for both the CLI and web interface.

