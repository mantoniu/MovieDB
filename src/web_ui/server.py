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

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")

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
