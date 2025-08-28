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
            'text': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Введите текст цитаты...'
            }),
            'source': forms.Select(attrs={
                'class': 'form-control'
            }),
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '1000',
                'step': '1',
                'value': '10'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['source'].empty_label = "--- Выберите источник ---"
        self.fields['source'].required = True
        # Устанавливаем подсказку для поля weight
        self.fields['weight'].help_text = 'Чем выше вес, тем чаще цитата будет показываться'

    def clean_source(self):
        source = self.cleaned_data.get('source')
        if not source:
            raise forms.ValidationError('Пожалуйста, выберите источник')
        return source

    def clean(self):
        cleaned_data = super().clean()
        text = cleaned_data.get('text')
        source = cleaned_data.get('source')

        # Если источник не выбран, останавливаем дальнейшие проверки
        if not source:
            return cleaned_data

        if text:
            # Проверка уникальности цитаты
            existing_quotes = Quote.objects.filter(text=text, source=source)
            if self.instance and self.instance.pk:
                existing_quotes = existing_quotes.exclude(pk=self.instance.pk)

            if existing_quotes.exists():
                self.add_error('text', 'Цитата с таким текстом уже существует для этого источника')

            # Проверка ограничения на количество цитат (только если источник уже сохранен в БД)
            if source.pk:  # только для существующих источников
                quote_count = Quote.objects.filter(source=source).count()
                if self.instance and self.instance.pk:
                    # Если редактируем существующую цитату, исключаем её из подсчета
                    quote_count = Quote.objects.filter(source=source).exclude(pk=self.instance.pk).count()

                if quote_count >= 3:
                    self.add_error('source', f'У источника "{source}" уже есть 3 цитаты. Нельзя добавить больше.')

        return cleaned_data