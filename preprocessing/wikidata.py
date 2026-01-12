import requests

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

HEADERS = {
    "Accept": "application/sparql+json",
    "User-Agent": "MovieDatasetLinker/1.0 (mailto:antoine-marie.michelozzi@etu.unice.fr)"
}

IMDB_TO_WIKIDATA = {
    "movie": "Q11424",
    "tvMovie": "Q506240",
    "tvSeries": "Q5398426",
    "tvMiniSeries": "Q1261214",
    "person": "Q5"
}

AUDIOVISUAL_WORK_QID = "Q2431196"

HUMAN_QID = "Q5"

def query_wikidata(title, qid):
    safe_title = title.replace('"', '\\"')

    query = f"""
    SELECT ?item WHERE {{
        ?item rdfs:label "{safe_title}"@en .
        ?item wdt:P31/wdt:P279* wd:{qid} .
    }}
    LIMIT 1
    """

    try:
        response = requests.get(WIKIDATA_SPARQL_URL, params={"query": query, "format": "json"}, headers=HEADERS, timeout=15)
        
        if response.status_code != 200: 
            return False
        
        data = response.json()
        bindings = data.get("results", {}).get("bindings", [])
        return bindings[0].get("item", {}).get("value", None) if bindings else None
    except:
        return False

def get_wikidata_item(title, category_key):    
    category_id = IMDB_TO_WIKIDATA.get(category_key, None)

    if category_id is None:
        print(f"Unknown category for key '{category_key}'.")
        return None
    
    print(f"Trying with category {category_key} ({category_id})...")
    result = query_wikidata(title, category_id)
    
    if result is None and category_key != "person":
        print(f"Not found. Attempting fallback to 'audiovisual work' ({AUDIOVISUAL_WORK_QID})...")
        result = query_wikidata(title, AUDIOVISUAL_WORK_QID)
        
    return result