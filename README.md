# GroqChat

GroqChat is a minimal command-line chat interface for Groq's language model. The script stores chat history locally so you can resume conversations at any time.

Chat history is kept in the `chat_history/` folder with two subdirectories:
* `autosave/`  – files automatically created while chatting
* `userchat/` – chats you explicitly save with `/save`

Run `python cli.py sort` to create these folders and organise any existing files.

## Usage

1. **Set your API key**

   Export the `GROQ_API_KEY` environment variable before running the tool:

   ```bash
   export GROQ_API_KEY="your_api_key"
   ```

2. **Install dependencies**

   Install the required packages using `requirements.txt`:

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the chat CLI**

   Launch the interface with:

   ```bash
   python cli.py
   ```

### Commands

- `/new` start a new chat session
- `/save <name>` save the current chat
- `/load <name>` load a saved chat
- `/chats` browse chat history starting with a list of subdirectories
- `/prompt new <name>` create a reusable prompt
- `/prompt use <name>` send a saved prompt as your message
- `/prompt list` list saved prompts
- `/summary` generate a summary of the current conversation
  Summaries are written from a neutral observer perspective and include key details.
  Only the last 50 messages are used to avoid exceeding model limits.

