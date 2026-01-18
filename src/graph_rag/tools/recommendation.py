import numpy as np
from langchain.tools import tool
from typing import List, Set, Tuple

from .common import index, meta, embed_one, rdf_graph

def get_user_movie_history(username: str, min_rating: float = 7.0) -> Tuple[List[Tuple[str, str, float]], Set[str]]:
    """
    Retrieve all movies with their synopsis that a user has rated above a certain threshold using SPARQL.

    Args:
        username (str): The username of the reviewer.
        min_rating (float): Minimum rating to consider a movie as "liked".

    Returns:
        Tuple[List[Tuple[str, str, float]], Set[str]]:
            - A list of tuples containing (movie_title, synopsis, rating) for movies the user liked.
            - A set of movie titles that the user has watched.
    """
    user_uri = f"<http://www.moviedb.fr/cinema#User/{username}>" 

    query = f"""
    PREFIX : <http://www.moviedb.fr/cinema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT DISTINCT ?movieTitle ?rating ?synopsis
    WHERE {{
        {user_uri} a :User .
        ?review a :Review ;
                :writtenBy {user_uri} ;
                :ratingValue ?rating ;
                :isReviewOf ?movie .
        ?movie a :Movie ;
                :primaryTitle ?movieTitle .
        
        OPTIONAL {{
            ?movie :synopsis ?synopsis .
            FILTER (xsd:float(?rating) > {min_rating})
        }}
    }}
    """
    
    liked_movies = {}
    watched_titles = set()

    try:
        results = list(rdf_graph.query(query))

        for row in results:
            movie_title = str(row[0])

            try:
                rating = float(row[1])
            except Exception as e:
                print(f"Error parsing rating for '{movie_title}': {e}")
                continue
            
            synopsis = str(row[2]) if row[2] is not None else ""

            watched_titles.add(movie_title.lower())

            if rating >= min_rating and movie_title not in liked_movies:
                liked_movies[movie_title] = (movie_title, synopsis, rating)

    except Exception as e:
        print(f"Error fetching liked movies for '{username}': {e}")
        return [], set()
    
    return list(liked_movies.values()), watched_titles

def recommend_movies(
    username: str,
    min_rating: float = 7.0,
    k: int = 10,
    exclude_watched: bool = True
) -> str:
    """
    Recommend movies to a user based on their liked movies.

    This function:
    1. Retrieves all movies (with synopsis) the user has rated above min_rating via SPARQL
    2. Creates embeddings for these synopses
    3. Computes the average embedding vector
    4. Finds k nearest movies to this average (excluding already watched)

    Args:
        username (str): The username of the reviewer.
        min_rating (float): Minimum rating to consider a movie as "liked" (default: 7.0).
        k (int): Number of recommendations to return (default: 10).
        exclude_watched (bool): Whether to exclude movies already watched by the user.

    Returns:
        Tuple[List[dict], List[Tuple[str, float]]]:
            - A list of recommendation dictionaries.
            - A list of tuples of valid movies (title, rating).
    """
    liked_movies, watched_titles = get_user_movie_history(username, min_rating)
    
    if not liked_movies:
        return [], []

    embeddings = []
    valid_movies = []
    
    for movie_title, synopsis, rating in liked_movies:
        if synopsis and len(synopsis.strip()) > 0:
            try:
                emb = embed_one(synopsis)
                embeddings.append(emb)
                valid_movies.append((movie_title, rating))
            except Exception as e:
                print(f"Error embedding synopsis for '{movie_title}': {e}")
                continue
    
    if not embeddings:
        return [], []
    
    avg_embedding = np.mean(embeddings, axis=0).astype('float32')
    
    norm = np.linalg.norm(avg_embedding)
    if norm > 0:
        avg_embedding = avg_embedding / norm
    
    search_k = k * 3 if exclude_watched else k
    scores, ids = index.search(avg_embedding.reshape(1, -1), search_k)
    
    recommendations = []
    for i, s in zip(ids[0], scores[0]):
        if int(i) == -1:
            continue
        
        row = meta.iloc[int(i)]
        title = row.get("primaryTitle", "N/A")
        
        # Skip if already watched
        if exclude_watched and title.lower() in watched_titles:
            continue
        
        year = row.get("startYear", "N/A")
        tconst = row.get("tconst", "N/A")
        genres = row.get("genres", "N/A")
        synopsis = (row.get("synopsis") or "").strip()
        
        recommendation = {
            'title': title,
            'year': year,
            'tconst': tconst,
            'score': float(s),
            'genres': genres,
            'synopsis': synopsis
        }
        recommendations.append(recommendation)
        
        if len(recommendations) >= k:
            break
    
    return recommendations, valid_movies

def format_recommendations(recommendations: List[dict], username: str, valid_movies: List[tuple], min_rating: float, k: int) -> str:
    """
    Format a list of recommendation dictionaries into a readable string.

    Args:
        recommendations (List[dict]): List of recommendation dictionaries.
        username (str): The username for whom recommendations are made.
        valid_movies (List[tuple]): List of tuples of valid movies (title, rating).
        min_rating (float): Minimum rating threshold.
        k (int): Number of recommendations.

    Returns:
        str: Formatted string of recommendations.
    """
    if len(recommendations) == 0:
        return f"No recommendations could be made for user '{username}'."

    results = []
    results.append(f"🎬 Recommendations for {username} (based on {len(valid_movies)} liked movies)")
    results.append(f"📊 Minimum rating: {min_rating}/10")
    results.append(f"\nReference movies ({len(valid_movies)}):")
    for movie_title, rating in valid_movies[:5]:
        results.append(f"  • {movie_title} ({rating}/10)")
    if len(valid_movies) > 5:
        results.append(f"  ... and {len(valid_movies) - 5} more liked movies.")
    
    results.append(f"\n{'='*60}")
    results.append(f"🎯 Top {k} recommendations:\n")

    for rank, rec in enumerate(recommendations, 1):
        results.append(f"{rank}. {rec['title']} ({rec['year']}) — score={rec['score']:.3f}")
        results.append(f"   ID: {rec['tconst']} | Genres: {rec['genres']}")
        if rec['synopsis']:
            synopsis_preview = rec['synopsis'][:200].replace('\n', ' ')
            results.append(f"   📝 {synopsis_preview}{'...' if len(rec['synopsis']) > 200 else ''}")
        results.append("")
    return "\n".join(results)

@tool
def user_recommendation_tool(username: str, min_rating: float = 7.0, k: int = 10) -> str:
    """
    Recommend movies to a user based on their liked movies.
    
    This function analyzes all movies a user has liked (rated >= min_rating),
    computes the average of their embeddings, then finds the most similar movies
    that the user hasn't seen yet.
    
    Args:
        username: The username (reviewer) for whom to make recommendations.
        min_rating: Minimum rating to consider a movie liked (default 7.0).
        k: Number of recommendations to return (default 10).
    
    Returns:
        str: Formatted list of movie recommendations.
    
    Examples:
        - user_recommendation_tool("OriginalMovieBuff21", 8.0, 5)
        - user_recommendation_tool("sentra14", 7.0)
    """

    recommendations, valid_movies = recommend_movies(username, min_rating, k, exclude_watched=True)
    return format_recommendations(recommendations, username, valid_movies, min_rating=min_rating, k=k)