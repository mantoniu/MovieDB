from langchain.tools import tool

from .sparql import rdf_graph

def _generate_prefix_block() -> str:
    """
    Generate SPARQL PREFIX declarations for all namespaces in the RDF graph.

    Returns:
        str: Formatted PREFIX declarations.
    """
    prefixes = []
    for prefix, uri in rdf_graph.namespaces():
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

@tool
def ontology_schema_tool() -> str:
    """
    Get a summary of the ontology schema including classes and properties.
    Returns:
        str: Formatted summary of the ontology schema.
    """
    return CACHED_SUMMARY

@tool
def property_details_tool(property_name: str) -> str:
    """
    Get details about a specific property in the ontology.
    
    Args:
        property_name (str): The full URI or prefixed name of the property.
    Returns:
        str: Formatted details about the property's domain and range.
    """
    prefix_block = "\n".join([f"PREFIX {p}: <{u}>" for p, u in rdf_graph.namespaces()])
    query = f"""
    {prefix_block}
    SELECT ?domain ?range WHERE {{
        {property_name} rdfs:domain ?domain .
        OPTIONAL {{ {property_name} rdfs:range ?range }}
    }}
    """
    try:
        rows = list(rdf_graph.query(query))
        if not rows: 
            return "No information found."

        res = [f"Details of {property_name}:"]
        for d, r in rows:
            res.append(f"- Domain: {d.n3(rdf_graph.namespace_manager) if d else 'N/A'}")
            res.append(f"- Range: {r.n3(rdf_graph.namespace_manager) if r else 'N/A'}")
        return "\n".join(res)
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    print("--- SUMMARY TEST ---")
    print(CACHED_SUMMARY)

    print("\n--- PROPERTY DETAILS TEST ---")
    print(property_details_tool.run(":directed"))