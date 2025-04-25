import requests
import logging
from django.conf import settings
from contacts.models import Contact

logger = logging.getLogger(__name__)

class HunterService:
    """
    Service for interacting with the Hunter.io API to find contact information
    for companies.
    """
    
    BASE_URL = "https://api.hunter.io/v2"
    
    def __init__(self, api_key=None):
        """Initialize with API key from settings if not provided"""
        self.api_key = api_key or getattr(settings, 'HUNTER_API_KEY', None)
        if not self.api_key:
            raise ValueError("Hunter API key is required")
        
    def get_account_info(self):
        """
        Get account information from Hunter API.
        
        Returns:
            dict: Account information
        """
        try:
            response = requests.get(f"{self.BASE_URL}/account", params={'api_key': self.api_key})
            response.raise_for_status()  # Raise exception for HTTP errors
            return response.json()['data']['requests']
        except requests.RequestException as e:
            logger.error(f"Hunter API request error: {str(e)}")
            raise
    
    def domain_search(self, domain=None, company=None, limit=10, offset=0, 
                      email_type=None, seniority=None, department=None, 
                      required_fields=None):
        """
        Search for email addresses at a specific domain or company.
        
        Args:
            domain (str): Domain name to search (e.g., 'stripe.com')
            company (str): Company name to search (e.g., 'Stripe')
            limit (int): Maximum number of results to return (default: 10)
            offset (int): Number of results to skip (default: 0)
            email_type (str): Filter by email type ('personal' or 'generic')
            seniority (list): Filter by seniority level(s) ('junior', 'senior', 'executive')
            department (list): Filter by department(s) ('executive', 'it', 'finance', etc.)
            required_fields (list): Fields that must be present ('full_name', 'position', 'phone_number')
            
        Returns:
            dict: API response data
        """
        if not domain and not company:
            raise ValueError("Either domain or company must be provided")
        
        # Build request parameters
        params = {
            'api_key': self.api_key,
            'limit': limit,
            'offset': offset
        }
        
        # Add domain or company parameters
        if domain:
            params['domain'] = domain
        elif company:
            params['company'] = company
            
        # Add filters if provided
        if email_type:
            params['type'] = email_type
            
        # Handle list parameters that need to be comma-separated
        if seniority:
            if isinstance(seniority, list):
                params['seniority'] = ','.join(seniority)
            else:
                params['seniority'] = seniority
                
        if department:
            if isinstance(department, list):
                params['department'] = ','.join(department)
            else:
                params['department'] = department
                
        if required_fields:
            if isinstance(required_fields, list):
                params['required_field'] = ','.join(required_fields)
            else:
                params['required_field'] = required_fields
        
        # Make the API request
        try:
            response = requests.get(f"{self.BASE_URL}/domain-search", params=params)
            response.raise_for_status()  # Raise exception for HTTP errors
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Hunter API request error: {str(e)}")
            raise
    
    def create_contacts_from_results(self, results, company=None):
        """
        Create Contact objects from Hunter API results
        
        Args:
            results (dict): Results from Hunter API domain search
            company (Company): Company object to associate contacts with
            
        Returns:
            list: List of created/updated Contact objects
        """
        created_contacts = []
        
        # Check if we have any results
        if 'data' not in results or 'emails' not in results['data']:
            return created_contacts
        
        # Process each email
        for email_data in results['data']['emails']:
            email = email_data.get('value')
            if not email:
                continue
            
            # Try to find existing contact
            try:
                contact = Contact.objects.get(email=email)
                # Update existing contact with new data
                updated = self._update_contact_from_hunter_data(contact, email_data, company)
                if updated:
                    contact.save()
                    
                created_contacts.append(contact)
                continue
            except Contact.DoesNotExist:
                # Create new contact
                contact = self._create_contact_from_hunter_data(email_data, company)
                created_contacts.append(contact)
        
        return created_contacts
    
    def _create_contact_from_hunter_data(self, email_data, company=None):
        """Create a new Contact from Hunter API data"""
        email = email_data.get('value')
        first_name = email_data.get('first_name', '')
        last_name = email_data.get('last_name', '')
        position = email_data.get('position', '')
        
        # Create the contact
        contact = Contact(
            first_name=first_name,
            last_name=last_name,
            email=email,
            position=position,
            company=company,
            source_channel=Contact.SourceChannel.HUNTER,
            status=Contact.ContactStatus.NEW
        )
        
        # Add organization name if company is provided
        if company:
            contact.organization_name = company.name
        elif 'organization' in email_data:
            contact.organization_name = email_data.get('organization')
        
        # Add additional Hunter-specific fields
        contact.hunter_confidence = email_data.get('confidence')
        contact.hunter_type = email_data.get('type')
        
        # Sources are stored as JSON
        if 'sources' in email_data:
            contact.hunter_sources = email_data.get('sources')
            
        # Store department and seniority
        contact.hunter_department = email_data.get('department')
        contact.hunter_seniority = email_data.get('seniority')
        
        # Add social profiles if available
        contact.twitter = email_data.get('twitter')
        contact.linkedin_url = email_data.get('linkedin')
        contact.phone_number = email_data.get('phone_number')
        
        # Handle verification status
        if 'verification' in email_data:
            verification = email_data.get('verification')
            if verification:
                contact.verification_status = verification.get('status')
                contact.verification_date = verification.get('date')
        
        contact.save()
        return contact
    
    def _update_contact_from_hunter_data(self, contact, email_data, company=None):
        """Update an existing Contact with Hunter API data, return True if updated"""
        updated = False
        
        # Update basic info if missing
        if not contact.first_name and email_data.get('first_name'):
            contact.first_name = email_data.get('first_name')
            updated = True
            
        if not contact.last_name and email_data.get('last_name'):
            contact.last_name = email_data.get('last_name')
            updated = True
            
        if not contact.position and email_data.get('position'):
            contact.position = email_data.get('position')
            updated = True
            
        # Update company if provided and not already set
        if company and not contact.company:
            contact.company = company
            updated = True
            
        # Update social profiles if missing
        if not contact.twitter and email_data.get('twitter'):
            contact.twitter = email_data.get('twitter')
            updated = True
            
        if not contact.linkedin_url and email_data.get('linkedin'):
            contact.linkedin_url = email_data.get('linkedin')
            updated = True
            
        if not contact.phone_number and email_data.get('phone_number'):
            contact.phone_number = email_data.get('phone_number')
            updated = True
        
        # Always update Hunter-specific fields
        if email_data.get('confidence') and email_data.get('confidence') != contact.hunter_confidence:
            contact.hunter_confidence = email_data.get('confidence')
            updated = True
            
        if email_data.get('type') and email_data.get('type') != contact.hunter_type:
            contact.hunter_type = email_data.get('type')
            updated = True
            
        if 'sources' in email_data:
            contact.hunter_sources = email_data.get('sources')
            updated = True
            
        if email_data.get('department') and email_data.get('department') != contact.hunter_department:
            contact.hunter_department = email_data.get('department')
            updated = True
            
        if email_data.get('seniority') and email_data.get('seniority') != contact.hunter_seniority:
            contact.hunter_seniority = email_data.get('seniority')
            updated = True
        
        # Handle verification status
        if 'verification' in email_data:
            verification = email_data.get('verification')
            if verification:
                if verification.get('status') and verification.get('status') != contact.verification_status:
                    contact.verification_status = verification.get('status')
                    updated = True
                
                if verification.get('date') and verification.get('date') != contact.verification_date:
                    contact.verification_date = verification.get('date')
                    updated = True
        
        return updated