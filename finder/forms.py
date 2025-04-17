from django import forms
from finder.models import CompanySearch, SerpAPISearchParameters

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
    
    latitude = forms.FloatField(
        label="Latitude",
        required=False,
        widget=forms.NumberInput(attrs={'step': 'any'}),
        help_text="Latitude coordinate (e.g., 40.7128)"
    )
    
    longitude = forms.FloatField(
        label="Longitude",
        required=False,
        widget=forms.NumberInput(attrs={'step': 'any'}),
        help_text="Longitude coordinate (e.g., -74.0060)"
    )
    
    zoom = forms.IntegerField(
        label="Zoom Level",
        min_value=3,
        max_value=21,
        initial=14,
        help_text="Zoom level (3-21, higher values = more zoomed in)"
    )
    
    max_results = forms.IntegerField(
        label="Maximum Results",
        min_value=1,
        max_value=100,
        initial=20,
        help_text="Maximum number of results to return (1-100)"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        place_name = cleaned_data.get('place_name')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        # Either place_name OR (latitude AND longitude) must be provided
        if not place_name and (latitude is None or longitude is None):
            raise forms.ValidationError(
                "Either a place name or both latitude and longitude coordinates must be provided."
            )
            
        # If both are provided, prefer coordinates
        if place_name and latitude is not None and longitude is not None:
            self.add_warning(
                "Both place name and coordinates provided. Coordinates will be used."
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