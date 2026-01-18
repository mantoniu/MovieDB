import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_rag.tools.common import rdf_graph, load_faiss_safe

OUT_DIR = str(Path(__file__).resolve().parent / "graph_embedding_out")
SYNOPSIS_DIR = Path(__file__).resolve().parents[1] / "synopsis_index"
SYNOPSIS_INDEX_PATH = str(SYNOPSIS_DIR / "synopsis.index.faiss")
SYNOPSIS_META_PATH = str(SYNOPSIS_DIR / "synopsis.meta.parquet")
MOVIE_TITLE = "The Matrix"
K = 10

PREFIX = "PREFIX : <http://www.moviedb.fr/cinema#>\n"


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


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec / (norm if norm else 1.0)


def main() -> int:
    ids_path = os.path.join(OUT_DIR, "movie_ids.json")
    embs_path = os.path.join(OUT_DIR, "movie_embs.npy")

    if not os.path.exists(ids_path) or not os.path.exists(embs_path):
        print("Missing movie_ids.json or movie_embs.npy")
        return 1

    with open(ids_path, "r", encoding="utf-8") as f:
        movie_ids = json.load(f)

    movie_embs = np.load(embs_path)
    if not os.path.exists(SYNOPSIS_INDEX_PATH) or not os.path.exists(SYNOPSIS_META_PATH):
        print("Missing synopsis index or metadata.")
        return 1

    index = load_faiss_safe(SYNOPSIS_INDEX_PATH)
    meta = pd.read_parquet(SYNOPSIS_META_PATH)
    tconst_to_row = {tconst: i for i, tconst in enumerate(meta["tconst"].tolist())}
    movie_to_tconst = fetch_movie_imdb_ids()
    movie_titles = fetch_movie_titles()

    fused_ids = []
    fused_embs = []
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
        print("No movies with both graph and synopsis embeddings.")
        return 1

    fused_embs = np.asarray(fused_embs, dtype=np.float32)
    movie_uri = find_movie_uri_by_title(MOVIE_TITLE)
    if not movie_uri:
        print("Movie title not found in RDF graph.")
        return 1
    if movie_uri not in fused_ids:
        print("movie_uri not found in fused embeddings.")
        return 1

    idx = fused_ids.index(movie_uri)
    query = fused_embs[idx : idx + 1]

    knn = NearestNeighbors(metric="cosine")
    knn.fit(fused_embs)
    distances, indices = knn.kneighbors(query, n_neighbors=min(K + 1, len(fused_ids)))

    print(f"Query: {movie_uri}")
    count = 0
    for dist, i in zip(distances[0], indices[0]):
        if fused_ids[i] == movie_uri:
            continue
        score = 1.0 - float(dist)
        title = movie_titles.get(fused_ids[i], "Titre inconnu")
        print(f"{title} | {fused_ids[i]} | score={score:.4f}")
        count += 1
        if count >= K:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
