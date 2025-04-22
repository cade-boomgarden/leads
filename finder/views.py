from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .forms import SerpAPISearchForm, WebScrapeForm, HunterDomainSearchForm
from .models import CompanySearch, SerpAPISearchParameters, ContactSearch, WebScrapeParameters, HunterDomainSearchParameters
from .tasks import execute_serpapi_search, execute_webscrape_search, execute_hunter_search

def serpapi_search(request):
    """View for the SerpAPI search form"""
    if request.method == 'POST':
        form = SerpAPISearchForm(request.POST)
        if form.is_valid():
            # Create CompanySearch object
            company_search = CompanySearch.objects.create(
                method=CompanySearch.CompanySearchMethods.SERPAPI,
                results_count=0  # Will be updated when the search completes
            )
            
            # Create SerpAPISearchParameters
            search_params = SerpAPISearchParameters.objects.create(
                company_search=company_search,
                query=form.cleaned_data['query'],
                place_name=form.cleaned_data.get('place_name'),
                latitude=form.cleaned_data.get('latitude'),
                longitude=form.cleaned_data.get('longitude'),
                zoom=form.cleaned_data['zoom'],
                google_domain='google.com',  # Always use US domain
                language='en',  # Always use English
                country='us',   # Always use US
                per_page=20,    # Standard per page value
            )
            
            # Queue the search task
            execute_serpapi_search(
                company_search.id, 
                max_results=form.cleaned_data['max_results']
            )
            
            # Display any warnings
            for warning in getattr(form, 'warnings', []):
                messages.warning(request, warning)
            
            messages.success(request, "Search initiated successfully! You'll be notified when it's complete.")
            return redirect('search_list')
    else:
        form = SerpAPISearchForm()
    
    return render(request, 'pages/finder/serpapi_search.html', {'form': form})

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
    
    return render(request, 'pages/finder/company_search_detail.html', {
        'search': search,
        'companies': companies,
        'search_params': search_params
    })

def contact_search_list(request):
    """View for listing all contact searches"""
    searches = ContactSearch.objects.all().order_by('-created_at')
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
    
    return render(request, 'pages/finder/contact_search_detail.html', {
        'search': search,
        'contacts': contacts,
        'search_params': search_params
    })

def hunter_search(request):
    """View for the Hunter.io domain search form"""
    if request.method == 'POST':
        form = HunterDomainSearchForm(request.POST)
        if form.is_valid():
            # Create ContactSearch object
            contact_search = ContactSearch.objects.create(
                method=ContactSearch.ContactSearchMethods.HUNTER,
                results_count=0  # Will be updated when the search completes
            )
            
            # Get the form data
            source_type = form.cleaned_data['source_type']
            domain = form.cleaned_data.get('domain', '')
            company = form.cleaned_data.get('company', '')
            company_list = form.cleaned_data.get('company_list')
            
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
            return redirect('contact_search_list')
    else:
        form = HunterDomainSearchForm()
    
    return render(request, 'pages/finder/hunter_search.html', {'form': form})