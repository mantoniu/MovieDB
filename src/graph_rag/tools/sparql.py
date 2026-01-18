from langchain.tools import tool
from rdflib import Literal, URIRef
from rdflib.namespace import RDF, XSD

from .common import rdf_graph
from ..config import MOVIE_NS, REVIEW_NS

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
        rows = list(rdf_graph.query(query))
        if not rows:
            return "The query returned no results."

        output = []
        max_lines = 50
        for i, row in enumerate(rows[:max_lines], 1):
            output.append(f"{i}. " + " | ".join(str(v) for v in row))

        if len(rows) > max_lines:
            output.append(f"... ({len(rows) - max_lines} additional results)")

        return "\n".join(output)
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
    return sparql_query(sparql_query_str)

@tool
def graph_statistics_tool() -> str:
    """
    Get basic statistics about the RDF graph.

    Returns:
        str: Formatted statistics about the RDF graph.
    """
    return get_graph_statistics()

if __name__ == "__main__":
    # Choisis un movie_id existant dans ton graphe
    movies = get_movies()
    if not movies:
        raise SystemExit("No movies found in graph. Cannot run insert_review test.")

    # Prend le premier film par ordre alphabétique (vu que get_movies() ORDER BY ?title)
    movie_id, movie_title = next(iter(movies.items()))

    username = "dbgeorge"
    text = "Test review from __main__."
    rating = 8.7
    spoiler = False

    # Compte avant
    count_before = int(list(rdf_graph.query("""
        PREFIX : <http://www.moviedb.fr/cinema#>
        SELECT (COUNT(?r) AS ?c) WHERE { ?r a :Review . }
    """))[0][0])

    # Insère
    insert_review(
        movie_id=movie_id,
        rating=rating,
        spoiler=spoiler,
        text=text,
        username=username,
    )

    # Recalcule les URIs pour vérifier exactement la review qu'on vient d'ajouter
    review_id = f"review_{hash((movie_id, username, text)) & 0xFFFFFFFF}"
    review_uri = REVIEW_NS[review_id]
    user_uri = URIRef(f"http://www.moviedb.fr/cinema#User/{username}")
    movie_uri = URIRef(f"http://www.moviedb.fr/cinema#MotionPicture/{movie_id}")

    # Compte après
    count_after = int(list(rdf_graph.query("""
        PREFIX : <http://www.moviedb.fr/cinema#>
        SELECT (COUNT(?r) AS ?c) WHERE { ?r a :Review . }
    """))[0][0])

    print(f"Reviews before: {count_before} | after: {count_after} | delta: {count_after - count_before}")

    # Test booléen "ça existe vraiment ?"
    ask_query = f"""
        PREFIX : <http://www.moviedb.fr/cinema#>

        ASK {{
            <{review_uri}> a :Review ;
                :isReviewOf <{movie_uri}> ;
                :writtenBy <{user_uri}> ;
                :ratingValue "{float(rating)}"^^xsd:float ;
                :isSpoiler "{str(spoiler).lower()}"^^xsd:boolean ;
                :reviewBody {Literal(text).n3()} .
        }}
    """
    # Note: on doit déclarer xsd sinon ASK peut échouer selon le parser
    ask_query = "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n" + ask_query

    exists = bool(rdf_graph.query(ask_query))
    print(f"Inserted review exists (ASK): {exists}")

    if not exists:
        raise AssertionError("Insert review test failed: expected triples not found.")

    # Affiche la review insérée (preuve humaine)
    select_query = f"""
        PREFIX : <http://www.moviedb.fr/cinema#>

        SELECT ?review ?movie ?rating ?spoiler ?text ?user WHERE {{
            BIND(<{review_uri}> AS ?review)
            ?review a :Review ;
                    :isReviewOf ?movie ;
                    :ratingValue ?rating ;
                    :isSpoiler ?spoiler ;
                    :reviewBody ?text ;
                    :writtenBy ?user .
        }}
    """
    print("Inserted review (SELECT):")
    print(sparql_query(select_query))

    # Bonus: affiche 5 dernières reviews
    last_query = """
        PREFIX : <http://www.moviedb.fr/cinema#>

        SELECT ?review ?movie ?rating ?spoiler ?text ?user WHERE {
            ?review a :Review ;
                    :isReviewOf ?movie ;
                    :ratingValue ?rating ;
                    :isSpoiler ?spoiler ;
                    :reviewBody ?text ;
                    :writtenBy ?user .
        }
        ORDER BY DESC(STR(?review))
        LIMIT 5
    """
    print("Last 5 reviews:")
    print(sparql_query(last_query))

