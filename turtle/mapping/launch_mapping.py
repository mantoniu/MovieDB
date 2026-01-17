import subprocess
import os
from pathlib import Path

def run_rml_mappings():

    mapping_config = {
        "mapping_concept": "./turtle/ontology",
        "mapping_data": "./rdf_graph/",
        "mapping_ontology": "./turtle/ontology"
    }
    
    input_dir = "./turtle/mapping"
    current_dir = os.getcwd()

    for full_name, target_output_dir in mapping_config.items():
        short_name = full_name.split('_')[-1]
        
        Path(target_output_dir).mkdir(parents=True, exist_ok=True)
        
        input_file = f"{input_dir}/{full_name}.ttl"
        output_file = f"{target_output_dir}/{short_name}.ttl"
        
        print(f"--- Traitement de {full_name} ---")
        print(f"Entrée  : {input_file}")
        print(f"Sortie  : {output_file}")

        command = [
            "docker", "run", "--rm",
            "-v", f"{current_dir}:/data",
            "rmlio/rmlmapper-java:latest",
            "--mappingfile", f"/data/{input_file}",
            "--outputfile", f"/data/{output_file}",
            "--serialization", "turtle"
        ]

        try:
            subprocess.run(command, check=True)
            print(f"Succès : {short_name}.ttl généré dans {target_output_dir}\n")
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors du traitement de {full_name} : {e}\n")

if __name__ == "__main__":
    run_rml_mappings()