from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import (
    CompanySearch, ContactSearch, SerpAPISearchParameters, 
    WebScrapeParameters, HunterDomainSearchParameters,
    EmailValidationBatch
)
from .forms import (
    SerpAPISearchForm, WebScrapeForm, HunterDomainSearchForm,
    ZeroBounceValidationForm
)
from .tasks import (
    execute_serpapi_search, execute_webscrape_search, 
    execute_hunter_search, validate_emails_with_zerobounce
)
from contacts.models import Contact, ContactList
from companies.models import Company, CompanyList
from .services import SerpAPIService, HunterService, ZeroBounceService

def finder_dashboard(request):
    """Main dashboard view for the finder app showing recent searches and validations"""
    # Get recent company searches
    company_searches = CompanySearch.objects.all().order_by('-created_at')[:10]
    
    # Get recent contact searches
    contact_searches = ContactSearch.objects.all().order_by('-created_at')[:10]
    
    # Get recent email validations
    email_validations = EmailValidationBatch.objects.all().order_by('-created_at')[:10]
    
    # Update status of pending/processing validations
    for validation in email_validations:
        if validation.status in [EmailValidationBatch.ValidationStatus.PENDING, 
                               EmailValidationBatch.ValidationStatus.PROCESSING]:
            validation.update_task_status()

    serpapi = SerpAPIService()
    # Get the current account info
    serpapi_account_info = serpapi.get_account_info()
    serpapi_remaining_searches = serpapi_account_info.get('plan_searches_left', 0)
    hunter = HunterService()
    # Get the current account info
    hunter_account_info = hunter.get_account_info()
    hunter_available_searches = hunter_account_info.get('searches', {}).get('available', 0)
    hunter_used_searches = hunter_account_info.get('searches', {}).get('used', 0)
    hunter_remaining_searches = hunter_available_searches - hunter_used_searches


    zerobounce = ZeroBounceService()
    # Get remaining credits
    zerobounce_credits = zerobounce.get_credits()
    
    context = {
        'company_searches': company_searches,
        'contact_searches': contact_searches,
        'email_validations': email_validations,
        'serpapi_remaining_searches': serpapi_remaining_searches,
        'hunter_remaining_searches': hunter_remaining_searches,
        'zerobounce_credits': zerobounce_credits,
    }
    
    return render(request, 'pages/finder/dashboard.html', context)

def serpapi_search(request):
    serpapi = SerpAPIService()
    account_info = serpapi.get_account_info()
    monthly_searches = account_info.get('searches_per_month', 0)
    remaining_searches = account_info.get('plan_searches_left', 0)
    if request.method == 'POST':
        form = SerpAPISearchForm(request.POST)
        if form.is_valid():
            # Add geocoding logic here if needed
            company_search = CompanySearch.objects.create(
                method=CompanySearch.CompanySearchMethods.SERPAPI,
                results_count=0
            )
            
            # Create parameters with proper location handling
            search_params = SerpAPISearchParameters.objects.create(
                company_search=company_search,
                query=form.cleaned_data['query'],
                place_name=form.cleaned_data.get('place_name'),
                latitude=form.cleaned_data.get('latitude'),
                longitude=form.cleaned_data.get('longitude'),
                zoom=form.cleaned_data.get('zoom'),  # Force reasonable default
                google_domain='google.com',
                language='en',
                country='us'
            )
            
            execute_serpapi_search(company_search.id)
            return redirect('company_search_list')
    else:
        form = SerpAPISearchForm()
    
    return render(request, 'pages/finder/serpapi_search.html', {'form': form, 'monthly_searches': monthly_searches, 'remaining_searches': remaining_searches})

def webscrape_search(request):
    """View for the web scrape search form"""
    if request.method == 'POST':
        form = WebScrapeForm(request.POST)
        if form.is_valid():
            # Create ContactSearch object
            contact_search = ContactSearch.objects.create(
                method=ContactSearch.ContactSearchMethods.SCRAPE,
                results_count=0  # Will be updated when the search completes
            )
            
            # Create WebScrapeParameters
            scrape_params = WebScrapeParameters.objects.create(
                contact_search=contact_search,
                target_url=form.cleaned_data.get('target_url', ''),
                max_depth=form.cleaned_data['max_depth'],
                max_pages=form.cleaned_data['max_pages'],
                stay_within_domain=form.cleaned_data['stay_within_domain'],
                follow_subdomains=form.cleaned_data['follow_subdomains'],
                priority_paths=form.cleaned_data['priority_paths'],
                exclude_paths=form.cleaned_data['exclude_paths'],
                target_keywords=form.cleaned_data['target_keywords'],
                extract_names=form.cleaned_data['extract_names'],
                extract_job_titles=form.cleaned_data['extract_job_titles'],
                extract_phone_numbers=form.cleaned_data['extract_phone_numbers'],
                request_delay=form.cleaned_data['request_delay'],
                concurrent_requests=form.cleaned_data['concurrent_requests'],
                request_timeout=30.0,  # Default timeout
                follow_robotstxt=True,  # Always respect robots.txt
                user_agent="Mozilla/5.0 (compatible; CompanyBot/1.0)",  # Default user agent
            )
            
            # Queue the search task based on source type
            company_list_id = None
            if form.cleaned_data['source_type'] == 'company_list' and form.cleaned_data['company_list']:
                company_list_id = form.cleaned_data['company_list'].id
                
            execute_webscrape_search(contact_search.id, company_list_id)
            
            messages.success(request, "Web scrape initiated successfully! This may take some time depending on the number of websites to process.")
            return redirect('contact_search_list')
    else:
        form = WebScrapeForm()
    
    return render(request, 'pages/finder/webscrape_search.html', {'form': form})

def company_search_list(request):
    """View for listing all company searches"""
    searches = CompanySearch.objects.all().order_by('-created_at')
    return render(request, 'pages/finder/company_search_list.html', {'searches': searches})

def company_search_detail(request, search_id):
    """View for showing details of a specific company search"""
    search = get_object_or_404(CompanySearch, id=search_id)
    companies = search.companies.all()
    
    # Get the search parameters based on the method
    search_params = None
    if search.method == CompanySearch.CompanySearchMethods.SERPAPI:
        search_params = search.serpapi_parameters
    
    # Get all company lists for the dropdown
    company_lists = CompanyList.objects.all().order_by('name')
    
    return render(request, 'pages/finder/company_search_detail.html', {
        'search': search,
        'companies': companies,
        'search_params': search_params,
        'company_lists': company_lists
    })

def contact_search_list(request):
    """View for listing all contact searches"""
    # Get all contact searches, regardless of method
    searches = ContactSearch.objects.all().order_by('-created_at')
    
    # Log the methods of searches found for debugging
    import logging
    logger = logging.getLogger(__name__)
    method_counts = {}
    for search in searches:
        method = search.get_method_display()
        if method in method_counts:
            method_counts[method] += 1
        else:
            method_counts[method] = 1
    
    logger.info(f"Contact search methods count: {method_counts}")
    
    return render(request, 'pages/finder/contact_search_list.html', {'searches': searches})

def contact_search_detail(request, search_id):
    """View for showing details of a specific contact search"""
    search = get_object_or_404(ContactSearch, id=search_id)
    contacts = search.contacts.all()
    
    # Get the search parameters based on the method
    search_params = None
    if search.method == ContactSearch.ContactSearchMethods.SCRAPE:
        search_params = search.webscrape_parameters
    elif search.method == ContactSearch.ContactSearchMethods.HUNTER:
        search_params = search.hunter_parameters
    
    # Get all contact lists for the dropdown
    contact_lists = ContactList.objects.all().order_by('name')
    
    return render(request, 'pages/finder/contact_search_detail.html', {
        'search': search,
        'contacts': contacts,
        'search_params': search_params,
        'contact_lists': contact_lists
    })

def hunter_search(request):
    """View for the Hunter.io domain search form"""
    if request.method == 'POST':
        form = HunterDomainSearchForm(request.POST)
        if form.is_valid():
            # Get form data
            source_type = form.cleaned_data['source_type']
            domain = form.cleaned_data.get('domain', '')
            company = form.cleaned_data.get('company', '')
            company_list = form.cleaned_data.get('company_list')
            
            # Create ContactSearch object with correct method
            contact_search = ContactSearch.objects.create(
                method=ContactSearch.ContactSearchMethods.HUNTER,  # Ensure this is set to HUNTER
                results_count=0  # Will be updated when the search completes
            )
            
            # Convert multiple choice fields to lists
            seniority_levels = list(form.cleaned_data.get('seniority', []))
            departments = list(form.cleaned_data.get('department', []))
            required_fields = list(form.cleaned_data.get('required_fields', []))
            
            # Create HunterDomainSearchParameters
            search_params = HunterDomainSearchParameters.objects.create(
                contact_search=contact_search,
                domain=domain if source_type == 'domain' else '',
                company=company if source_type == 'company' else '',
                type=form.cleaned_data['type'],
                seniority_levels=seniority_levels,
                departments=departments,
                required_fields=required_fields,
                limit=form.cleaned_data['limit'],
                offset=0  # Start from the first page
            )
            
            # Queue the search task based on the source type
            if source_type == 'domain':
                execute_hunter_search(contact_search.id, domain=domain)
            elif source_type == 'company':
                execute_hunter_search(contact_search.id, company=company)
            elif source_type == 'company_list' and company_list:
                # Search for all domains in the company list
                execute_hunter_search(contact_search.id, company_list_id=company_list.id)
            
            # Display any warnings
            for warning in getattr(form, 'warnings', []):
                messages.warning(request, warning)
            
            messages.success(request, "Hunter search initiated successfully! You'll be notified when it's complete.")
            return redirect('contact_search_detail', search_id=contact_search.id)
    else:
        form = HunterDomainSearchForm()
    
    return render(request, 'pages/finder/hunter_search.html', {'form': form})

def zerobounce_validation(request):
    """View for validating emails using ZeroBounce API"""
    if request.method == 'POST':
        form = ZeroBounceValidationForm(request.POST)
        if form.is_valid():
            # Get form data
            validation_type = form.cleaned_data['validation_type']
            contact_list = form.cleaned_data.get('contact_list')
            contact = form.cleaned_data.get('contact')
            max_validations = form.cleaned_data.get('max_validations')
            use_ip = form.cleaned_data.get('use_ip', True)
            timeout = form.cleaned_data.get('timeout', 10)
            
            # Determine which contacts to validate
            contact_id = None
            contact_list_id = None
            
            if validation_type == 'contact':
                contact_id = contact.id
                validation_name = f"contact {contact.email}"
            elif validation_type == 'contact_list':
                contact_list_id = contact_list.id
                validation_name = f"list '{contact_list.name}'"
            elif validation_type == 'all_unverified':
                # We'll handle this in the task by not specifying a list
                validation_name = "all unverified contacts"
            
            # Queue the validation task
            validate_emails_with_zerobounce(
                contact_list_id=contact_list_id,
                contact_id=contact_id,
                max_validations=max_validations,
                use_ip=use_ip,
                timeout=timeout
            )
            
            # Check available credits first
            try:
                from finder.services.zerobounce_service import ZeroBounceService
                service = ZeroBounceService()
                credits = service.get_credits()
                messages.success(
                    request, 
                    f"Email validation for {validation_name} initiated! Available credits: {credits}"
                )
            except Exception as e:
                messages.warning(
                    request,
                    f"Email validation for {validation_name} initiated! Unable to check available credits: {str(e)}"
                )
            
            # Redirect based on validation type
            if validation_type == 'contact':
                return redirect('contact_detail', contact_id=contact.id)
            elif validation_type == 'contact_list':
                return redirect('contact_list_detail', list_id=contact_list.id)
            else:
                return redirect('contact_list')
    else:
        form = ZeroBounceValidationForm()
        
        # Pre-fill contact or contact list if provided in query string
        contact_id = request.GET.get('contact_id')
        contact_list_id = request.GET.get('contact_list_id')
        
        if contact_id:
            try:
                contact = Contact.objects.get(id=contact_id)
                form.fields['contact'].initial = contact.id
                form.fields['validation_type'].initial = 'contact'
            except Contact.DoesNotExist:
                pass
        elif contact_list_id:
            try:
                contact_list = ContactList.objects.get(id=contact_list_id)
                form.fields['contact_list'].initial = contact_list.id
                form.fields['validation_type'].initial = 'contact_list'
            except ContactList.DoesNotExist:
                pass
    
    # Display current ZeroBounce credits
    credits = "Unknown"
    try:
        from finder.services.zerobounce_service import ZeroBounceService
        service = ZeroBounceService()
        credits = service.get_credits()
    except Exception:
        pass
    
    return render(request, 'pages/finder/zerobounce_validation.html', {
        'form': form,
        'credits': credits
    })

def zerobounce_validation_list(request):
    """View for listing all email validation batches"""
    validation_batches = EmailValidationBatch.objects.all().order_by('-created_at')
    
    # Update status of pending/processing batches
    for batch in validation_batches:
        if batch.status in [EmailValidationBatch.ValidationStatus.PENDING, 
                          EmailValidationBatch.ValidationStatus.PROCESSING]:
            batch.update_task_status()
    
    return render(request, 'pages/finder/zerobounce_validation_list.html', {
        'validation_batches': validation_batches
    })

def zerobounce_validation_detail(request, batch_id):
    """View for showing details of a specific email validation batch"""
    validation_batch = get_object_or_404(EmailValidationBatch, id=batch_id)
    
    # Update the status if it's still in progress
    if validation_batch.status in [EmailValidationBatch.ValidationStatus.PENDING, 
                                 EmailValidationBatch.ValidationStatus.PROCESSING]:
        validation_batch.update_task_status()
        # Refresh after update
        validation_batch = EmailValidationBatch.objects.get(id=batch_id)
    
    # Get the validated contacts if a contact list is associated
    contacts = []
    if validation_batch.contact_list:
        contacts = validation_batch.contact_list.contacts.filter(
            zerobounce_status__isnull=False
        ).order_by('-zerobounce_processed_at')[:100]  # Limit to 100 most recent validations
    
    # Check if this is an HTMX request for polling
    if request.headers.get('HX-Request'):
        # Return only the status card
        return render(request, 'components/finder/validation_status_card.html', {
            'validation': validation_batch
        })
    
    # For normal requests, return the full detail view
    return render(request, 'pages/finder/zerobounce_validation_detail.html', {
        'validation': validation_batch,
        'contacts': contacts
    })

def add_contacts_to_list(request, search_id):
    """Add all contacts from a search to a contact list"""
    if request.method == 'POST':
        search = get_object_or_404(ContactSearch, id=search_id)
        contact_list_id = request.POST.get('contact_list_id')
        
        if not contact_list_id:
            messages.error(request, "Please select a contact list.")
            return redirect('contact_search_detail', search_id=search_id)
        
        # Get the contact list
        try:
            contact_list = ContactList.objects.get(id=contact_list_id)
        except ContactList.DoesNotExist:
            messages.error(request, "Selected contact list not found.")
            return redirect('contact_search_detail', list_id=contact_list_id)
        
        # Get all contacts from the search
        contacts = search.contacts.all()
        
        # Track how many contacts were added
        added_count = 0
        
        # Add each contact to the list if not already present
        for contact in contacts:
            if contact not in contact_list.contacts.all():
                contact_list.contacts.add(contact)
                added_count += 1
        
        if added_count > 0:
            messages.success(request, f"Added {added_count} contacts to '{contact_list.name}'.")
        else:
            messages.info(request, f"No new contacts were added to '{contact_list.name}'. All contacts were already in the list.")
        
        return redirect('contact_list_detail', list_id=contact_list_id)
    
    # If not POST, redirect back to search detail
    return redirect('contact_search_detail', search_id=search_id)

def add_companies_to_list(request, search_id):
    """Add all companies from a search to a company list"""
    if request.method == 'POST':
        search = get_object_or_404(CompanySearch, id=search_id)
        company_list_id = request.POST.get('company_list_id')
        
        if not company_list_id:
            messages.error(request, "Please select a company list.")
            return redirect('company_search_detail', search_id=search_id)
        
        # Get the company list
        try:
            company_list = CompanyList.objects.get(id=company_list_id)
        except CompanyList.DoesNotExist:
            messages.error(request, "Selected company list not found.")
            return redirect('company_search_detail', search_id=search_id)
        
        # Get all companies from the search
        companies = search.companies.all()
        
        # Track how many companies were added
        added_count = 0
        
        # Add each company to the list if not already present
        for company in companies:
            if company not in company_list.companies.all():
                company_list.companies.add(company)
                added_count += 1
        
        if added_count > 0:
            messages.success(request, f"Added {added_count} companies to '{company_list.name}'.")
        else:
            messages.info(request, f"No new companies were added to '{company_list.name}'. All companies were already in the list.")
        
        return redirect('company_list_detail', list_id=company_list_id)
    
    # If not POST, redirect back to search detail
    return redirect('company_search_detail', search_id=search_id)