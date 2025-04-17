from django import forms
from django.db.models import Count
from .models import Company, CompanyList

# Helper for getting all US states
def get_us_states():
    """Return a list of US states as choices for a dropdown."""
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
    
    # Convert to list of tuples for choices
    choices = [('', 'All States')]  # Add empty choice
    choices.extend([(code, name) for code, name in sorted(state_dict.items(), key=lambda x: x[1])])
    
    return choices

def get_business_types():
    """Return a list of unique business types from the database."""
    types = Company.objects.exclude(primary_type__isnull=True).exclude(primary_type='').values_list('primary_type', flat=True).distinct().order_by('primary_type')
    choices = [('', 'All Types')]  # Add empty choice
    choices.extend([(t, t) for t in types])
    return choices

class CompanyListForm(forms.ModelForm):
    class Meta:
        model = CompanyList
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class CompanyForm(forms.ModelForm):
    # Add a dropdown for state selection
    state_select = forms.ChoiceField(
        choices=get_us_states,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Company
        fields = [
            'name', 'domain', 'website_url', 'phone', 'address', 
            'city', 'state', 'state_code', 'description',
            'primary_type', 'rating', 'reviews_count',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'domain': forms.TextInput(attrs={'class': 'form-control'}),
            'website_url': forms.URLInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'state_code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'primary_type': forms.TextInput(attrs={'class': 'form-control'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'reviews_count': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If we have a company instance, set the initial value for state_select
        if self.instance and self.instance.pk and self.instance.state_code:
            self.fields['state_select'].initial = self.instance.state_code
    
    def save(self, commit=True):
        # Get the instance
        instance = super().save(commit=False)
        
        # If state_select was used, update the state and state_code
        if self.cleaned_data.get('state_select'):
            state_code = self.cleaned_data['state_select']
            if state_code:
                instance.state_code = state_code
                # Get the full state name from the code
                state_dict = dict(get_us_states())[state_code]
                instance.state = state_dict
        
        if commit:
            instance.save()
        
        return instance

class CompanyFilterForm(forms.Form):
    name = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by name'})
    )
    
    city = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by city'})
    )
    
    state = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by state'})
    )
    
    state_select = forms.ChoiceField(
        choices=get_us_states,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    primary_type = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by type'})
    )
    
    primary_type_select = forms.ChoiceField(
        choices=get_business_types,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class CompanyListAddForm(forms.Form):
    companies = forms.ModelMultipleChoiceField(
        queryset=Company.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )