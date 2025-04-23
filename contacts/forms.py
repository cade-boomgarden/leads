from django import forms
from django.db.models import Count
from .models import Contact, ContactList, Cohort
from companies.models import Company

class ContactListForm(forms.ModelForm):
    class Meta:
        model = ContactList
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(),
            'description': forms.Textarea(attrs={'rows': 4}),
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
            'first_name': forms.TextInput(),
            'last_name': forms.TextInput(),
            'email': forms.EmailInput(),
            'position': forms.TextInput(),
            'phone_number': forms.TextInput(),
            'company': forms.Select(),
            'organization_name': forms.TextInput(),
            'linkedin_url': forms.URLInput(),
            'twitter': forms.TextInput(),
            'status': forms.Select(),
            'source_channel': forms.Select(),
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
        widget=forms.TextInput(attrs={'placeholder': 'Filter by name'})
    )
    
    email = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'placeholder': 'Filter by email'})
    )
    
    company = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'placeholder': 'Filter by company'})
    )
    
    position = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'placeholder': 'Filter by position'})
    )
    
    zerobounce_status = forms.ChoiceField(
        choices=[('', 'All Verification')] + list(Contact.EmailStatus.choices),
        required=False,
        label="Verification Status",
        widget=forms.Select(attrs={'aria-label': 'Filter by verification status'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Contact.ContactStatus.choices),
        required=False,
        widget=forms.Select()
    )

class ContactListAddForm(forms.Form):
    contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
class CohortForm(forms.ModelForm):
    # Fields for verification status filtering
    include_verification_statuses = forms.MultipleChoiceField(
        label="Include Verification Statuses",
        choices=Contact.EmailStatus.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        help_text="Only include contacts with these verification statuses (leave empty to include all)"
    )
    
    include_verification_substatuses = forms.MultipleChoiceField(
        label="Include Verification Sub-statuses",
        choices=Contact.EmailSubStatus.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        help_text="Only include contacts with these verification sub-statuses (leave empty to include all)"
    )
    
    exclude_unverified = forms.BooleanField(
        label="Exclude Unverified Contacts",
        required=False,
        initial=False,
        help_text="Exclude contacts that have never been verified"
    )
    
    class Meta:
        model = Cohort
        fields = [
            'name', 'description', 'company_list', 'selection_method',
            'email_prefix_hierarchy', 'target_department', 'minimum_seniority', 
            'job_title_keywords', 'include_verification_statuses',
            'include_verification_substatuses', 'exclude_unverified'
        ]
        widgets = {
            'name': forms.TextInput(),
            'description': forms.Textarea(attrs={'rows': 4}),
            'company_list': forms.Select(),
            'selection_method': forms.RadioSelect(),
            'email_prefix_hierarchy': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'Enter one prefix per line (e.g., sales\ninfo\ncontact)'
            }),
            'target_department': forms.TextInput(attrs={
                'placeholder': 'e.g., Marketing, Sales, IT'
            }),
            'minimum_seniority': forms.NumberInput(attrs={
                'min': 0,
                'max': 10
            }),
            'job_title_keywords': forms.Textarea(attrs={
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
        
        # Ordering of substatuses for readability - group similar substatuses together
        substatus_order = [
            # Empty value first
            '',
            # Role-based statuses
            'role_based', 'role_based_catch_all',
            # Mail server issues
            'mail_server_temporary_error', 'mail_server_did_not_respond', 'does_not_accept_mail',
            # Connection issues
            'failed_smtp_connection', 'timeout_exceeded', 'forcible_disconnect',
            # Mailbox issues
            'mailbox_quota_exceeded', 'mailbox_not_found',
            # DNS/Routing issues
            'no_dns_entries', 'unroutable_ip_address',
            # Spam/Filter related
            'antispam_system', 'greylisted', 'global_suppression',
            # Possible traps/security concerns
            'possible_trap', 'toxic', 'disposable',
            # Syntax/Format issues
            'failed_syntax_check', 'possible_typo', 'leading_period_removed',
            # Others
            'alternate', 'alias_address', 'exception_occurred'
        ]
        
        # Reorder choices based on the desired order
        ordered_choices = []
        for status_value in substatus_order:
            for choice in Contact.EmailSubStatus.choices:
                if choice[0] == status_value:
                    ordered_choices.append(choice)
                    break
                    
        # Add any remaining choices not in our ordering
        for choice in Contact.EmailSubStatus.choices:
            if choice not in ordered_choices:
                ordered_choices.append(choice)
                
        self.fields['include_verification_substatuses'].choices = ordered_choices
        
        # If instance already has verification statuses and substatuses, populate them
        if self.instance.pk:
            if hasattr(self.instance, 'include_verification_statuses'):
                self.fields['include_verification_statuses'].initial = self.instance.include_verification_statuses
                
            if hasattr(self.instance, 'include_verification_substatuses'):
                self.fields['include_verification_substatuses'].initial = self.instance.include_verification_substatuses
                
            if hasattr(self.instance, 'exclude_unverified'):
                self.fields['exclude_unverified'].initial = self.instance.exclude_unverified
    
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