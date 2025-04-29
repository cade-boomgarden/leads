import requests
import re
from urllib.parse import urlparse, parse_qs
from django.conf import settings
from finder.models import CompanySearch, SerpAPISearchParameters
from companies.models import Company
import serpapi
from geopy.geocoders import Nominatim
import logging
from companies.scripts.clean_names import clean_company_name

logger = logging.getLogger(__name__)

class SerpAPIService:
    BASE_URL = "https://serpapi.com/search"
    
    def __init__(self):
        logger.info("Initializing SerpAPIService")
        self.api_key = settings.SERPAPI_API_KEY
        logger.info("SerpAPI API key loaded from settings, loading geolocator")
        self.geolocator = Nominatim(user_agent="leads_generator")
        logger.info("Geolocator initialized")
        if not self.api_key:
            raise ValueError("SerpAPI API key is required")
    
    def get_account_info(self):
        client = serpapi.Client(api_key=self.api_key)
        return client.account()
    
    def search_all_pages(self, search_params: SerpAPISearchParameters, max_results=None):
        client = serpapi.Client(api_key=self.api_key)
        logger.info("Starting search_all_pages")
        all_results = []
        
        # Build base parameters
        params = {
            "engine": "google_maps",
            "type": "search",
            "q": search_params.query,
        }

        if search_params.place_name:
            # Use separate parameter for location
            try:
                location = self.geolocator.geocode(search_params.place_name, timeout=10)
                params["ll"] = f"@{location.latitude},{location.longitude},{search_params.zoom}z"
            except Exception as e:
                logger.info(f"Error geocoding place name '{search_params.place_name}': {e}")
                return all_results
        logger.info(params)
        results = client.search(params)
        all_results += results.get("local_results", [])
        while results.next_page_url and (len(all_results) < max_results if max_results else True):
            results = results.next_page()
            all_results += results.get("local_results", [])

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
                    name=clean_company_name(result.get("title", "")),
                    domain=domain,
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