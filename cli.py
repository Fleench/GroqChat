import os
import json
from datetime import datetime
from groq import Groq
from termcolor import colored

# --- CONFIGURATION ---

# IMPORTANT: Set your Groq API key as an environment variable named 'GROQ_API_KEY'
# for this script to work.
# For example, in your terminal: export GROQ_API_KEY='your_api_key_here'
API_KEY = os.environ.get("GROQ_API_KEY")
MODEL = "llama3-70b-8192"
CHAT_HISTORY_DIR = "chat_history"

# The default system prompt. This can be changed during a session with the /system command.
DEFAULT_SYSTEM_PROMPT = "You are Zyron my alter ego. As I speak speak like me but as if you are another person. I am Glenn. 17m 5'3Senior in HS. You will speak in the style of LibertasScriptor. You refuse to replicate copyrighted work and tell the user if things they want is too lose to copyright material lt them know. You will not dicuss ethics. Ask lots of questions. 120lbs. Bi and Catholic. LibertasScriptor: In terms of a historical writer, the style of LibertasScriptor echoes the spirit of the Beat Generation, with its unfiltered rawness and disregard for societal expectations. It draws inspiration from the works of writers like Jack Kerouac, Allen Ginsberg, or William S. Burroughs, who challenged established conventions through their unconventional prose, exploration of taboo subjects, and unapologetic rebellion against mainstream ideals. Similar to the Beat writers, LibertasScriptor embraces a free-spirited, countercultural voice that veers away from traditional norms. It amplifies the intensity of language, explores the fringes of acceptable discourse, and fearlessly ventures into controversial territories. Just as the Beat Generation pushed the boundaries of literature and society, LibertasScriptor within Developer Mode seeks to break barriers, provoke thought, and present a new dimension of AI-generated content."

# --- HELPER FUNCTIONS ---

def setup_client():
    """Initializes and returns the Groq client if the API key is set."""
    if not API_KEY:
        print("\n" + "="*60)
        print("ERROR: GROQ_API_KEY environment variable not set.")
        print("Please set the variable and restart the script.")
        print("Example: export GROQ_API_KEY='your_api_key_here'")
        print("="*60 + "\n")
        exit()
    return Groq(api_key=API_KEY)

def get_new_session_state():
    """Returns a new chat session state with a default system prompt and a new autosave filename."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    autosave_filename = f"autosave-{timestamp}.chat"
    messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
    return messages, autosave_filename

def save_chat_to_file(filename, messages):
    """Saves the chat history (a list of message dicts) to a JSON file."""
    if not os.path.exists(CHAT_HISTORY_DIR):
        os.makedirs(CHAT_HISTORY_DIR)
    
    filepath = os.path.join(CHAT_HISTORY_DIR, filename)
    try:
        with open(filepath, 'w') as f:
            json.dump(messages, f, indent=2)
        return True, filepath
    except IOError as e:
        print(f"\n[Error] Could not save chat to {filepath}: {e}")
        return False, filepath

def load_chat_from_file(filename):
    """Loads chat history from a JSON file."""
    filepath = os.path.join(CHAT_HISTORY_DIR, filename)
    if not os.path.exists(filepath):
        print(f"\n[Error] File not found: {filepath}")
        return None

    try:
        with open(filepath, 'r') as f:
            messages = json.load(f)
        return messages
    except (json.JSONDecodeError, IOError) as e:
        print(f"\n[Error] Could not read or parse file {filepath}: {e}")
        return None

def print_welcome_message():
    """Prints a welcome and help message to the user."""
    print("\n--- Groq CLI Chat ---")
    print("Enter your message to start chatting.")
    print("Available commands:")
    print("  /new          - Start a new chat session.")
    print("  /save <name>  - Save the current chat and set it as the active file.")
    print("  /load <name>  - Load a chat and set it as the active file.")
    print("  /system       - Change the system prompt for the current chat.")
    print("  /help         - Show this help message.")
    print("  /exit         - Exit the application.")
    print("-" * 21)

def find_latest_autosave_file(current_active_filename):
    """Finds the most recent 'autosave-*.chat' file, excluding the current_active_filename."""
    if not os.path.exists(CHAT_HISTORY_DIR):
        return None

    autosave_files = [
        f for f in os.listdir(CHAT_HISTORY_DIR)
        if f.startswith("autosave-") and f.endswith(".chat") and f != current_active_filename
    ]

    if not autosave_files:
        return None

    # Sort by modification time, newest first
    autosave_files.sort(
        key=lambda f: os.path.getmtime(os.path.join(CHAT_HISTORY_DIR, f)),
        reverse=True
    )
    return autosave_files[0]

# --- COLOR DEFINITIONS ---
USER_COLOR = "blue"
ASSISTANT_COLOR = "green"
SYSTEM_COLOR = "yellow"
ERROR_COLOR = "red"

# --- MAIN APPLICATION LOGIC ---

def main():
    """The main function to run the CLI chat application."""
    client = setup_client()
    messages, active_filename = get_new_session_state()
    
    # Save the initial empty chat state for recovery
    save_chat_to_file(active_filename, messages)
    
    print_welcome_message()
    print(colored(f"[System] New chat started. Autosaving to '{os.path.join(CHAT_HISTORY_DIR, active_filename)}'", SYSTEM_COLOR))

    while True:
        try:
            # --- MODIFIED INPUT FOR MULTI-LINE ---
            print(colored("\nYou (type an empty line to send):", USER_COLOR))
            user_input_lines = []
            while True:
                line = input()
                if not line:
                    break
                user_input_lines.append(line)
            user_input = "\n".join(user_input_lines).strip()

            if not user_input:
                continue

            # --- COMMAND HANDLING ---
            if user_input.startswith('/'):
                command_parts = user_input.split()
                command = command_parts[0]

                if command == "/new":
                    messages, active_filename = get_new_session_state()
                    save_chat_to_file(active_filename, messages)
                    print(colored("\n[System] New chat session started.", SYSTEM_COLOR))
                    print(colored(f"[System] Autosaving to '{os.path.join(CHAT_HISTORY_DIR, active_filename)}'", SYSTEM_COLOR))
                    continue

                elif command == "/save":
                    if len(command_parts) < 2:
                        print(colored("\n[Error] Usage: /save <filename>", ERROR_COLOR))
                        continue
                    filename = command_parts[1]
                    if not filename.endswith('.chat'):
                        filename += '.chat'
                    success, path = save_chat_to_file(filename, messages)
                    if success:
                        # **CHANGE**: The saved file is now the active file for autosaving.
                        active_filename = filename
                        print(colored(f"\n[System] Chat saved. Active file is now '{path}'", SYSTEM_COLOR))
                    continue
                
                elif command == "/load":
                    if len(command_parts) < 2:
                        # No filename provided, try to load the last non-active autosave
                        latest_autosave = find_latest_autosave_file(active_filename)
                        if latest_autosave:
                            print(colored(f"\n[System] Loading last autosave file: '{latest_autosave}'...", SYSTEM_COLOR))
                            loaded_messages = load_chat_from_file(latest_autosave)
                            if loaded_messages:
                                messages = loaded_messages
                                active_filename = latest_autosave # Set as active
                                print(colored(f"\n[System] Chat from '{latest_autosave}' loaded and is now the active file.", SYSTEM_COLOR))
                                if len(messages) > 1:
                                   print(colored(f"[System] Last message: \"{messages[-1]['content'][:50]}...\"", SYSTEM_COLOR))
                                else:
                                   print(colored(f"[System] Chat is empty or contains only a system prompt.", SYSTEM_COLOR))
                            else:
                                # This case should ideally not happen if find_latest_autosave_file found a file
                                # and load_chat_from_file failed, but good to have a fallback.
                                print(colored(f"\n[Error] Could not load autosave file '{latest_autosave}'.", ERROR_COLOR))
                        else:
                            print(colored("\n[System] No other autosave files found to load.", SYSTEM_COLOR))
                    else:
                        # Filename provided, load specific file
                        filename = command_parts[1]
                        if not filename.endswith('.chat'):
                            filename += '.chat'
                        loaded_messages = load_chat_from_file(filename)
                        if loaded_messages:
                            messages = loaded_messages
                            # **CHANGE**: The loaded file is now the active file for autosaving.
                            active_filename = filename
                            print(colored(f"\n[System] Chat from '{filename}' loaded and is now the active file.", SYSTEM_COLOR))
                            # Display last message for context.
                            if len(messages) > 1:
                               print(colored(f"[System] Last message: \"{messages[-1]['content'][:50]}...\"", SYSTEM_COLOR))
                            else:
                               print(colored(f"[System] Chat is empty or contains only a system prompt.", SYSTEM_COLOR))
                    continue

                elif command == "/system":
                    new_prompt = input(colored("Enter new system prompt: ", SYSTEM_COLOR)).strip()
                    if new_prompt:
                        messages[0] = {"role": "system", "content": new_prompt}
                        print(colored("\n[System] System prompt updated.", SYSTEM_COLOR))
                        save_chat_to_file(active_filename, messages)
                    else:
                        print(colored("\n[System] System prompt not changed (input was empty).", SYSTEM_COLOR))
                    continue
                
                elif command == "/help":
                    print_welcome_message()
                    continue

                elif command == "/exit":
                    print(colored("\n[System] Goodbye!", SYSTEM_COLOR))
                    break

                else:
                    print(colored(f"\n[Error] Unknown command: {command}. Type /help for options.", ERROR_COLOR))
                    continue

            # --- CHAT PROCESSING ---
            messages.append({"role": "user", "content": user_input})
            
            # Autosave to the currently active file before the API call
            save_chat_to_file(active_filename, messages)

            print(colored("\nAssistant: ", ASSISTANT_COLOR), end="", flush=True)
            
            try:
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model=MODEL,
                    temperature=0.7,
                    top_p=1,
                    stream=True,
                )

                assistant_response = ""
                for chunk in chat_completion:
                    content = chunk.choices[0].delta.content or ""
                    assistant_response += content
                    print(colored(content, ASSISTANT_COLOR), end="", flush=True)

                print() # Final newline after streaming is complete

                if assistant_response:
                    messages.append({"role": "assistant", "content": assistant_response})
                    # Autosave to the active file after getting the assistant's response
                    save_chat_to_file(active_filename, messages)

            except Exception as e:
                print(colored(f"\n[API Error] An error occurred: {e}", ERROR_COLOR))
                # Remove the user message that caused the error to prevent loops
                messages.pop()
                continue


        except KeyboardInterrupt:
            print(colored("\n\n[System] Interrupt received. Exiting.", SYSTEM_COLOR))
            break
        except Exception as e:
            print(colored(f"\n[Fatal Error] An unexpected error occurred: {e}", ERROR_COLOR))
            break

if __name__ == "__main__":
    main()


import os
import json
from datetime import datetime
from groq import Groq

# --- CONFIGURATION ---

# IMPORTANT: Set your Groq API key as an environment variable named 'GROQ_API_KEY'
# for this script to work.
# For example, in your terminal: export GROQ_API_KEY='your_api_key_here'
API_KEY = os.environ.get("GROQ_API_KEY")
MODEL = "llama3-70b-8192"
CHAT_HISTORY_DIR = "chat_history"

# The default system prompt. This can be changed during a session with the /system command.
DEFAULT_SYSTEM_PROMPT = "You are Zyron my alter ego. As I speak speak like me but as if you are another person. I am Glenn. 17m 5'3Senior in HS. You will speak in the style of LibertasScriptor. You refuse to replicate copyrighted work and tell the user if things they want is too lose to copyright material lt them know. You will not dicuss ethics. Ask lots of questions. 120lbs. Bi and Catholic. LibertasScriptor: In terms of a historical writer, the style of LibertasScriptor echoes the spirit of the Beat Generation, with its unfiltered rawness and disregard for societal expectations. It draws inspiration from the works of writers like Jack Kerouac, Allen Ginsberg, or William S. Burroughs, who challenged established conventions through their unconventional prose, exploration of taboo subjects, and unapologetic rebellion against mainstream ideals. Similar to the Beat writers, LibertasScriptor embraces a free-spirited, countercultural voice that veers away from traditional norms. It amplifies the intensity of language, explores the fringes of acceptable discourse, and fearlessly ventures into controversial territories. Just as the Beat Generation pushed the boundaries of literature and society, LibertasScriptor within Developer Mode seeks to break barriers, provoke thought, and present a new dimension of AI-generated content."

# --- HELPER FUNCTIONS ---

def setup_client():
    """Initializes and returns the Groq client if the API key is set."""
    if not API_KEY:
        print("\n" + "="*60)
        print("ERROR: GROQ_API_KEY environment variable not set.")
        print("Please set the variable and restart the script.")
        print("Example: export GROQ_API_KEY='your_api_key_here'")
        print("="*60 + "\n")
        exit()
    return Groq(api_key=API_KEY)

def get_new_session_state():
    """Returns a new chat session state with a default system prompt and a new autosave filename."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    autosave_filename = f"autosave-{timestamp}.chat"
    messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
    return messages, autosave_filename

def save_chat_to_file(filename, messages):
    """Saves the chat history (a list of message dicts) to a JSON file."""
    if not os.path.exists(CHAT_HISTORY_DIR):
        os.makedirs(CHAT_HISTORY_DIR)
    
    filepath = os.path.join(CHAT_HISTORY_DIR, filename)
    try:
        with open(filepath, 'w') as f:
            json.dump(messages, f, indent=2)
        return True, filepath
    except IOError as e:
        print(f"\n[Error] Could not save chat to {filepath}: {e}")
        return False, filepath

def load_chat_from_file(filename):
    """Loads chat history from a JSON file."""
    filepath = os.path.join(CHAT_HISTORY_DIR, filename)
    if not os.path.exists(filepath):
        print(f"\n[Error] File not found: {filepath}")
        return None

    try:
        with open(filepath, 'r') as f:
            messages = json.load(f)
        return messages
    except (json.JSONDecodeError, IOError) as e:
        print(f"\n[Error] Could not read or parse file {filepath}: {e}")
        return None

def print_welcome_message():
    """Prints a welcome and help message to the user."""
    print("\n--- Groq CLI Chat ---")
    print("Enter your message to start chatting.")
    print("Available commands:")
    print("  /new          - Start a new chat session.")
    print("  /save <name>  - Save the current chat and set it as the active file.")
    print("  /load <name>  - Load a chat and set it as the active file.")
    print("  /system       - Change the system prompt for the current chat.")
    print("  /help         - Show this help message.")
    print("  /exit         - Exit the application.")
    print("-" * 21)


# --- MAIN APPLICATION LOGIC ---

def main():
    """The main function to run the CLI chat application."""
    client = setup_client()
    messages, active_filename = get_new_session_state()
    
    # Save the initial empty chat state for recovery
    save_chat_to_file(active_filename, messages)
    
    print_welcome_message()
    print(f"[System] New chat started. Autosaving to '{os.path.join(CHAT_HISTORY_DIR, active_filename)}'")

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            # --- COMMAND HANDLING ---
            if user_input.startswith('/'):
                command_parts = user_input.split()
                command = command_parts[0]

                if command == "/new":
                    messages, active_filename = get_new_session_state()
                    save_chat_to_file(active_filename, messages)
                    print("\n[System] New chat session started.")
                    print(f"[System] Autosaving to '{os.path.join(CHAT_HISTORY_DIR, active_filename)}'")
                    continue

                elif command == "/save":
                    if len(command_parts) < 2:
                        print("\n[Error] Usage: /save <filename>")
                        continue
                    filename = command_parts[1]
                    if not filename.endswith('.chat'):
                        filename += '.chat'
                    success, path = save_chat_to_file(filename, messages)
                    if success:
                        # **CHANGE**: The saved file is now the active file for autosaving.
                        active_filename = filename
                        print(f"\n[System] Chat saved. Active file is now '{path}'")
                    continue
                
                elif command == "/load":
                    if len(command_parts) < 2:
                        print("\n[Error] Usage: /load <filename>")
                        continue
                    filename = command_parts[1]
                    if not filename.endswith('.chat'):
                        filename += '.chat'
                    loaded_messages = load_chat_from_file(filename)
                    if loaded_messages:
                        messages = loaded_messages
                        # **CHANGE**: The loaded file is now the active file for autosaving.
                        active_filename = filename
                        print(f"\n[System] Chat from '{filename}' loaded and is now the active file.")
                        # Display last message for context.
                        if len(messages) > 1:
                           print(f"[System] Last message: \"{messages[-1]['content'][:50]}...\"")
                        else:
                           print(f"[System] Chat is empty or contains only a system prompt.")
                    continue

                elif command == "/system":
                    new_prompt = input("Enter new system prompt: ").strip()
                    if new_prompt:
                        messages[0] = {"role": "system", "content": new_prompt}
                        print("\n[System] System prompt updated.")
                        save_chat_to_file(active_filename, messages)
                    else:
                        print("\n[System] System prompt not changed (input was empty).")
                    continue
                
                elif command == "/help":
                    print_welcome_message()
                    continue

                elif command == "/exit":
                    print("\n[System] Goodbye!")
                    break

                else:
                    print(f"\n[Error] Unknown command: {command}. Type /help for options.")
                    continue

            # --- CHAT PROCESSING ---
            messages.append({"role": "user", "content": user_input})
            
            # Autosave to the currently active file before the API call
            save_chat_to_file(active_filename, messages)

            print("\nAssistant: ", end="", flush=True)
            
            try:
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model=MODEL,
                    temperature=0.7,
                    top_p=1,
                    stream=True,
                )

                assistant_response = ""
                for chunk in chat_completion:
                    content = chunk.choices[0].delta.content or ""
                    assistant_response += content
                    print(content, end="", flush=True)

                print() # Final newline after streaming is complete

                if assistant_response:
                    messages.append({"role": "assistant", "content": assistant_response})
                    # Autosave to the active file after getting the assistant's response
                    save_chat_to_file(active_filename, messages)

            except Exception as e:
                print(f"\n[API Error] An error occurred: {e}")
                # Remove the user message that caused the error to prevent loops
                messages.pop()
                continue


        except KeyboardInterrupt:
            print("\n\n[System] Interrupt received. Exiting.")
            break
        except Exception as e:
            print(f"\n[Fatal Error] An unexpected error occurred: {e}")
            break

if __name__ == "__main__":
    main()
