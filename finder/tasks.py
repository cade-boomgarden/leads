# finder/tasks.py

from huey.contrib.djhuey import task
from django.conf import settings

from .models import CompanySearch, SerpAPISearchParameters
from .services.serpapi_service import SerpAPIService

@task()
def execute_serpapi_search(company_search_id, max_results=None):
    """
    Execute a SerpAPI search as a background task
    
    Args:
        company_search_id: ID of the CompanySearch to process
        max_results: Maximum number of results to return (None for all)
    """
    try:
        # Get the CompanySearch and search parameters
        company_search = CompanySearch.objects.get(id=company_search_id)
        search_params = SerpAPISearchParameters.objects.get(company_search=company_search)
        
        # Create service and execute search
        service = SerpAPIService()
        results = service.search_all_pages(search_params, max_results=max_results)
        
        # Create companies from results
        companies = service.create_companies_from_results(results, company_search)
        
        # Update results count (safely handle None result)
        if companies is not None:
            company_search.results_count = len(companies)
        else:
            company_search.results_count = 0
            companies = []  # Ensure we have an empty list for logging
        
        company_search.save()
        
        return f"Found {company_search.results_count} companies for search #{company_search_id}"
        
    except Exception as e:
        # Log the error
        print(f"Error executing SerpAPI search #{company_search_id}: {str(e)}")
        # Re-raise to mark task as failed
        raise