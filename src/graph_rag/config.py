import os
from pathlib import Path
from rdflib import Namespace

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent.parent

OUT_DIR = MODULE_DIR / "synopsis_index"
INDEX_PATH = str(OUT_DIR / "synopsis.index.faiss")
META_PATH = str(OUT_DIR / "synopsis.meta.parquet")
RDF_GRAPH_PATH = str(PROJECT_ROOT / "export_with_inference.ttl")

EMBED_MODEL = "gemini-embedding-001"
CHAT_MODEL = "gemini-2.5-flash"

MOVIE_NS = Namespace("http://www.moviedb.fr/cinema#")
REVIEW_NS = Namespace("http://www.moviedb.fr/cinema#Review/")