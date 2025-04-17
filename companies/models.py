from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class CompanyList(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Company(models.Model):
    # Common fields
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True)  # Unique identifier
    website_url = models.URLField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    state_code = models.CharField(max_length=2, blank=True, null=True)  # For two-letter state codes
    
    # SerpAPI fields
    serp_position = models.IntegerField(blank=True, null=True)
    place_id = models.CharField(max_length=255, blank=True, null=True)
    data_id = models.CharField(max_length=255, blank=True, null=True)
    data_cid = models.CharField(max_length=255, blank=True, null=True)
    provider_id = models.CharField(max_length=255, blank=True, null=True)
    rating = models.FloatField(
        blank=True, 
        null=True, 
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    reviews_count = models.IntegerField(blank=True, null=True)
    primary_type = models.CharField(max_length=255, blank=True, null=True)
    types = models.JSONField(blank=True, null=True)
    type_ids = models.JSONField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # GPS coordinates
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    
    # Service options
    dine_in_available = models.BooleanField(default=False)
    takeout_available = models.BooleanField(default=False)
    no_contact_delivery_available = models.BooleanField(default=False)
    
    # Thumbnail/Logo
    thumbnail_url = models.URLField(blank=True, null=True)
    logo_url = models.URLField(blank=True, null=True)
    
    # Apollo fields
    apollo_id = models.CharField(max_length=255, blank=True, null=True)
    blog_url = models.URLField(blank=True, null=True)
    angellist_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    # Changed from TextField to JSONField
    languages = models.JSONField(blank=True, null=True)
    alexa_ranking = models.IntegerField(blank=True, null=True)
    linkedin_uid = models.CharField(max_length=50, blank=True, null=True)
    founded_year = models.IntegerField(blank=True, null=True)
    publicly_traded_symbol = models.CharField(max_length=20, blank=True, null=True)
    publicly_traded_exchange = models.CharField(max_length=50, blank=True, null=True)
    crunchbase_url = models.URLField(blank=True, null=True)
    primary_domain = models.CharField(max_length=255, blank=True, null=True)
    intent_strength = models.FloatField(blank=True, null=True)
    show_intent = models.BooleanField(default=True)
    has_intent_signal_account = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Lists
    company_lists = models.ManyToManyField(
        CompanyList,
        blank=True,
        related_name='companies'
    )
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['place_id']),
            models.Index(fields=['apollo_id']),
            models.Index(fields=['domain']),
        ]
    
    def save(self, *args, **kwargs):
        # If we have an address but no city/state, try to parse them
        if self.address and (not self.city or not self.state):
            self.parse_address()
        
        super().save(*args, **kwargs)
    
    def parse_address(self):
        """Extract city and state from address using the usaddress library"""
        if not self.address:
            return
            
        try:
            import usaddress
            
            # Parse the address
            tagged_address, address_type = usaddress.tag(self.address)
            
            # Extract city (PlaceName)
            if 'PlaceName' in tagged_address:
                self.city = tagged_address['PlaceName']
            
            # Extract state
            if 'StateName' in tagged_address:
                state_value = tagged_address['StateName']
                
                # If it's a state code (2 letters)
                if len(state_value) == 2:
                    self.state_code = state_value.upper()
                    self.state = self._get_state_from_code(self.state_code)
                # If it's a full state name
                else:
                    self.state = state_value
                    self.state_code = self._get_code_from_state(state_value)
            
            # Sometimes usaddress might not correctly identify the state
            # Try to extract from the address string as a fallback
            if not self.state and not self.state_code:
                # Look for state code pattern (2 uppercase letters followed by space and 5-digit zip)
                import re
                state_pattern = r'\b([A-Z]{2})\s+\d{5}(?:-\d{4})?\b'
                match = re.search(state_pattern, self.address.upper())
                if match:
                    self.state_code = match.group(1)
                    self.state = self._get_state_from_code(self.state_code)
            
            # Clean up values (remove any trailing commas, extra spaces)
            if self.city:
                self.city = self.city.strip().rstrip(',')
            if self.state:
                self.state = self.state.strip().rstrip(',')
            if self.state_code:
                self.state_code = self.state_code.strip().upper()
            
        except ImportError:
            # If usaddress isn't installed, log a warning
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("usaddress package not installed. Unable to parse address.")
            
        except Exception as e:
            # If parsing fails for any other reason, log the error
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error parsing address '{self.address}': {str(e)}")

    def _get_state_from_code(self, code):
        """Convert state code to full state name"""
        state_dict = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 
            'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 
            'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 
            'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 
            'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 
            'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 
            'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 
            'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 
            'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 
            'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 
            'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
        }
        return state_dict.get(code.upper(), '')
    
    def _get_code_from_state(self, state):
        """Convert full state name to state code"""
        state_dict = {
            'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 
            'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 
            'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID', 
            'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS', 
            'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD', 
            'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 
            'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 
            'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY', 
            'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK', 
            'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC', 
            'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 
            'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 
            'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC'
        }
        return state_dict.get(state.lower(), '')
    # Helper methods updated to work with JSONField
    def get_types(self):
        """Return the types directly from JSONField"""
        return self.types or []
    
    def set_types(self, types_list):
        """Store a list directly in JSONField"""
        self.types = types_list
    
    def get_type_ids(self):
        """Return the type_ids directly from JSONField"""
        return self.type_ids or []
    
    def get_languages(self):
        """Return the languages directly from JSONField"""
        return self.languages or []
    
    @classmethod
    def extract_domain(cls, url):
        """Extract domain from a URL"""
        import re
        if not url:
            return None
        
        # Remove protocol (http://, https://)
        domain = re.sub(r'^https?://', '', url)
        
        # Remove www.
        domain = re.sub(r'^www\.', '', domain)
        
        # Remove path (everything after first /)
        domain = domain.split('/')[0]
        
        return domain