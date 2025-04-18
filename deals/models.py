from django.db import models
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

class DealStage(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    conversion_probability = models.DecimalField(max_digits=5, decimal_places=2)
    order = models.IntegerField()

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['order']
    
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
    manual_conversion_probability = models.FloatField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    estimated_close_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)
    lost_reason = models.CharField(max_length=128, choices=LostReason.choices, blank=True, null=True)

    @property
    def expected_value(self):
        """Calculate the expected value based on probability"""
        if self.is_won:
            return self.value
        elif self.is_lost:
            return Decimal('0.00')
        
        if self.manual_conversion_probability is not None:
            return self.value * Decimal(str(self.manual_conversion_probability))
        elif self.stage:
            return self.value * self.stage.conversion_probability
        else:
            return Decimal('0.00')
    
    @property
    def status(self):
        """Return the status of the deal"""
        if self.is_won:
            return "Won"
        elif self.is_lost:
            return "Lost"
        else:
            return "Active"
            
    @property
    def days_until_close(self):
        """Return the number of days until close"""
        if not self.estimated_close_date:
            return None
        
        now = timezone.now()
        if now > self.estimated_close_date:
            return 0
        
        delta = self.estimated_close_date - now
        return delta.days
    
    def mark_as_won(self):
        """Mark the deal as won"""
        self.is_won = True
        self.is_lost = False
        self.lost_reason = None
        self.save()
    
    def mark_as_lost(self, reason=LostReason.NONE):
        """Mark the deal as lost with a reason"""
        self.is_lost = True
        self.is_won = False
        self.lost_reason = reason
        self.save()
    
    def __str__(self):
        contact_name = self.contact.first_name + " " + self.contact.last_name if self.contact else "No Contact"
        stage_name = self.stage.name if self.stage else "No Stage"
        return f"{contact_name} - {stage_name} - ${self.value}"
    
    @classmethod
    def get_pipeline_value(cls, days=None):
        """
        Calculate the total expected pipeline value
        
        Args:
            days (int, optional): Only include deals expected to close within this many days
            
        Returns:
            Decimal: The total expected value
        """
        queryset = cls.objects.filter(is_won=False, is_lost=False)
        
        # Filter by estimated close date if days is specified
        if days is not None:
            end_date = timezone.now() + timedelta(days=days)
            queryset = queryset.filter(estimated_close_date__lte=end_date)
        
        # Calculate expected value for each deal
        total = Decimal('0.00')
        for deal in queryset:
            total += deal.expected_value
            
        return total
    
    @classmethod
    def get_pipeline_by_stage(cls):
        """
        Calculate the pipeline value grouped by stage
        
        Returns:
            dict: A dictionary mapping stage names to expected values
        """
        stages = DealStage.objects.all().order_by('order')
        pipeline = {}
        
        for stage in stages:
            deals = cls.objects.filter(stage=stage, is_won=False, is_lost=False)
            total = Decimal('0.00')
            for deal in deals:
                total += deal.expected_value
            
            pipeline[stage.name] = total
            
        return pipeline
        
    class Meta:
        ordering = ['-created_at']