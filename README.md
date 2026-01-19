# Web Sémantique – Projet MovieDB (Graphe de connaissances cinéma)

Projet de Web Sémantique visant à construire et exploiter un **graphe de connaissances centré sur le cinéma** (films, séries, téléfilms, personnes) enrichi par des **reviews utilisateurs**, avec :
- une **ontologie OWL** + un **thésaurus SKOS** (genres),
- une **validation SHACL**,
- des requêtes **SPARQL** d’analyse,
- un module de **recommandation (Link Prediction)** via embeddings + FAISS,
- une approche **Graph RAG** : *Text-to-SPARQL* + recommandation par embeddings.

**Auteurs** : Antoine-Marie Michelozzi, Jilian Lubrat  
**Date** : Janvier 2026

---

## Sommaire

- [Aperçu](#aperçu)
- [Données](#données)
- [Ontologie & Modélisation](#ontologie--modélisation)
- [Construction du graphe](#construction-du-graphe)
- [Alignement & Liage](#alignement--liage)
- [Exploitation (SPARQL)](#exploitation-sparql)
- [Recommandation (Link Prediction)](#recommandation-link-prediction)
- [Graph RAG](#graph-rag)
- [Interface](#interface)
- [Structure](#structure)
---

## Aperçu

L’objectif est de regrouper des informations sur :
- des **œuvres audiovisuelles** : *Movie*, *TvSeries*, *TvMovie*, *TvSpecial*,
- des **personnes** : acteurs, réalisateurs, producteurs, etc.
- des **reviews** (contenu, note, utilité, date, spoiler…).

Les reviews servent aussi de base à un **système de recommandation** :
- similarité sémantique via synopsis + embeddings,
- recommandations personnalisées par historique utilisateur,
- extension via Graph RAG et embeddings issus du graphe.

---

## Données

### Données structurées
- **Kaggle – IMDb Review Dataset (JSON)** : critiques avec id, reviewer, film, note (/10 si dispo), résumé, contenu, date, spoiler, “helpfulness votes”.
- **IMDb Non-Commercial Datasets (TSV)** : œuvres, personnes, contributions (liens œuvre ↔ personne, rôles, personnages…).

Le prétraitement se fait en cascade :
1. échantillonnage d’un ensemble d’œuvres,
2. filtrage des contributions associées,
3. filtrage des personnes associées,
4. jointure des reviews sur les titres.

### Données non structurées
- Extraction automatique de **biographies Wikipédia** (section “Biographie”) pour enrichir les personnes (études, conjoint, enfants, fratrie…).
- Génération de triplets conforme à l’ontologie et aux shapes via **LLM (gemini-2.5-flash)**, puis **validation pyshacl** avec boucle de correction si nécessaire.

---

## Ontologie & Modélisation

### Classes principales
- `:Item` → `:CreativeWork` → `:MotionPicture` → `:Movie`, `:TvSeries`, `:TvMovie`, `:TvSpecial` (**disjointes**).
- `:Agent` → `:Person`, `:Organization`.
- Métiers : `:Actor`, `:Director`, `:Producer`, `:Writer`… (sous-classes de `:Person`).
- Certaines classes sont **inférées** à partir des relations (ex. une personne est `:Director` si elle a dirigé au moins une œuvre).

### Propriétés & inférences OWL
- Propriétés symétriques/irréflexives (ex. `:hasSpouse`, `:hasSibling`).
- Transitivité (ex. `:hasDescendant`).
- Inverses (ex. `:directed` / `:hasDirector`) et hiérarchie (`:hasDirector`, `:hasActor` ⊂ `:hasContributor`).
- Propriétés fonctionnelles (`:imdbId`, `:birthYear`, `:gender`…).
- Chaînes de propriétés : ex. `:actedIn` = `:hasRole` ∘ `:inMotionPicture`.

### Thésaurus (SKOS)
- Genres modélisés en `skos:Concept` avec labels + (si pertinent) définitions.
- Hiérarchie via `skos:broader` / `skos:narrower`.
- Concepts générés automatiquement lors de l’import, à partir des genres du dataset.

### Validation (SHACL)
- Contrôle des formats (ex. regex IMDb id, ISO country codes…).
- Cardinalités (`sh:maxCount 1`) pour éviter les ambiguïtés.
- Contraintes de cohérence (ex. genre attendu pour `:Actor`/`:Actress`, `:Man`/`:Woman`).
- Disjonctions (`sh:not`) et règles complexes via contraintes SPARQL (cohérence temporelle, cohérence des relations acteur/œuvre, symétrie, inverses parent/enfant…).

---

## Construction du graphe

L’intégration RDF repose sur **3 mappings** (RML + FnML) :
1. **Instances** (œuvres, personnes, reviews, contributions…) + typage dynamique (ex. film vs série) via fonctions GREL/IDLab.
2. **Genres SKOS** (URI + triplets SKOS + définition enrichie).
3. **Métiers dynamiques** : génération de classes de job + propriétés `:has[JOB]Contribution` à partir des intitulés.

---

## Alignement & Liage

Trois axes :
- **Alignement d’ontologies** : liens vers Schema.org, Wikidata et une ontologie cinéma (semantics.id) via **AgreementMakerLight**, puis vérification manuelle.
- **Alignement SKOS** : mapping des genres vers **ContentGenre (EBU)** via **OnaGui**, avec validation et compléments manuels.
- **Alignement des données** : liage des instances (œuvres, personnes) vers **Wikidata** via titres + identifiants IMDb (écosystème Ontotext), puis génération de fichiers de liage.

---

## Exploitation (SPARQL)

Exemples d’analyses effectuées :
- **Films polarisants** : proportion de reviews très négatives (≤3) et très positives (≥8) + pondération par volume.
- **Réalisateurs** associés aux reviews les plus “utiles” (helpfulness votes).
- **Acteurs** dont la filmographie est en moyenne la mieux notée.
- **Requête fédérée Wikidata** : comptage des récompenses d’acteurs (`SERVICE <https://query.wikidata.org/sparql>`).

Les requêtes SPARQL complètes sont disponibles dans le rapport (annexe).

---

## Recommandation (Link Prediction)

Mise en place d’un système de recommandation basé sur la similarité sémantique :
1. récupération de synopsis depuis Wikipedia (via Wikidata + IMDb id),
2. embeddings texte via **gemini-embedding-1.0**,
3. normalisation + indexation **FAISS**,
4. profil utilisateur = moyenne des embeddings des films aimés,
5. recherche des plus proches voisins, en excluant les films déjà vus.

---

## Graph RAG

Deux approches complémentaires :

### 1) Text-to-SPARQL (LangChain)
Agent conversationnel avec des tools :
- `ontology_schema_tool` : vue globale classes/propriétés/namespaces,
- `property_details_tool` : domaine/range d’une propriété,
- `sparql_query_tool` : exécution protégée (timeout, formatage résultats),
- `user_recommendation_tool` : recommandations personnalisées.

### 2) Recommandation par embeddings du graphe (Node2Vec) + hybride
- apprentissage Node2Vec sur un sous-graphe (films + entités liées),
- filtrage de nœuds très connectés,
- limitation observée : similarité trop “structurelle”.
- solution : **hybride** = concaténation embedding graphe + embedding synopsis (normalisés), puis KNN cosinus.

---

## Interface

L’interface propose :
- un chat pour **interroger le graphe** (agent),
- un bloc de **recommandations personnalisées**,
- la possibilité d’**ajouter une review**, qui met à jour le graphe et donc les recommandations.
  
<img width="1919" height="910" alt="interface" src="https://github.com/user-attachments/assets/6d4c4dde-bba5-4f71-8a34-aa28fe5ab635" />

## Structure

```
.
|-- AML_v3.2/                 AgreementMakerLight + resources (alignment)
|-- datasets/                 jeux de donnees bruts (IMDB, etc.)
|   `-- reduced/              versions reduites pour tests
|-- rdf_graph/                graph RDF exporte
|   |-- persons/              fichiers TTL par personne
|   `-- triplets/             triplets agreges (data.ttl)
|-- src/                      code source principal
|   |-- alignment/            generation et fichiers d'alignement
|   |-- graph_rag/            agent RAG + outils + index synopsis
|   |   |-- prompts/          prompts systeme
|   |   |-- tools/            outils SPARQL/recos/similarity
|   |   |-- graph_embedding/  embeddings et tests KNN
|   |   `-- synopsis_index/   index FAISS + metadata
|   |-- preprocessing/        preprocessing des donnees
|   |-- sparql/               scripts SPARQL + doc
|   |-- web_ui/               serveur + front statique
|   `-- wikipedia/            extraction synopsis/biographies
|-- turtle/                   ontologies, mapping, SHACL, thesaurus
|   |-- mapping/              mapping ontology/data
|   |-- ontology/             ontologies TTL + alignments + OWL
|   |-- shacl/                contraintes SHACL
|   `-- thesaurus/            thesaurus de genres/concepts
|-- requirements.txt         dependances Python
|-- report.pdf                rapport du projet
`-- README.md                 ce fichier
```

## Installation

```bash
pip install -r requirements.txt
```

## Lancer l'UI

La variable d'environnement GEMINI_API_KEY est necessaire pour authentifier l'acces a l'API Gemini utilisee par l'agent.

Windows (PowerShell):

```powershell
$env:GEMINI_API_KEY=""; python3.12 -m src.web_ui.server
```

Windows (Command Prompt):

```bat
set GEMINI_API_KEY= && python3.12 -m src.web_ui.server
```

Linux:

```bash
export GEMINI_API_KEY=""; python3.12 -m src.web_ui.server
```
