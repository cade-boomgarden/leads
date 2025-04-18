from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField
from django.utils import timezone
import csv
from datetime import timedelta
from decimal import Decimal

from .models import Deal, DealStage
from .forms import DealForm, DealStageForm, DealFilterForm
from contacts.models import Contact

# Deal views
def deal_list(request):
    """View for listing all deals with filters"""
    # Start with all deals
    deals = Deal.objects.all()
    
    # Initialize the filter form
    form = DealFilterForm(request.GET)
    if form.is_valid():
        # Apply filters if provided
        if form.cleaned_data.get('contact'):
            contact_query = form.cleaned_data['contact']
            deals = deals.filter(
                Q(contact__first_name__icontains=contact_query) | 
                Q(contact__last_name__icontains=contact_query)
            )
        
        if form.cleaned_data.get('value_min'):
            deals = deals.filter(value__gte=form.cleaned_data['value_min'])
        
        if form.cleaned_data.get('value_max'):
            deals = deals.filter(value__lte=form.cleaned_data['value_max'])
        
        if form.cleaned_data.get('stage'):
            deals = deals.filter(stage=form.cleaned_data['stage'])
        
        if form.cleaned_data.get('status'):
            status = form.cleaned_data['status']
            if status == 'won':
                deals = deals.filter(is_won=True)
            elif status == 'lost':
                deals = deals.filter(is_lost=True)
            elif status == 'active':
                deals = deals.filter(is_won=False, is_lost=False)
        
        if form.cleaned_data.get('close_date_start'):
            deals = deals.filter(estimated_close_date__gte=form.cleaned_data['close_date_start'])
        
        if form.cleaned_data.get('close_date_end'):
            deals = deals.filter(estimated_close_date__lte=form.cleaned_data['close_date_end'])
    
    # Add pagination
    paginator = Paginator(deals, 20)  # Show 20 deals per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get summary statistics
    active_deals = Deal.objects.filter(is_won=False, is_lost=False)
    won_deals = Deal.objects.filter(is_won=True)
    lost_deals = Deal.objects.filter(is_lost=True)
    
    active_value = sum(deal.value for deal in active_deals)
    won_value = sum(deal.value for deal in won_deals)
    lost_value = sum(deal.value for deal in lost_deals)
    pipeline_value = sum(deal.expected_value for deal in active_deals)
    
    stats = {
        'active_count': active_deals.count(),
        'won_count': won_deals.count(),
        'lost_count': lost_deals.count(),
        'active_value': active_value,
        'won_value': won_value,
        'lost_value': lost_value,
        'pipeline_value': pipeline_value,
    }
    
    return render(request, 'pages/deals/deal_list.html', {
        'deals': page_obj,
        'form': form,
        'stats': stats,
    })

def deal_list_results(request):
    """View for HTMX to return just the deal list results"""
    # Similar to deal_list but returns only the results component
    deals = Deal.objects.all()
    
    # Initialize the filter form
    form = DealFilterForm(request.GET)
    if form.is_valid():
        # Apply filters if provided
        if form.cleaned_data.get('contact'):
            contact_query = form.cleaned_data['contact']
            deals = deals.filter(
                Q(contact__first_name__icontains=contact_query) | 
                Q(contact__last_name__icontains=contact_query)
            )
        
        if form.cleaned_data.get('value_min'):
            deals = deals.filter(value__gte=form.cleaned_data['value_min'])
        
        if form.cleaned_data.get('value_max'):
            deals = deals.filter(value__lte=form.cleaned_data['value_max'])
        
        if form.cleaned_data.get('stage'):
            deals = deals.filter(stage=form.cleaned_data['stage'])
        
        if form.cleaned_data.get('status'):
            status = form.cleaned_data['status']
            if status == 'won':
                deals = deals.filter(is_won=True)
            elif status == 'lost':
                deals = deals.filter(is_lost=True)
            elif status == 'active':
                deals = deals.filter(is_won=False, is_lost=False)
        
        if form.cleaned_data.get('close_date_start'):
            deals = deals.filter(estimated_close_date__gte=form.cleaned_data['close_date_start'])
        
        if form.cleaned_data.get('close_date_end'):
            deals = deals.filter(estimated_close_date__lte=form.cleaned_data['close_date_end'])
    
    # Add pagination
    paginator = Paginator(deals, 20)  # Show 20 deals per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'components/deals/deal_results.html', {
        'deals': page_obj,
    })

def deal_detail(request, deal_id):
    """View for showing details of a specific deal"""
    deal = get_object_or_404(Deal, id=deal_id)
    return render(request, 'pages/deals/deal_detail.html', {
        'deal': deal,
    })

def deal_create(request):
    """View for creating a new deal"""
    if request.method == 'POST':
        form = DealForm(request.POST)
        if form.is_valid():
            deal = form.save()
            messages.success(request, f"Deal for {deal.contact} created successfully!")
            return redirect('deals:deal_detail', deal_id=deal.id)
    else:
        form = DealForm()
        
        # Pre-fill contact if provided in query string
        contact_id = request.GET.get('contact')
        if contact_id:
            try:
                contact = Contact.objects.get(id=contact_id)
                form.fields['contact'].initial = contact.id
            except Contact.DoesNotExist:
                pass
    
    return render(request, 'pages/deals/deal_form.html', {
        'form': form,
        'title': 'Create Deal',
        'submit_text': 'Create Deal',
    })

def deal_update(request, deal_id):
    """View for updating an existing deal"""
    deal = get_object_or_404(Deal, id=deal_id)
    
    if request.method == 'POST':
        form = DealForm(request.POST, instance=deal)
        if form.is_valid():
            form.save()
            messages.success(request, f"Deal updated successfully!")
            return redirect('deals:deal_detail', deal_id=deal.id)
    else:
        form = DealForm(instance=deal)
    
    return render(request, 'pages/deals/deal_form.html', {
        'form': form,
        'deal': deal,
        'title': 'Update Deal',
        'submit_text': 'Update Deal',
    })

def deal_delete(request, deal_id):
    """View for deleting a deal"""
    deal = get_object_or_404(Deal, id=deal_id)
    
    if request.method == 'POST':
        contact_name = deal.contact.first_name + " " + deal.contact.last_name if deal.contact else "Unknown"
        deal.delete()
        messages.success(request, f"Deal for {contact_name} deleted successfully!")
        return redirect('deals:deal_list')
    
    return render(request, 'pages/deals/deal_confirm_delete.html', {
        'deal': deal,
    })

def deal_mark_as_won(request, deal_id):
    """View for marking a deal as won"""
    deal = get_object_or_404(Deal, id=deal_id)
    
    if request.method == 'POST':
        deal.mark_as_won()
        messages.success(request, f"Deal marked as won successfully!")
        return redirect('deals:deal_detail', deal_id=deal.id)
    
    return redirect('deals:deal_detail', deal_id=deal.id)

def deal_mark_as_lost(request, deal_id):
    """View for marking a deal as lost"""
    deal = get_object_or_404(Deal, id=deal_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', Deal.LostReason.NONE)
        deal.mark_as_lost(reason=reason)
        messages.success(request, f"Deal marked as lost successfully!")
        return redirect('deals:deal_detail', deal_id=deal.id)
    
    return render(request, 'pages/deals/deal_mark_as_lost.html', {
        'deal': deal,
        'lost_reasons': Deal.LostReason.choices,
    })

# Deal Stage views
def stage_list(request):
    """View for listing all deal stages"""
    stages = DealStage.objects.all()
    return render(request, 'pages/deals/stage_list.html', {
        'stages': stages,
    })

def stage_detail(request, stage_id):
    """View for showing details of a specific deal stage"""
    stage = get_object_or_404(DealStage, id=stage_id)
    deals = Deal.objects.filter(stage=stage)
    
    # Add pagination for deals in this stage
    paginator = Paginator(deals, 20)  # Show 20 deals per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'pages/deals/stage_detail.html', {
        'stage': stage,
        'deals': page_obj,
    })

def stage_create(request):
    """View for creating a new deal stage"""
    if request.method == 'POST':
        form = DealStageForm(request.POST)
        if form.is_valid():
            stage = form.save()
            messages.success(request, f"Deal stage '{stage.name}' created successfully!")
            return redirect('deals:stage_list')
    else:
        form = DealStageForm()
    
    return render(request, 'pages/deals/stage_form.html', {
        'form': form,
        'title': 'Create Deal Stage',
        'submit_text': 'Create Stage',
    })

def stage_update(request, stage_id):
    """View for updating an existing deal stage"""
    stage = get_object_or_404(DealStage, id=stage_id)
    
    if request.method == 'POST':
        form = DealStageForm(request.POST, instance=stage)
        if form.is_valid():
            form.save()
            messages.success(request, f"Deal stage '{stage.name}' updated successfully!")
            return redirect('deals:stage_detail', stage_id=stage.id)
    else:
        form = DealStageForm(instance=stage)
    
    return render(request, 'pages/deals/stage_form.html', {
        'form': form,
        'stage': stage,
        'title': 'Update Deal Stage',
        'submit_text': 'Update Stage',
    })

def stage_delete(request, stage_id):
    """View for deleting a deal stage"""
    stage = get_object_or_404(DealStage, id=stage_id)
    
    if request.method == 'POST':
        stage_name = stage.name
        stage.delete()
        messages.success(request, f"Deal stage '{stage_name}' deleted successfully!")
        return redirect('deals:stage_list')
    
    return render(request, 'pages/deals/stage_confirm_delete.html', {
        'stage': stage,
    })

# Pipeline view
def pipeline_view(request):
    """View for displaying the deal pipeline"""
    # Get all active deals
    active_deals = Deal.objects.filter(is_won=False, is_lost=False)
    
    # Group deals by stage for the pipeline visualization
    stages = DealStage.objects.all().order_by('order')
    pipeline_stages = []
    
    for stage in stages:
        stage_deals = active_deals.filter(stage=stage)
        stage_total = sum(deal.value for deal in stage_deals)
        stage_expected = sum(deal.expected_value for deal in stage_deals)
        
        pipeline_stages.append({
            'stage': stage,
            'deals': stage_deals,
            'deal_count': stage_deals.count(),
            'total_value': stage_total,
            'expected_value': stage_expected,
        })
    
    # Calculate pipeline values for different time periods
    pipeline_7_days = Deal.get_pipeline_value(days=7)
    pipeline_14_days = Deal.get_pipeline_value(days=14)
    pipeline_30_days = Deal.get_pipeline_value(days=30)
    pipeline_90_days = Deal.get_pipeline_value(days=90)
    total_pipeline = Deal.get_pipeline_value()
    
    # Get deals closing soon (next 7 days)
    now = timezone.now()
    seven_days_later = now + timedelta(days=7)
    closing_soon = active_deals.filter(
        estimated_close_date__gte=now,
        estimated_close_date__lte=seven_days_later
    ).order_by('estimated_close_date')
    
    pipeline_data = {
        'stages': pipeline_stages,
        'pipeline_7_days': pipeline_7_days,
        'pipeline_14_days': pipeline_14_days,
        'pipeline_30_days': pipeline_30_days,
        'pipeline_90_days': pipeline_90_days,
        'total_pipeline': total_pipeline,
        'closing_soon': closing_soon,
    }
    
    return render(request, 'pages/deals/pipeline.html', {
        'pipeline_data': pipeline_data,
    })