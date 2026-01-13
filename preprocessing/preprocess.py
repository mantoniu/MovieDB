import json
import csv
import os
import re

# Configuration
csv.field_size_limit(10**9)
N_MOVIES = 50

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(BASE_DIR, 'datasets')
OUTPUT_DIR = os.path.join(DATASETS_DIR, 'reduced')

SAMPLE_FILE = os.path.join(DATASETS_DIR, 'sample.json')
TITLE_BASICS_FILE = os.path.join(DATASETS_DIR, 'title.basics.tsv')
TITLE_PRINCIPALS_FILE = os.path.join(DATASETS_DIR, 'title.principals.tsv')
NAME_BASICS_FILE = os.path.join(DATASETS_DIR, 'name.basics.tsv')

SAMPLE_OUTPUT = os.path.join(OUTPUT_DIR, 'sample.json')
TITLE_BASICS_OUTPUT = os.path.join(OUTPUT_DIR, 'title.basics.tsv')
TITLE_PRINCIPALS_OUTPUT = os.path.join(OUTPUT_DIR, 'title.principals.tsv')
NAME_BASICS_OUTPUT = os.path.join(OUTPUT_DIR, 'name.basics.tsv')


class Preprocessing:
    
    @staticmethod
    def normalize_title(title):

        if not title:
            return ""
        return re.sub(r'\s*\(\d{4}.*?\)', '', title).strip()
    
    @staticmethod
    def normalize_title_date(title):

        if not title:
            return ""
        return re.sub(r'^(\s*.*?\(\d{4}).*$', r'\1', title).strip() + ")"


class Reduction:
    
    @staticmethod
    def reduce_sample(input_path, output_path, n_movies):
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
            
            clean_title = Preprocessing.normalize_title(raw_title)
            
            if clean_title in seen_movies:
                entry["movie"] = Preprocessing.normalize_title_date(entry["movie"])
                entry["review_detail"] = entry["review_detail"].replace("^^", "^ ^")
                if entry["helpful"][1] == "0":
                    entry["helpful_ratio"] = 0
                else:
                    entry["helpful_ratio"] =  (int(entry["helpful"][0].replace(",", ""))/int(entry["helpful"][1].replace(",", ""))) *100
                reduced_data.append(entry)
            else:
                if len(seen_movies) < n_movies:
                    seen_movies.add(clean_title)
                    target_titles.add(Preprocessing.normalize_title_date(entry["movie"]))
                    entry["movie"] = Preprocessing.normalize_title_date(entry["movie"])
                    entry["review_detail"] = entry["review_detail"].replace("^^", "^ ^")
                    if entry["helpful"][1] == "0":
                        entry["helpful_ratio"] = 0
                    else:
                        entry["helpful_ratio"] =  (int(entry["helpful"][0].replace(",", ""))/int(entry["helpful"][1].replace(",", ""))) *100
                    reduced_data.append(entry)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(reduced_data, f, indent=4)
        
        print(f"Saved {len(reduced_data)} reviews ({len(seen_movies)} movies) to {output_path}")
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
        filtered_data = [
            {**entry, "movie": Preprocessing.normalize_title(entry["movie"]), "review_detail": entry["review_detail"].replace("^^", "^ ^")}
            for entry in data
            if entry.get('movie') in title_lookup
        ]
        
        os.makedirs(os.path.dirname(input_path), exist_ok=True)
        with open(input_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, indent=4)
        
        print(f"Commentaires supprimés : {initial_count - len(filtered_data)}")
    
    @staticmethod
    def filter_imdb_datasets(titles_to_keep):
        print("Starting IMDB datasets filtering...")
        
        valid_tconsts = set()
        different_names = set()
        valid_types = {"movie", "tvMovie", "tvSeries", "tvSpecial"}
        
        # Filter title.basics.tsv
        if os.path.exists(TITLE_BASICS_FILE):
            print(f"Filtering {TITLE_BASICS_FILE}...")
            with open(TITLE_BASICS_FILE, 'r', encoding='utf-8') as fin, \
                 open(TITLE_BASICS_OUTPUT, 'w', encoding='utf-8', newline='') as fout:
                
                reader = csv.DictReader(fin, delimiter='\t')
                writer = csv.DictWriter(fout, fieldnames=reader.fieldnames, delimiter='\t')
                writer.writeheader()
                
                for row in reader:
                    if row["titleType"] not in valid_types:
                        continue
                    
                    title_with_year = f"{row['primaryTitle']} ({row['startYear']})"
                    original_with_year = f"{row['originalTitle']} ({row['startYear']})"
                    
                    if title_with_year in titles_to_keep or original_with_year in titles_to_keep:
                        different_names.add(row['primaryTitle'])
                        valid_tconsts.add(row['tconst'])
                        writer.writerow(row)
            
            print(f"Kept {len(different_names)} titles from title.basics.tsv")
        else:
            print(f"Warning: {TITLE_BASICS_FILE} not found.")
        
        # Filter title.principals.tsv
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
        
        # Filter name.basics.tsv
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

print("=== Starting Dataset Reduction and Preprocessing ===")

titles = Reduction.reduce_sample(SAMPLE_FILE, SAMPLE_OUTPUT, N_MOVIES)
print(f"Total titles: {len(titles)}")

Reduction.filter_imdb_datasets(titles)
Reduction.filter_sample(SAMPLE_OUTPUT, TITLE_BASICS_OUTPUT)

print("\nProcessing complete. Reduced datasets are in 'datasets/reduced/'")