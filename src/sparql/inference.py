import os
from rdflib import Graph
from owlrl import DeductiveClosure, OWLRL_Semantics

g = Graph()

# Load ontology triples
for file in os.listdir("turtle/ontology"):
    file_path = os.path.join("turtle/ontology", file)
    if os.path.isfile(file_path) and file.endswith(".ttl"):
        print(f"Loading {file_path}...")
        g.parse(file_path, format="turtle")

# Load alignment files
for file in os.listdir("turtle/ontology/alignment"):
    file_path = os.path.join("turtle/ontology/alignment", file)
    if os.path.isfile(file_path):
        if file.endswith(".ttl"):
            print(f"Loading {file_path}...")
            g.parse(file_path, format="turtle")
        elif file.endswith(".rdf"):
            print(f"Loading {file_path}...")
            g.parse(file_path, format="xml")

# Add data triples
g.parse("rdf_graph/triplets/data.ttl", format="turtle")

# Load person data from multiple files
for file in os.listdir("rdf_graph/persons"):
    if file.endswith(".ttl"):
        print(f"Loading {os.path.join("rdf_graph/persons", file)}...")
        g.parse(os.path.join("rdf_graph/persons", file), format="turtle")

DeductiveClosure(OWLRL_Semantics).expand(g)

g.serialize(destination="export_with_inference.ttl", format="turtle")