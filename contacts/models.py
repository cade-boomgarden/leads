from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q

class ContactList(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Contact(models.Model):
    class ContactStatus(models.TextChoices):
        NEW = 'new', 'New'
        SENT = 'sent', 'Sent'
        REPLIED = 'replied', 'Replied'
        UNSUBSCRIBED = 'unsubscribed', 'Unsubscribed'

    class SourceChannel(models.TextChoices):
        SCRAPED = 'scraped', 'Scraped'
        HUNTER = 'hunter', 'Hunter'
        APOLLO = 'apollo', 'Apollo'
        MANUAL = 'manual', 'Manual'
    
    class EmailStatus(models.TextChoices):
        VALID = 'valid', 'Valid'
        INVALID = 'invalid', 'Invalid'
        CATCH_ALL = 'catch-all', 'Catch-All'
        UNKNOWN = 'unknown', 'Unknown'
        SPAMTRAP = 'spamtrap', 'Spam Trap'
        ABUSE = 'abuse', 'Abuse'
        DO_NOT_MAIL = 'do_not_mail', 'Do Not Mail'
        UNVERIFIED = 'unverified', 'Unverified'
    
    class EmailSubStatus(models.TextChoices):
        NONE = '', 'None'
        ALTERNATE = 'alternate', 'Alternate'
        ANTISPAM_SYSTEM = 'antispam_system', 'Antispam System'
        GREYLISTED = 'greylisted', 'Greylisted'
        MAIL_SERVER_TEMPORARY_ERROR = 'mail_server_temporary_error', 'Mail Server Temporary Error'
        FORCIBLE_DISCONNECT = 'forcible_disconnect', 'Forcible Disconnect'
        MAIL_SERVER_DID_NOT_RESPOND = 'mail_server_did_not_respond', 'Mail Server Did Not Respond'
        TIMEOUT_EXCEEDED = 'timeout_exceeded', 'Timeout Exceeded'
        FAILED_SMTP_CONNECTION = 'failed_smtp_connection', 'Failed SMTP Connection'
        MAILBOX_QUOTA_EXCEEDED = 'mailbox_quota_exceeded', 'Mailbox Quota Exceeded'
        EXCEPTION_OCCURRED = 'exception_occurred', 'Exception Occurred'
        POSSIBLE_TRAP = 'possible_trap', 'Possible Trap'
        ROLE_BASED = 'role_based', 'Role Based'
        GLOBAL_SUPPRESSION = 'global_suppression', 'Global Suppression'
        MAILBOX_NOT_FOUND = 'mailbox_not_found', 'Mailbox Not Found'
        NO_DNS_ENTRIES = 'no_dns_entries', 'No DNS Entries'
        FAILED_SYNTAX_CHECK = 'failed_syntax_check', 'Failed Syntax Check'
        POSSIBLE_TYPO = 'possible_typo', 'Possible Typo'
        UNROUTABLE_IP_ADDRESS = 'unroutable_ip_address', 'Unroutable IP Address'
        LEADING_PERIOD_REMOVED = 'leading_period_removed', 'Leading Period Removed'
        DOES_NOT_ACCEPT_MAIL = 'does_not_accept_mail', 'Does Not Accept Mail'
        ALIAS_ADDRESS = 'alias_address', 'Alias Address'
        ROLE_BASED_CATCH_ALL = 'role_based_catch_all', 'Role Based Catch All'
        DISPOSABLE = 'disposable', 'Disposable'
        TOXIC = 'toxic', 'Toxic'

    # Common fields
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(unique=True)  # Unique identifier
    position = models.CharField(max_length=255, blank=True, null=True)  # Hunter's "position", Apollo's "title"
    
    # Social profiles
    linkedin_url = models.URLField(blank=True, null=True)
    twitter = models.CharField(max_length=255, blank=True, null=True)  # Twitter handle
    twitter_url = models.URLField(blank=True, null=True)
    
    # Contact information
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Organization
    organization_name = models.CharField(max_length=255, blank=True, null=True)
    organization_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Hunter-specific fields
    hunter_confidence = models.IntegerField(
        blank=True, 
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    hunter_type = models.CharField(max_length=50, blank=True, null=True)  # "personal", "work", etc.
    # Changed from TextField to JSONField
    hunter_sources = models.JSONField(blank=True, null=True)
    hunter_seniority = models.CharField(max_length=50, blank=True, null=True)
    hunter_department = models.CharField(max_length=100, blank=True, null=True)
    verification_status = models.CharField(max_length=50, blank=True, null=True)
    verification_date = models.DateField(blank=True, null=True)
    
    # Apollo-specific fields
    apollo_id = models.CharField(max_length=255, blank=True, null=True)
    # Changed from TextField to JSONField
    apollo_contact_roles = models.JSONField(blank=True, null=True)
    photo_url = models.URLField(blank=True, null=True)
    headline = models.TextField(blank=True, null=True)
    present_raw_address = models.TextField(blank=True, null=True)
    email_status = models.CharField(max_length=100, blank=True, null=True)
    email_true_status = models.CharField(max_length=100, blank=True, null=True)
    email_source = models.CharField(max_length=100, blank=True, null=True)
    source = models.CharField(max_length=100, blank=True, null=True)
    original_source = models.CharField(max_length=100, blank=True, null=True)
    
    # ZeroBounce verification fields
    zerobounce_status = models.CharField(
        max_length=50,
        choices=EmailStatus.choices,
        default=EmailStatus.UNVERIFIED,
        blank=True,
        null=True
    )
    zerobounce_sub_status = models.CharField(
        max_length=50,
        choices=EmailSubStatus.choices,
        default=EmailSubStatus.NONE,
        blank=True,
        null=True
    )
    zerobounce_free_email = models.BooleanField(blank=True, null=True)
    zerobounce_did_you_mean = models.CharField(max_length=255, blank=True, null=True)
    zerobounce_domain_age_days = models.IntegerField(blank=True, null=True)
    zerobounce_active_in_days = models.CharField(max_length=50, blank=True, null=True)
    zerobounce_smtp_provider = models.CharField(max_length=100, blank=True, null=True)
    zerobounce_mx_record = models.CharField(max_length=255, blank=True, null=True)
    zerobounce_mx_found = models.BooleanField(blank=True, null=True)
    zerobounce_country = models.CharField(max_length=100, blank=True, null=True)
    zerobounce_region = models.CharField(max_length=100, blank=True, null=True)
    zerobounce_city = models.CharField(max_length=100, blank=True, null=True)
    zerobounce_zipcode = models.CharField(max_length=20, blank=True, null=True)
    zerobounce_processed_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity_date = models.DateTimeField(blank=True, null=True)

    # Status
    status = models.CharField(
        max_length=50,
        choices=ContactStatus.choices,
        default=ContactStatus.NEW
    )
    source_channel = models.CharField(
        max_length=50,
        choices=SourceChannel.choices,
        default=SourceChannel.SCRAPED
    )
    
    # Relationship to Company model 
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='contacts',
        blank=True,
        null=True
    )
    # Relationship to ContactList model
    contact_lists = models.ManyToManyField(
        ContactList,
        blank=True,
        related_name='contacts'
    )
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['organization_id']),
            models.Index(fields=['apollo_id']),
            models.Index(fields=['zerobounce_status']),
        ]
    
    # Helper methods updated for JSONField
    def get_hunter_sources(self):
        """Return the hunter_sources directly from JSONField"""
        return self.hunter_sources or []
    
    def set_hunter_sources(self, sources_list):
        """Store sources list directly in JSONField"""
        self.hunter_sources = sources_list
    
    def get_contact_roles(self):
        """Return the apollo_contact_roles directly from JSONField"""
        return self.apollo_contact_roles or []
    
    @property
    def email_domain(self):
        """Extract domain from email address"""
        if not self.email:
            return None
        return self.email.split('@')[-1]
    
    @property
    def is_email_valid(self):
        """Check if the email is valid based on ZeroBounce results"""
        return self.zerobounce_status == self.EmailStatus.VALID
    
    def verify_with_zerobounce(self, api_key, ip_address=None):
        """
        Method to verify the email with ZeroBounce
        
        This is a placeholder for the actual implementation,
        which would make an API call to ZeroBounce and update the fields
        """
        try:
            from zerobouncesdk import ZeroBounce, ZBException
            
            zero_bounce = ZeroBounce(api_key)
            
            try:
                response = zero_bounce.validate(self.email, ip_address)
                # Parse response and update fields
                self._update_from_zerobounce_response(response)
                return True
            except ZBException as e:
                print(f"ZeroBounce validate error: {str(e)}")
                return False
        except ImportError:
            print("ZeroBounce SDK not installed. Run: pip install zerobouncesdk")
            return False
    
    def _update_from_zerobounce_response(self, response):
        """Update Contact fields from ZeroBounce response"""
        import json
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.JSONDecodeError:
                print("Invalid JSON response from ZeroBounce")
                return
        
        # Map ZeroBounce response to model fields
        self.zerobounce_status = response.get('status', self.EmailStatus.UNKNOWN)
        self.zerobounce_sub_status = response.get('sub_status', '')
        self.zerobounce_free_email = response.get('free_email', None)
        self.zerobounce_did_you_mean = response.get('did_you_mean', None)
        self.zerobounce_domain_age_days = (
            int(response.get('domain_age_days')) 
            if response.get('domain_age_days') and response.get('domain_age_days').isdigit() 
            else None
        )
        self.zerobounce_active_in_days = response.get('active_in_days', None)
        self.zerobounce_smtp_provider = response.get('smtp_provider', None)
        self.zerobounce_mx_record = response.get('mx_record', None)
        self.zerobounce_mx_found = (
            response.get('mx_found') == 'true' 
            if response.get('mx_found') 
            else None
        )
        
        # Update name if not already present
        if not self.first_name and response.get('firstname'):
            self.first_name = response.get('firstname')
        if not self.last_name and response.get('lastname'):
            self.last_name = response.get('lastname')
        
        # Location data
        self.zerobounce_country = response.get('country', None)
        self.zerobounce_region = response.get('region', None)
        self.zerobounce_city = response.get('city', None)
        self.zerobounce_zipcode = response.get('zipcode', None)
        
        # Convert processed_at to a datetime if present
        if response.get('processed_at'):
            from datetime import datetime
            try:
                self.zerobounce_processed_at = datetime.strptime(
                    response.get('processed_at'), 
                    '%Y-%m-%d %H:%M:%S.%f'
                )
            except ValueError:
                try:
                    # Try alternative format
                    self.zerobounce_processed_at = datetime.strptime(
                        response.get('processed_at'), 
                        '%Y-%m-%d %H:%M:%S'
                    )
                except ValueError:
                    self.zerobounce_processed_at = None
        
        self.save()

class Cohort(models.Model):
    """
    A cohort is a specialized contact list containing one contact from each company 
    in a company list, selected based on specific criteria.
    """
    class ContactSelectionMethod(models.TextChoices):
        EMAIL_PREFIX = 'email_prefix', 'Email Prefix Hierarchy'
        DEPARTMENT = 'department', 'By Department'
        SENIORITY = 'seniority', 'By Seniority Level'
        JOB_TITLE = 'job_title', 'By Job Title'
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    company_list = models.ForeignKey(
        'companies.CompanyList', 
        on_delete=models.CASCADE,
        related_name='cohorts'
    )
    selection_method = models.CharField(
        max_length=20,
        choices=ContactSelectionMethod.choices,
        default=ContactSelectionMethod.EMAIL_PREFIX
    )
    
    # Fields for email prefix hierarchy
    email_prefix_hierarchy = models.JSONField(
        default=list,
        blank=True,
        help_text="List of email prefixes to try, in order of preference (e.g., ['sales', 'info', 'contact'])"
    )
    
    # Fields for department selection
    target_department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Target department name to select contacts from"
    )
    
    # Fields for seniority selection
    minimum_seniority = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Minimum seniority level (0-10, where 10 is highest)"
    )
    
    # Fields for job title selection
    job_title_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="List of job title keywords to match, in order of preference"
    )
    
    # Fields for verification status filtering
    include_verification_statuses = models.JSONField(
        default=list,
        blank=True,
        help_text="List of verification statuses to include (empty means include all)"
    )
    
    include_verification_substatuses = models.JSONField(
        default=list,
        blank=True,
        help_text="List of verification sub-statuses to include (empty means include all)"
    )
    
    exclude_unverified = models.BooleanField(
        default=False,
        help_text="Whether to exclude contacts that have never been verified"
    )
    
    # Generated contacts list
    contacts = models.ManyToManyField(
        'contacts.Contact',
        blank=True,
        related_name='cohorts'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_generated = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    def generate_contacts(self):
        """
        Generate the cohort by selecting one contact from each company in the company list
        based on the selected method.
        
        Returns:
            int: Number of contacts added to the cohort
        """
        # Get all companies from the company list
        companies = self.company_list.companies.all()
        
        # Clear existing contacts
        self.contacts.clear()
        
        # Counter for added contacts
        added_count = 0
        
        # Process each company
        for company in companies:
            # Get all contacts for this company
            company_contacts = company.contacts.all()
            
            if not company_contacts:
                continue  # Skip companies with no contacts
            
            # Apply verification filters if specified
            if self.include_verification_statuses:
                company_contacts = company_contacts.filter(
                    zerobounce_status__in=self.include_verification_statuses
                )
            
            if self.include_verification_substatuses:
                company_contacts = company_contacts.filter(
                    zerobounce_sub_status__in=self.include_verification_substatuses
                )
            
            if self.exclude_unverified:
                company_contacts = company_contacts.exclude(
                    Q(zerobounce_status__isnull=True) | 
                    Q(zerobounce_status='') | 
                    Q(zerobounce_status=Contact.EmailStatus.UNVERIFIED)
                )
            
            if not company_contacts:
                continue  # Skip if no contacts match the verification criteria
            
            # Select contact based on the method
            selected_contact = None
            
            if self.selection_method == self.ContactSelectionMethod.EMAIL_PREFIX:
                selected_contact = self._select_by_email_prefix(company_contacts)
            elif self.selection_method == self.ContactSelectionMethod.DEPARTMENT:
                selected_contact = self._select_by_department(company_contacts)
            elif self.selection_method == self.ContactSelectionMethod.SENIORITY:
                selected_contact = self._select_by_seniority(company_contacts)
            elif self.selection_method == self.ContactSelectionMethod.JOB_TITLE:
                selected_contact = self._select_by_job_title(company_contacts)
            
            # Add the selected contact to the cohort
            if selected_contact:
                self.contacts.add(selected_contact)
                added_count += 1
        
        # Update last generated timestamp
        from django.utils import timezone
        self.last_generated = timezone.now()
        self.save()
        
        return added_count
    
    def _select_by_email_prefix(self, contacts):
        """
        Select a contact based on email prefix hierarchy.
        """
        # Use default hierarchy if none specified
        hierarchy = self.email_prefix_hierarchy
        if not hierarchy:
            hierarchy = ['sales', 'info', 'contact', 'hello', 'support', 'general', 'admin']
        
        # Try each prefix in order
        for prefix in hierarchy:
            for contact in contacts:
                username = contact.email.split('@')[0].lower()
                if username.startswith(prefix):
                    return contact
        
        # If no match, return the first contact
        return contacts.first()
    
    def _select_by_department(self, contacts):
        """
        Select a contact based on department.
        """
        if not self.target_department:
            return contacts.first()
        
        # Try to find a contact in the target department
        department_contacts = contacts.filter(
            Q(hunter_department__icontains=self.target_department) |
            Q(position__icontains=self.target_department)
        )
        
        if department_contacts.exists():
            return department_contacts.first()
        
        # If no match, return the first contact
        return contacts.first()
    
    def _select_by_seniority(self, contacts):
        """
        Select a contact based on seniority.
        """
        # Define seniority keywords with scores
        seniority_scores = {
            'ceo': 10, 'chief': 9, 'president': 9, 'founder': 9, 'owner': 9,
            'director': 8, 'vp': 8, 'vice president': 8, 'head': 7,
            'senior': 6, 'manager': 5, 'lead': 5,
            'associate': 3, 'assistant': 2, 'junior': 1
        }
        
        # Score each contact
        scored_contacts = []
        for contact in contacts:
            score = 0
            
            # Check hunter_seniority field
            if contact.hunter_seniority:
                if contact.hunter_seniority.lower() in seniority_scores:
                    score = seniority_scores[contact.hunter_seniority.lower()]
            
            # Check position/title
            if contact.position:
                position_lower = contact.position.lower()
                for keyword, keyword_score in seniority_scores.items():
                    if keyword in position_lower:
                        score = max(score, keyword_score)
            
            scored_contacts.append((contact, score))
        
        # Filter by minimum seniority
        qualifying_contacts = [(contact, score) for contact, score in scored_contacts 
                              if score >= self.minimum_seniority]
        
        if qualifying_contacts:
            # Sort by score (highest first)
            qualifying_contacts.sort(key=lambda x: x[1], reverse=True)
            return qualifying_contacts[0][0]
        
        # If no qualifying contacts, return the first contact
        return contacts.first()
    
    def _select_by_job_title(self, contacts):
        """
        Select a contact based on job title keywords.
        """
        # Use default keywords if none specified
        keywords = self.job_title_keywords
        if not keywords:
            keywords = ['sales', 'marketing', 'business development', 'account manager']
        
        # Try each keyword in order
        for keyword in keywords:
            matching_contacts = contacts.filter(position__icontains=keyword)
            if matching_contacts.exists():
                return matching_contacts.first()
        
        # If no match, return the first contact
        return contacts.first()