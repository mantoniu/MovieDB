import numpy as np
import pandas as pd
import faiss
from google import genai
from .config import EMBED_MODEL, INDEX_PATH, META_PATH

client = genai.Client()

def embed_one(text: str) -> np.ndarray:
    res = client.models.embed_content(model=EMBED_MODEL, contents=[text])
    emb = res.embeddings[0]
    vec = getattr(emb, "values", emb)
    v = np.array(vec, dtype="float32")
    n = np.linalg.norm(v)
    return v / (n if n else 1.0)

index = faiss.read_index(INDEX_PATH)
meta = pd.read_parquet(META_PATH)

query = "un hacker découvre que la réalité est une simulation et rejoint une résistance"
q = embed_one(query).reshape(1, -1)

k = 10
scores, ids = index.search(q, k)

for rank, (i, s) in enumerate(zip(ids[0], scores[0]), 1):
    row = meta.iloc[int(i)]
    print(f"{rank:02d} score={s:.3f} | {row.get('primaryTitle')} ({row.get('startYear')}) | {row.get('tconst')}")
