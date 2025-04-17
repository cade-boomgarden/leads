from django.db import models

class DealStage(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    conversion_probability = models.DecimalField(max_digits=5, decimal_places=2)
    order = models.IntegerField()

    def __str__(self):
        return self.name
    
class Deal(models.Model):
    class LostReason(models.TextChoices):
        NONE = 'none', 'None'
        COMPETITOR = 'competitor', 'Competitor'
        BUDGET = 'budget', 'Budget'
        NO_RESPONSE = 'no_response', 'No Response'
        OTHER = 'other', 'Other'
        PRODUCT = 'product', 'Product'
        TIMING = 'timing', 'Timing'
        
    contact = models.ForeignKey('contacts.Contact', on_delete=models.SET_NULL, blank=True, null=True, related_name='deals')
    value = models.DecimalField(max_digits=10, decimal_places=2)
    stage = models.ForeignKey(DealStage, on_delete=models.SET_NULL, blank=True, null=True, related_name='deals')
    manual_conversion_probability = models.FloatField()
    notes = models.TextField(blank=True, null=True)
    estimated_close_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)
    lost_reason = models.CharField(max_length=128, choices=LostReason.choices, blank=True, null=True)

    @property
    def expected_value(self):
        if self.manual_conversion_probability:
            return self.value * self.manual_conversion_probability
        else:
            return self.value * self.stage.conversion_probability

    def __str__(self):
        return f"{self.contact} - {self.stage} - {self.value}"