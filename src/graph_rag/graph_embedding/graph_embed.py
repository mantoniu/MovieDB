import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import networkx as nx
from node2vec import Node2Vec

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_rag.tools.common import rdf_graph

PREFIX = "PREFIX : <http://www.moviedb.fr/cinema#>\n"

OUT_DIR = str(Path.cwd() / "graph_embedding_out")
DIMS = 128
WALK_LENGTH = 60
NUM_WALKS = 10
WINDOW = 10
P = 1.0
Q = 1.0
INCLUDE_ACTORS = False
TOP_N_ACTORS = 5
PERSON_DEGREE_CAP = 200
SEED = 42


def run_sparql(query: str):
    try:
        return list(rdf_graph.query(query))
    except Exception as exc:
        raise RuntimeError(f"SPARQL query failed: {exc}") from exc


def fetch_movies() -> list[str]:
    query = (
        PREFIX
        + """
SELECT DISTINCT ?m WHERE {
  ?m a :Movie .
}
"""
    )
    rows = run_sparql(query)
    return [str(row.m) for row in rows if getattr(row, "m", None)]


def fetch_edges(predicate: str, obj_var: str = "o") -> list[tuple[str, str]]:
    query = (
        PREFIX
        + f"""
SELECT DISTINCT ?m ?{obj_var} WHERE {{
  ?m a :Movie .
  ?m {predicate} ?{obj_var} .
}}
"""
    )
    rows = run_sparql(query)
    edges = []
    for row in rows:
        m_uri = str(getattr(row, "m", "")) if getattr(row, "m", None) else ""
        o_uri = str(getattr(row, obj_var, "")) if getattr(row, obj_var, None) else ""
        if m_uri and o_uri:
            edges.append((m_uri, o_uri))
    return edges


def fetch_actor_edges(top_n: int) -> list[tuple[str, str]]:
    query = (
        PREFIX
        + """
SELECT DISTINCT ?m ?a WHERE {
  ?m a :Movie .
  ?m :hasActor ?a .
}
"""
    )
    rows = run_sparql(query)
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        m_uri = str(getattr(row, "m", "")) if getattr(row, "m", None) else ""
        a_uri = str(getattr(row, "a", "")) if getattr(row, "a", None) else ""
        if m_uri and a_uri:
            grouped[m_uri].append(a_uri)

    edges = []
    for m_uri, actors in grouped.items():
        actors_sorted = sorted(set(actors))
        for a_uri in actors_sorted[:top_n]:
            edges.append((m_uri, a_uri))
    return edges


def fetch_user_movie_edges() -> list[tuple[str, str]]:
    query = (
        PREFIX
        + """
SELECT DISTINCT ?u ?m WHERE {
  ?r a :Review ;
     :writtenBy ?u ;
     :isReviewOf ?m .
  ?m a :Movie .
}
"""
    )
    rows = run_sparql(query)
    edges = []
    for row in rows:
        u_uri = str(getattr(row, "u", "")) if getattr(row, "u", None) else ""
        m_uri = str(getattr(row, "m", "")) if getattr(row, "m", None) else ""
        if u_uri and m_uri:
            edges.append((u_uri, m_uri))
    return edges


def build_graph(
    movies: list[str],
    genre_edges: list[tuple[str, str]],
    director_edges: list[tuple[str, str]],
    writer_edges: list[tuple[str, str]],
    actor_edges: list[tuple[str, str]],
    user_edges: list[tuple[str, str]],
    person_degree_cap: int,
) -> tuple[nx.Graph, list[str]]:
    graph = nx.Graph()

    movie_nodes = [f"m:{uri}" for uri in movies]
    graph.add_nodes_from(movie_nodes)

    def add_edges(edges: list[tuple[str, str]], prefix_left: str, prefix_right: str) -> None:
        for left, right in edges:
            graph.add_edge(f"{prefix_left}{left}", f"{prefix_right}{right}")

    add_edges(genre_edges, "m:", "g:")
    add_edges(director_edges, "m:", "p:")
    add_edges(writer_edges, "m:", "p:")
    add_edges(actor_edges, "m:", "p:")
    add_edges(user_edges, "u:", "m:")

    person_nodes = [n for n in graph.nodes if n.startswith("p:")]
    to_remove = [n for n in person_nodes if graph.degree(n) > person_degree_cap]
    if to_remove:
        graph.remove_nodes_from(to_remove)

    return graph, movie_nodes


def train_node2vec(
    graph: nx.Graph,
    dims: int,
    walk_length: int,
    num_walks: int,
    window: int,
    p: float,
    q: float,
    seed: int,
):
    node2vec = Node2Vec(
        graph,
        dimensions=dims,
        walk_length=walk_length,
        num_walks=num_walks,
        p=p,
        q=q,
        workers=1,
        seed=seed,
    )
    model = node2vec.fit(window=window, min_count=1, batch_words=64, seed=seed)
    return model


def is_local_movie(uri: str) -> bool:
    return uri.startswith("http://www.moviedb.fr/cinema#MotionPicture/")

def main() -> int:
    print("Fetching movies...")
    movies = fetch_movies()
    print(f"Movies: {len(movies)}")

    print("Fetching edges...")
    genre_edges = fetch_edges(":hasGenre", "g")
    director_edges = fetch_edges(":hasDirector", "p")
    writer_edges = fetch_edges(":hasWriter", "p")
    actor_edges = []
    if INCLUDE_ACTORS:
        actor_edges = fetch_actor_edges(TOP_N_ACTORS)
    user_edges = fetch_user_movie_edges()

    graph, movie_nodes = build_graph(
        movies=movies,
        genre_edges=genre_edges,
        director_edges=director_edges,
        writer_edges=writer_edges,
        actor_edges=actor_edges,
        user_edges=user_edges,
        person_degree_cap=PERSON_DEGREE_CAP,
    )
    print(f"Graph nodes: {graph.number_of_nodes()}, edges: {graph.number_of_edges()}")

    print("Training Node2Vec...")
    model = train_node2vec(
        graph,
        dims=DIMS,
        walk_length=WALK_LENGTH,
        num_walks=NUM_WALKS,
        window=WINDOW,
        p=P,
        q=Q,
        seed=SEED,
    )

    movie_ids = []
    movie_embs = []
    for node in movie_nodes:
        if node in model.wv:
            uri = node[2:]
            if is_local_movie(uri):
                movie_ids.append(uri)
                movie_embs.append(model.wv[node])

    movie_embs = np.asarray(movie_embs, dtype=np.float32)
    os.makedirs(OUT_DIR, exist_ok=True)
    ids_path = os.path.join(OUT_DIR, "movie_ids.json")
    embs_path = os.path.join(OUT_DIR, "movie_embs.npy")
    with open(ids_path, "w", encoding="utf-8") as f:
        json.dump(movie_ids, f, ensure_ascii=True, indent=2)
    np.save(embs_path, movie_embs)

    print(f"Wrote {len(movie_ids)} movie ids to {ids_path}")
    print(f"Wrote embeddings to {embs_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
