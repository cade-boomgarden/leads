from django import forms
from finder.models import CompanySearch, SerpAPISearchParameters, ContactSearch, WebScrapeParameters
from companies.models import CompanyList
from contacts.models import ContactList, Contact

class SerpAPISearchForm(forms.Form):
    query = forms.CharField(
        label="Search Term",
        max_length=255,
        help_text="The type of business you want to search for (e.g., 'coffee shops', 'restaurants')"
    )
    
    place_name = forms.CharField(
        label="Location",
        max_length=255,
        required=False,
        help_text="City, state, or specific location name (e.g., 'New York, NY')"
    )
    
    zoom = forms.IntegerField(
        label="Zoom Level",
        min_value=3,
        max_value=21,
        initial=13,
        help_text="Zoom level (3-21, higher values = more zoomed in)"
    )
    
    max_results = forms.IntegerField(
        label="Maximum Results",
        min_value=1,
        max_value=100,
        initial=100,
        help_text="Maximum number of results to return (1-100)"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get('source_type')
        target_url = cleaned_data.get('target_url')
        company_list = cleaned_data.get('company_list')
        
        # Validate source type selection
        if source_type == 'url' and not target_url:
            self.add_error('target_url', "Website URL is required when 'Single Website URL' is selected.")
        
        if source_type == 'company_list' and not company_list:
            self.add_error('company_list', "Company List is required when 'Company List' is selected.")
        
        # Convert multi-line text fields to lists
        if 'priority_paths' in cleaned_data and cleaned_data['priority_paths']:
            cleaned_data['priority_paths'] = [
                path.strip() for path in cleaned_data['priority_paths'].split('\n') if path.strip()
            ]
        else:
            cleaned_data['priority_paths'] = []
        
        if 'exclude_paths' in cleaned_data and cleaned_data['exclude_paths']:
            cleaned_data['exclude_paths'] = [
                path.strip() for path in cleaned_data['exclude_paths'].split('\n') if path.strip()
            ]
        else:
            cleaned_data['exclude_paths'] = []
        
        if 'target_keywords' in cleaned_data and cleaned_data['target_keywords']:
            cleaned_data['target_keywords'] = [
                keyword.strip() for keyword in cleaned_data['target_keywords'].split('\n') if keyword.strip()
            ]
        else:
            cleaned_data['target_keywords'] = []
            
        return cleaned_data

    
    def add_warning(self, message):
        """Add a non-blocking warning message"""
        if not hasattr(self, '_warnings'):
            self._warnings = []
        self._warnings.append(message)
    
    @property
    def warnings(self):
        """Get any warning messages"""
        return getattr(self, '_warnings', [])

class WebScrapeForm(forms.Form):
    """Form for scraping websites for contact information"""
    
    # Source selection
    source_type = forms.ChoiceField(
        label="Source Type",
        choices=[
            ('url', 'Single Website URL'),
            ('company_list', 'Company List'),
            ('all', 'All Companies'),
        ],
        widget=forms.RadioSelect,
        initial='url',
        help_text="Select where to scrape contacts from"
    )
    
    target_url = forms.URLField(
        label="Website URL",
        required=False,
        widget=forms.URLInput(attrs={ 'placeholder': 'https://www.example.com'}),
        help_text="The company website URL to start scraping"
    )
    
    company_list = forms.ModelChoiceField(
        label="Company List",
        queryset=CompanyList.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'select is-fullwidth form-control'}),
        help_text="Select a list of companies to scrape"
    )
    
    # Scraping depth
    max_depth = forms.IntegerField(
        label="Link Depth",
        min_value=1,
        max_value=5,
        initial=2,
        widget=forms.NumberInput(attrs={'class': 'input form-control'}),
        help_text="Maximum number of links to follow from the initial page (1-5)"
    )
    
    max_pages = forms.IntegerField(
        label="Maximum Pages",
        min_value=1,
        max_value=500,
        initial=100,
        widget=forms.NumberInput(attrs={'class': 'input form-control'}),
        help_text="Maximum number of pages to scrape per website"
    )
    
    # Domain control
    stay_within_domain = forms.BooleanField(
        label="Stay Within Domain",
        required=False,
        initial=True,
        help_text="Only follow links that belong to the same domain"
    )
    
    follow_subdomains = forms.BooleanField(
        label="Follow Subdomains",
        required=False,
        initial=True,
        help_text="Follow links to subdomains of the target domain"
    )
    
    # Target specific pages
    priority_paths = forms.CharField(
        label="Priority Paths",
        required=False,
        widget=forms.Textarea(attrs={'class': 'textarea form-control', 'rows': 3, 'placeholder': '/about\n/team\n/contact'}),
        help_text="Enter URL paths to prioritize, one per line (e.g., '/about', '/team')"
    )
    
    exclude_paths = forms.CharField(
        label="Exclude Paths",
        required=False,
        widget=forms.Textarea(attrs={'class': 'textarea form-control', 'rows': 3, 'placeholder': '/blog\n/products\n/privacy'}),
        help_text="Enter URL paths to exclude, one per line (e.g., '/blog', '/products')"
    )
    
    # Content targeting
    target_keywords = forms.CharField(
        label="Target Keywords",
        required=False,
        widget=forms.Textarea(attrs={'class': 'textarea form-control', 'rows': 3, 'placeholder': 'contact\nteam\npeople\nstaff'}),
        help_text="Enter keywords that suggest a page may contain contact information, one per line"
    )
    
    # Extraction options
    extract_names = forms.BooleanField(
        label="Extract Names",
        required=False,
        initial=True,
        help_text="Attempt to extract names associated with email addresses"
    )
    
    extract_job_titles = forms.BooleanField(
        label="Extract Job Titles",
        required=False,
        initial=True,
        help_text="Attempt to extract job titles associated with email addresses"
    )
    
    extract_phone_numbers = forms.BooleanField(
        label="Extract Phone Numbers",
        required=False,
        initial=True,
        help_text="Extract phone numbers from the website"
    )
    
    # Rate limiting
    request_delay = forms.FloatField(
        label="Request Delay",
        min_value=0.5,
        max_value=10.0,
        initial=1.0,
        widget=forms.NumberInput(attrs={ 'step': '0.1'}),
        help_text="Delay between requests in seconds (to avoid overloading the server)"
    )
    
    concurrent_requests = forms.IntegerField(
        label="Concurrent Requests",
        min_value=1,
        max_value=20,
        initial=5,
        widget=forms.NumberInput(attrs={'class': 'input form-control'}),
        help_text="Number of concurrent requests"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get('source_type')
        target_url = cleaned_data.get('target_url')
        company_list = cleaned_data.get('company_list')
        
        # Validate source type selection
        if source_type == 'url' and not target_url:
            self.add_error('target_url', "Website URL is required when 'Single Website URL' is selected.")
        
        if source_type == 'company_list' and not company_list:
            self.add_error('company_list', "Company List is required when 'Company List' is selected.")
        
        # Convert multi-line text fields to lists
        if 'priority_paths' in cleaned_data and cleaned_data['priority_paths']:
            cleaned_data['priority_paths'] = [
                path.strip() for path in cleaned_data['priority_paths'].split('\n') if path.strip()
            ]
        else:
            cleaned_data['priority_paths'] = []
        
        if 'exclude_paths' in cleaned_data and cleaned_data['exclude_paths']:
            cleaned_data['exclude_paths'] = [
                path.strip() for path in cleaned_data['exclude_paths'].split('\n') if path.strip()
            ]
        else:
            cleaned_data['exclude_paths'] = []
        
        if 'target_keywords' in cleaned_data and cleaned_data['target_keywords']:
            cleaned_data['target_keywords'] = [
                keyword.strip() for keyword in cleaned_data['target_keywords'].split('\n') if keyword.strip()
            ]
        else:
            cleaned_data['target_keywords'] = []
        
        # Validate request parameters
        if cleaned_data.get('max_depth', 0) > 3 and cleaned_data.get('max_pages', 0) > 200:
            self.add_warning(
                "High depth and high page count may result in very long processing times. Consider reducing one or both values."
            )
        
        # Check if concurrent requests is too high relative to request delay
        if cleaned_data.get('concurrent_requests', 0) > 10 and cleaned_data.get('request_delay', 0) < 1.0:
            self.add_warning(
                "High concurrent requests with low delay may overload websites. Consider increasing delay or reducing concurrency."
            )
            
        return cleaned_data

    def add_warning(self, message):
        """Add a non-blocking warning message"""
        if not hasattr(self, '_warnings'):
            self._warnings = []
        self._warnings.append(message)

    @property
    def warnings(self):
        """Get any warning messages"""
        return getattr(self, '_warnings', [])
    
class HunterDomainSearchForm(forms.Form):
    """Form for searching domains using Hunter.io API"""
    
    # Source selection
    source_type = forms.ChoiceField(
        label="Source Type",
        choices=[
            ('domain', 'Single Domain'),
            ('company', 'Company Name'),
            ('company_list', 'Company List'),
        ],
        widget=forms.RadioSelect,
        initial='domain',
        help_text="Select what to search for contacts"
    )
    
    domain = forms.CharField(
        label="Domain",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'example.com'}),
        help_text="Domain name to search (e.g., 'stripe.com')"
    )
    
    company = forms.CharField(
        label="Company Name",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Example Inc'}),
        help_text="Company name to search (e.g., 'Stripe')"
    )
    
    company_list = forms.ModelChoiceField(
        label="Company List",
        queryset=CompanyList.objects.all(),
        required=False,
        help_text="Select a list of companies to search"
    )
    
    # Email type filter
    type = forms.ChoiceField(
        label="Email Type",
        choices=[
            ('all', 'All Email Types'),
            ('personal', 'Personal Emails Only'),
            ('generic', 'Generic Emails Only'),
        ],
        initial='all',
        help_text="Type of email addresses to return"
    )
    
    # Filtering options
    seniority = forms.MultipleChoiceField(
        label="Seniority Levels",
        choices=[
            ('junior', 'Junior'),
            ('senior', 'Senior'),
            ('executive', 'Executive'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Filter by seniority level"
    )
    
    department = forms.MultipleChoiceField(
        label="Departments",
        choices=[
            ('executive', 'Executive'),
            ('it', 'IT'),
            ('finance', 'Finance'),
            ('management', 'Management'),
            ('sales', 'Sales'),
            ('legal', 'Legal'),
            ('support', 'Support'),
            ('hr', 'Human Resources'),
            ('marketing', 'Marketing'),
            ('communication', 'Communication'),
            ('education', 'Education'),
            ('design', 'Design'),
            ('health', 'Health'),
            ('operations', 'Operations'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Filter by department"
    )
    
    required_fields = forms.MultipleChoiceField(
        label="Required Fields",
        choices=[
            ('full_name', 'Full Name'),
            ('position', 'Position'),
            ('phone_number', 'Phone Number'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Only return contacts with these fields available"
    )
    
    # Pagination options
    limit = forms.IntegerField(
        label="Results Limit",
        min_value=1,
        max_value=100,
        initial=10,
        help_text="Maximum number of results to return per domain (1-100)"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get('source_type')
        domain = cleaned_data.get('domain')
        company = cleaned_data.get('company')
        company_list = cleaned_data.get('company_list')
        
        # Validate source type selection
        if source_type == 'domain' and not domain:
            self.add_error('domain', "Domain is required when 'Single Domain' is selected.")
        
        if source_type == 'company' and not company:
            self.add_error('company', "Company name is required when 'Company Name' is selected.")
        
        if source_type == 'company_list' and not company_list:
            self.add_error('company_list', "Company List is required when 'Company List' is selected.")
            
        return cleaned_data
    
    def add_warning(self, message):
        """Add a non-blocking warning message"""
        if not hasattr(self, '_warnings'):
            self._warnings = []
        self._warnings.append(message)
    
    @property
    def warnings(self):
        """Get any warning messages"""
        return getattr(self, '_warnings', [])
    
class ZeroBounceValidationForm(forms.Form):
    """Form for validating emails using ZeroBounce API"""
    
    # Validation source
    validation_type = forms.ChoiceField(
        label="Validation Source",
        choices=[
            ('contact_list', 'Contact List'),
            ('contact', 'Single Contact'),
            ('all_unverified', 'All Unverified Contacts'),
        ],
        widget=forms.RadioSelect,
        initial='contact_list',
        help_text="Select what contacts to validate"
    )
    
    contact_list = forms.ModelChoiceField(
        label="Contact List",
        queryset=ContactList.objects.all(),
        required=False,
        help_text="Select a contact list to validate emails for"
    )
    
    contact = forms.ModelChoiceField(
        label="Contact",
        queryset=Contact.objects.all(),
        required=False,
        help_text="Select a single contact to validate"
    )
    
    # Validation options
    max_validations = forms.IntegerField(
        label="Maximum Validations",
        min_value=1,
        max_value=1000,
        initial=100,
        required=False,
        help_text="Maximum number of emails to validate (leave blank to validate all available)"
    )
    
    use_ip = forms.BooleanField(
        label="Include IP Address",
        required=False,
        initial=True,
        help_text="Include IP address data with validation (when available)"
    )
    
    timeout = forms.IntegerField(
        label="Timeout",
        min_value=3,
        max_value=60,
        initial=10,
        help_text="Timeout in seconds for API requests (3-60)"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        validation_type = cleaned_data.get('validation_type')
        contact_list = cleaned_data.get('contact_list')
        contact = cleaned_data.get('contact')
        
        # Validate based on selected type
        if validation_type == 'contact_list' and not contact_list:
            self.add_error('contact_list', "Contact List is required when 'Contact List' is selected.")
        
        if validation_type == 'contact' and not contact:
            self.add_error('contact', "Contact is required when 'Single Contact' is selected.")
            
        return cleaned_data