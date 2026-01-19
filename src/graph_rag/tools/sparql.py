from langchain.tools import tool
import concurrent.futures
from rdflib import Literal, URIRef
from rdflib.namespace import RDF, XSD

from .common import rdf_graph
from ..config import MOVIE_NS, REVIEW_NS

SPARQL_TIMEOUT_SEC = 20

def get_movies() -> list:
    """
    Retrieve a list of movie titles from the RDF graph.

    Returns:
        dict: A dict with movie IDs and titles.
    """
    query = """
        PREFIX : <http://www.moviedb.fr/cinema#>

        SELECT DISTINCT ?id ?title WHERE {
            ?movie a :Movie ;
                   :originalTitle ?title ;
                   :imdbId ?id .

        }

        ORDER BY ?title 
    """

    rows = list(rdf_graph.query(query))
    return {str(row[0]): str(row[1]) for row in rows}

def insert_review(movie_id: str, rating: float, spoiler: bool, text: str, username: str) -> None:
    """
    Insert a new movie review into the RDF graph.

    Args:
        movie_id (str): The movie ID.
        rating (float): The rating given to the movie.
        spoiler (bool): Whether the review contains spoilers.
        text (str): The review text.
        username (str): The username of the reviewer.
    """
    print(f"Inserting review for '{movie_id}' by user '{username}'")
    print(f"Rating: {rating}, Spoiler: {spoiler} Text: {text}")

    user_uri = URIRef(f"http://www.moviedb.fr/cinema#User/{username}")
    movie_uri = URIRef(f"http://www.moviedb.fr/cinema#MotionPicture/{movie_id}")

    review_id = f"review_{hash((movie_id, username, text)) & 0xFFFFFFFF}"
    review_uri = REVIEW_NS[review_id]

    print(review_uri, user_uri, movie_uri)

    rdf_graph.add((review_uri, RDF.type, MOVIE_NS.Review))
    rdf_graph.add((review_uri, MOVIE_NS.isReviewOf, movie_uri))
    rdf_graph.add((review_uri, MOVIE_NS.writtenBy, user_uri))
    rdf_graph.add((review_uri, MOVIE_NS.ratingValue, Literal(rating, datatype=XSD.float)))
    rdf_graph.add((review_uri, MOVIE_NS.isSpoiler, Literal(spoiler, datatype=XSD.boolean)))
    rdf_graph.add((review_uri, MOVIE_NS.reviewBody, Literal(text)))

def sparql_query(query: str) -> str:
    """
    Execute a SPARQL query against the RDF graph.

    Args:
        query (str): The SPARQL query string.
    Returns:
        str: Formatted results of the SPARQL query.
    """
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: list(rdf_graph.query(query)))
            rows = future.result(timeout=SPARQL_TIMEOUT_SEC)
        if not rows:
            return "The query returned no results."

        output = []
        max_lines = 50
        for i, row in enumerate(rows[:max_lines], 1):
            output.append(f"{i}. " + " | ".join(str(v) for v in row))

        if len(rows) > max_lines:
            output.append(f"... ({len(rows) - max_lines} additional results)")

        return "\n".join(output)
    except concurrent.futures.TimeoutError:
        return (
            "SPARQL request too slow (timeout). "
            "Please simplify the query (fewer joins, "
            "stricter filters, add a LIMIT)."
        )
    except Exception as e:
        return f"SPARQL Error: {e}"

def get_graph_statistics() -> str:
    """
    Get basic statistics about the RDF graph.

    Returns:
        str: Formatted statistics about the RDF graph.
    """
    stats = [
        "RDF Graph Statistics:",
        f"- Total number of triples: {len(rdf_graph)}"
    ]

    type_query = """
        SELECT ?type (COUNT(?s) as ?count)
        WHERE { ?s a ?type . }
        GROUP BY ?type
        ORDER BY DESC(?count)
    """

    try:
        rows = list(rdf_graph.query(type_query))
        stats.append("\nResource Types:")
        for t, c in rows[:30]:
            stats.append(f"  - {t}: {c}")
        if len(rows) > 30:
            stats.append(f"  ... ({len(rows)-30} additional types)")
    except:
        pass

    return "\n".join(stats)

@tool
def sparql_query_tool(sparql_query_str: str) -> str:
    """
    Execute a SPARQL query against the RDF graph.

    Args:
        sparql_query_str (str): The SPARQL query string.
    Returns:
        str: Formatted results of the SPARQL query.
    """
    res = sparql_query(sparql_query_str)
    print(res, sparql_query_str)
    return res

@tool
def graph_statistics_tool() -> str:
    """
    Get basic statistics about the RDF graph.

    Returns:
        str: Formatted statistics about the RDF graph.
    """
    return get_graph_statistics()