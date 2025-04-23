import requests
import logging
from datetime import datetime
from django.conf import settings
from contacts.models import Contact

logger = logging.getLogger(__name__)

class ZeroBounceService:
    """
    Service for validating email addresses using the ZeroBounce API.
    """
    
    BASE_URL = "https://api.zerobounce.net/v2"
    
    def __init__(self, api_key=None):
        """Initialize with API key from settings if not provided"""
        self.api_key = api_key or getattr(settings, 'ZEROBOUNCE_API_KEY', None)
        if not self.api_key:
            raise ValueError("ZeroBounce API key is required")
    
    def validate_email(self, email, ip_address=None, timeout=None):
        """
        Validate a single email address using ZeroBounce API.
        
        Args:
            email (str): The email address to validate
            ip_address (str, optional): The IP address the email signed up from
            timeout (int, optional): Timeout in seconds (3-60)
            
        Returns:
            dict: API response data
        """
        # Build request parameters
        params = {
            'api_key': self.api_key,
            'email': email,
            'ip_address': ip_address or ''
        }
        
        # Add optional timeout parameter
        if timeout and 3 <= timeout <= 60:
            params['timeout'] = timeout
        
        # Make the API request
        try:
            response = requests.get(f"{self.BASE_URL}/validate", params=params)
            response.raise_for_status()  # Raise exception for HTTP errors
            return response.json()
        except requests.RequestException as e:
            logger.error(f"ZeroBounce API request error: {str(e)}")
            raise
    
    def get_credits(self):
        """
        Get the number of credits available in the ZeroBounce account.
        
        Returns:
            int: Number of available credits
        """
        params = {
            'api_key': self.api_key
        }
        
        try:
            response = requests.get(f"{self.BASE_URL}/getcredits", params=params)
            response.raise_for_status()
            result = response.json()
            
            # Make sure the credits value is returned as an integer
            credits_value = result.get('Credits', 0)
            try:
                # Convert to integer if it's a string
                return int(credits_value)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert credits value '{credits_value}' to integer. Returning 0.")
                return 0
        except requests.RequestException as e:
            logger.error(f"ZeroBounce API credits check error: {str(e)}")
            raise
    
    def update_contact_from_validation(self, contact, validation_result):
        """
        Update a Contact object with ZeroBounce validation results.
        
        Args:
            contact (Contact): The contact to update
            validation_result (dict): Results from ZeroBounce validation
            
        Returns:
            bool: True if the contact was updated
        """
        if not validation_result or 'status' not in validation_result:
            return False
        
        updated = False
        
        # Map ZeroBounce status to Contact model status
        status_mapping = {
            'valid': Contact.EmailStatus.VALID,
            'invalid': Contact.EmailStatus.INVALID,
            'catch-all': Contact.EmailStatus.CATCH_ALL,
            'unknown': Contact.EmailStatus.UNKNOWN,
            'spamtrap': Contact.EmailStatus.SPAMTRAP,
            'abuse': Contact.EmailStatus.ABUSE,
            'do_not_mail': Contact.EmailStatus.DO_NOT_MAIL
        }
        
        # Update email verification status
        new_status = status_mapping.get(validation_result.get('status'), Contact.EmailStatus.UNVERIFIED)
        if contact.zerobounce_status != new_status:
            contact.zerobounce_status = new_status
            updated = True
        
        # Update sub-status if provided
        sub_status = validation_result.get('sub_status', '')
        if sub_status and contact.zerobounce_sub_status != sub_status:
            contact.zerobounce_sub_status = sub_status
            updated = True
        
        # Update other ZeroBounce fields
        if 'free_email' in validation_result and contact.zerobounce_free_email != validation_result['free_email']:
            contact.zerobounce_free_email = validation_result['free_email']
            updated = True
        
        if validation_result.get('did_you_mean') and contact.zerobounce_did_you_mean != validation_result['did_you_mean']:
            contact.zerobounce_did_you_mean = validation_result['did_you_mean']
            updated = True
        
        if validation_result.get('domain_age_days') and contact.zerobounce_domain_age_days != validation_result['domain_age_days']:
            try:
                contact.zerobounce_domain_age_days = int(validation_result['domain_age_days'])
                updated = True
            except (ValueError, TypeError):
                # Handle case where domain_age_days is not a valid integer
                pass
        
        if validation_result.get('active_in_days') and contact.zerobounce_active_in_days != validation_result['active_in_days']:
            contact.zerobounce_active_in_days = validation_result['active_in_days']
            updated = True
            
        if validation_result.get('smtp_provider') and contact.zerobounce_smtp_provider != validation_result['smtp_provider']:
            contact.zerobounce_smtp_provider = validation_result['smtp_provider']
            updated = True
            
        if validation_result.get('mx_record') and contact.zerobounce_mx_record != validation_result['mx_record']:
            contact.zerobounce_mx_record = validation_result['mx_record']
            updated = True
            
        if 'mx_found' in validation_result:
            mx_found = validation_result['mx_found'] == 'true'
            if contact.zerobounce_mx_found != mx_found:
                contact.zerobounce_mx_found = mx_found
                updated = True
        
        # Update location data if provided
        if validation_result.get('country') and contact.zerobounce_country != validation_result['country']:
            contact.zerobounce_country = validation_result['country']
            updated = True
            
        if validation_result.get('region') and contact.zerobounce_region != validation_result['region']:
            contact.zerobounce_region = validation_result['region']
            updated = True
            
        if validation_result.get('city') and contact.zerobounce_city != validation_result['city']:
            contact.zerobounce_city = validation_result['city']
            updated = True
            
        if validation_result.get('zipcode') and contact.zerobounce_zipcode != validation_result['zipcode']:
            contact.zerobounce_zipcode = validation_result['zipcode']
            updated = True
        
        # Update name if not already present and provided by ZeroBounce
        if validation_result.get('firstname') and not contact.first_name:
            contact.first_name = validation_result['firstname']
            updated = True
            
        if validation_result.get('lastname') and not contact.last_name:
            contact.last_name = validation_result['lastname']
            updated = True
        
        # Update processed timestamp
        if validation_result.get('processed_at'):
            try:
                processed_at = datetime.strptime(validation_result['processed_at'], '%Y-%m-%d %H:%M:%S.%f')
                if not contact.zerobounce_processed_at or contact.zerobounce_processed_at != processed_at:
                    contact.zerobounce_processed_at = processed_at
                    updated = True
            except (ValueError, TypeError):
                # Try alternative format
                try:
                    processed_at = datetime.strptime(validation_result['processed_at'], '%Y-%m-%d %H:%M:%S')
                    if not contact.zerobounce_processed_at or contact.zerobounce_processed_at != processed_at:
                        contact.zerobounce_processed_at = processed_at
                        updated = True
                except (ValueError, TypeError):
                    # If date parsing fails, skip updating this field
                    pass
        
        # Save the contact if any fields were updated
        if updated:
            contact.save()
        
        return updated