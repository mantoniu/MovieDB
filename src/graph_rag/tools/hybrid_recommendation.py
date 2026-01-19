import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from langchain.tools import tool

from .common import rdf_graph, load_faiss_safe, log_tool_use

BASE_DIR = Path(__file__).resolve().parents[1]
GRAPH_OUT_DIR = BASE_DIR / "graph_embedding" / "graph_embedding_out"
SYNOPSIS_DIR = BASE_DIR / "synopsis_index"

MOVIE_IDS_PATH = GRAPH_OUT_DIR / "movie_ids.json"
MOVIE_EMBS_PATH = GRAPH_OUT_DIR / "movie_embs.npy"
SYNOPSIS_INDEX_PATH = SYNOPSIS_DIR / "synopsis.index.faiss"
SYNOPSIS_META_PATH = SYNOPSIS_DIR / "synopsis.meta.parquet"

PREFIX = "PREFIX : <http://www.moviedb.fr/cinema#>\n"


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec / (norm if norm else 1.0)


def find_movie_uri_by_title(title: str) -> str | None:
    safe_title = title.replace('"', '\\"')
    query = (
        PREFIX
        + f"""
SELECT DISTINCT ?m WHERE {{
  ?m a :Movie ;
     :originalTitle ?t .
  FILTER(lcase(str(?t)) = lcase("{safe_title}"))
}}
LIMIT 1
"""
    )
    rows = list(rdf_graph.query(query))
    if rows:
        return str(rows[0].m)

    query = (
        PREFIX
        + f"""
SELECT DISTINCT ?m WHERE {{
  ?m a :Movie ;
     :primaryTitle ?t .
  FILTER(lcase(str(?t)) = lcase("{safe_title}"))
}}
LIMIT 1
"""
    )
    rows = list(rdf_graph.query(query))
    if rows:
        return str(rows[0].m)
    return None


def fetch_movie_titles() -> dict[str, str]:
    query = (
        PREFIX
        + """
SELECT DISTINCT ?m ?title WHERE {
  ?m a :Movie ;
     :primaryTitle ?title .
}
"""
    )
    rows = list(rdf_graph.query(query))
    return {str(row.m): str(row.title) for row in rows if getattr(row, "m", None)}


def fetch_movie_imdb_ids() -> dict[str, str]:
    query = (
        PREFIX
        + """
SELECT DISTINCT ?m ?id WHERE {
  ?m a :Movie ;
     :imdbId ?id .
}
"""
    )
    rows = list(rdf_graph.query(query))
    return {str(row.m): str(row.id) for row in rows if getattr(row, "m", None)}


def load_graph_embeddings() -> tuple[list[str], np.ndarray]:
    if not MOVIE_IDS_PATH.exists() or not MOVIE_EMBS_PATH.exists():
        raise RuntimeError("Missing graph embeddings files.")

    with MOVIE_IDS_PATH.open("r", encoding="utf-8") as f:
        movie_ids = json.load(f)
    movie_embs = np.load(MOVIE_EMBS_PATH)
    return movie_ids, movie_embs


def load_synopsis_index() -> tuple[object, pd.DataFrame]:
    if not SYNOPSIS_INDEX_PATH.exists() or not SYNOPSIS_META_PATH.exists():
        raise RuntimeError("Missing synopsis index files.")
    index = load_faiss_safe(str(SYNOPSIS_INDEX_PATH))
    meta = pd.read_parquet(SYNOPSIS_META_PATH)
    return index, meta


def build_fused_embeddings() -> tuple[list[str], np.ndarray]:
    movie_ids, movie_embs = load_graph_embeddings()
    index, meta = load_synopsis_index()

    tconst_to_row = {
        tconst: i for i, tconst in enumerate(meta["tconst"].tolist())
    }
    movie_to_tconst = fetch_movie_imdb_ids()

    fused_ids: list[str] = []
    fused_embs: list[np.ndarray] = []
    for idx, movie_uri in enumerate(movie_ids):
        tconst = movie_to_tconst.get(movie_uri)
        if not tconst:
            continue
        row = tconst_to_row.get(tconst)
        if row is None:
            continue
        synopsis_vec = index.reconstruct(row)
        graph_vec = movie_embs[idx]
        fused = np.concatenate(
            [l2_normalize(graph_vec), l2_normalize(synopsis_vec)], axis=0
        )
        fused_ids.append(movie_uri)
        fused_embs.append(l2_normalize(fused))

    if not fused_ids:
        raise RuntimeError("No movies with both graph and synopsis embeddings.")

    return fused_ids, np.asarray(fused_embs, dtype=np.float32)


def hybrid_movie_recommendations(movie_title: str, k: int = 10) -> str:
    movie_title = movie_title.strip()
    if not movie_title:
        return "Movie title missing."

    movie_uri = find_movie_uri_by_title(movie_title)
    if not movie_uri:
        return "Movie not found in the graph."
    try:
        fused_ids, fused_embs = build_fused_embeddings()
    except RuntimeError as exc:
        return str(exc)

    if movie_uri not in fused_ids:
        return "Movie not found in fused embeddings."

    idx = fused_ids.index(movie_uri)
    query = fused_embs[idx : idx + 1]
    knn = NearestNeighbors(metric="cosine")
    knn.fit(fused_embs)
    distances, indices = knn.kneighbors(
        query, n_neighbors=min(k + 1, len(fused_ids))
    )

    movie_titles = fetch_movie_titles()
    results = []
    for dist, i in zip(distances[0], indices[0]):
        if fused_ids[i] == movie_uri:
            continue
        score = 1.0 - float(dist)
        title = movie_titles.get(fused_ids[i], "Unknown title")
        results.append(f"- {title} | {fused_ids[i]} | score={score:.4f}")
        if len(results) >= k:
            break

    if not results:
        return "No similar movies found."
    return "\n".join(results)


@tool
def hybrid_movie_recommendation_tool(movie_title: str, k: int = 10) -> str:
    """
    Recommend movies similar to a given movie title using fused graph+synopsis embeddings.
    """
    log_tool_use("hybrid_movie_recommendation_tool", movie_title=movie_title, k=k)
    return hybrid_movie_recommendations(movie_title=movie_title, k=k)
