from langchain.tools import tool

from .common import index, meta, embed_one

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
