from companies.models import Company

def update_all_companies_location():
    companies = Company.objects.filter(address__isnull=False)
    updated_count = 0
    
    for company in companies:
        # Store original values to detect changes
        original_city = company.city
        original_state = company.state
        
        # Parse address
        company.parse_address()
        
        # Only save if something changed
        if company.city != original_city or company.state != original_state:
            company.save()
            updated_count += 1
    
    return updated_count

# Run the function
def run():
    updated = update_all_companies_location()
    print(f"Updated {updated} companies with city and state information")