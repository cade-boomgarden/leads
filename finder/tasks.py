from huey.contrib.djhuey import task
from django.conf import settings

from .models import CompanySearch, SerpAPISearchParameters, ContactSearch, WebScrapeParameters 
from .services.serpapi_service import SerpAPIService
from .services.webscrape_service import WebScrapeService
from companies.models import Company

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

@task()
def execute_webscrape_search(contact_search_id, company_list_id=None):
    """
    Execute a web scrape as a background task
    
    Args:
        contact_search_id: ID of the ContactSearch to process
        company_list_id: Optional ID of a CompanyList to limit scope
    """
    try:
        # Get the ContactSearch and search parameters
        contact_search = ContactSearch.objects.get(id=contact_search_id)
        search_params = WebScrapeParameters.objects.get(contact_search=contact_search)
        
        # Get companies to scrape
        if company_list_id:
            from companies.models import CompanyList
            company_list = CompanyList.objects.get(id=company_list_id)
            companies = company_list.companies.all()
        else:
            # If scraping a single website URL directly
            if search_params.target_url:
                # Try to find a company with this domain
                from urllib.parse import urlparse
                parsed_url = urlparse(search_params.target_url)
                domain = parsed_url.netloc
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                try:
                    company = Company.objects.get(domain=domain)
                    companies = [company]
                except Company.DoesNotExist:
                    # Create a temporary company object for this domain
                    company = Company(
                        name=domain,
                        domain=domain,
                        website_url=search_params.target_url
                    )
                    company.save()
                    companies = [company]
            else:
                # Get all companies with website URLs
                companies = Company.objects.exclude(website_url__isnull=True).exclude(website_url='')
        
        total_contacts = 0
        
        # Process each company
        for company in companies:
            # Skip companies without websites
            if not company.website_url:
                continue
            
            # Configure the scraper for this company
            config = search_params.configuration
            config['target_url'] = company.website_url
            
            # Create and run the scraper
            scraper = WebScrapeService(config)
            scraper.start()
            
            # Create contacts from results
            contacts = scraper.create_contacts_from_results(company)
            
            # Add contacts to the search
            for contact in contacts:
                contact_search.contacts.add(contact)
            
            total_contacts += len(contacts)
        
        # Update results count
        contact_search.results_count = total_contacts
        contact_search.save()
        
        return f"Found {total_contacts} contacts for search #{contact_search_id}"
        
    except Exception as e:
        # Log the error
        print(f"Error executing web scrape search #{contact_search_id}: {str(e)}")
        # Re-raise to mark task as failed
        raise