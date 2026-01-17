import os
import math
import numpy as np
import pandas as pd
from tqdm import tqdm
import faiss
from google import genai

INPUT_FILE = "./datasets/reduced/title.basics.with_synopsis.tsv"
OUT_DIR = "./src/graph_rag/synopsis_index"
MODEL = "gemini-embedding-001"
BATCH_SIZE = 64

os.makedirs(OUT_DIR, exist_ok=True)
INDEX_PATH = os.path.join(OUT_DIR, "synopsis.index.faiss")
META_PATH = os.path.join(OUT_DIR, "synopsis.meta.parquet")

client = genai.Client()

def embed_texts(texts):
    result = client.models.embed_content(
        model=MODEL,
        contents=texts
    )
    vectors = []
    for emb in result.embeddings:
        vec = getattr(emb, "values", None)
        if vec is None:
            vec = emb
        vectors.append(list(vec))
    return vectors

def l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms

if __name__ == "__main__":
    df = pd.read_csv(INPUT_FILE, sep="\t", dtype=str)
    df["synopsis"] = df["synopsis"].fillna("").astype(str).str.strip()

    df = df[df["synopsis"].str.len() > 0].copy()
    df.reset_index(drop=True, inplace=True)

    embeddings = []
    total_batches = math.ceil(len(df) / BATCH_SIZE)
    pbar = tqdm(total=total_batches, desc="Embedding synopsis (Gemini)")

    for b in range(total_batches):
        start = b * BATCH_SIZE
        end = min((b + 1) * BATCH_SIZE, len(df))
        texts = df.loc[start:end-1, "synopsis"].tolist()

        vecs = embed_texts(texts)
        embeddings.extend(vecs)

        pbar.update(1)

    pbar.close()

    X = np.array(embeddings, dtype="float32")
    X = l2_normalize(X)

    dim = X.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(X)

    faiss.write_index(index, INDEX_PATH)
    df.to_parquet(META_PATH, index=False)

    print(f"FAISS index saved: {INDEX_PATH}")
    print(f"Metadata saved:   {META_PATH}")
    print(f"Vectors indexed:  {index.ntotal} | dim={dim}")
