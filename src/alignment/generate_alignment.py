import xml.etree.ElementTree as ET
from rdflib import Graph, URIRef, Namespace, OWL, RDFS
import os
import subprocess
import tempfile

JAVA_EXE = r"C:/Program Files/Amazon Corretto/jdk1.8.0_422/bin/java.exe"
AML_JAR = "./AML_v3.2/AgreementMakerLight.jar"
ONTOLOGY_DIR = "./turtle/ontology/"
MOVIEDB = Namespace("http://www.moviedb.fr/cinema#")

def run_aml_match(source_path, target_path, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cmd = [
        JAVA_EXE, "-Xmx4g", "-jar", AML_JAR,
        "-s", source_path,
        "-t", target_path,
        "-o", output_path,
        "-m"
    ]
    try:
        subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
        print(f"   RDF genere : {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"   Erreur AML : {e}")

def merge_to_final_ttl(tasks, final_path):
    g_final = Graph()
    g_final.bind("owl", OWL)
    g_final.bind("moviedb", MOVIEDB)
    ns = {'align': 'http://knowledgeweb.semanticweb.org/heterogeneity/alignment',
          'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'}
    count = 0
    for target_path, info in tasks.items():
        xml_path = info["output"]
        threshold = info["threshold"]
        if not os.path.exists(xml_path):
            continue
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for cell in root.findall('.//align:map/align:Cell', ns):
            measure_node = cell.find('align:measure', ns)
            if measure_node is None:
                continue
            measure = float(measure_node.text)
            if measure >= threshold:
                ent1 = cell.find('align:entity1', ns).get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
                ent2 = cell.find('align:entity2', ns).get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
                subj, obj = URIRef(ent1), URIRef(ent2)
                local_name = ent1.split('#')[-1]
                if local_name and local_name[0].isupper():
                    g_final.add((subj, OWL.equivalentClass, obj))
                else:
                    g_final.add((subj, OWL.equivalentProperty, obj))
                count += 1
    g_final.serialize(destination=final_path, format="turtle")
    print(f"Operation terminee : {count} liens crees.")

if __name__ == "__main__":
    for filename in os.listdir(ONTOLOGY_DIR):
        if filename.endswith(".ttl"):
            SOURCE_ONT_TTL = os.path.join(ONTOLOGY_DIR, filename)
            name = os.path.splitext(filename)[0]
            
            ALIGNMENT_TASKS = {
                "./turtle/ontology/owl/schema.owl": {"output": f"./src/alignment/{name}_aml_schema.rdf", "threshold": 0.8},
                "./turtle/ontology/owl/movies.owl": {"output": f"./src/alignment/{name}_aml_movies.rdf", "threshold": 0.9},
                "./turtle/ontology/owl/dbpedia.owl": {"output": f"./src/alignment/{name}_aml_dbpedia.rdf", "threshold": 0.8},
            }
            OUTPUT_FINAL_TTL = f"./turtle/ontology/alignment/{name}_alignement.ttl"

            print(f"Traitement du fichier : {filename}")
            g_src = Graph()
            g_src.parse(SOURCE_ONT_TTL, format="turtle")
            
            with tempfile.NamedTemporaryFile(suffix=".owl", delete=False) as tmp:
                temp_owl_path = tmp.name
                g_src.serialize(destination=temp_owl_path, format="xml")
            
            try:
                for target_ont, info in ALIGNMENT_TASKS.items():
                    if os.path.exists(target_ont):
                        run_aml_match(temp_owl_path, target_ont, info["output"])
                    else:
                        print(f"Cible introuvable : {target_ont}")

                os.makedirs(os.path.dirname(OUTPUT_FINAL_TTL), exist_ok=True)
                merge_to_final_ttl(ALIGNMENT_TASKS, OUTPUT_FINAL_TTL)

            finally:
                if os.path.exists(temp_owl_path):
                    os.remove(temp_owl_path)

    print("Traitement de tous les fichiers termine.")