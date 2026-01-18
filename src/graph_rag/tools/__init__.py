from .similarity import similarity_search_tool
from .sparql import sparql_query_tool, graph_statistics_tool
from .recommendation import user_recommendation_tool, recommend_movies
from .ontology import (
    ontology_schema_tool,
    property_details_tool
)

ALL_TOOLS = [
    similarity_search_tool,
    sparql_query_tool,
    graph_statistics_tool,
    ontology_schema_tool,
    property_details_tool,
    user_recommendation_tool
]

__all__ = [
    'ALL_TOOLS',
    'similarity_search_tool',
    'sparql_query_tool',
    'graph_statistics_tool',
    'ontology_schema_tool',
    'property_details_tool',
    'user_recommendation_tool',
    'recommend_movies'
]
