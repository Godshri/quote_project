from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class Source(models.Model):
    TYPE_CHOICES = [
        ('movie', 'Фильм'),
        ('book', 'Книга'),
        ('series', 'Сериал'),
        ('game', 'Игра'),
        ('person', 'Люди'),
        ('other', 'Другое'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Название")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Тип")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['name', 'type']
    
    def __str__(self):
        return f"{self.get_type_display()}: {self.name}"
    
    def clean(self):
        # Проверяем уникальность (дублирует unique_together, но дает лучшее сообщение)
        if Source.objects.filter(name=self.name, type=self.type).exclude(pk=self.pk).exists():
            raise ValidationError('Источник с таким названием и типом уже существует')
        
        # Проверяем, что у источника не больше 3 цитат
        if self.pk:  # только для существующих объектов
            if self.quote_set.count() >= 3:
                raise ValidationError('У одного источника не может быть больше 3 цитат')

class Quote(models.Model):
    text = models.TextField(verbose_name="Текст цитаты")
    source = models.ForeignKey(Source, on_delete=models.CASCADE, verbose_name="Источник", 
                              null=True, blank=True)  # Добавьте это
    weight = models.PositiveIntegerField(default=1, verbose_name="Вес")
    views = models.PositiveIntegerField(default=0, verbose_name="Просмотры")
    likes = models.PositiveIntegerField(default=0, verbose_name="Лайки")
    dislikes = models.PositiveIntegerField(default=0, verbose_name="Дизлайки")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['text', 'source']
    
    def __str__(self):
        source_name = self.source.name if self.source else "Без источника"
        return f"{self.text[:50]}... ({source_name})"
    
    def clean(self):
        # Если источник не указан, пропускаем проверки
        if not self.source:
            return
            
        # Проверяем уникальность цитаты для источника
        if Quote.objects.filter(text=self.text, source=self.source).exclude(pk=self.pk).exists():
            raise ValidationError('Цитата с таким текстом уже существует')
        
        # Проверяем ограничение на количество цитат у источника
        if self.source.pk:
            quote_count = Quote.objects.filter(source=self.source).count()
            if not self.pk:  # только для новых объектов
                if quote_count >= 3:
                    raise ValidationError('У одного источника не может быть больше 3 цитат')
            else:
                # Для существующих объектов исключаем текущую цитату из подсчета
                quote_count = Quote.objects.filter(source=self.source).exclude(pk=self.pk).count()
                if quote_count >= 3:
                    raise ValidationError('У одного источника не может быть больше 3 цитат')