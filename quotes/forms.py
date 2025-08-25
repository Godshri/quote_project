from django import forms
from .models import Quote, Source

class SourceForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = ['name', 'type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
        }

class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ['text', 'source', 'weight']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'source': forms.Select(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
        }