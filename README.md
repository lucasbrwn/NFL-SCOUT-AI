# NFL Scout AI

NFL Scout AI is a RAG-powered scouting tool for football fans. Enter any NFL player's name
to get an AI-generated combine grade, compare two players head-to-head, or plug in your own
combine numbers to see how you'd stack up against real draft prospects.

## Requirements

- Python 3.11+
- An OpenAI API key

## Setup

1. Clone the repo and navigate to it:
   ```
   git clone https://github.com/lucasbrwn/NFL-SCOUT-AI
   cd NFL-SCOUT-AI
   ```

2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Copy the environment template and add your OpenAI key:
   ```
   cp .env.example .env
   ```
   Edit `.env` and replace the placeholder with your actual key.

5. Build the vector index (runs once, takes ~30 seconds):
   ```
   python rag/build_index.py
   ```

6. Run the app:
   ```
   python app.py
   ```

7. Open your browser to: http://localhost:5000

## Running the Eval Suite

```
python eval/eval_v3.py
```

This runs 12 labeled test cases and prints accuracy. Costs ~$0.05–$0.10 in OpenAI API credits.
