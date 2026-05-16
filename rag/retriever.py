import os

from dotenv import load_dotenv
from openai import OpenAI
import chromadb

load_dotenv()

RAG_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(RAG_DIR, "chroma_db")

_openai_client = None
_chroma_collection = None


def _openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _openai_client


def _collection():
    global _chroma_collection
    if _chroma_collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _chroma_collection = client.get_collection("player_combine")
    return _chroma_collection


def _embed(text: str) -> list[float]:
    response = _openai().embeddings.create(model="text-embedding-3-small", input=[text])
    return response.data[0].embedding


def get_player_combine(name: str, position: str = None) -> list[dict]:
    vector = _embed(name)
    kwargs = {"query_embeddings": [vector], "n_results": 3}
    if position:
        kwargs["where"] = {"position": {"$eq": position}}

    results = _collection().query(**kwargs)

    return [
        {
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        }
        for i in range(len(results["ids"][0]))
    ]


def get_position_peers(position: str, n: int = 5) -> list[dict]:
    vector = _embed(f"combine performance athlete {position}")
    results = _collection().query(
        query_embeddings=[vector],
        n_results=n,
        where={"position": {"$eq": position}},
    )

    return [
        {
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        }
        for i in range(len(results["ids"][0]))
    ]


if __name__ == "__main__":
    results = get_player_combine("Zachariah Branch")
    print(results[0]["metadata"])
    peers = get_position_peers("WR")
    print([r["metadata"]["name"] for r in peers])
