import os
import re
import time
import pandas as pd
from rdflib import Graph
from pyshacl import validate
from google import genai
from google.genai import types

from utils import get_wikipedia_section

NAME_BASICS_FILE = "./datasets/reduced/name.basics.tsv"
ONTOLOGY_PATH = "./turtle/ontology/person.ttl"
SHACL_PATH = "./turtle/shacl/person.ttl"
OUTPUT_DIR = "./rdf_graph/persons"

START_INDEX = 1
PERSON_NUMBER = 500

API_KEY = ""
client = genai.Client(api_key=API_KEY)

MAX_FIX_ATTEMPTS = 3
MODEL_NAME = "gemini-2.5-flash"

def strip_markdown_fences(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("```turtle", "")
            .replace("```ttl", "")
            .replace("```", "")
            .strip()
    )

def call_gemini_api(prompt, temperature=0.0):
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature)
        )
        return response.text or ""
    except Exception as e:
        print(f"API call error: {e}")
        return ""

def get_generate_prompt(ontology, shacl, biography, name, nconst):
    return f"""
You are a Semantic Web and RDF expert.

TASK:
Convert the provided biography text into RDF Turtle format (.ttl) for the person: {name} (URI: <http://www.moviedb.fr/cinema#{nconst}>).

CONTEXT (ONTOLOGY Definitions):
{ontology}

SHACL CONSTRAINTS:
{shacl}

INSTRUCTIONS:
1) Main Subject: Use <http://www.moviedb.fr/cinema#{nconst}> as the Subject URI for the main person.
2) Object properties: never use strings as objects. Create URIs in strict snake_case.
3) Define every new URI at the bottom with rdf:type and :name.
4) Years: use "YYYY"^^xsd:gYear.
5) Respect EVERY SHACL constraint strictly.
6) If information is missing/uncertain, OMIT the triple rather than guessing.

INPUT TEXT:
{biography}

OUTPUT:
Return ONLY valid Turtle. No markdown fences.
"""

def shacl_validate(data_ttl: str, shacl_ttl: str):
    data_graph = Graph()
    shacl_graph = Graph()

    # Parse
    data_graph.parse(data=data_ttl, format="turtle")
    shacl_graph.parse(data=shacl_ttl, format="turtle")

    conforms, report_graph, report_text = validate(
        data_graph=data_graph,
        shacl_graph=shacl_graph,
        inference="rdfs",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
        meta_shacl=False,
        advanced=True
    )
    return conforms, report_text

def get_fix_prompt(ontology, shacl, biography, name, nconst, bad_ttl, shacl_report):
    return f"""
You are a Semantic Web + SHACL validation expert.

We generated Turtle data for: {name} (<http://www.moviedb.fr/cinema#{nconst}>), but it DOES NOT conform to SHACL.

ONTOLOGY (context):
{ontology}

SHACL SHAPES:
{shacl}

BIOGRAPHY (source text):
{biography}

SHACL VALIDATION REPORT (what is wrong):
{shacl_report}

BAD TURTLE (to fix):
{bad_ttl}

TASK:
Return a corrected Turtle document that:
- Conforms to ALL SHACL constraints.
- Keeps as much correct data as possible.
- Removes or fixes invalid triples.
- Uses correct datatypes (xsd:gYear, xsd:string, etc.).
- Defines all new URIs with rdf:type and :name.
- If some required info is not present in the biography, omit the triple rather than inventing it.

OUTPUT:
Return ONLY valid Turtle. No markdown fences.
"""

def safe_filename(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9_\-]", "", name)
    return name[:80] if name else "unknown"

if __name__ == "__main__":
    if not API_KEY:
        raise RuntimeError("Missing GOOGLE_API_KEY env var")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(ONTOLOGY_PATH, "r", encoding="utf-8") as f:
        ontology = f.read()
    with open(SHACL_PATH, "r", encoding="utf-8") as f:
        shacl = f.read()

    df = pd.read_csv(
        NAME_BASICS_FILE,
        sep="\t",
        usecols=["nconst", "primaryName"],
        skiprows=range(1, START_INDEX + 1),
        nrows=PERSON_NUMBER
    )

    for _, row in df.iterrows():
        name = row["primaryName"]
        nconst = row["nconst"]

        print(f"\nProcessing: {name} ({nconst})")
        biography = get_wikipedia_section("Biographie", name)
        if not biography:
            print("Biography not found. Skipping.")
            continue

        prompt = get_generate_prompt(ontology, shacl, biography, name, nconst)
        ttl = strip_markdown_fences(call_gemini_api(prompt))
        if not ttl:
            print("Empty TTL returned. Skipping.")
            continue

        for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
            try:
                conforms, report = shacl_validate(ttl, shacl)
            except Exception as e: 
                conforms = False
                report = f"Parser error / invalid Turtle: {e}"

            if conforms:
                print(f"SHACL OK (attempt {attempt}).")
                break

            print(f"SHACL FAIL (attempt {attempt}) with error: {report}. Asking AI to fix...")
            fix_prompt = get_fix_prompt(ontology, shacl, biography, name, nconst, ttl, report)
            ttl = strip_markdown_fences(call_gemini_api(fix_prompt, temperature=0.0))

            time.sleep(0.4)

        if not ttl:
            print("No TTL after fixes. Skipping.")
            continue
        
        if conforms:
            out = f"{OUTPUT_DIR}/{nconst}_{safe_filename(name)}.ttl"
            with open(out, "w", encoding="utf-8") as f:
                f.write(ttl)
            print(f"Saved: {out}")