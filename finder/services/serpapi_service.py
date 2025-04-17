import requests
import re
from urllib.parse import urlparse
from django.conf import settings
from finder.models import CompanySearch, SerpAPISearchParameters
from companies.models import Company

class SerpAPIService:
    BASE_URL = "https://serpapi.com/search"
    
    def __init__(self):
        self.api_key = settings.SERPAPI_API_KEY
        if not self.api_key:
            raise ValueError("SerpAPI API key is required")
    
    def search_companies(self, search_params):
        """
        Execute a search for companies using SerpAPI's Google Maps API
        
        Args:
            search_params: SerpAPISearchParameters instance
            
        Returns:
            dict: API response data
        """
        params = {
            "engine": "google_maps",
            "type": "search",
            "api_key": self.api_key
        }
        
        # Handle query and location more explicitly
        if search_params.place_name:
            # When using place name, combine it with the query
            params["q"] = f"{search_params.query} {search_params.place_name}"
        else:
            # Just use the query alone
            params["q"] = search_params.query
            
        # Only add ll parameter if both latitude and longitude are provided
        if search_params.latitude is not None and search_params.longitude is not None:
            params["ll"] = f"@{search_params.latitude},{search_params.longitude},{search_params.zoom}z"
        
        # Add any additional parameters from the search_params that might be relevant
        if search_params.google_domain:
            params["google_domain"] = search_params.google_domain
            
        if search_params.language:
            params["hl"] = search_params.language
            
        if search_params.country:
            params["gl"] = search_params.country
        
        # Make the API request
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        return response.json()
    
    def search_all_pages(self, search_params, max_results=None):
        """
        Search all pages of results up to max_results
        
        Args:
            search_params: SerpAPISearchParameters instance
            max_results: Maximum number of results to return (None for all)
            
        Returns:
            list: List of company data dictionaries
        """
        all_results = []
        remaining_results = max_results if max_results else float('inf')
        
        # Initial parameters for the API
        params = {
            "engine": "google_maps",
            "type": "search",
            "api_key": self.api_key
        }
        
        # Handle query and location explicitly
        if search_params.place_name:
            # When using place name, combine it with the query
            params["q"] = f"{search_params.query} {search_params.place_name}"
        else:
            # Just use the query alone
            params["q"] = search_params.query
            
        # Only add ll parameter if both latitude and longitude are provided
        if search_params.latitude is not None and search_params.longitude is not None:
            params["ll"] = f"@{search_params.latitude},{search_params.longitude},{search_params.zoom}z"
        
        # Add any additional parameters
        if search_params.google_domain:
            params["google_domain"] = search_params.google_domain
            
        if search_params.language:
            params["hl"] = search_params.language
            
        if search_params.country:
            params["gl"] = search_params.country
        
        # Process all pages or until max_results is reached
        while remaining_results > 0:
            # Execute search
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            results = response.json()
            
            # Extract local results
            if "local_results" in results:
                # Get current page results
                current_results = results["local_results"]
                
                # Determine how many to take from this page
                results_to_take = min(len(current_results), remaining_results)
                
                # Add the results to our list
                all_results.extend(current_results[:results_to_take])
                
                # Update remaining results
                remaining_results -= results_to_take
                
                # Check if we have a next page
                if "serpapi_pagination" in results and "next" in results["serpapi_pagination"] and remaining_results > 0:
                    # Extract the 'start' parameter from the next URL
                    next_url = results["serpapi_pagination"]["next"]
                    
                    # Get the start parameter for the next page
                    start_match = re.search(r'start=(\d+)', next_url)
                    if start_match:
                        params["start"] = start_match.group(1)
                    else:
                        break  # Can't find start parameter, exit loop
                else:
                    break  # No more pages or we have enough results
            else:
                break  # No results found
        
        return all_results
    
    def create_companies_from_results(self, results, company_search):
        """
        Create Company objects from SerpAPI results
        
        Args:
            results: List of company data from SerpAPI
            company_search: CompanySearch instance to associate created companies with
            
        Returns:
            list: List of created Company objects
        """
        created_companies = []
        
        # Handle the case where results is None or empty
        if not results:
            # Update results count to 0
            company_search.results_count = 0
            company_search.save()
            return created_companies
        
        for result in results:
            # Extract domain from website if available
            domain = None
            website_url = result.get("website")
            if website_url:
                try:
                    parsed = urlparse(website_url)
                    if parsed.netloc:
                        # Remove www. prefix if present
                        domain_value = parsed.netloc
                        if domain_value.startswith('www.'):
                            domain_value = domain_value[4:]
                        domain = domain_value
                except Exception:
                    # In case of parsing errors, leave domain as None
                    pass
            
            # Skip if no domain was found - domain is required for Company model
            if not domain:
                print(f"Skipping business '{result.get('title')}' - no domain available")
                continue
            
            # Check if company already exists by domain
            try:
                company = Company.objects.get(domain=domain)
                # Update existing company details if needed
                updated = False
                
                # Add missing details if needed
                if not company.place_id and result.get("place_id"):
                    company.place_id = result.get("place_id")
                    updated = True
                    
                if not company.address and result.get("address"):
                    company.address = result.get("address")
                    updated = True
                    
                if not company.phone and result.get("phone"):
                    company.phone = result.get("phone")
                    updated = True
                    
                if updated:
                    company.save()
            except Company.DoesNotExist:
                # Create coordinates model if available
                coords = None
                if "gps_coordinates" in result:
                    coords = result["gps_coordinates"]
                
                # Create the company
                company = Company(
                    name=result.get("title", ""),
                    domain=domain,  # This is now guaranteed to be non-None
                    website_url=website_url,
                    phone=result.get("phone"),
                    serp_position=result.get("position"),
                    place_id=result.get("place_id"),
                    data_id=result.get("data_id"),
                    data_cid=result.get("data_cid"),
                    provider_id=result.get("provider_id"),
                    rating=result.get("rating"),
                    reviews_count=result.get("reviews"),
                    primary_type=result.get("type"),
                    types=result.get("types", []),
                    type_ids=result.get("type_ids", []),
                    address=result.get("address"),
                    description=result.get("description"),
                )
                
                # Add coordinate data if available
                if coords:
                    company.latitude = coords.get("latitude")
                    company.longitude = coords.get("longitude")
                
                # Add service options if available
                if "service_options" in result:
                    options = result["service_options"]
                    company.dine_in_available = options.get("dine_in", False)
                    company.takeout_available = options.get("takeout", False)
                    company.no_contact_delivery_available = options.get("no_contact_delivery", False)
                
                # Add thumbnail if available
                if "thumbnail" in result:
                    company.thumbnail_url = result.get("thumbnail")
                
                # Save the company
                company.save()
            
            # Add company to the company search if not already there
            if company not in company_search.companies.all():
                company_search.companies.add(company)
                
            created_companies.append(company)
                
        # Update results count
        company_search.results_count = len(created_companies)
        company_search.save()
        
        return created_companies