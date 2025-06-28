# GroqChat

GroqChat is a minimal command-line chat interface for Groq's language model. The script stores chat history locally so you can resume conversations at any time.

## Usage

1. **Set your API key**

   Export the `GROQ_API_KEY` environment variable before running the tool:

   ```bash
   export GROQ_API_KEY="your_api_key"
   ```

2. **Install dependencies**

   This project requires `groq` and `termcolor`. Install them with pip:

   ```bash
   pip install groq termcolor
   ```

3. **Run the chat CLI**

   Launch the interface with:

   ```bash
   python cli.py
   ```

