from django import forms
from django.db.models import Count
from .models import Contact, ContactList, Cohort
from companies.models import Company

class ContactListForm(forms.ModelForm):
    class Meta:
        model = ContactList
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
            'first_name', 'last_name', 'email', 'position', 'phone_number',
            'company', 'organization_name', 'linkedin_url', 'twitter',
            'status', 'source_channel'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'organization_name': forms.TextInput(attrs={'class': 'form-control'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-control'}),
            'twitter': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'source_channel': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make company field optional
        self.fields['company'].required = False
        self.fields['company'].empty_label = "Select a company (optional)"
        
        # Set up the initial status and source if this is a new contact
        if not self.instance.pk:
            self.fields['status'].initial = Contact.ContactStatus.NEW
            self.fields['source_channel'].initial = Contact.SourceChannel.MANUAL

class ContactFilterForm(forms.Form):
    name = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by name'})
    )
    
    email = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by email'})
    )
    
    company = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by company'})
    )
    
    position = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by position'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Contact.ContactStatus.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class ContactListAddForm(forms.Form):
    contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

class CohortForm(forms.ModelForm):
    class Meta:
        model = Cohort
        fields = [
            'name', 'description', 'company_list', 'selection_method',
            'email_prefix_hierarchy', 'target_department', 'minimum_seniority', 
            'job_title_keywords'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'company_list': forms.Select(attrs={'class': 'form-control'}),
            'selection_method': forms.RadioSelect(),
            'email_prefix_hierarchy': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Enter one prefix per line (e.g., sales\ninfo\ncontact)'
            }),
            'target_department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Marketing, Sales, IT'
            }),
            'minimum_seniority': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 10
            }),
            'job_title_keywords': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Enter one keyword per line (e.g., sales\nmarketing\nbusiness development)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make the selection_method field clear labels
        self.fields['selection_method'].empty_label = None
        
        # Set appropriate help text
        self.fields['company_list'].help_text = "Select a company list to generate contacts from"
        self.fields['selection_method'].help_text = "Method to select one contact from each company"
    
    def clean_email_prefix_hierarchy(self):
        """Convert multiline text to a list"""
        text = self.cleaned_data.get('email_prefix_hierarchy', '')
        if isinstance(text, str):
            # Split by newlines and filter out empty lines
            return [line.strip() for line in text.split('\n') if line.strip()]
        return text
    
    def clean_job_title_keywords(self):
        """Convert multiline text to a list"""
        text = self.cleaned_data.get('job_title_keywords', '')
        if isinstance(text, str):
            # Split by newlines and filter out empty lines
            return [line.strip() for line in text.split('\n') if line.strip()]
        return text