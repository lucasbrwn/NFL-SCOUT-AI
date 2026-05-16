# NFL Scout AI

NFL Scout AI is a RAG-powered scouting tool for football fans. Enter any NFL player's name
to get an AI-generated combine grade, compare two players head-to-head, or plug in your own
combine numbers to see how you'd stack up against real draft prospects.

## Requirements

- **Python 3.11.9** (exact version — install via [python.org](https://www.python.org/downloads/release/python-3119/) or `pyenv install 3.11.9`)
- An OpenAI API key

## Setup

1. Clone the repo and navigate to it:
   ```bash
   git clone https://github.com/lucasbrwn/NFL-SCOUT-AI
   cd NFL-SCOUT-AI
   ```

2. Create and activate a virtual environment using Python 3.11.9:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

   Verify the version before continuing:
   ```bash
   python --version
   # Expected: Python 3.11.9
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment template and add your OpenAI key:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and replace the placeholder with your actual key.

5. Build the vector index (runs once, takes ~30 seconds):
   ```bash
   python rag/build_index.py
   ```

6. Run the app:
   ```bash
   python app.py
   ```

7. Open your browser to: http://localhost:5001

## Running the Eval Suite

```bash
python eval/eval_v3.py
```

This runs 12 labeled test cases and prints accuracy. Costs ~$0.05–$0.10 in OpenAI API credits.
