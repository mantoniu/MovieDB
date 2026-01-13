import re

def extract_rdf_subset(input_path, output_path, classes, limit=10):
    """
    Extrait un sous-ensemble d'un fichier Turtle (.ttl)
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Extraction des préfixes (l'en-tête du fichier)
    prefixes = re.findall(r'@prefix.*', content)
    
    # 2. Extraction des blocs d'entités
    # Recherche les motifs : <URI> a Classe; ... .
    # Le flag re.DOTALL permet de capturer sur plusieurs lignes
    blocks = re.findall(r'(<[^>]+>\s+a\s+[^;]+;.*?\s\.)', content, re.DOTALL)
    
    subset = []
    counts = {cls: 0 for cls in classes}
    # 3. Filtrage par classe
    for block in blocks:
        for cls in classes:
            # On vérifie si le bloc appartient à la classe et si le quota n'est pas atteint
            if f'a {cls}' in block and counts[cls] < limit:
                subset.append(block)
                counts[cls] += 1
                break # Passe au bloc suivant dès qu'une classe est trouvée
        
        # Optionnel : Arrêt si toutes les classes ont atteint le quota
        if all(count >= limit for count in counts.values()):
            break
            
    # 4. Écriture du nouveau fichier
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Fichier extrait automatiquement\n")
        for p in prefixes:
            f.write(p + '\n')
        f.write('\n')
        for b in subset:
            f.write(b + '\n\n')
    
    print(f"Extraction terminée : {output_path} créé avec {len(subset)} éléments.")

# Configuration
target_classes = [':Review', ':MotionPicture', ':Agent', ':Role', ':Job']
extract_rdf_subset('output.ttl', 'subset_output.ttl', target_classes, limit=10)