#!/usr/bin/env python
import os
import sys
import logging
import json
from datetime import datetime

# Set up Django environment
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leads_generator.settings')
django.setup()

# Import models
from finder.models import CompanySearch, SerpAPISearchParameters
from finder.services import SerpAPIService

# Import the debug service
from .tasks import debug_execute_serpapi_search
import logging

logger = logging.getLogger(__name__)
# Add a file handler for persistent logging
log_filename = f'serpapi_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def test_direct_pagination():
    """
    Test the pagination directly without using the task
    """
    try:
        # Ask user for company search ID
        if len(sys.argv) > 1:
            company_search_id = int(sys.argv[1])
        else:
            company_search_id = int(input("Enter CompanySearch ID: "))
        
        # Ask user for max results (optional)
        max_results_input = input("Enter max results (leave empty for all): ")
        max_results = int(max_results_input) if max_results_input.strip() else None
        
        logger.info(f"Testing direct pagination with company_search_id={company_search_id}, max_results={max_results}")
        
        # Get the CompanySearch and search parameters
        company_search = CompanySearch.objects.get(id=company_search_id)
        logger.info(f"Found CompanySearch: {company_search}")
        
        search_params = SerpAPISearchParameters.objects.get(company_search=company_search)
        logger.info(f"Found SerpAPISearchParameters: query={search_params.query}, place_name={search_params.place_name}")
        
        # Create service and execute search
        service = SerpAPIService()
        
        # Test getting one page first (for comparison)
        logger.info("Testing single page search first")
        single_page = service.search_companies(search_params)
        
        # Save the response to a file for inspection
        with open('serpapi_response_single.json', 'w') as f:
            json.dump(single_page, f, indent=2)
        
        if "local_results" in single_page:
            local_results_count = len(single_page.get("local_results", []))
            logger.info(f"Single page search returned {local_results_count} local results")
        else:
            logger.warning("No local_results in single page response")
        
        # Now test the multi-page search
        logger.info("Testing multi-page search")
        results = service.search_all_pages(search_params, max_results=max_results)
        
        logger.info(f"Multi-page search returned {len(results) if results else 0} total results")
        
        # Save the first and last 3 results to a file for inspection
        with open('serpapi_results_sample.json', 'w') as f:
            if results and len(results) > 0:
                sample = {
                    "first_three": results[:min(3, len(results))],
                    "last_three": results[-min(3, len(results)):],
                    "total_count": len(results)
                }
            else:
                sample = {"error": "No results found"}
            json.dump(sample, f, indent=2)
        
        logger.info(f"Test completed. Log saved to {log_filename}")
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
        
def test_task_execution():
    """
    Test the task execution with debugging
    """
    try:
        # Ask user for company search ID
        if len(sys.argv) > 1:
            company_search_id = int(sys.argv[1])
        else:
            company_search_id = int(input("Enter CompanySearch ID: "))
        
        # Ask user for max results (optional)
        max_results_input = input("Enter max results (leave empty for all): ")
        max_results = int(max_results_input) if max_results_input.strip() else None
        
        logger.info(f"Testing task execution with company_search_id={company_search_id}, max_results={max_results}")
        
        # Execute the task directly (not via Huey)
        result = debug_execute_serpapi_search(company_search_id, max_results)
        
        logger.info(f"Task execution result: {result}")
        logger.info(f"Test completed. Log saved to {log_filename}")
        
    except Exception as e:
        logger.error(f"Error during task test: {str(e)}", exc_info=True)

def run():
    print(f"Log file: {log_filename}")
    print("1. Test direct pagination")
    print("2. Test task execution")
    choice = input("Choose a test (1/2): ")
    
    if choice == "1":
        test_direct_pagination()
    elif choice == "2":
        test_task_execution()
    else:
        print("Invalid choice")