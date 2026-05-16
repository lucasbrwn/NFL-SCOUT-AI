import os
import sys

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

load_dotenv()

RAG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(RAG_DIR)
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "combine_stats.csv")
CHROMA_PATH = os.path.join(RAG_DIR, "chroma_db")


def _build_doc_text(row: pd.Series) -> str:
    clauses = []
    if pd.notna(row["forty_yard"]):
        clauses.append(f"ran the 40-yard dash in {row['forty_yard']}s")
    if pd.notna(row["bench_reps"]):
        clauses.append(f"bench pressed {int(row['bench_reps'])} reps")
    if pd.notna(row["vertical_jump"]):
        clauses.append(f'had a {row["vertical_jump"]}" vertical')
    if pd.notna(row["broad_jump"]):
        clauses.append(f'{row["broad_jump"]}" broad jump')
    if pd.notna(row["three_cone"]):
        clauses.append(f"{row['three_cone']}s 3-cone")
    if pd.notna(row["shuttle"]):
        clauses.append(f"{row['shuttle']}s shuttle")

    base = f"{row['name']} is a {row['position']}"
    if clauses:
        base += " who " + ", ".join(clauses)
    base += "."

    parts = [base]

    if pd.notna(row["height_in"]) and pd.notna(row["weight_lbs"]):
        parts.append(f'Height: {int(row["height_in"])}", Weight: {int(row["weight_lbs"])} lbs.')

    if pd.notna(row["draft_round"]) and pd.notna(row["draft_pick"]):
        parts.append(
            f"Drafted in round {int(row['draft_round'])}, pick {int(row['draft_pick'])} in {int(row['draft_year'])}."
        )
    else:
        parts.append(f"Draft year: {int(row['draft_year'])}.")

    is_hof = str(row["is_hof"]).strip().lower() == "true"
    parts.append(f"Hall of Fame: {is_hof}. College: {row['college']}.")

    return " ".join(parts)


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Error: OPENAI_API_KEY not set in environment or .env file.")

    client = OpenAI(api_key=api_key)

    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} players from combine_stats.csv")

    documents = []
    ids = []
    metadatas = []

    for _, row in df.iterrows():
        documents.append(_build_doc_text(row))
        ids.append(str(row["player_id"]))
        metadatas.append({
            "player_id": str(row["player_id"]),
            "name": str(row["name"]),
            "position": str(row["position"]),
            "draft_year": int(row["draft_year"]),
            "is_hof": str(row["is_hof"]).strip().lower() == "true",
        })

    BATCH_SIZE = 2048
    embeddings = []
    print(f"Embedding {len(documents)} player documents in batches of {BATCH_SIZE}...")
    for i in range(0, len(documents), BATCH_SIZE):
        batch = documents[i : i + BATCH_SIZE]
        response = client.embeddings.create(model="text-embedding-3-small", input=batch)
        embeddings.extend(item.embedding for item in response.data)
        print(f"  Embedded {min(i + BATCH_SIZE, len(documents))}/{len(documents)}")
    print(f"Received {len(embeddings)} embeddings.")

    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    try:
        chroma_client.delete_collection("player_combine")
        print("Deleted existing player_combine collection.")
    except Exception:
        pass

    collection = chroma_client.create_collection("player_combine")
    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    print(f"Indexed {len(documents)} players into player_combine collection.")


if __name__ == "__main__":
    main()
