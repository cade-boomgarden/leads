from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Search(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    results_count = models.IntegerField(default=0)

class ContactSearch(Search):
    class ContactSearchMethods(models.TextChoices):
        APOLLO = 'apollo', 'Apollo'
        HUNTER = 'hunter', 'Hunter'
        SCRAPE = 'scrape', 'Scrape'

    method = models.CharField(max_length=10, choices=ContactSearchMethods.choices, default=ContactSearchMethods.HUNTER)
    contacts = models.ManyToManyField('contacts.Contact', blank=True, related_name='contact_searches')

    class Meta:
        verbose_name = "Contact Search"
        verbose_name_plural = "Contact Searches"

    def __str__(self):
        return f"{self.method} Search - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

class CompanySearch(Search):
    class CompanySearchMethods(models.TextChoices):
        SERPAPI = 'serpapi', 'SerpAPI'
        APOLLO = 'apollo', 'Apollo'
    
    method = models.CharField(max_length=10, choices=CompanySearchMethods.choices, default=CompanySearchMethods.SERPAPI)
    companies = models.ManyToManyField('companies.Company', blank=True, related_name='company_searches')

    class Meta:
        verbose_name = "Company Search"
        verbose_name_plural = "Company Searches"

    def __str__(self):
        return f"{self.method} Search - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"


class SerpAPISearchParameters(models.Model):
    # Link to the parent CompanySearch
    company_search = models.OneToOneField('CompanySearch', on_delete=models.CASCADE, related_name='serpapi_parameters')
    
    # Required search parameters
    query = models.CharField(max_length=255, help_text="The search query (q parameter)")
    
    # Geographic location parameters
    place_name = models.CharField(null=True, blank=True, help_text='Location component')
    latitude = models.FloatField(null=True, blank=True, help_text="Latitude component for the ll parameter")
    longitude = models.FloatField(null=True, blank=True, help_text="Longitude component for the ll parameter")
    zoom = models.IntegerField(default=14, help_text="Zoom level (3z to 21z)")
    
    # Localization parameters
    GOOGLE_DOMAINS = [
        ('google.com', 'Google.com (US)'),
        ('google.co.uk', 'Google UK'),
        ('google.fr', 'Google France'),
        # Add other domains as needed
    ]
    google_domain = models.CharField(max_length=20, choices=GOOGLE_DOMAINS, default='google.com', 
                                   help_text="Google domain to use")
    
    language = models.CharField(max_length=5, default='en', help_text="Language code (e.g., en, es, fr)")
    country = models.CharField(max_length=5, blank=True, help_text="Country code (e.g., us, uk, fr)")
    
    # Pagination parameters
    start = models.IntegerField(default=0, help_text="Result offset for pagination")
    per_page = models.IntegerField(default=20, help_text="Number of results per page")
    
    # Additional search options
    no_cache = models.BooleanField(default=False, help_text="Force a fresh search instead of using cached results")
    
    class Meta:
        verbose_name = "SerpAPI Search Parameters"
        verbose_name_plural = "SerpAPI Search Parameters"
    
    def __str__(self):
        if self.latitude and self.longitude:
            return f"{self.query} ({self.latitude}, {self.longitude})"
        return self.query
    
    def to_api_params(self):
        """Convert model data to format expected by SerpAPI"""
        params = {
            'engine': 'google_maps',
            'q': self.query,
            'google_domain': self.google_domain,
            'hl': self.language,
        }
        
        # Add geographic location if both latitude and longitude are provided
        if self.latitude is not None and self.longitude is not None:
            params['ll'] = f"@{self.latitude},{self.longitude},{self.zoom}z"
        
        # Add optional parameters if they exist
        if self.country:
            params['gl'] = self.country
            
        if self.start > 0:
            params['start'] = self.start
            
        params['type'] = 'search'  # Always set to search for company searches
        
        if self.no_cache:
            params['no_cache'] = 'true'
            
        return params

class ApolloCompanySearchParameters(models.Model):
    # Link to the parent CompanySearch
    company_search = models.OneToOneField('CompanySearch', on_delete=models.CASCADE, related_name='apollo_parameters')
    
    # Employee count fields - changed from JSONField default=list to JSONField
    organization_num_employees_ranges = models.JSONField(default=list, blank=True, help_text="Employee count ranges for companies (format: '1,10')")
    
    # Location fields - changed from JSONField default=list to JSONField
    organization_locations = models.JSONField(default=list, blank=True, help_text="Locations of company headquarters")
    organization_not_locations = models.JSONField(default=list, blank=True, help_text="Exclude companies based on headquarters location")
    
    # Revenue fields
    revenue_range_min = models.BigIntegerField(null=True, blank=True, help_text="Lower range of organization revenue")
    revenue_range_max = models.BigIntegerField(null=True, blank=True, help_text="Upper range of organization revenue")
    
    # Technology fields - changed from JSONField default=list to JSONField
    currently_using_any_of_technology_uids = models.JSONField(default=list, blank=True, help_text="Technologies currently used by organizations")
    
    # Keyword fields - changed from JSONField default=list to JSONField
    q_organization_keyword_tags = models.JSONField(default=list, blank=True, help_text="Keywords associated with companies")
    q_organization_name = models.CharField(max_length=255, blank=True, help_text="Specific company name to filter by")
    
    # Company identifiers - changed from JSONField default=list to JSONField
    organization_ids = models.JSONField(default=list, blank=True, help_text="Apollo IDs for specific companies to include")
    
    # Pagination (these might be better as transient properties not stored in DB)
    page = models.PositiveIntegerField(default=1, help_text="Page number to retrieve")
    per_page = models.PositiveIntegerField(default=10, help_text="Number of results per page")
    
    def __str__(self):
        return f"Apollo parameters for {self.company_search}"
    
    def to_api_params(self):
        """Convert model data to format expected by Apollo API"""
        params = {}
        
        if self.organization_num_employees_ranges:
            params['organization_num_employees_ranges[]'] = self.organization_num_employees_ranges
            
        if self.organization_locations:
            params['organization_locations[]'] = self.organization_locations
            
        if self.organization_not_locations:
            params['organization_not_locations[]'] = self.organization_not_locations
            
        if self.revenue_range_min is not None:
            params['revenue_range[min]'] = self.revenue_range_min
            
        if self.revenue_range_max is not None:
            params['revenue_range[max]'] = self.revenue_range_max
            
        if self.currently_using_any_of_technology_uids:
            params['currently_using_any_of_technology_uids[]'] = self.currently_using_any_of_technology_uids
            
        if self.q_organization_keyword_tags:
            params['q_organization_keyword_tags[]'] = self.q_organization_keyword_tags
            
        if self.q_organization_name:
            params['q_organization_name'] = self.q_organization_name
            
        if self.organization_ids:
            params['organization_ids[]'] = self.organization_ids
            
        params['page'] = self.page
        params['per_page'] = self.per_page
        
        return params

class ApolloContactSearchParameters(models.Model):
    # Link to the parent ContactSearch
    contact_search = models.OneToOneField('ContactSearch', on_delete=models.CASCADE, related_name='apollo_parameters')
    
    # Job title related fields - changed from JSONField default=list to JSONField
    person_titles = models.JSONField(default=list, blank=True, help_text="Job titles held by the people you want to find")
    include_similar_titles = models.BooleanField(default=True, help_text="Whether to include people with similar job titles")
    
    # Location fields - changed from JSONField default=list to JSONField
    person_locations = models.JSONField(default=list, blank=True, help_text="Locations where people live (cities, states, countries)")
    organization_locations = models.JSONField(default=list, blank=True, help_text="Locations of company headquarters")
    
    # Seniority fields
    SENIORITY_CHOICES = [
        ('owner', 'Owner'),
        ('founder', 'Founder'),
        ('c_suite', 'C-Suite'),
        ('partner', 'Partner'),
        ('vp', 'VP'),
        ('head', 'Head'),
        ('director', 'Director'),
        ('manager', 'Manager'),
        ('senior', 'Senior'),
        ('entry', 'Entry'),
        ('intern', 'Intern'),
    ]
    # Changed from JSONField default=list to JSONField
    person_seniorities = models.JSONField(default=list, blank=True, help_text="Job seniority levels")
    
    # Organization fields - changed from JSONField default=list to JSONField
    organization_domains = models.JSONField(default=list, blank=True, help_text="Domain names for the person's employer")
    organization_ids = models.JSONField(default=list, blank=True, help_text="Apollo IDs for the companies to include")
    organization_num_employees_ranges = models.JSONField(default=list, blank=True, help_text="Employee count ranges for companies (format: '1,10')")
    
    # Email status fields
    EMAIL_STATUS_CHOICES = [
        ('verified', 'Verified'),
        ('unverified', 'Unverified'),
        ('likely to engage', 'Likely to Engage'),
        ('unavailable', 'Unavailable'),
    ]
    # Changed from JSONField default=list to JSONField
    contact_email_status = models.JSONField(default=list, blank=True, help_text="Email statuses to search for")
    
    # Keyword search
    q_keywords = models.CharField(max_length=255, blank=True, help_text="Keywords to filter results")
    
    # Pagination (these might be better as transient properties not stored in DB)
    page = models.PositiveIntegerField(default=1, help_text="Page number to retrieve")
    per_page = models.PositiveIntegerField(default=10, help_text="Number of results per page")
    
    def __str__(self):
        return f"Apollo parameters for {self.contact_search}"
    
    def to_api_params(self):
        """Convert model data to format expected by Apollo API"""
        params = {}
        
        if self.person_titles:
            params['person_titles[]'] = self.person_titles
        
        params['include_similar_titles'] = self.include_similar_titles
        
        if self.person_locations:
            params['person_locations[]'] = self.person_locations
            
        if self.organization_locations:
            params['organization_locations[]'] = self.organization_locations
            
        if self.person_seniorities:
            params['person_seniorities[]'] = self.person_seniorities
            
        if self.organization_domains:
            params['q_organization_domains_list[]'] = self.organization_domains
            
        if self.organization_ids:
            params['organization_ids[]'] = self.organization_ids
            
        if self.organization_num_employees_ranges:
            params['organization_num_employees_ranges[]'] = self.organization_num_employees_ranges
            
        if self.contact_email_status:
            params['contact_email_status[]'] = self.contact_email_status
            
        if self.q_keywords:
            params['q_keywords'] = self.q_keywords
            
        params['page'] = self.page
        params['per_page'] = self.per_page
        
        return params

class HunterDomainSearchParameters(models.Model):
    # Email type choices
    class EmailType(models.TextChoices):
        GENERIC = 'generic', 'Generic'
        PERSONAL = 'personal', 'Personal'
        ALL = 'all', 'All'
    
    # Seniority level choices
    class SeniorityLevel(models.TextChoices):
        JUNIOR = 'junior', 'Junior'
        SENIOR = 'senior', 'Senior'
        EXECUTIVE = 'executive', 'Executive'
    
    # Department choices
    class Department(models.TextChoices):
        EXECUTIVE = 'executive', 'Executive'
        IT = 'it', 'IT'
        FINANCE = 'finance', 'Finance'
        MANAGEMENT = 'management', 'Management'
        SALES = 'sales', 'Sales'
        LEGAL = 'legal', 'Legal'
        SUPPORT = 'support', 'Support'
        HR = 'hr', 'Human Resources'
        MARKETING = 'marketing', 'Marketing'
        COMMUNICATION = 'communication', 'Communication'
        EDUCATION = 'education', 'Education'
        DESIGN = 'design', 'Design'
        HEALTH = 'health', 'Health'
        OPERATIONS = 'operations', 'Operations'
    
    # Required field choices
    class RequiredField(models.TextChoices):
        FULL_NAME = 'full_name', 'Full Name'
        POSITION = 'position', 'Position'
        PHONE_NUMBER = 'phone_number', 'Phone Number'
    
    # Link to the parent ContactSearch
    contact_search = models.OneToOneField('ContactSearch', on_delete=models.CASCADE, related_name='hunter_parameters')
    
    # Primary search parameters (at least one required)
    domain = models.CharField(max_length=255, blank=True, help_text="Domain name to search (e.g., 'stripe.com')")
    company = models.CharField(max_length=255, blank=True, help_text="Company name to search (e.g., 'Stripe')")
    
    # Filtering parameters
    type = models.CharField(max_length=10, choices=EmailType.choices, default=EmailType.ALL, 
                          help_text="Type of email addresses to return")
    
    # Multi-select fields - changed from JSONField default=list to JSONField
    seniority_levels = models.JSONField(default=list, blank=True, 
                                      help_text="Seniority levels to filter by")
    departments = models.JSONField(default=list, blank=True, 
                                 help_text="Departments to filter by")
    required_fields = models.JSONField(default=list, blank=True, 
                                     help_text="Fields that must be present")
    
    # Pagination parameters
    limit = models.IntegerField(default=10, help_text="Maximum number of email addresses to return")
    offset = models.IntegerField(default=0, help_text="Number of email addresses to skip")
    
    class Meta:
        verbose_name = "Hunter Domain Search Parameters"
        verbose_name_plural = "Hunter Domain Search Parameters"
    
    def __str__(self):
        if self.domain:
            return f"Hunter search for {self.domain}"
        elif self.company:
            return f"Hunter search for {self.company}"
        return "Hunter Domain Search"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Ensure at least domain or company is provided
        if not self.domain and not self.company:
            raise ValidationError("Either domain or company must be provided")
        
        # Validate seniority levels
        for level in self.seniority_levels:
            if level not in [choice[0] for choice in self.SeniorityLevel.choices]:
                raise ValidationError(f"Invalid seniority level: {level}")
        
        # Validate departments
        for dept in self.departments:
            if dept not in [choice[0] for choice in self.Department.choices]:
                raise ValidationError(f"Invalid department: {dept}")
        
        # Validate required fields
        for field in self.required_fields:
            if field not in [choice[0] for choice in self.RequiredField.choices]:
                raise ValidationError(f"Invalid required field: {field}")
    
    def to_api_params(self):
        """Convert model data to format expected by Hunter API"""
        params = {}
        
        # Add primary search parameters
        if self.domain:
            params['domain'] = self.domain
        elif self.company:
            params['company'] = self.company
        
        # Add filtering parameters
        if self.type != self.EmailType.ALL:
            params['type'] = self.type
        
        # Add multi-select parameters if they exist
        if self.seniority_levels:
            params['seniority'] = ','.join(self.seniority_levels)
            
        if self.departments:
            params['department'] = ','.join(self.departments)
            
        if self.required_fields:
            params['required_field'] = ','.join(self.required_fields)
        
        # Add pagination parameters
        params['limit'] = self.limit
        params['offset'] = self.offset
        
        return params

class WebScrapeParameters(models.Model):
    # Link to the parent ContactSearch
    contact_search = models.OneToOneField('ContactSearch', on_delete=models.CASCADE, related_name='webscrape_parameters')
    
    # Primary parameters
    target_url = models.URLField(
        max_length=512, 
        help_text="The company website URL to start scraping"
    )
    
    # Scraping depth configuration
    max_depth = models.IntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Maximum link depth to follow from the initial page (1-5)"
    )
    
    max_pages = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        help_text="Maximum number of pages to scrape"
    )
    
    # Domain control
    stay_within_domain = models.BooleanField(
        default=True,
        help_text="Only follow links that belong to the same domain"
    )
    
    follow_subdomains = models.BooleanField(
        default=True,
        help_text="Follow links to subdomains of the target domain"
    )
    
    # Specific page targeting - changed from JSONField default=list to JSONField
    priority_paths = models.JSONField(
        default=list,
        blank=True,
        help_text="List of URL paths to prioritize (e.g., '/about', '/team', '/contact')"
    )
    
    exclude_paths = models.JSONField(
        default=list,
        blank=True,
        help_text="List of URL paths to exclude (e.g., '/products', '/blog')"
    )
    
    # Content targeting - changed from JSONField default=list to JSONField
    target_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="Keywords that suggest a page may contain contact information"
    )
    
    # Email extraction options
    extract_names = models.BooleanField(
        default=True,
        help_text="Attempt to extract names associated with email addresses"
    )
    
    extract_job_titles = models.BooleanField(
        default=True,
        help_text="Attempt to extract job titles associated with email addresses"
    )
    
    extract_phone_numbers = models.BooleanField(
        default=True,
        help_text="Extract phone numbers from the website"
    )
    
    # Rate limiting
    request_delay = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.5), MaxValueValidator(10.0)],
        help_text="Delay between requests in seconds (to avoid overloading the server)"
    )
    
    concurrent_requests = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="Number of concurrent requests"
    )
    
    # Timeout settings
    request_timeout = models.FloatField(
        default=30.0,
        validators=[MinValueValidator(5.0), MaxValueValidator(120.0)],
        help_text="Request timeout in seconds"
    )
    
    # Advanced options
    follow_robotstxt = models.BooleanField(
        default=True,
        help_text="Respect robots.txt directives"
    )
    
    user_agent = models.CharField(
        max_length=255,
        default="Mozilla/5.0 (compatible; CompanyBot/1.0)",
        blank=True,
        help_text="User agent string to use for requests"
    )
    
    class Meta:
        verbose_name = "Web Scrape Parameters"
        verbose_name_plural = "Web Scrape Parameters"
    
    def __str__(self):
        return f"Web scrape for {self.target_url} (depth: {self.max_depth})"
    
    @property
    def configuration(self):
        """Return a dictionary of scraping configuration parameters"""
        return {
            'target_url': self.target_url,
            'max_depth': self.max_depth,
            'max_pages': self.max_pages,
            'stay_within_domain': self.stay_within_domain,
            'follow_subdomains': self.follow_subdomains,
            'priority_paths': self.priority_paths,
            'exclude_paths': self.exclude_paths,
            'target_keywords': self.target_keywords,
            'extract_names': self.extract_names,
            'extract_job_titles': self.extract_job_titles,
            'extract_phone_numbers': self.extract_phone_numbers,
            'request_delay': self.request_delay,
            'concurrent_requests': self.concurrent_requests,
            'request_timeout': self.request_timeout,
            'follow_robotstxt': self.follow_robotstxt,
            'user_agent': self.user_agent,
        }