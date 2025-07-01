import os
import json
import shutil
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

# Load variables from .env first and fall back to system environment
load_dotenv(override=True)

# Prefer .env values, then system environment, then a fallback
API_KEY = os.getenv("GROQ_API_KEY", "your_groq_api_key")
MODEL = "llama3-70b-8192"
CHAT_VERSION = "1.0"
CHAT_HISTORY_DIR = "chat_history"
AUTOSAVE_DIR = os.path.join(CHAT_HISTORY_DIR, "autosave")
USERCHAT_DIR = os.path.join(CHAT_HISTORY_DIR, "userchat")
ARCHIVE_DIR = os.path.join(CHAT_HISTORY_DIR, "archive")
PROMPTS_DIR = "prompts"
EXPORTS_DIR = "exports"
PROMT_FILE = "promt.txt"
AVAILABLE_MODELS = [
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b",
]

DEFAULT_SYSTEM_PROMPT_FALLBACK = (
    "You are Zyron my alter ego. As I speak speak like me but as if you are another person."
    " I am Glenn. 17m 5'3Senior in HS. You will speak in the style of LibertasScriptor."
    " You refuse to replicate copyrighted work and tell the user if things they want"
    " is too lose to copyright material lt them know. You will not dicuss ethics."
    " Ask lots of questions. 120lbs. Bi and Catholic. LibertasScriptor: In terms of"
    " a historical writer, the style of LibertasScriptor echoes the spirit of the Beat Generation,"
    " with its unfiltered rawness and disregard for societal expectations..."
)

def load_default_prompt():
    try:
        with open(PROMT_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return DEFAULT_SYSTEM_PROMPT_FALLBACK

DEFAULT_SYSTEM_PROMPT = load_default_prompt()
SUMMARY_SYSTEM_PROMPT = (
    "You are a neutral third-party summarizer. Provide a detailed summary of"
    " the conversation between USER and ASSISTANT. Ignore any personality or"
    " style instructions from the chat. Do not continue the conversation or"
    " roleplay as either speaker."
)

SUMMARY_HISTORY_LIMIT = 50
SUMMARY_MAX_TOKENS = 200
HISTORY_LIMIT = 10


def ensure_directories():
    os.makedirs(AUTOSAVE_DIR, exist_ok=True)
    os.makedirs(USERCHAT_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    os.makedirs(EXPORTS_DIR, exist_ok=True)


def setup_client():
    if not API_KEY:
        raise RuntimeError("GROQ_API_KEY environment variable not set")
    return Groq(api_key=API_KEY)


def get_new_session_state():
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    autosave_filename = os.path.join("autosave", f"autosave-{timestamp}.chat")
    chat_data = {
        "name": f"Chat {timestamp}",
        "version": CHAT_VERSION,
        "model": MODEL,
        "messages": [{"role": "system", "content": load_default_prompt()}],
        "summary": "",
    }
    return chat_data, autosave_filename


def generate_chat_name(client, messages):
    convo = "\n".join(
        f"{m['role']}: {m['content']}" for m in messages if m['role'] != 'system'
    )
    prompt_msgs = [
        {"role": "system", "content": "Provide a short (max 5 words) name for this conversation."},
        {"role": "user", "content": convo},
    ]
    completion = client.chat.completions.create(
        messages=prompt_msgs,
        model=MODEL,
        temperature=0.5,
        top_p=1,
        max_tokens=10,
    )
    return completion.choices[0].message.content.strip().strip('"')


def save_chat_to_file(filename, chat_data):
    ensure_directories()
    filepath = os.path.join(CHAT_HISTORY_DIR, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(chat_data, f, indent=2)
    return True, filepath


def load_chat_from_file(filename):
    ensure_directories()
    filepath = os.path.join(CHAT_HISTORY_DIR, filename)
    if not os.path.exists(filepath):
        alt_auto = os.path.join(AUTOSAVE_DIR, filename)
        alt_user = os.path.join(USERCHAT_DIR, filename)
        alt_arch = os.path.join(ARCHIVE_DIR, filename)
        if os.path.exists(alt_auto):
            filepath = alt_auto
        elif os.path.exists(alt_user):
            filepath = alt_user
        elif os.path.exists(alt_arch):
            filepath = alt_arch
        else:
            return None, None

    with open(filepath, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        chat_data = {
            "name": os.path.splitext(os.path.basename(filepath))[0],
            "version": "0",
            "model": MODEL,
            "messages": data,
            "summary": "",
        }
    elif isinstance(data, dict) and "messages" in data:
        data.setdefault("name", os.path.splitext(os.path.basename(filepath))[0])
        data.setdefault("model", MODEL)
        data.setdefault("version", CHAT_VERSION)
        data.setdefault("summary", "")
        chat_data = data
    else:
        return None, None
    return chat_data, os.path.relpath(filepath, CHAT_HISTORY_DIR)


def ensure_prompts_dir():
    os.makedirs(PROMPTS_DIR, exist_ok=True)


def list_prompts():
    ensure_prompts_dir()
    names = []
    for fname in os.listdir(PROMPTS_DIR):
        if fname.endswith('.txt'):
            names.append(os.path.splitext(fname)[0])
    return names


def save_prompt(name, text):
    ensure_prompts_dir()
    path = os.path.join(PROMPTS_DIR, f"{name}.txt")
    with open(path, 'w') as f:
        f.write(text)
    return True, path


def load_prompt(name):
    ensure_prompts_dir()
    path = os.path.join(PROMPTS_DIR, f"{name}.txt")
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return f.read()


def export_chat(chat_data, name):
    ensure_directories()
    if not name:
        name = chat_data["name"].replace(" ", "_") + ".txt"
    path = os.path.join(EXPORTS_DIR, name)
    if name.endswith('.md'):
        with open(path, 'w') as f:
            f.write(f"# {chat_data['name']}\n\n")
            for m in chat_data['messages']:
                f.write(f"**{m['role']}**: {m['content']}\n\n")
    else:
        if not name.endswith('.txt'):
            path += '.txt'
        with open(path, 'w') as f:
            for m in chat_data['messages']:
                f.write(f"{m['role'].capitalize()}: {m['content']}\n\n")
    return path
