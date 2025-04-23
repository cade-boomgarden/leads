from huey.contrib.djhuey import task
from django.conf import settings

from .models import CompanySearch, SerpAPISearchParameters, ContactSearch, WebScrapeParameters 
from .services.serpapi_service import SerpAPIService
from .services.webscrape_service import WebScrapeService
from companies.models import Company
import logging

logger = logging.getLogger(__name__)

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
        company_search.results_count = len(companies) if companies is not None else 0
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

@task()
def execute_hunter_search(contact_search_id, domain=None, company=None, company_list_id=None):
    """
    Execute a Hunter.io domain search as a background task
    
    Args:
        contact_search_id: ID of the ContactSearch to process
        domain: Domain to search (if specific domain)
        company: Company name to search (if specific company)
        company_list_id: ID of a CompanyList to search all domains in the list
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Get the ContactSearch and search parameters
        from finder.models import ContactSearch, HunterDomainSearchParameters
        from finder.services.hunter_service import HunterService
        from companies.models import Company, CompanyList
        
        contact_search = ContactSearch.objects.get(id=contact_search_id)
        search_params = HunterDomainSearchParameters.objects.get(contact_search=contact_search)
        
        # Mark as hunter search explicitly
        if contact_search.method != ContactSearch.ContactSearchMethods.HUNTER:
            contact_search.method = ContactSearch.ContactSearchMethods.HUNTER
            contact_search.save()
        
        # Create Hunter service
        hunter_service = HunterService()
        
        # Track total contacts found
        total_contacts = 0
        
        # Process either a single domain/company or all domains in a list
        if company_list_id:
            # Get all companies from the list
            company_list = CompanyList.objects.get(id=company_list_id)
            companies = company_list.companies.all()
            
            # Process each company
            for company_obj in companies:
                # Skip companies without domains
                if not company_obj.domain:
                    continue
                
                # Execute domain search for this company
                try:
                    logger.info(f"Searching Hunter for company {company_obj.name} (domain: {company_obj.domain})")
                    results = hunter_service.domain_search(
                        domain=company_obj.domain,
                        limit=search_params.limit,
                        offset=search_params.offset,
                        email_type=search_params.type if search_params.type != 'all' else None,
                        seniority=search_params.seniority_levels,
                        department=search_params.departments,
                        required_fields=search_params.required_fields
                    )
                    
                    # Create contacts from results
                    contacts = hunter_service.create_contacts_from_results(results, company_obj)
                    
                    # Add contacts to the search
                    for contact in contacts:
                        contact_search.contacts.add(contact)
                    
                    total_contacts += len(contacts)
                    logger.info(f"Found {len(contacts)} contacts for {company_obj.name}")
                except Exception as e:
                    logger.error(f"Error searching Hunter for company {company_obj.name}: {str(e)}")
                    # Continue with other companies
                    continue
        else:
            # Search for a specific domain or company
            domain_param = domain or search_params.domain
            company_param = company or search_params.company
            
            # Get the company object if available
            company_obj = None
            if domain_param:
                try:
                    company_obj = Company.objects.get(domain=domain_param)
                except Company.DoesNotExist:
                    # Will create contacts without company association
                    pass
            
            search_type = "domain" if domain_param else "company"
            search_value = domain_param if domain_param else company_param
            logger.info(f"Searching Hunter by {search_type}: {search_value}")
            
            # Execute domain search
            results = hunter_service.domain_search(
                domain=domain_param,
                company=company_param,
                limit=search_params.limit,
                offset=search_params.offset,
                email_type=search_params.type if search_params.type != 'all' else None,
                seniority=search_params.seniority_levels,
                department=search_params.departments,
                required_fields=search_params.required_fields
            )
            
            # Create contacts from results
            contacts = hunter_service.create_contacts_from_results(results, company_obj)
            
            # Add contacts to the search
            for contact in contacts:
                contact_search.contacts.add(contact)
            
            total_contacts = len(contacts)
            logger.info(f"Found {total_contacts} contacts for {search_type} {search_value}")
        
        # Update results count
        contact_search.results_count = total_contacts
        contact_search.save()
        
        return f"Found {total_contacts} contacts for Hunter search #{contact_search_id}"
        
    except Exception as e:
        # Log the error
        logger.error(f"Error executing Hunter search #{contact_search_id}: {str(e)}")
        # Re-raise to mark task as failed
        raise

@task()
def validate_emails_with_zerobounce(batch_id=None, contact_list_id=None, contact_id=None, max_validations=None, use_ip=True, timeout=10):
    """
    Task to validate emails using ZeroBounce API.
    
    Args:
        batch_id (int): ID of EmailValidationBatch to track progress
        contact_list_id (int, optional): ID of ContactList to validate emails for
        contact_id (int, optional): ID of single Contact to validate
        max_validations (int, optional): Maximum number of validations to perform
        use_ip (bool): Whether to include IP address in validation
        timeout (int): Timeout in seconds for API requests (3-60)
    """
    try:
        from contacts.models import Contact, ContactList
        from finder.services.zerobounce_service import ZeroBounceService
        from finder.models import EmailValidationBatch
        from django.utils import timezone
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Get or create the validation batch
        validation_batch = None
        if batch_id:
            try:
                validation_batch = EmailValidationBatch.objects.get(id=batch_id)
                validation_batch.status = EmailValidationBatch.ValidationStatus.PROCESSING
                validation_batch.save()
            except EmailValidationBatch.DoesNotExist:
                logger.error(f"EmailValidationBatch with ID {batch_id} not found")
                return f"EmailValidationBatch with ID {batch_id} not found"
        
        # Create ZeroBounce service
        zerobounce_service = ZeroBounceService()
        
        # Check available credits
        try:
            available_credits = zerobounce_service.get_credits()
            logger.info(f"ZeroBounce credits available: {available_credits}")
        except Exception as e:
            logger.error(f"Error checking ZeroBounce credits: {str(e)}")
            available_credits = 0
            
        if available_credits <= 0:
            error_msg = "No ZeroBounce credits available for email validation"
            logger.error(error_msg)
            
            if validation_batch:
                validation_batch.status = EmailValidationBatch.ValidationStatus.FAILED
                validation_batch.save()
                
            return error_msg
        
        # If max_validations not specified, use available credits
        if max_validations is None:
            max_validations = available_credits
        else:
            max_validations = min(max_validations, available_credits)
        
        # Get contacts to validate
        contacts_to_validate = []
        
        if contact_id:
            # Single contact validation
            try:
                contact = Contact.objects.get(id=contact_id)
                contacts_to_validate = [contact]
            except Contact.DoesNotExist:
                error_msg = f"Contact with ID {contact_id} not found"
                logger.error(error_msg)
                
                if validation_batch:
                    validation_batch.status = EmailValidationBatch.ValidationStatus.FAILED
                    validation_batch.save()
                    
                return error_msg
        elif contact_list_id:
            # ContactList validation
            try:
                contact_list = ContactList.objects.get(id=contact_list_id)
                
                # Filter contacts that haven't been validated or have unknown status
                contacts_to_validate = list(contact_list.contacts.filter(
                    zerobounce_status__in=[
                        None, 
                        '', 
                        Contact.EmailStatus.UNVERIFIED,
                        Contact.EmailStatus.UNKNOWN
                    ]
                ).order_by('email')[:max_validations])
                
                if not contacts_to_validate:
                    # If no unverified contacts, try to get all contacts
                    contacts_to_validate = list(contact_list.contacts.all().order_by('email')[:max_validations])
            except ContactList.DoesNotExist:
                error_msg = f"ContactList with ID {contact_list_id} not found"
                logger.error(error_msg)
                
                if validation_batch:
                    validation_batch.status = EmailValidationBatch.ValidationStatus.FAILED
                    validation_batch.save()
                    
                return error_msg
        else:
            # No specific contacts provided
            error_msg = "No contacts specified for validation"
            logger.error(error_msg)
            
            if validation_batch:
                validation_batch.status = EmailValidationBatch.ValidationStatus.FAILED
                validation_batch.save()
                
            return error_msg
        
        # Log the number of contacts to validate
        logger.info(f"Validating {len(contacts_to_validate)} contacts")
        
        # Track validation results
        valid_count = 0
        invalid_count = 0
        catch_all_count = 0
        unknown_count = 0
        other_count = 0
        error_count = 0
        
        # Process each contact
        for i, contact in enumerate(contacts_to_validate):
            try:
                # Get IP address if available and requested
                ip_address = None
                if use_ip and contact.zerobounce_country:
                    # If we already have country data, we might have IP data too
                    ip_address = "127.0.0.1"  # Placeholder, would need actual IP tracking
                
                # Log the current validation
                logger.info(f"Validating email {i+1}/{len(contacts_to_validate)}: {contact.email}")
                
                # Validate the email
                result = zerobounce_service.validate_email(
                    contact.email, 
                    ip_address=ip_address,
                    timeout=timeout
                )
                
                # Log the validation result
                logger.info(f"Validation result for {contact.email}: {result.get('status', 'unknown')}")
                
                # Update the contact with validation results
                zerobounce_service.update_contact_from_validation(contact, result)
                
                # Track results by status
                status = result.get('status', 'unknown')
                if status == 'valid':
                    valid_count += 1
                elif status == 'invalid':
                    invalid_count += 1
                elif status == 'catch-all':
                    catch_all_count += 1
                elif status == 'unknown':
                    unknown_count += 1
                else:
                    other_count += 1
                
                # Update batch progress periodically (every 5 validations)
                if validation_batch and i % 5 == 0:
                    validation_batch.valid_count = valid_count
                    validation_batch.invalid_count = invalid_count
                    validation_batch.catch_all_count = catch_all_count
                    validation_batch.unknown_count = unknown_count
                    validation_batch.other_count = other_count
                    validation_batch.error_count = error_count
                    validation_batch.save()
                    
            except Exception as e:
                logger.error(f"Error validating email {contact.email}: {str(e)}")
                error_count += 1
                continue
        
        # Update the validation batch with results
        if validation_batch:
            validation_batch.valid_count = valid_count
            validation_batch.invalid_count = invalid_count
            validation_batch.catch_all_count = catch_all_count
            validation_batch.unknown_count = unknown_count
            validation_batch.other_count = other_count
            validation_batch.error_count = error_count
            validation_batch.status = EmailValidationBatch.ValidationStatus.COMPLETED
            validation_batch.completed_at = timezone.now()
            validation_batch.save()
        
        # Return a summary of results
        result_summary = (
            f"Validated {len(contacts_to_validate)} emails. Results: "
            f"{valid_count} valid, {invalid_count} invalid, "
            f"{catch_all_count} catch-all, {unknown_count} unknown, "
            f"{other_count} other, {error_count} errors"
        )
        
        logger.info(result_summary)
        return result_summary
            
    except Exception as e:
        logger.error(f"Error in ZeroBounce validation task: {str(e)}")
        
        # Update the validation batch status
        if batch_id:
            try:
                validation_batch = EmailValidationBatch.objects.get(id=batch_id)
                validation_batch.status = EmailValidationBatch.ValidationStatus.FAILED
                validation_batch.save()
            except EmailValidationBatch.DoesNotExist:
                pass
                
        raise

from huey.contrib.djhuey import task

@task()
def debug_execute_serpapi_search(company_search_id, max_results=None):
    """
    Execute a SerpAPI search as a background task with enhanced debugging
    
    Args:
        company_search_id: ID of the CompanySearch to process
        max_results: Maximum number of results to return (None for all)
    """
    try:
        logger.debug(f"Starting debug_execute_serpapi_search with company_search_id={company_search_id}, max_results={max_results}")
        
        # Get the CompanySearch and search parameters
        company_search = CompanySearch.objects.get(id=company_search_id)
        logger.debug(f"Found CompanySearch: {company_search}")
        
        search_params = SerpAPISearchParameters.objects.get(company_search=company_search)
        logger.debug(f"Found SerpAPISearchParameters: query={search_params.query}, place_name={search_params.place_name}")
        
        # Create service and execute search
        service = SerpAPIService()
        logger.debug("Created SerpAPIService, starting search_all_pages")
        
        results = service.search_all_pages(search_params, max_results=max_results)
        logger.debug(f"search_all_pages returned {len(results) if results else 0} results")
        
        # Create companies from results
        companies = service.create_companies_from_results(results, company_search)
        logger.debug(f"create_companies_from_results created/found {len(companies) if companies else 0} companies")
        
        # Update results count (safely handle None result)
        if companies is not None:
            company_search.results_count = len(companies)
        else:
            company_search.results_count = 0
            companies = []  # Ensure we have an empty list for logging
        
        company_search.save()
        logger.debug(f"Updated company_search.results_count to {company_search.results_count}")
        
        return f"Found {company_search.results_count} companies for search #{company_search_id}"
        
    except Exception as e:
        # Log the error
        logger.error(f"Error executing SerpAPI search #{company_search_id}: {str(e)}", exc_info=True)
        # Re-raise to mark task as failed
        raise