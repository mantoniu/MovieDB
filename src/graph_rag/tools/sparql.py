from langchain.tools import tool

from .common import rdf_graph

def sparql_query(query: str) -> str:
    """
    Execute a SPARQL query against the RDF graph.

    Args:
        query (str): The SPARQL query string.
    Returns:
        str: Formatted results of the SPARQL query.
    """
    try:
        rows = list(rdf_graph.query(query))
        if not rows:
            return "The query returned no results."

        output = []
        max_lines = 50
        for i, row in enumerate(rows[:max_lines], 1):
            output.append(f"{i}. " + " | ".join(str(v) for v in row))

        if len(rows) > max_lines:
            output.append(f"... ({len(rows) - max_lines} additional results)")

        return "\n".join(output)
    except Exception as e:
        return f"SPARQL Error: {e}"

def get_graph_statistics() -> str:
    """
    Get basic statistics about the RDF graph.

    Returns:
        str: Formatted statistics about the RDF graph.
    """
    stats = [
        "RDF Graph Statistics:",
        f"- Total number of triples: {len(rdf_graph)}"
    ]

    type_query = """
        SELECT ?type (COUNT(?s) as ?count)
        WHERE { ?s a ?type . }
        GROUP BY ?type
        ORDER BY DESC(?count)
    """

    try:
        rows = list(rdf_graph.query(type_query))
        stats.append("\nResource Types:")
        for t, c in rows[:30]:
            stats.append(f"  - {t}: {c}")
        if len(rows) > 30:
            stats.append(f"  ... ({len(rows)-30} additional types)")
    except:
        pass

    return "\n".join(stats)

@tool
def sparql_query_tool(sparql_query_str: str) -> str:
    """
    Execute a SPARQL query against the RDF graph.

    Args:
        sparql_query_str (str): The SPARQL query string.
    Returns:
        str: Formatted results of the SPARQL query.
    """
    return sparql_query(sparql_query_str)

@tool
def graph_statistics_tool() -> str:
    """
    Get basic statistics about the RDF graph.

    Returns:
        str: Formatted statistics about the RDF graph.
    """
    return get_graph_statistics()
