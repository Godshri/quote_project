from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Quote, Source

class SourceForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = ['name', 'type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
        }
        error_messages = {
            'name': {
                'unique': _("Источник с таким названием и типом уже существует"),
            },
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        type = cleaned_data.get('type')
        
        # Проверка на уникальность источника (name + type)
        if name and type:
            # Используем exists() для проверки
            existing_sources = Source.objects.filter(name=name, type=type)
            if self.instance and self.instance.pk:
                existing_sources = existing_sources.exclude(pk=self.instance.pk)
            
            if existing_sources.exists():
                # Добавляем ошибку к полю, а не общую ошибку
                self.add_error('name', 'Источник с таким названием и типом уже существует')
        
        # Проверка ограничения на количество цитат при редактировании
        if self.instance and self.instance.pk:
            if self.instance.quote_set.count() >= 3:
                self.add_error(None, 'У одного источника не может быть больше 3 цитат')
        
        return cleaned_data

class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ['text', 'source', 'weight']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'source': forms.Select(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        text = cleaned_data.get('text')
        source = cleaned_data.get('source')
        
        if text and source:
            # Проверка уникальности цитаты
            existing_quotes = Quote.objects.filter(text=text, source=source)
            if self.instance and self.instance.pk:
                existing_quotes = existing_quotes.exclude(pk=self.instance.pk)
            
            if existing_quotes.exists():
                self.add_error('text', 'Цитата с таким текстом уже существует для этого источника')
            
            # Проверка ограничения на количество цитат
            if source and source.quote_set.count() >= 3:
                if not self.instance or not self.instance.pk:  # только для новых объектов
                    self.add_error('source', 'У одного источника не может быть больше 3 цитат')
        
        return cleaned_data