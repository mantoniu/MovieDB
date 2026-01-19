from langchain.tools import tool
from typing import Iterable, List
from .common import rdf_graph, log_tool_use

def _generate_prefix_block() -> str:
    """
    Generate SPARQL PREFIX declarations for all namespaces in the RDF graph.

    Returns:
        str: Formatted PREFIX declarations.
    """
    keep_prefixes = {"", "xsd"}
    prefixes = []
    for prefix, uri in rdf_graph.namespaces():
        if prefix in keep_prefixes:
            prefixes.append(f"PREFIX {prefix}: <{uri}>")
    return "\n".join(prefixes)

PREFIX_BLOCK = _generate_prefix_block()

def _generate_ontology_summary() -> str:
    """
    Generate a summary of the ontology schema including classes and properties.

    Returns:
        str: Formatted summary of the ontology schema.
    """    
    query_classes = f"""
    {PREFIX_BLOCK}
    SELECT DISTINCT ?class WHERE {{
        ?class a owl:Class .
        FILTER(STRSTARTS(STR(?class), "http://www.moviedb.fr/cinema#"))
    }} ORDER BY ?class
    """
    
    query_props = f"""
    {PREFIX_BLOCK}
    SELECT DISTINCT ?prop WHERE {{
        {{ ?prop a owl:ObjectProperty }} UNION {{ ?prop a owl:DatatypeProperty }}
        FILTER(STRSTARTS(STR(?prop), "http://www.moviedb.fr/cinema#"))
    }} ORDER BY ?prop
    """

    summary = ["=== ONTOLOGY SUMMARY ==="]
    summary.append("\n[NAMESPACES]")
    summary.append(PREFIX_BLOCK)

    summary.append("\n[CLASSES]")
    res_classes = rdf_graph.query(query_classes)
    for row in res_classes:
        summary.append(f"  {row[0].n3(rdf_graph.namespace_manager)}")

    summary.append("\n[PROPERTIES]")
    res_props = rdf_graph.query(query_props)
    for row in res_props:
        summary.append(f"  {row[0].n3(rdf_graph.namespace_manager)}")

    return "\n".join(summary)

CACHED_SUMMARY = _generate_ontology_summary()

def _normalize_property_key(property_name: str) -> str:
    """
    Normalize property name to a full URI when possible.
    """
    name = property_name.strip()
    if name.startswith("<") and name.endswith(">"):
        return name[1:-1]
    if name.startswith("http://") or name.startswith("https://"):
        return name
    try:
        return str(rdf_graph.namespace_manager.expand_curie(name, False))
    except Exception:
        try:
            return str(rdf_graph.namespace_manager.expand_curie(name))
        except Exception:
            return name

def _build_property_details_cache() -> dict:
    """
    Build a cache of property details (domain, range, comments) in one query.
    """
    query = f"""
    {PREFIX_BLOCK}
    SELECT ?prop ?domain ?range ?comment WHERE {{
        {{ ?prop a owl:ObjectProperty }} UNION {{ ?prop a owl:DatatypeProperty }}
        OPTIONAL {{ ?prop rdfs:domain ?domain }}
        OPTIONAL {{ ?prop rdfs:range ?range }}
        OPTIONAL {{ ?prop rdfs:comment ?comment }}
        FILTER(STRSTARTS(STR(?prop), "http://www.moviedb.fr/cinema#"))
    }} ORDER BY ?prop
    """
    rows = list(rdf_graph.query(query))
    cache: dict = {}
    namespace_root = "http://www.moviedb.fr/cinema#"

    def _keep_term(term):
        if term is None:
            return None
        term_str = str(term)
        if term_str.startswith("_:"):
            return None
        if term_str.startswith(namespace_root):
            return term
        return None

    for prop, domain, range_, comment in rows:
        keys = {
            str(prop),
            prop.n3(rdf_graph.namespace_manager),
        }
        domain_kept = _keep_term(domain)
        range_kept = _keep_term(range_)
        for key in keys:
            entry = cache.setdefault(key, {"pairs": set(), "comments": set()})
            if domain_kept is not None or range_kept is not None:
                entry["pairs"].add((domain_kept, range_kept))
            if comment:
                entry["comments"].add(str(comment))
    return cache

PROPERTY_DETAILS_CACHE = _build_property_details_cache()

def _cached_property_details(property_name: str) -> str:
    """
    Return property details from the precomputed cache.
    """
    key = _normalize_property_key(property_name)
    entry = PROPERTY_DETAILS_CACHE.get(key) or PROPERTY_DETAILS_CACHE.get(property_name)
    if not entry:
        return "No information found."

    res = [f"Details of {property_name}:"]
    if entry["comments"]:
        for comment in sorted(entry["comments"]):
            res.append(f"- Comment: {comment}")
    domains = {d for d, _ in entry["pairs"] if d}
    ranges = {r for _, r in entry["pairs"] if r}
    for d in sorted(domains, key=str):
        res.append(f"- Domain: {d.n3(rdf_graph.namespace_manager)}")
    for r in sorted(ranges, key=str):
        res.append(f"- Range: {r.n3(rdf_graph.namespace_manager)}")
    if len(res) == 1:
        return "No information found."
    return "\n".join(res)

@tool
def ontology_schema_tool() -> str:
    """
    Get a summary of the ontology schema including classes and properties.
    Returns:
        str: Formatted summary of the ontology schema.
    """
    log_tool_use("ontology_schema_tool")
    return CACHED_SUMMARY

@tool
def property_details_tool(property_names: List[str]) -> str:
    """
    Get details about one or more properties in the ontology.

    Args:
        property_names (List[str]): The full URI(s) or prefixed name(s) of properties.
    Returns:
        str: Formatted details about the properties' domain, range, and comments.
    """
    names: List[str] = []
    if isinstance(property_names, Iterable):
        for item in property_names:
            if item is None:
                continue
            item_str = str(item).strip()
            if item_str:
                names.append(item_str)
    else:
        names = [str(property_names).strip()]

    seen = set()
    ordered_names = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered_names.append(name)

    print("Asked for properties:", ordered_names)
    log_tool_use("property_details_tool", property_names=ordered_names)
    try:
        results = [_cached_property_details(name) for name in ordered_names]
        print(results)
        return "\n\n".join(results)
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    print("--- SUMMARY TEST ---")
    print(CACHED_SUMMARY)

    print("\n--- PROPERTY DETAILS TEST ---")
    print(property_details_tool.run([":directed"]))
