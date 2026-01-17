from utils import get_wikipedia_section
import pandas as pd
import requests
from tqdm import tqdm
from pathlib import Path

TITLE_BASICS_FILE = "./datasets/reduced/title.basics.tsv"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

tqdm.pandas()

def imdb_to_wikipedia_title(tconst, lang="fr"):
    query = f"""
    SELECT ?article WHERE {{
      ?item wdt:P345 "{tconst}" .
      ?article schema:about ?item ;
               schema:isPartOf <https://{lang}.wikipedia.org/> .
    }}
    LIMIT 1
    """

    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "MovieDB (antoine-marie.michelozzi@etu.unice.fr)"
    }

    r = requests.get(
        WIKIDATA_SPARQL,
        params={"query": query},
        headers=headers,
        timeout=20
    )
    r.raise_for_status()
    data = r.json()

    bindings = data["results"]["bindings"]
    if not bindings:
        return None

    url = bindings[0]["article"]["value"]
    return url.split("/wiki/")[-1]

if __name__ == "__main__":
    in_path = Path(TITLE_BASICS_FILE)
    out_path = in_path.with_name(in_path.stem + ".with_synopsis.tsv")

    df = pd.read_csv(
        in_path,
        sep="\t",
        dtype=str,
        na_values="\\N"
    )

    # on garde toutes les colonnes, on filtre juste les lignes
    df = df[df["titleType"] == "movie"].copy()

    # caches (pour éviter des appels multiples sur les mêmes valeurs)
    tconst_to_wp = {}
    wp_to_synopsis = {}

    def resolve_wp(tconst):
        if tconst in tconst_to_wp:
            return tconst_to_wp[tconst]
        wp = imdb_to_wikipedia_title(tconst, lang="fr")
        tconst_to_wp[tconst] = wp
        return wp

    def resolve_synopsis(wp_title):
        if not wp_title:
            return None
        if wp_title in wp_to_synopsis:
            return wp_to_synopsis[wp_title]
        syn = get_wikipedia_section("Synopsis", wp_title)
        wp_to_synopsis[wp_title] = syn
        return syn

    print("Resolving Wikipedia titles and synopses...")
    df["wikipedia_title"] = df["tconst"].progress_apply(resolve_wp)

    print("All titles resolved. Now resolving synopses...")
    df["synopsis"] = df["wikipedia_title"].progress_apply(resolve_synopsis)

    print("All synopses resolved.")

    df = df.drop(columns=["wikipedia_title"])
    df.to_csv(out_path, sep="\t", index=False)
    print(f"Saved: {out_path}")
