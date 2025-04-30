from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import Q
import csv

from .models import Contact, ContactList, Cohort
from .forms import ContactForm, ContactListForm, ContactFilterForm, ContactListAddForm, CohortForm
from finder.models import ContactSearch

def contact_list_list(request):
    """View for listing all contact lists"""
    contact_lists = ContactList.objects.all().order_by('name')
    return render(request, 'pages/contacts/contact_list_list.html', {
        'contact_lists': contact_lists
    })

def contact_list_create(request):
    """View for creating a new contact list"""
    if request.method == 'POST':
        form = ContactListForm(request.POST)
        if form.is_valid():
            contact_list = form.save()
            messages.success(request, f"Contact list '{contact_list.name}' created successfully!")
            return redirect('contact_list_detail', list_id=contact_list.id)
    else:
        form = ContactListForm()
    
    return render(request, 'pages/contacts/contact_list_form.html', {
        'form': form,
        'title': 'Create Contact List',
        'submit_text': 'Create List'
    })

def contact_list_detail(request, list_id):
    """View for showing details of a specific contact list"""
    contact_list = get_object_or_404(ContactList, id=list_id)
    contacts = contact_list.contacts.all().order_by('last_name', 'first_name')
    
    # Add pagination
    paginator = Paginator(contacts, 20)  # Show 20 contacts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available searches to add
    searches = ContactSearch.objects.filter(results_count__gt=0).order_by('-created_at')
    
    return render(request, 'pages/contacts/contact_list_detail.html', {
        'contact_list': contact_list,
        'contacts': page_obj,
        'searches': searches
    })

def contact_list_update(request, list_id):
    """View for updating an existing contact list"""
    contact_list = get_object_or_404(ContactList, id=list_id)
    
    if request.method == 'POST':
        form = ContactListForm(request.POST, instance=contact_list)
        if form.is_valid():
            form.save()
            messages.success(request, f"Contact list '{contact_list.name}' updated successfully!")
            return redirect('contact_list_detail', list_id=contact_list.id)
    else:
        form = ContactListForm(instance=contact_list)
    
    return render(request, 'pages/contacts/contact_list_form.html', {
        'form': form,
        'contact_list': contact_list,
        'title': 'Update Contact List',
        'submit_text': 'Update List'
    })

def contact_list_delete(request, list_id):
    """View for deleting a contact list"""
    contact_list = get_object_or_404(ContactList, id=list_id)
    
    if request.method == 'POST':
        list_name = contact_list.name
        contact_list.delete()
        messages.success(request, f"Contact list '{list_name}' deleted successfully!")
        return redirect('contact_list_list')
    
    return render(request, 'pages/contacts/contact_list_confirm_delete.html', {
        'contact_list': contact_list
    })

def contact_list_export(request, list_id):
    """View for exporting contacts from a list to CSV"""
    contact_list = get_object_or_404(ContactList, id=list_id)
    contacts = contact_list.contacts.all().order_by('last_name', 'first_name')
    
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{contact_list.name.replace(" ", "_")}_contacts.csv"'},
    )
    
    writer = csv.writer(response)
    # Write header row
    writer.writerow([
        'First Name', 'Last Name', 'Email', 'Position', 'Phone Number',
        'Organization Name', 'LinkedIn URL', 'Twitter', 'Status'
    ])
    
    # Write data rows
    for contact in contacts:
        writer.writerow([
            contact.first_name, contact.last_name, contact.email,
            contact.position or '', contact.phone_number or '',
            contact.organization_name or '', contact.linkedin_url or '',
            contact.twitter or '', contact.get_status_display()
        ])
    
    return response

def contact_list_add_contacts(request, list_id):
    """View for adding contacts to a list"""
    contact_list = get_object_or_404(ContactList, id=list_id)
    
    if request.method == 'POST':
        form = ContactListAddForm(request.POST)
        if form.is_valid():
            contacts = form.cleaned_data['contacts']
            for contact in contacts:
                contact_list.contacts.add(contact)
            
            contact_list.save()
            messages.success(request, f"{len(contacts)} contacts added to '{contact_list.name}'!")
            return redirect('contact_list_detail', list_id=contact_list.id)
    else:
        # Get contacts not already in this list
        existing_contact_ids = contact_list.contacts.values_list('id', flat=True)
        available_contacts = Contact.objects.exclude(id__in=existing_contact_ids).order_by('last_name', 'first_name')
        
        form = ContactListAddForm()
        form.fields['contacts'].queryset = available_contacts
    
    return render(request, 'pages/contacts/contact_list_add_contacts.html', {
        'form': form,
        'contact_list': contact_list
    })

def contact_list_add_search_results(request, list_id, search_id):
    """View for adding search results to a contact list"""
    contact_list = get_object_or_404(ContactList, id=list_id)
    search = get_object_or_404(ContactSearch, id=search_id)
    
    # Get contacts from the search
    search_contacts = search.contacts.all()
    added_count = 0
    
    # Add each contact to the list if not already present
    for contact in search_contacts:
        if contact not in contact_list.contacts.all():
            contact_list.contacts.add(contact)
            added_count += 1
    
    messages.success(request, f"Added {added_count} contacts from search #{search.id} to '{contact_list.name}'!")
    return redirect('contact_list_detail', list_id=contact_list.id)

def contact_list_remove_contact(request, list_id, contact_id):
    """View for removing a contact from a list"""
    if request.method == 'POST':
        contact_list = get_object_or_404(ContactList, id=list_id)
        contact = get_object_or_404(Contact, id=contact_id)
        
        if contact in contact_list.contacts.all():
            contact_list.contacts.remove(contact)
            messages.success(request, f"Removed '{contact.first_name} {contact.last_name}' from the list.")
        else:
            messages.warning(request, f"'{contact.first_name} {contact.last_name}' is not in this list.")
            
    return redirect('contact_list_detail', list_id=list_id)

def contact_list_add_from_filter(request):
    """View for adding contacts from filter results to a list"""
    if request.method == 'POST':
        contact_list_id = request.POST.get('contact_list_id')
        save_type = request.POST.get('save_type')
        filter_params = request.POST.get('filter_params')
        page_number = request.POST.get('page_number', 1)
        
        # Get the target list
        contact_list = get_object_or_404(ContactList, id=contact_list_id)
        
        # Get the contacts based on the filter
        contacts = Contact.objects.all()
        
        # Parse filter parameters
        if filter_params:
            filter_dict = {}
            for param in filter_params.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    filter_dict[key] = value
            
            # Apply filters
            if 'name' in filter_dict:
                name_query = filter_dict['name']
                contacts = contacts.filter(
                    Q(first_name__icontains=name_query) | Q(last_name__icontains=name_query)
                )
            
            if 'email' in filter_dict:
                contacts = contacts.filter(email__icontains=filter_dict['email'])
            
            if 'company' in filter_dict:
                contacts = contacts.filter(
                    Q(company__name__icontains=filter_dict['company']) |
                    Q(organization_name__icontains=filter_dict['company'])
                )
            
            if 'position' in filter_dict:
                contacts = contacts.filter(position__icontains=filter_dict['position'])
                
            if 'status' in filter_dict:
                contacts = contacts.filter(status=filter_dict['status'])
        
        # Get only the current page or all contacts
        if save_type == 'page':
            # Paginate the results to get just the current page
            paginator = Paginator(contacts, 20)  # Match the page size from the list view
            page_obj = paginator.get_page(page_number)
            contacts_to_add = page_obj.object_list
        else:  # 'all'
            # Use all contacts from the filter
            contacts_to_add = contacts
        
        # Add contacts to the list
        added_count = 0
        for contact in contacts_to_add:
            if contact not in contact_list.contacts.all():
                contact_list.contacts.add(contact)
                added_count += 1
        
        if added_count > 0:
            messages.success(
                request, 
                f"Added {added_count} contacts to '{contact_list.name}' from {save_type} results."
            )
        else:
            messages.info(
                request, 
                f"No new contacts were added to '{contact_list.name}'. All filtered contacts were already in the list."
            )
        
        return redirect('contact_list_detail', list_id=contact_list.id)
    
    # If not POST, redirect to contact list
    return redirect('contact_list')

# Contact Views
def contact_list(request):
    """View for listing all contacts with filters"""
    # Start with all contacts
    contacts = Contact.objects.all()
    
    # Initialize the filter form
    form = ContactFilterForm(request.GET)
    if form.is_valid():
        # Apply filters if provided
        if form.cleaned_data.get('name'):
            name_query = form.cleaned_data['name']
            contacts = contacts.filter(
                Q(first_name__icontains=name_query) | Q(last_name__icontains=name_query)
            )
        
        if form.cleaned_data.get('email'):
            contacts = contacts.filter(email__icontains=form.cleaned_data['email'])
        
        if form.cleaned_data.get('company'):
            company_query = form.cleaned_data['company']
            contacts = contacts.filter(
                Q(company__name__icontains=company_query) |
                Q(organization_name__icontains=company_query)
            )
        
        if form.cleaned_data.get('position'):
            contacts = contacts.filter(position__icontains=form.cleaned_data['position'])
        
        if form.cleaned_data.get('status'):
            contacts = contacts.filter(status=form.cleaned_data['status'])
    
    # Order contacts by name
    contacts = contacts.order_by('last_name', 'first_name')
    
    # Add pagination
    paginator = Paginator(contacts, 20)  # Show 20 contacts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all contact lists for the save to list dropdown
    contact_lists = ContactList.objects.all().order_by('name')
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        # If HTMX request, return only the results component
        return render(request, 'components/contacts/contact_results.html', {
            'contacts': page_obj,
            'contact_lists': contact_lists
        })
    else:
        # For non-HTMX requests, return the full page
        return render(request, 'pages/contacts/contact_list.html', {
            'contacts': page_obj,
            'form': form,
            'contact_lists': contact_lists
        })

def contact_detail(request, contact_id):
    """View for showing details of a specific contact"""
    contact = get_object_or_404(Contact, id=contact_id)
    
    # Get all lists this contact is in
    contact_lists = contact.contact_lists.all()
    
    return render(request, 'pages/contacts/contact_detail.html', {
        'contact': contact,
        'contact_lists': contact_lists
    })

def contact_create(request):
    """View for creating a new contact"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            messages.success(request, f"Contact '{contact.first_name} {contact.last_name}' created successfully!")
            return redirect('contact_detail', contact_id=contact.id)
    else:
        form = ContactForm()
    
    return render(request, 'pages/contacts/contact_form.html', {
        'form': form,
        'title': 'Create Contact',
        'submit_text': 'Create Contact'
    })

def contact_update(request, contact_id):
    """View for updating an existing contact"""
    contact = get_object_or_404(Contact, id=contact_id)
    
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            messages.success(request, f"Contact '{contact.first_name} {contact.last_name}' updated successfully!")
            return redirect('contact_detail', contact_id=contact.id)
    else:
        form = ContactForm(instance=contact)
    
    return render(request, 'pages/contacts/contact_form.html', {
        'form': form,
        'contact': contact,
        'title': 'Update Contact',
        'submit_text': 'Update Contact'
    })

def contact_delete(request, contact_id):
    """View for deleting a contact"""
    contact = get_object_or_404(Contact, id=contact_id)
    
    if request.method == 'POST':
        contact_name = f"{contact.first_name} {contact.last_name}"
        contact.delete()
        messages.success(request, f"Contact '{contact_name}' deleted successfully!")
        return redirect('contact_list')
    
    return render(request, 'pages/contacts/contact_confirm_delete.html', {
        'contact': contact
    })

def cohort_list(request):
    """View for listing all cohorts"""
    cohorts = Cohort.objects.all().order_by('name')
    return render(request, 'pages/contacts/cohort_list.html', {
        'cohorts': cohorts
    })

def cohort_create(request):
    """View for creating a new cohort"""
    if request.method == 'POST':
        form = CohortForm(request.POST)
        if form.is_valid():
            cohort = form.save()
            
            # Generate contacts for the cohort immediately
            contacts_added = cohort.generate_contacts()
            
            messages.success(request, f"Cohort '{cohort.name}' created successfully with {contacts_added} contacts!")
            return redirect('cohort_detail', cohort_id=cohort.id)
    else:
        form = CohortForm()
    
    return render(request, 'pages/contacts/cohort_form.html', {
        'form': form,
        'title': 'Create Cohort',
        'submit_text': 'Create Cohort'
    })

def cohort_detail(request, cohort_id):
    cohort = get_object_or_404(Cohort, id=cohort_id)
    contacts = cohort.contacts.all().order_by('company__name', 'last_name', 'first_name')
    
    # Check if the user requested regeneration
    if request.method == 'POST' and 'regenerate' in request.POST:
        contacts_added = cohort.generate_contacts()
        messages.success(request, f"Cohort regenerated successfully with {contacts_added} contacts!")
        return redirect('cohort_detail', cohort_id=cohort.id)
    
    # Add pagination
    paginator = Paginator(contacts, 20)  # Show 20 contacts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'pages/contacts/cohort_detail.html', {
        'cohort': cohort,
        'contacts': page_obj,
    })

def cohort_update(request, cohort_id):
    """View for updating an existing cohort"""
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    if request.method == 'POST':
        form = CohortForm(request.POST, instance=cohort)
        if form.is_valid():
            cohort = form.save()
            
            # Regenerate contacts if selection criteria changed
            regenerate = False
            changed_fields = form.changed_data
            criteria_fields = ['company_list', 'selection_method', 'email_prefix_hierarchy', 
                              'target_department', 'minimum_seniority', 'job_title_keywords']
            
            for field in criteria_fields:
                if field in changed_fields:
                    regenerate = True
                    break
            
            if regenerate:
                contacts_added = cohort.generate_contacts()
                messages.success(request, f"Cohort '{cohort.name}' updated and regenerated with {contacts_added} contacts!")
            else:
                messages.success(request, f"Cohort '{cohort.name}' updated successfully!")
                
            return redirect('cohort_detail', cohort_id=cohort.id)
    else:
        form = CohortForm(instance=cohort)
    
    return render(request, 'pages/contacts/cohort_form.html', {
        'form': form,
        'cohort': cohort,
        'title': 'Update Cohort',
        'submit_text': 'Update Cohort'
    })

def cohort_delete(request, cohort_id):
    """View for deleting a cohort"""
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    if request.method == 'POST':
        cohort_name = cohort.name
        cohort.delete()
        messages.success(request, f"Cohort '{cohort_name}' deleted successfully!")
        return redirect('cohort_list')
    
    return render(request, 'pages/contacts/cohort_confirm_delete.html', {
        'cohort': cohort
    })

def cohort_export(request, cohort_id):
    """View for exporting cohort contacts to CSV"""
    cohort = get_object_or_404(Cohort, id=cohort_id)
    contacts = cohort.contacts.all().order_by('company__name', 'last_name', 'first_name')
    
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{cohort.name.replace(" ", "_")}_contacts.csv"'},
    )
    
    writer = csv.writer(response)
    # Write header row
    writer.writerow([
        'First Name', 'Last Name', 'Email', 'Position', 'Phone Number',
        'Company', 'LinkedIn URL', 'Twitter', 'Status'
    ])
    
    # Write data rows
    for contact in contacts:
        company_name = contact.company.name if contact.company else contact.organization_name or ''
        
        writer.writerow([
            contact.first_name, contact.last_name, contact.email,
            contact.position or '', contact.phone_number or '',
            company_name, contact.linkedin_url or '',
            contact.twitter or '', contact.get_status_display()
        ])
    
    return response