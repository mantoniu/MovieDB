import os
import wikipediaapi
import pandas as pd
from google import genai
from google.genai import types

NAME_BASICS_FILE = "./datasets/reduced/name.basics.tsv"
ONTOLOGY_PATH = "./turtle/ontology/person.ttl"
START_INDEX = 600
PERSON_NUMBER = 500
API_KEY = "YOUR_API_KEY" 

client = genai.Client(api_key=API_KEY)

wiki_wiki = wikipediaapi.Wikipedia(
    user_agent='MovieDB (antoine-marie.michelozzi@etu.unice.fr)',
    language='fr',
    extract_format=wikipediaapi.ExtractFormat.WIKI
)

def extract_section_text(section):
    text = section.text or ""
    for subsection in section.sections:
        text += "\n" + extract_section_text(subsection)
    return text

def get_biography(page_title):
    page = wiki_wiki.page(page_title)

    if not page.exists():
        return None

    bio_section = page.section_by_title("Biographie")

    if bio_section:
        return extract_section_text(bio_section)
    
    return None

def get_prompt(ontology, biography, name, nconst):
    return f"""
    You are a Semantic Web and RDF expert.

    TASK:
    Convert the provided biography text into RDF Turtle format (.ttl) for the person: {name} (URI: <http://www.moviedb.fr/cinema#{nconst}>).

    CONTEXT (ONTOLOGY Definitions):
    {ontology}

    INSTRUCTIONS:
    1. **Main Subject**: Use <http://www.moviedb.fr/cinema#{nconst}> as the Subject URI for the main person.
    
    2. **Object Properties (Relations)**: 
       - Do NOT use strings for object properties.
       - You MUST create new URIs for these entities based on their names.
       - Naming convention for new URIs: strict snake_case (e.g., "London" -> <http://www.moviedb.fr/cinema#london>, "Saint Ignatius College" -> <http://www.moviedb.fr/cinema#saint_ignatius_college>).

    3. **Entity Definition**:
       - When you create a NEW URI (for a place, organization, or person), you must define it at the bottom of the file.
       - Give it a type (a :Place, a :Organization, or a :Person).
       - Give it a :name property.
        - **CRITICAL:** If the biography contains details about these secondary entities (e.g., a parent's birth year, a city's country), add them ONLY IF a corresponding property exists in the provided ONTOLOGY. Do not invent properties.
    
    4. **Dates**: Use xsd:gYear for years.

    INPUT TEXT:
    {biography}

    OUTPUT FORMAT:
    Provide ONLY the raw Turtle code. No markdown code blocks. ensure prefixes are defined.
    """

def call_gemini_api(prompt):
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        return response.text
    except Exception as e:
        print(f"API call error: {e}")
        return ""

if __name__ == "__main__":
    if not os.path.exists('./datasets/biographies'):
        os.makedirs('./datasets/biographies')

    try:
        with open(ONTOLOGY_PATH, 'r', encoding='utf-8') as f:
            ontology = f.read()
    except FileNotFoundError:
        ontology = ""
        print("Ontology file not found.")

    df = pd.read_csv(
        NAME_BASICS_FILE, 
        sep='\t', 
        usecols=['nconst', 'primaryName'], 
        skiprows=range(1, START_INDEX + 1), 
        nrows=PERSON_NUMBER
    )

    for index, row in df.iterrows():
        name = row['primaryName']
        nconst = row['nconst']
        
        print(f"Processing: {name}")
        biography = get_biography(name)
        
        if biography is None:
            print(f"Biography not found for {name}. Skipping.")
            continue
        
        prompt = get_prompt(ontology, biography, name, nconst)
        rdf_result = call_gemini_api(prompt)
        
        clean_turtle = rdf_result.replace("```turtle", "").replace("```", "").strip()
        
        ttl_filename = f'./datasets/biographies/{nconst}_{name.replace(" ", "_")}.ttl'
        with open(ttl_filename, 'w', encoding='utf-8') as f:
            f.write(clean_turtle)
        
        print(f"RDF saved to {ttl_filename}")