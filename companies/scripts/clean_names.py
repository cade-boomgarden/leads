import re
from ..models import Company

def clean_company_name(business_name):
    """
    Clean a business name from Google Maps results.
    
    Args:
        business_name (str): The original business name
        
    Returns:
        str: The cleaned business name
    """
    # Step 1: Remove everything after " - ", " (", or " |" if they exist
    separators = [" - ", " (", " |"]
    for separator in separators:
        if separator in business_name:
            business_name = business_name.split(separator)[0]
    
    # Step 2: Remove any non-Latin characters
    # This regex keeps only Latin letters, numbers, spaces, and basic punctuation
    # business_name = re.sub(r'[^\x00-\x7F]+', '', business_name)
    
    # Step 3: Clean up any extra whitespace
    business_name = business_name.strip()
    
    return business_name

# Example usage
def run():
    companies = Company.objects.all()
    for company in companies:
        original_name = company.name
        cleaned_name = clean_company_name(original_name)
        
        # Update the company name if it has changed
        if original_name != cleaned_name:
            company.name = cleaned_name
            company.save()
            print(f"Updated: {original_name} -> {cleaned_name}")
