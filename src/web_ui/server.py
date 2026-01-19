import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

SRC_DIR = BASE_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph_rag.agent import chat
from graph_rag.tools.recommendation import recommend_movies
from graph_rag.tools.sparql import get_movies, insert_review

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")

MOVIE_MAP = get_movies()
MOVIE_IDS_SET = set(MOVIE_MAP.keys())
MOVIE_TITLE_TO_ID = {title.lower(): movie_id for movie_id, title in MOVIE_MAP.items()}

@app.get("/api/recommendations")
def recommendations() -> tuple:
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"error": "username is required"}), 400

    try:
        min_rating = float(request.args.get("min_rating", "7.0"))
    except ValueError:
        min_rating = 7.0

    try:
        k = int(request.args.get("k", "10"))
    except ValueError:
        k = 10

    try:
        recommendations, reference_movies = recommend_movies(
            username, min_rating=min_rating, k=k
        )
    except Exception as exc:
        return jsonify({"error": f"recommendation failed: {exc}"}), 500

    return jsonify(
        {
            "username": username,
            "min_rating": min_rating,
            "k": k,
            "recommendations": recommendations,
            "reference_movies": reference_movies,
        }
    )


@app.post("/api/chat")
def chat_endpoint() -> tuple:
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    try:
        result = chat(message)
    except Exception as exc:
        return jsonify({"error": f"chat failed: {exc}"}), 500

    return jsonify(result)


@app.get("/api/movies")
def movies_endpoint() -> tuple:
    return jsonify({"movies": MOVIE_MAP})


@app.post("/api/reviews")
def reviews_endpoint() -> tuple:
    payload = request.get_json(silent=True) or {}
    movie_id = str(payload.get("movie_id", "")).strip()
    title = str(payload.get("title", "")).strip()
    rating = payload.get("rating", None)
    spoiler = bool(payload.get("spoiler", False))
    text = str(payload.get("text", "")).strip()
    username = str(payload.get("username", "")).strip()

    if not movie_id and not title:
        return jsonify({"error": "movie_id is required"}), 400

    if not movie_id and title:
        movie_id = MOVIE_TITLE_TO_ID.get(title.lower(), "")

    if movie_id not in MOVIE_IDS_SET:
        return jsonify({"error": "movie_id is not in list"}), 400

    try:
        rating_value = float(rating)
    except (TypeError, ValueError):
        return jsonify({"error": "rating is required"}), 400

    if rating_value < 1 or rating_value > 10:
        return jsonify({"error": "rating must be between 1 and 10"}), 400

    resolved_title = MOVIE_MAP.get(movie_id, title)

    try:
        insert_review(movie_id, rating_value, spoiler, text, username)
    except Exception as exc:
        return jsonify({"error": f"failed to insert review: {exc}"}), 500

    return jsonify(
        {
            "status": "ok",
            "review": {
                "movie_id": movie_id,
                "title": resolved_title,
                "rating": rating_value,
                "spoiler": spoiler,
                "text": text,
                "username": username,
            },
        }
    )


@app.get("/")
def index() -> object:
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/app")
def app_page() -> object:
    return send_from_directory(STATIC_DIR, "app.html")


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    print(f"MovieDB UI server running on http://{host}:{port}")
    app.run(host=host, port=port)


if __name__ == "__main__":
    run_server()
