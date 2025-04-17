from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
import csv

from .models import Company, CompanyList
from .forms import CompanyForm, CompanyListForm, CompanyFilterForm, CompanyListAddForm
from finder.models import CompanySearch

def home(request):
    """
    Render the home page.
    """
    return render(request, 'pages/home.html')

# Company List Views
def company_list_list(request):
    """View for listing all company lists"""
    company_lists = CompanyList.objects.all().order_by('name')
    return render(request, 'pages/companies/company_list_list.html', {
        'company_lists': company_lists
    })

def company_list_create(request):
    """View for creating a new company list"""
    if request.method == 'POST':
        form = CompanyListForm(request.POST)
        if form.is_valid():
            company_list = form.save()
            messages.success(request, f"Company list '{company_list.name}' created successfully!")
            return redirect('company_list_detail', list_id=company_list.id)
    else:
        form = CompanyListForm()
    
    return render(request, 'pages/companies/company_list_form.html', {
        'form': form,
        'title': 'Create Company List',
        'submit_text': 'Create List'
    })

def company_list_detail(request, list_id):
    """View for showing details of a specific company list"""
    company_list = get_object_or_404(CompanyList, id=list_id)
    companies = company_list.companies.all().order_by('name')
    
    # Add pagination
    paginator = Paginator(companies, 20)  # Show 20 companies per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available searches to add
    searches = CompanySearch.objects.filter(results_count__gt=0).order_by('-created_at')
    
    return render(request, 'pages/companies/company_list_detail.html', {
        'company_list': company_list,
        'companies': page_obj,
        'searches': searches
    })

def company_list_update(request, list_id):
    """View for updating an existing company list"""
    company_list = get_object_or_404(CompanyList, id=list_id)
    
    if request.method == 'POST':
        form = CompanyListForm(request.POST, instance=company_list)
        if form.is_valid():
            form.save()
            messages.success(request, f"Company list '{company_list.name}' updated successfully!")
            return redirect('company_list_detail', list_id=company_list.id)
    else:
        form = CompanyListForm(instance=company_list)
    
    return render(request, 'pages/companies/company_list_form.html', {
        'form': form,
        'company_list': company_list,
        'title': 'Update Company List',
        'submit_text': 'Update List'
    })

def company_list_delete(request, list_id):
    """View for deleting a company list"""
    company_list = get_object_or_404(CompanyList, id=list_id)
    
    if request.method == 'POST':
        list_name = company_list.name
        company_list.delete()
        messages.success(request, f"Company list '{list_name}' deleted successfully!")
        return redirect('company_list_list')
    
    return render(request, 'pages/companies/company_list_confirm_delete.html', {
        'company_list': company_list
    })

def company_list_export(request, list_id):
    """View for exporting companies from a list to CSV"""
    company_list = get_object_or_404(CompanyList, id=list_id)
    companies = company_list.companies.all().order_by('name')
    
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{company_list.name.replace(" ", "_")}_companies.csv"'},
    )
    
    writer = csv.writer(response)
    # Write header row
    writer.writerow([
        'Name', 'Domain', 'Website URL', 'Phone', 'Address', 
        'City', 'State', 'State Code', 'Primary Type', 'Rating',
        'Reviews Count', 'Description'
    ])
    
    # Write data rows
    for company in companies:
        writer.writerow([
            company.name, company.domain, company.website_url, company.phone,
            company.address, company.city, company.state, company.state_code,
            company.primary_type, company.rating, company.reviews_count,
            company.description
        ])
    
    return response

def company_list_add_companies(request, list_id):
    """View for adding companies to a list"""
    company_list = get_object_or_404(CompanyList, id=list_id)
    
    if request.method == 'POST':
        form = CompanyListAddForm(request.POST)
        if form.is_valid():
            companies = form.cleaned_data['companies']
            for company in companies:
                company_list.companies.add(company)
            
            company_list.save()
            messages.success(request, f"{len(companies)} companies added to '{company_list.name}'!")
            return redirect('company_list_detail', list_id=company_list.id)
    else:
        # Get companies not already in this list
        existing_company_ids = company_list.companies.values_list('id', flat=True)
        available_companies = Company.objects.exclude(id__in=existing_company_ids).order_by('name')
        
        form = CompanyListAddForm()
        form.fields['companies'].queryset = available_companies
    
    return render(request, 'pages/companies/company_list_add_companies.html', {
        'form': form,
        'company_list': company_list
    })

def company_list_add_search_results(request, list_id, search_id):
    """View for adding search results to a company list"""
    company_list = get_object_or_404(CompanyList, id=list_id)
    search = get_object_or_404(CompanySearch, id=search_id)
    
    # Get companies from the search
    search_companies = search.companies.all()
    added_count = 0
    
    # Add each company to the list if not already present
    for company in search_companies:
        if company not in company_list.companies.all():
            company_list.companies.add(company)
            added_count += 1
    
    messages.success(request, f"Added {added_count} companies from search #{search.id} to '{company_list.name}'!")
    return redirect('company_list_detail', list_id=company_list.id)

def company_list_remove_company(request, list_id, company_id):
    """View for removing a company from a list"""
    if request.method == 'POST':
        company_list = get_object_or_404(CompanyList, id=list_id)
        company = get_object_or_404(Company, id=company_id)
        
        if company in company_list.companies.all():
            company_list.companies.remove(company)
            messages.success(request, f"Removed '{company.name}' from the list.")
        else:
            messages.warning(request, f"'{company.name}' is not in this list.")
            
    return redirect('company_list_detail', list_id=list_id)

def company_list_add_from_filter(request):
    """View for adding companies from filter results to a list"""
    if request.method == 'POST':
        company_list_id = request.POST.get('company_list_id')
        save_type = request.POST.get('save_type')
        filter_params = request.POST.get('filter_params')
        page_number = request.POST.get('page_number', 1)
        
        # Get the target list
        company_list = get_object_or_404(CompanyList, id=company_list_id)
        
        # Get the companies based on the filter
        companies = Company.objects.all()
        
        # Parse filter parameters
        if filter_params:
            filter_dict = {}
            for param in filter_params.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    filter_dict[key] = value
            
            # Apply the same filters as in the company_list view
            if 'name' in filter_dict:
                companies = companies.filter(name__icontains=filter_dict['name'])
            
            if 'city' in filter_dict:
                companies = companies.filter(city__icontains=filter_dict['city'])
            
            if 'state' in filter_dict:
                companies = companies.filter(
                    Q(state__icontains=filter_dict['state']) | Q(state_code__icontains=filter_dict['state'])
                )
            
            if 'state_select' in filter_dict:
                companies = companies.filter(state_code=filter_dict['state_select'])
            
            if 'primary_type' in filter_dict:
                companies = companies.filter(primary_type__icontains=filter_dict['primary_type'])
                
            if 'primary_type_select' in filter_dict:
                companies = companies.filter(primary_type=filter_dict['primary_type_select'])
        
        # Get only the current page or all companies
        if save_type == 'page':
            # Paginate the results to get just the current page
            paginator = Paginator(companies, 20)  # Match the page size from the list view
            page_obj = paginator.get_page(page_number)
            companies_to_add = page_obj.object_list
        else:  # 'all'
            # Use all companies from the filter
            companies_to_add = companies
        
        # Add companies to the list
        added_count = 0
        for company in companies_to_add:
            if company not in company_list.companies.all():
                company_list.companies.add(company)
                added_count += 1
        
        if added_count > 0:
            messages.success(
                request, 
                f"Added {added_count} companies to '{company_list.name}' from {save_type} results."
            )
        else:
            messages.info(
                request, 
                f"No new companies were added to '{company_list.name}'. All filtered companies were already in the list."
            )
        
        return redirect('company_list_detail', list_id=company_list.id)
    
    # If not POST, redirect to company list
    return redirect('company_list')

# Company Views
def company_list(request):
    """View for listing all companies with filters"""
    # Start with all companies
    companies = Company.objects.all()
    
    # Initialize the filter form with dropdown choices
    form = CompanyFilterForm(request.GET)
    if form.is_valid():
        # Apply filters if provided
        if form.cleaned_data.get('name'):
            companies = companies.filter(name__icontains=form.cleaned_data['name'])
        
        if form.cleaned_data.get('city'):
            companies = companies.filter(city__icontains=form.cleaned_data['city'])
        
        # Handle both text and dropdown state filters
        if form.cleaned_data.get('state'):
            # Text field
            state_query = form.cleaned_data['state']
            companies = companies.filter(
                Q(state__icontains=state_query) | Q(state_code__icontains=state_query)
            )
        elif form.cleaned_data.get('state_select'):
            # Dropdown field
            state_code = form.cleaned_data['state_select']
            companies = companies.filter(state_code=state_code)
        
        # Handle both text and dropdown type filters
        if form.cleaned_data.get('primary_type'):
            # Text field
            companies = companies.filter(primary_type__icontains=form.cleaned_data['primary_type'])
        elif form.cleaned_data.get('primary_type_select'):
            # Dropdown field
            companies = companies.filter(primary_type=form.cleaned_data['primary_type_select'])
    
    # Order companies by name
    companies = companies.order_by('name')
    
    # Add pagination
    paginator = Paginator(companies, 20)  # Show 20 companies per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all company lists for the save to list dropdown
    company_lists = CompanyList.objects.all().order_by('name')
    
    return render(request, 'pages/companies/company_list.html', {
        'companies': page_obj,
        'form': form,
        'company_lists': company_lists
    })

def company_list_results(request):
    """View for HTMX to return just the company list results"""
    # This is similar to company_list but returns only the results component
    companies = Company.objects.all()
    
    # Initialize the filter form with dropdown choices
    form = CompanyFilterForm(request.GET)
    if form.is_valid():
        # Apply filters if provided
        if form.cleaned_data.get('name'):
            companies = companies.filter(name__icontains=form.cleaned_data['name'])
        
        if form.cleaned_data.get('city'):
            companies = companies.filter(city__icontains=form.cleaned_data['city'])
        
        # Handle both text and dropdown state filters
        if form.cleaned_data.get('state'):
            # Text field
            state_query = form.cleaned_data['state']
            companies = companies.filter(
                Q(state__icontains=state_query) | Q(state_code__icontains=state_query)
            )
        elif form.cleaned_data.get('state_select'):
            # Dropdown field
            state_code = form.cleaned_data['state_select']
            companies = companies.filter(state_code=state_code)
        
        # Handle both text and dropdown type filters
        if form.cleaned_data.get('primary_type'):
            # Text field
            companies = companies.filter(primary_type__icontains=form.cleaned_data['primary_type'])
        elif form.cleaned_data.get('primary_type_select'):
            # Dropdown field
            companies = companies.filter(primary_type=form.cleaned_data['primary_type_select'])
    
    # Order companies by name
    companies = companies.order_by('name')
    
    # Add pagination
    paginator = Paginator(companies, 20)  # Show 20 companies per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all company lists for the save to list dropdown
    company_lists = CompanyList.objects.all().order_by('name')
    
    return render(request, 'components/companies/company_results.html', {
        'companies': page_obj,
        'company_lists': company_lists
    })

def company_detail(request, company_id):
    """View for showing details of a specific company"""
    company = get_object_or_404(Company, id=company_id)
    
    # Get all lists this company is in
    company_lists = company.company_lists.all()
    
    return render(request, 'pages/companies/company_detail.html', {
        'company': company,
        'company_lists': company_lists
    })

def company_create(request):
    """View for creating a new company"""
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save()
            messages.success(request, f"Company '{company.name}' created successfully!")
            return redirect('company_detail', company_id=company.id)
    else:
        form = CompanyForm()
    
    return render(request, 'pages/companies/company_form.html', {
        'form': form,
        'title': 'Create Company',
        'submit_text': 'Create Company'
    })

def company_update(request, company_id):
    """View for updating an existing company"""
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Company '{company.name}' updated successfully!")
            return redirect('company_detail', company_id=company.id)
    else:
        form = CompanyForm(instance=company)
    
    return render(request, 'pages/companies/company_form.html', {
        'form': form,
        'company': company,
        'title': 'Update Company',
        'submit_text': 'Update Company'
    })

def company_delete(request, company_id):
    """View for deleting a company"""
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        company_name = company.name
        company.delete()
        messages.success(request, f"Company '{company_name}' deleted successfully!")
        return redirect('company_list')
    
    return render(request, 'pages/companies/company_confirm_delete.html', {
        'company': company
    })