"""FastAPI server exposing the GroqChat web interface and REST API."""

from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import json
import shutil
from datetime import datetime
import subprocess
import sys
import threading
from dotenv import load_dotenv, set_key

# Load variables from .env first and fall back to system environment values
load_dotenv(override=True)

import logic

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')


@app.middleware("http")
async def verify_app_key(request: Request, call_next):
    """Optional header based authentication for production deployments."""
    if not DEV_MODE:
        required_key = os.getenv("APP_KEY", "your_app_key")
        if required_key and request.headers.get("x-app-key") != required_key:
            raise HTTPException(status_code=403, detail="Invalid or missing app key")
    response = await call_next(request)
    return response

# Prepare the chat environment and start a session on startup
logic.ensure_directories()
client = logic.setup_client()
MODEL = logic.MODEL
chat_data, active_filename = logic.get_new_session_state()
messages = chat_data["messages"]


def summarize(messages):
    """Return a short summary of the most recent conversation history."""

    recent = messages[-logic.SUMMARY_HISTORY_LIMIT:]
    convo = "\n".join(
        f"{m['role']}: {m['content']}" for m in recent if m['role'] != 'system'
    )
    summary_messages = [
        {"role": "system", "content": logic.SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": f"Summarize the following conversation:\n{convo}"},
    ]
    completion = client.chat.completions.create(
        messages=summary_messages,
        model=MODEL,
        temperature=0.7,
        top_p=1,
        max_tokens=logic.SUMMARY_MAX_TOKENS,
    )
    return completion.choices[0].message.content


def search_messages(messages, term):
    """Return list of message strings containing the search term."""

    term = term.lower()
    results = []
    for i, m in enumerate(messages[1:], start=1):
        if term in m["content"].lower():
            results.append(f"{i}: {m['role']} - {m['content']}")
    return results


def list_chats():
    """Return a mapping of chat directories to available chat files."""

    data = {}
    if not os.path.exists(logic.CHAT_HISTORY_DIR):
        return data
    for d in os.listdir(logic.CHAT_HISTORY_DIR):
        path = os.path.join(logic.CHAT_HISTORY_DIR, d)
        if os.path.isdir(path):
            chats = []
            if d == 'archive':
                for root, _, files in os.walk(path):
                    for fname in files:
                        if not fname.endswith('.chat'):
                            continue
                        fpath = os.path.join(root, fname)
                        rel = os.path.relpath(fpath, logic.CHAT_HISTORY_DIR)
                        try:
                            with open(fpath, 'r') as f:
                                j = json.load(f)
                            name = j.get('name', os.path.splitext(fname)[0]) if isinstance(j, dict) else os.path.splitext(fname)[0]
                        except Exception:
                            name = os.path.splitext(fname)[0]
                        chats.append({'file': rel, 'name': name})
            else:
                for fname in os.listdir(path):
                    if not fname.endswith('.chat'):
                        continue
                    fpath = os.path.join(path, fname)
                    try:
                        with open(fpath, 'r') as f:
                            j = json.load(f)
                        name = j.get('name', os.path.splitext(fname)[0]) if isinstance(j, dict) else os.path.splitext(fname)[0]
                    except Exception:
                        name = os.path.splitext(fname)[0]
                    chats.append({'file': os.path.join(d, fname), 'name': name})
            data[d] = chats
    return data


def archive_file(relpath: str) -> bool:
    """Move a chat file to the archive and record its original location."""
    src = os.path.join(logic.CHAT_HISTORY_DIR, relpath)
    if not os.path.exists(src) or relpath.startswith("archive/"):
        return False
    try:
        with open(src, "r") as f:
            data = json.load(f)
        data["archived_from"] = relpath
        with open(src, "w") as f:
            json.dump(data, f, indent=2)
        subdir = os.path.dirname(relpath)
        dest_dir = os.path.join(logic.ARCHIVE_DIR, subdir)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, os.path.basename(relpath))
        if os.path.exists(dest):
            base, ext = os.path.splitext(os.path.basename(relpath))
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            dest = os.path.join(dest_dir, f"{base}-{ts}{ext}")
        shutil.move(src, dest)
        return True
    except Exception:
        return False


def restore_file(relpath: str) -> bool:
    """Restore a chat from the archive to its original location."""
    subpath = relpath[len("archive/"):] if relpath.startswith("archive/") else relpath
    src = os.path.join(logic.ARCHIVE_DIR, subpath)
    if not os.path.exists(src):
        return False
    try:
        with open(src, "r") as f:
            data = json.load(f)
        dest_rel = data.get("archived_from", os.path.join("userchat", os.path.basename(relpath)))
        dest = os.path.join(logic.CHAT_HISTORY_DIR, dest_rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        data.pop("archived_from", None)
        with open(src, "w") as f:
            json.dump(data, f, indent=2)
        shutil.move(src, dest)
        return True
    except Exception:
        return False


def delete_file(relpath: str) -> bool:
    """Delete a chat file from the archive."""
    subpath = relpath[len("archive/"):] if relpath.startswith("archive/") else relpath
    path = os.path.join(logic.ARCHIVE_DIR, subpath)
    if not os.path.exists(path):
        return False
    try:
        os.remove(path)
        return True
    except Exception:
        return False


def clear_archive() -> bool:
    """Remove all chat files from the archive directory."""
    success = True
    if not os.path.exists(logic.ARCHIVE_DIR):
        return True
    for root, _, files in os.walk(logic.ARCHIVE_DIR):
        for fname in files:
            if not fname.endswith('.chat'):
                continue
            path = os.path.join(root, fname)
            try:
                os.remove(path)
            except Exception:
                success = False
    return success


def handle_command(user_input):
    """Process a slash command from the UI and return a response dict."""

    global chat_data, messages, active_filename, MODEL
    parts = user_input.split()
    cmd = parts[0]
    if cmd == '/new':
        chat_data, active_filename = logic.get_new_session_state()
        messages = chat_data['messages']
        return {
            "system": (
                f"New chat started: {chat_data['name']}. Autosave file will be "
                f"created at '{os.path.join(logic.CHAT_HISTORY_DIR, active_filename)}' "
                "after your first message"
            )
        }
    elif cmd == '/save':
        if len(parts) < 2:
            return {"error": "Usage: /save <name>"}
        name = parts[1]
        if not name.endswith('.chat'):
            name += '.chat'
        full = os.path.join('userchat', name)
        success, path = logic.save_chat_to_file(full, chat_data)
        if success:
            active_filename = full
            return {"system": f"Chat saved to {path}"}
        return {"error": "Could not save chat"}
    elif cmd == '/load':
        if len(parts) < 2:
            return {"error": "Usage: /load <name>"}
        name = parts[1]
        if not name.endswith('.chat'):
            name += '.chat'
        loaded, loaded_path = logic.load_chat_from_file(name)
        if loaded:
            chat_data = loaded
            messages = chat_data['messages']
            active_filename = loaded_path or name
            return {"system": f"Chat '{chat_data['name']}' loaded"}
        return {"error": f"File {name} not found"}
    elif cmd == '/chats':
        return {"chats": list_chats()}
    elif cmd == '/system':
        if len(parts) < 2:
            return {"error": "Usage: /system <prompt>"}
        new_prompt = " ".join(parts[1:])
        chat_data['messages'][0] = {"role": "system", "content": new_prompt}
        logic.save_chat_to_file(active_filename, chat_data)
        return {"system": "System prompt updated"}
    elif cmd == '/prompt':
        if len(parts) < 2:
            return {"error": "Usage: /prompt <new|use|list|sys>"}
        action = parts[1]
        if action == 'new':
            if len(parts) < 4:
                return {"error": "Usage: /prompt new <name> <text>"}
            name = parts[2]
            text = " ".join(parts[3:])
            success, path = logic.save_prompt(name, text)
            if success:
                return {"system": f"Prompt '{name}' saved to {path}"}
            return {"error": f"Could not save prompt {name}"}
        elif action == 'list':
            names = logic.list_prompts()
            return {"prompts": names}
        elif action == 'use':
            if len(parts) < 3:
                return {"error": "Usage: /prompt use <name>"}
            name = parts[2]
            text = logic.load_prompt(name)
            if text is None:
                return {"error": f"Prompt {name} not found"}
            messages.append({"role": "user", "content": text})
            logic.save_chat_to_file(active_filename, chat_data)
            completion = client.chat.completions.create(
                messages=messages[-logic.HISTORY_LIMIT:],
                model=MODEL,
                temperature=0.7,
                top_p=1,
            )
            assistant_response = completion.choices[0].message.content
            messages.append({"role": "assistant", "content": assistant_response})
            logic.save_chat_to_file(active_filename, chat_data)
            return {"assistant": assistant_response}
        elif action in ('sys', 'system'):
            if len(parts) < 3:
                return {"error": "Usage: /prompt sys <name>"}
            name = parts[2]
            text = logic.load_prompt(name)
            if text is None:
                return {"error": f"Prompt {name} not found"}
            chat_data['messages'][0] = {"role": "system", "content": text}
            logic.save_chat_to_file(active_filename, chat_data)
            return {"system": f"System prompt set from {name}"}
        else:
            return {"error": "Unknown prompt command"}
    elif cmd == '/summary':
        s = summarize(messages)
        chat_data['summary'] = s
        logic.save_chat_to_file(active_filename, chat_data)
        return {"summary": s}
    elif cmd == '/search':
        if len(parts) < 2:
            return {"error": "Usage: /search <term>"}
        term = " ".join(parts[1:])
        return {"results": search_messages(messages, term)}
    elif cmd == '/export':
        name = parts[1] if len(parts) > 1 else ''
        path = logic.export_chat(chat_data, name)
        return {"system": f"Exported to {path}"}
    elif cmd == '/update':
        script_dir = os.path.dirname(os.path.abspath(__file__))

        def do_update():
            update_path = os.path.join(script_dir, 'update.py')
            subprocess.run([sys.executable, update_path], cwd=script_dir)
            server_path = os.path.join(script_dir, 'server.py')
            os.execl(sys.executable, sys.executable, server_path)

        threading.Thread(target=do_update, daemon=True).start()
        return {"system": "Updating server..."}
    elif cmd == '/model':
        if len(parts) == 1:
            return {"system": f"Current model: {MODEL}"}
        if parts[1] == 'select':
            return {"models": logic.AVAILABLE_MODELS}
        MODEL = parts[1]
        chat_data['model'] = MODEL
        return {"system": f"Model set to {MODEL}"}
    elif cmd == '/info':
        path = os.path.join(logic.CHAT_HISTORY_DIR, active_filename)
        mtime = "unknown"
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            pass
        return {
            "file": active_filename,
            "model": chat_data['model'],
            "messages": len(messages)-1,
            "mtime": mtime,
        }
    else:
        return {"error": f"Unknown command {cmd}"}


def process_message(text):
    """Handle a user message or command and return the response."""

    global chat_data, messages
    if text.startswith('/'):
        return handle_command(text)
    messages.append({"role": "user", "content": text})
    logic.save_chat_to_file(active_filename, chat_data)
    context = messages[-logic.HISTORY_LIMIT:]
    if context[0]['role'] != 'system':
        context = [messages[0]] + context
    chat_completion = client.chat.completions.create(
        messages=context,
        model=MODEL,
        temperature=0.7,
        top_p=1,
    )
    assistant_response = chat_completion.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_response})
    logic.save_chat_to_file(active_filename, chat_data)
    if len(messages) == 3 and chat_data['name'].startswith('Chat '):
        new_name = logic.generate_chat_name(client, messages)
        if new_name:
            chat_data['name'] = new_name
            logic.save_chat_to_file(active_filename, chat_data)
    return {"assistant": assistant_response}


def get_chat_state():
    """Return chat data with the active filename."""
    data = dict(chat_data)
    data["file"] = active_filename
    return data


@app.get('/api/chat')
async def get_chat():
    """Return the current chat including pending messages."""
    return get_chat_state()


@app.get('/api/chats')
async def get_chats():
    """List saved chats grouped by directory."""
    return list_chats()


@app.post('/api/load')
async def api_load(data: dict):
    """Load a chat file and return the updated state."""
    res = handle_command(f"/load {data.get('filename','')}")
    return {"result": res, "chat": get_chat_state()}


@app.post('/api/archive')
async def api_archive(data: dict):
    """Archive the given chat file."""
    success = archive_file(data.get('filename', ''))
    return {"success": success, "chats": list_chats()}


@app.post('/api/restore')
async def api_restore(data: dict):
    """Restore an archived chat."""
    success = restore_file(data.get('filename', ''))
    return {"success": success, "chats": list_chats()}


@app.post('/api/delete')
async def api_delete(data: dict):
    """Delete an archived chat permanently."""
    success = delete_file(data.get('filename', ''))
    return {"success": success, "chats": list_chats()}


@app.post('/api/clear-archive')
async def api_clear_archive():
    """Delete all chats from the archive."""
    success = clear_archive()
    return {"success": success, "chats": list_chats()}


@app.post('/api/api-key')
async def api_set_api_key(data: dict):
    """Update the stored GROQ_API_KEY value."""
    global client
    key = data.get('api_key', '').strip()
    if not key:
        return {"success": False}
    try:
        set_key(ENV_PATH, 'GROQ_API_KEY', key)
    except Exception:
        return {"success": False}
    os.environ['GROQ_API_KEY'] = key
    logic.API_KEY = key
    client = logic.setup_client()
    return {"success": True}


@app.post('/api/update')
async def api_update(background_tasks: BackgroundTasks):
    """Run the updater in the background and then restart the server."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    def do_update():
        update_path = os.path.join(script_dir, 'update.py')
        subprocess.run([sys.executable, update_path], cwd=script_dir)
        server_path = os.path.join(script_dir, 'server.py')
        os.execl(sys.executable, sys.executable, server_path)

    background_tasks.add_task(do_update)
    return {"status": "updating"}


@app.post('/api/message')
async def api_message(data: dict):
    """Process a chat message or command."""
    res = process_message(data.get('message',''))
    return {"result": res, "chat": get_chat_state()}


@app.get('/manifest.json')
async def manifest():
    """Return the web app manifest."""
    data = {
        "name": "GroqChat",
        "short_name": "GroqChat",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#ffffff",
        "icons": [
            {
                "src": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAAB6klEQVR4nO3SQQ0AIRDAwOMcrH+zeKAPQjKjoI+umfng1H87gLcZiMRAJAYiMRCJgUgMRGIgEgORGIjEQCQGIjEQiYFIDERiIBIDkRiIxEAkBiIxEImBSAxEYiASA5EYiMRAJAYiMRCJgUgMRGIgEgORGIjEQCQGIjEQiYFIDERiIBIDkRiIxEAkBiIxEImBSAxEYiASA5EYiMRAJAYiMRCJgUgMRGIgEgORGIjEQCQGIjEQiYFIDERiIBIDkRiIxEAkBiIxEImBSAxEYiASA5EYiMRAJAYiMRCJgUgMRGIgEgORGIjEQCQGIjEQiYFIDERiIBIDkRiIxEAkBiIxEImBSAxEYiASA5EYiMRAJAYiMRCJgUgMRGIgEgORGIjEQCQGIjEQiYFIDERiIBIDkRiIxEAkBiIxEImBSAxEYiASA5EYiMRAJAYiMRCJgUgMRGIgEgORGIjEQCQGIjEQiYFIDERiIBIDkRiIxEAkBiIxEImBSAxEsgGOvgGzAbO4jAAAAABJRU5ErkJggg==",
                "sizes": "192x192",
                "type": "image/png"
            }
        ]
    }
    return Response(json.dumps(data), media_type="application/manifest+json")


@app.get('/sw.js')
async def service_worker():
    """Serve a minimal service worker for installability."""
    sw = """
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => self.clients.claim());
"""
    return Response(sw, media_type="application/javascript")



@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the single page web application."""
    with open("static/index.html") as f:
        return HTMLResponse(f.read())


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('server:app', host='0.0.0.0', port=8000)
