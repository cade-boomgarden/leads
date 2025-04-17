from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .forms import SerpAPISearchForm
from .models import CompanySearch, SerpAPISearchParameters
from .tasks import execute_serpapi_search

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

def search_list(request):
    """View for listing all searches"""
    searches = CompanySearch.objects.all().order_by('-created_at')
    return render(request, 'pages/finder/search_list.html', {'searches': searches})

def search_detail(request, search_id):
    """View for showing details of a specific search"""
    search = get_object_or_404(CompanySearch, id=search_id)
    companies = search.companies.all()
    
    # Get the search parameters based on the method
    search_params = None
    if search.method == CompanySearch.CompanySearchMethods.SERPAPI:
        search_params = search.serpapi_parameters
    
    return render(request, 'pages/finder/search_detail.html', {
        'search': search,
        'companies': companies,
        'search_params': search_params
    })