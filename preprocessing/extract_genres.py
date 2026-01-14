from preprocess import TITLE_BASICS_FILE
import pandas as pd
import json

from google import genai
from google.genai import types

API_KEY = "YOUR_API_KEY" 

client = genai.Client(api_key=API_KEY)

generate_genre_description_prompt = """
You are an expert Information Scientist and Film Archivist specializing in metadata standards.
Your task is to draft precise definitions for movie genres to populate a SKOS (Simple Knowledge Organization System) thesaurus.

CONTEXT:
These definitions will be used as `skos:definition` properties. They must clearly distinguish one concept from another.

INSTRUCTIONS:
1. **Precision**: Define the genre based on its narrative elements, mood, or production style.
2. **Tone**: Encyclopedic, objective, and formal. Avoid subjective adjectives like "exciting" or "best".
3. **Format**: Output valid JSON only. Key = Genre Name, Value = Definition.
4. **Length**: Keep definitions concise (15-25 words max).

GENRES TO DEFINE:
{genres}
"""

def get_genres_descriptions(list_of_genres):
    prompt = generate_genre_description_prompt.format(genres=", ".join(list_of_genres))
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Erreur lors de l'appel API : {e}")
        return {}

def process_full_workflow(input_tsv, final_csv):
    df_raw = pd.read_csv(input_tsv, sep='\t', usecols=['genres'], low_memory=False)
    df_raw = df_raw[df_raw['genres'] != r'\N'].dropna()
    unique_genres = sorted(df_raw['genres'].str.split(',').explode().str.strip().unique())

    descriptions_dict = get_genres_descriptions(unique_genres)

    print(descriptions_dict)

    final_df = pd.DataFrame([
        {"genre": g, "description": descriptions_dict.get(g, "No description available.")}
        for g in unique_genres
    ])
    
    final_df.to_csv(final_csv, index=False, encoding='utf-8')

process_full_workflow(TITLE_BASICS_FILE, './datasets/genres.csv')