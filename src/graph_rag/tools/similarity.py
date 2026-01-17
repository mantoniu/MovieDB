import numpy as np
import pandas as pd
import faiss
from google import genai
from langchain.tools import tool

from ..config import EMBED_MODEL, INDEX_PATH, META_PATH

def load_faiss_safe(path: str):
    """
    Load a FAISS index safely, handling potential issues with file paths containing accents.

    Args:
        path (str): The file path to the FAISS index.
    Returns:
        faiss.Index: The loaded FAISS index.
    """
    try:
        return faiss.read_index(path)
    except RuntimeError:
        vector = np.fromfile(path, dtype='uint8')
        return faiss.deserialize_index(vector)

client = genai.Client()
index = load_faiss_safe(INDEX_PATH)
meta = pd.read_parquet(META_PATH)

def embed_one(text: str) -> np.ndarray:
    """
    Embed a single text using Google Gemini embeddings.

    Args:
        text (str): The text to embed.
    Returns:
        np.ndarray: The normalized embedding vector.
    """
    res = client.models.embed_content(model=EMBED_MODEL, contents=[text])
    emb = res.embeddings[0]
    vec = getattr(emb, "values", emb)
    v = np.array(vec, dtype="float32")
    n = np.linalg.norm(v)
    return v / (n if n else 1.0)

def similarity_search(query: str, k: int = 5) -> str:
    """
    Do a semantic similarity search over movie synopses.

    Args:
        query (str): The search query.
        k (int): Number of top results to return.

    Returns:
        str: Formatted string of top-k similar movies.
    """
    q = embed_one(query).reshape(1, -1)
    scores, ids = index.search(q, k)

    results = []
    for rank, (i, s) in enumerate(zip(ids[0], scores[0]), 1):
        if int(i) == -1:
            continue

        row = meta.iloc[int(i)]
        title = row.get("primaryTitle", "N/A")
        year = row.get("startYear", "N/A")
        tconst = row.get("tconst", "N/A")
        synopsis = (row.get("synopsis") or "").strip()

        out = f"{rank}. {title} ({year}) [ID: {tconst}] — score={float(s):.3f}"
        if synopsis:
            out += f"\n   Synopsis: {synopsis[:250].replace(chr(10), ' ')}"
            if len(synopsis) > 250:
                out += "..."
        results.append(out)

    return "\n\n".join(results) if results else "Aucun résultat trouvé."

@tool
def similarity_search_tool(query: str) -> str:
    """
    Tool to perform a similarity search on movie synopses.

    Args:
        query (str): The search query.
    Returns:
        str: Formatted string of top-k similar movies.
    """
    return similarity_search(query, k=5)
