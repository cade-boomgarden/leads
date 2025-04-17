from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

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
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
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