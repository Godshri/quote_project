from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class Source(models.Model):
    TYPE_CHOICES = [
        ('movie', 'Фильм'),
        ('book', 'Книга'),
        ('series', 'Сериал'),
        ('other', 'Другое'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Название")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Тип")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['name', 'type']
    
    def __str__(self):
        return f"{self.get_type_display()}: {self.name}"
    
    def clean(self):
        # Проверяем, что у источника не больше 3 цитат
        if self.pk:  # только для существующих объектов
            if self.quote_set.count() >= 3:
                raise ValidationError('У одного источника не может быть больше 3 цитат')

class Quote(models.Model):
    text = models.TextField(verbose_name="Текст цитаты")
    source = models.ForeignKey(Source, on_delete=models.CASCADE, verbose_name="Источник")
    weight = models.PositiveIntegerField(default=1, verbose_name="Вес")
    views = models.PositiveIntegerField(default=0, verbose_name="Просмотры")
    likes = models.PositiveIntegerField(default=0, verbose_name="Лайки")
    dislikes = models.PositiveIntegerField(default=0, verbose_name="Дизлайки")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['text', 'source']
    
    def __str__(self):
        return f"{self.text[:50]}... ({self.source})"
    
    def clean(self):
        # Проверяем уникальность цитаты для источника
        if Quote.objects.filter(text=self.text, source=self.source).exclude(pk=self.pk).exists():
            raise ValidationError('Цитата с таким текстом уже существует для этого источника')
        
        # Проверяем ограничение на количество цитат у источника
        if not self.pk:  # только для новых объектов
            if self.source.quote_set.count() >= 3:
                raise ValidationError('У одного источника не может быть больше 3 цитат')