from django import forms
from django.forms import ModelForm
from .models import Deal, DealStage
from contacts.models import Contact

class DealForm(ModelForm):
    class Meta:
        model = Deal
        fields = [
            'contact', 'value', 'stage', 'manual_conversion_probability',
            'notes', 'estimated_close_date'
        ]
        widgets = {
            'contact': forms.TextInput(attrs={'disabled': 'disabled', 'placeholder': 'Contact'}),
            'value': forms.NumberInput(attrs={'step': '0.01'}),
            'stage': forms.Select(attrs={}),
            'manual_conversion_probability': forms.NumberInput(
                attrs={ 'min': '0', 'max': '1', 'step': '0.01'}
            ),
            'notes': forms.Textarea(attrs={ 'rows': 4}),
            'estimated_close_date': forms.DateTimeInput(
                attrs={ 'type': 'datetime-local'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields optional where appropriate
        self.fields['manual_conversion_probability'].required = False
        self.fields['estimated_close_date'].required = False

        # Add helpful labels and help text
        self.fields['manual_conversion_probability'].label = "Custom Conversion Probability"
        self.fields['manual_conversion_probability'].help_text = "Enter a value between 0 and 1 (e.g., 0.75 = 75%). Leave blank to use the stage's default."
        
        self.fields['value'].help_text = "The total monetary value of this deal"
        self.fields['estimated_close_date'].help_text = "When do you expect this deal to close?"

class DealStageForm(ModelForm):
    class Meta:
        model = DealStage
        fields = ['name', 'description', 'conversion_probability', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={ 'rows': 3}),
            'conversion_probability': forms.NumberInput(
                attrs={ 'min': '0', 'max': '1', 'step': '0.01'}
            ),
            'order': forms.NumberInput(attrs={ 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conversion_probability'].help_text = "Probability value between 0 and 1 (e.g., 0.2 = 20%)"
        self.fields['order'].help_text = "Display order in pipeline (lower numbers first)"

class DealFilterForm(forms.Form):
    contact = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={ 'placeholder': 'Filter by contact'})
    )
    
    value_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={ 'placeholder': 'Min value'})
    )
    
    value_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={ 'placeholder': 'Max value'})
    )
    
    stage = forms.ModelChoiceField(
        queryset=DealStage.objects.all().order_by('order'),
        required=False,
        empty_label="All Stages",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('active', 'Active'),
            ('won', 'Won'),
            ('lost', 'Lost')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    close_date_start = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={ 'type': 'date'})
    )
    
    close_date_end = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={ 'type': 'date'})
    )