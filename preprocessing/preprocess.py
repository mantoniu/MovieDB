import json
import csv
import os
import re
import sys

# Increase CSV field size limit just in case
csv.field_size_limit(10**9)

# Configuration
N_MOVIES = 50  # Number of Movies to keep
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(BASE_DIR, 'datasets')
OUTPUT_DIR = os.path.join(DATASETS_DIR, 'reduced')

# Input File Paths
SAMPLE_FILE = os.path.join(DATASETS_DIR, 'sample.json')
TITLE_BASICS_FILE = os.path.join(DATASETS_DIR, 'title.basics.tsv')
TITLE_PRINCIPALS_FILE = os.path.join(DATASETS_DIR, 'title.principals.tsv')
NAME_BASICS_FILE = os.path.join(DATASETS_DIR, 'name.basics.tsv')

# Output File Paths
SAMPLE_OUTPUT = os.path.join(OUTPUT_DIR, 'sample.json')
TITLE_BASICS_OUTPUT = os.path.join(OUTPUT_DIR, 'title.basics.tsv')
TITLE_PRINCIPALS_OUTPUT = os.path.join(OUTPUT_DIR, 'title.principals.tsv')
NAME_BASICS_OUTPUT = os.path.join(OUTPUT_DIR, 'name.basics.tsv')

class Preprocessing:
    """
    Handles data normalization and cleaning.
    """
    
    @staticmethod
    def normalize_title(title):
        """
        Removes the year and extra whitespace from the movie title.
        Example: 'The Matrix (1999)' -> 'The Matrix'
        """
        if not title:
            return ""
        # Remove (YYYY) at the end of the string
        return re.sub(r'\s*\(\d{4}.*?\)', '', title).strip()    

    @staticmethod
    def normalize_title_date(title):
        """
        Removes the year and extra whitespace from the movie title.
        Example: 'The Matrix (1999)' -> 'The Matrix'
        """
        if not title:
            return ""
        return re.sub(r'^(\s*.*?\(\d{4}).*$', r'\1', title).strip()+")" 
    
class Reduction:
    """
    Handles dataset reduction logic:
    1. Reducing the sample size to N items/movies.
    2. Filtering IMDB datasets based on the reduced sample.
    """
    
    @staticmethod
    def reduce_sample(input_path, output_path, n_movies):
        """
        Reads the sample json, takes the first n_movies unique movies,
        and saves a reduced json file.
        Returns the set of normalized titles for these movies.
        """
        print(f"Reading sample from {input_path}...")
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        seen_movies = set()
        target_titles = set()
        reduced_data = []
        
        print(f"Extracting first {n_movies} movies...")
        for entry in data:
            raw_title = entry.get('movie')
            if not raw_title:
                continue
            # Normalize title to check for uniqueness and for later matching
            clean_title = Preprocessing.normalize_title(raw_title)
            if clean_title in seen_movies:
                # We already decided to keep this movie, so we keep this review too
                entry["movie"] = Preprocessing.normalize_title_date(entry["movie"])
                reduced_data.append(entry)
            else:
                # New movie encountered
                if len(seen_movies) < n_movies:
                    seen_movies.add(clean_title)
                    target_titles.add(Preprocessing.normalize_title_date(entry["movie"]))
                    entry["movie"] = Preprocessing.normalize_title_date(entry["movie"])
                    reduced_data.append(entry)
                # If we reached the limit, we skip new movies
        
        # Save reduced sample
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(reduced_data, f, indent=4)
        
        print(f"Saved reduced sample with {len(reduced_data)} reviews ({len(seen_movies)} unique movies) to {output_path}")
        return target_titles

    @staticmethod
    def filter_sample(input_path, movie_path):
        title_lookup = set()
        if os.path.exists(movie_path):
            with open(movie_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    full_title = f"{row['primaryTitle']} ({row['startYear']})"
                    title_lookup.add(full_title)


        if not os.path.exists(input_path):
            print(f"Erreur : Le fichier {input_path} n'existe pas.")
            return

        print(f"Chargement du fichier JSON...")
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        initial_count = len(data)

        filtered_data = []

        for entry in data :
            if entry.get('movie') in title_lookup:
                entry["movie"] = Preprocessing.normalize_title(entry["movie"])
                filtered_data.append(entry)


        # Sauvegarde du résultat
        os.makedirs(os.path.dirname(input_path), exist_ok=True)
        with open(input_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, indent=4)

        print(f"Commentaires supprimés : {initial_count - len(filtered_data)}")

        
    @staticmethod
    def filter_imdb_datasets(titles_to_keep):
        """
        Filters IMDB TSV files to only include data related to the given titles.
        """
        print("Starting IMDB datasets filtering...")
        
        # 1. Filter title.basics.tsv -> Get tconsts
        valid_tconsts = set()
        different_names = set()
        if os.path.exists(TITLE_BASICS_FILE):
            print(f"Filtering {TITLE_BASICS_FILE}...")
            with open(TITLE_BASICS_FILE, 'r', encoding='utf-8') as fin, \
                 open(TITLE_BASICS_OUTPUT, 'w', encoding='utf-8', newline='') as fout:
                                
                reader = csv.DictReader(fin, delimiter='\t')
                writer = csv.DictWriter(fout, fieldnames=reader.fieldnames, delimiter='\t')
                writer.writeheader()
                
                for row in reader:
                    if (row["titleType"] != "movie" and row["titleType"] != "tvMovie" and row["titleType"] != "tvSeries" and row["titleType"] != "tvSpecial"):
                        continue
                    # Match against primaryTitle or originalTitle
                    if (f"{row['primaryTitle']} ({row['startYear']})" in titles_to_keep or 
                        f"{row['originalTitle']} ({row['startYear']}" in titles_to_keep):
                        different_names.add(row['primaryTitle'])
                        valid_tconsts.add(row['tconst'])
                        writer.writerow(row)
            print(f"Kept {len(different_names)} titles from title.basics.tsv")
        else:
            print(f"Warning: {TITLE_BASICS_FILE} not found.")

        # 2. Filter title.principals.tsv -> Get nconsts
        valid_nconsts = set()
        
        if os.path.exists(TITLE_PRINCIPALS_FILE):
            print(f"Filtering {TITLE_PRINCIPALS_FILE}...")
            with open(TITLE_PRINCIPALS_FILE, 'r', encoding='utf-8') as fin, \
                 open(TITLE_PRINCIPALS_OUTPUT, 'w', encoding='utf-8', newline='') as fout:
                
                reader = csv.DictReader(fin, delimiter='\t')
                writer = csv.DictWriter(fout, fieldnames=reader.fieldnames, delimiter='\t')
                writer.writeheader()
                
                for row in reader:
                    if row['tconst'] in valid_tconsts:
                        valid_nconsts.add(row['nconst'])
                        writer.writerow(row)
            print(f"Kept principals associated with reduced titles.")
        else:
            print(f"Warning: {TITLE_PRINCIPALS_FILE} not found.")

        # 3. Filter name.basics.tsv -> Using nconsts
        if os.path.exists(NAME_BASICS_FILE):
            print(f"Filtering {NAME_BASICS_FILE}...")
            with open(NAME_BASICS_FILE, 'r', encoding='utf-8') as fin, \
                 open(NAME_BASICS_OUTPUT, 'w', encoding='utf-8', newline='') as fout:
                
                reader = csv.DictReader(fin, delimiter='\t')
                writer = csv.DictWriter(fout, fieldnames=reader.fieldnames, delimiter='\t')
                writer.writeheader()
                
                for row in reader:
                    if row['nconst'] in valid_nconsts:
                        writer.writerow(row)
            print("Filtered name.basics.tsv.")
        else:
            print(f"Warning: {NAME_BASICS_FILE} not found.")

def main():
    print("=== Starting Dataset Reduction and Preprocessing ===")
    
    # Step 1: Reduce Sample
    # We get back the set of titles (normalized) that were kept
    titles = Reduction.reduce_sample(SAMPLE_FILE, SAMPLE_OUTPUT, N_MOVIES)
    print(len(titles))
    
    # Step 2: Filter IMDB Datasets using those titles
    Reduction.filter_imdb_datasets(titles)
    Reduction.filter_sample(SAMPLE_OUTPUT,TITLE_BASICS_OUTPUT)
    
    print("\nProcessing complete. Reduced datasets are in 'datasets/reduced/'")

if __name__ == "__main__":
    main()
