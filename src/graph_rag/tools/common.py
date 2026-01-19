import numpy as np
import pandas as pd
import faiss
from google import genai
from rdflib import Graph

from ..config import EMBED_MODEL, INDEX_PATH, META_PATH, RDF_GRAPH_PATH

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
rdf_graph = Graph()
rdf_graph.parse(RDF_GRAPH_PATH, format="turtle")

print(f"[INIT] Vector index loaded: {index.ntotal} vectors, dim={index.d}")
print(f"[INIT] Metadata loaded: {len(meta)} entries")
print(f"[INIT] RDF Graph loaded: {len(rdf_graph)} triples")

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

def _format_log_value(value, max_len: int = 160) -> str:
    text = str(value).replace("\n", " ")
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text

def log_tool_use(tool_name: str, **kwargs) -> None:
    if kwargs:
        args = ", ".join(f"{k}={_format_log_value(v)}" for k, v in kwargs.items())
        print(f"[TOOL] {tool_name}({args})")
    else:
        print(f"[TOOL] {tool_name}()")
