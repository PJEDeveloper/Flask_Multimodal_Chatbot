# app/services/google_search_service.py
from googlesearch import search
from config import logger  # Assuming logger is available in config.py

def google_search(query, num_results=5):
    """
    Performs a Google search using the 'googlesearch' library and returns top results.
    
    Args:
        query (str): The search query.
        num_results (int): Number of search results to return.
    
    Returns:
        list: A list of URLs as strings. Returns an empty list on failure.
    """
    # Validate the search query and return empty if invalid
    if not query or not query.strip():
        logger.warning("Google search called with empty query.")
        return []

    try:
        # Perform the search and log the number of results obtained
        logger.info(f"Performing Google search for query: {query}")
        results = list(search(query, num_results=num_results))
        logger.info(f"Google search returned {len(results)} results.")
        return results
    # Handle errors gracefully and log full details
    except Exception as e:
        logger.error(f"Google Search failed: {str(e)}", exc_info=True)
        return []