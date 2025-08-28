from django.forms import ValidationError
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Sum, F, Q
from django.views.decorators.http import require_POST
from django.contrib import messages
import random
import json
from .models import Quote, Source
from .forms import QuoteForm, SourceForm



def random_quote(request):
    """Получение случайной цитаты с учетом веса"""
    total_weight = Quote.objects.aggregate(total=Sum('weight'))['total'] or 0
    
    if total_weight <= 0:
        selected_quote = None
    else:
        # Оптимизированный выбор случайной цитаты
        random_weight = random.uniform(0, total_weight)
        
        # Используем агрегацию в БД для более эффективного поиска
        cumulative_weight = 0
        quotes = Quote.objects.values('id', 'weight').order_by('-weight')
        
        for quote in quotes:
            cumulative_weight += quote['weight']
            if cumulative_weight >= random_weight:
                selected_quote = Quote.objects.get(id=quote['id'])
                break
        else:
            # Если цитата не найдена, берем случайную
            selected_quote = Quote.objects.order_by('?').first()
    
    if selected_quote:
        # Оптимизированное обновление счетчика просмотров
        Quote.objects.filter(id=selected_quote.id).update(views=F('views') + 1)
        selected_quote.refresh_from_db()
        
        # Сохраняем информацию о просмотре в сессии
        viewed_quotes = request.session.setdefault('viewed_quotes', {})
        viewed_quotes[str(selected_quote.id)] = {
            'can_vote': True,
            'voted': False
        }
        request.session.modified = True
    
    return render(request, 'quotes/random_quote.html', {
        'quote': selected_quote,
        'total_quotes': Quote.objects.count()
    })


def can_user_vote(request, quote_id):
    """Проверяет, может ли пользователь голосовать за цитату"""
    viewed_quotes = request.session.get('viewed_quotes', {})
    quote_data = viewed_quotes.get(str(quote_id), {})
    
    return quote_data.get('can_vote', False) and not quote_data.get('voted', False)


@require_POST
def like_quote(request, quote_id):
    """Лайк цитаты с проверкой ограничений"""
    return _vote_quote(request, quote_id, 'like')


@require_POST
def dislike_quote(request, quote_id):
    """Дизлайк цитаты с проверкой ограничений"""
    return _vote_quote(request, quote_id, 'dislike')


def _vote_quote(request, quote_id, vote_type):
    """Общая функция для обработки голосования"""
    quote = get_object_or_404(Quote, id=quote_id)
    
    if not can_user_vote(request, quote_id):
        return JsonResponse({
            'success': False, 
            'error': 'Вы уже голосовали за эту цитату или не просматривали её',
            'likes': quote.likes, 
            'dislikes': quote.dislikes
        })
    
    # Обновляем счетчик
    if vote_type == 'like':
        Quote.objects.filter(id=quote_id).update(likes=F('likes') + 1)
    else:
        Quote.objects.filter(id=quote_id).update(dislikes=F('dislikes') + 1)
    
    quote.refresh_from_db()
    
    # Обновляем вес цитаты
    update_quote_weight(quote)
    
    # Отмечаем, что пользователь проголосовал
    viewed_quotes = request.session['viewed_quotes']
    viewed_quotes[str(quote_id)]['voted'] = True
    viewed_quotes[str(quote_id)]['can_vote'] = False
    request.session.modified = True
    
    return JsonResponse({
        'success': True,
        'likes': quote.likes, 
        'dislikes': quote.dislikes,
        'weight': quote.weight
    })


def update_quote_weight(quote):
    """Обновляет вес цитаты с ограничением максимального прироста в 80%"""
    # Базовый вес для новых цитат
    base_weight = 10
    current_weight = quote.weight
    
    # Рассчитываем рейтинг (лайки минус дизлайки)
    rating = quote.likes - quote.dislikes
    
    # Общее количество голосов
    total_votes = quote.likes + quote.dislikes
    
    if total_votes > 0:
        # Процент лайков (от 0 до 100)
        like_percentage = (quote.likes / total_votes) * 100
        
        # Рассчитываем новый вес без ограничений
        raw_new_weight = max(1, base_weight + rating + (like_percentage / 10))
        

        max_allowed_weight = current_weight * 1.8
        new_weight = min(raw_new_weight, max_allowed_weight)
    else:
        # Если нет голосов, используем базовый вес
        new_weight = base_weight
    

    if abs(new_weight - current_weight) > 0.1:
        Quote.objects.filter(id=quote.id).update(weight=new_weight)


def add_quote(request):
    """Добавление новой цитаты"""
    if request.method == 'POST':
        form = QuoteForm(request.POST)
        if form.is_valid():
            try:
                # Сохраняем форму, но не коммитим в БД сразу
                quote = form.save(commit=False)
                
                # Проверяем, что источник существует
                if not quote.source or not quote.source.pk:
                    messages.error(request, 'Ошибка: источник не выбран или не существует')
                    return render(request, 'quotes/add_quote.html', {'form': form})
                
                # Дополнительная проверка ограничения на количество цитат
                if quote.source.quote_set.count() >= 3:
                    messages.error(request, f'У источника "{quote.source}" уже есть 3 цитаты. Нельзя добавить больше.')
                    return render(request, 'quotes/add_quote.html', {'form': form})
                
                # Проверяем уникальность цитаты
                if Quote.objects.filter(text=quote.text, source=quote.source).exists():
                    messages.error(request, 'Цитата с таким текстом уже существует для этого источника')
                    return render(request, 'quotes/add_quote.html', {'form': form})
                
                # Сохраняем цитату
                quote.save()
                messages.success(request, 'Цитата успешно добавлена!')
                return redirect('random_quote')
                
            except ValidationError as e:
                messages.error(request, f'Ошибка валидации: {e}')
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении: {str(e)}')
        else:
            # Показываем все ошибки формы
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_name = form.fields[field].label if field in form.fields else field
                        messages.error(request, f'{field_name}: {error}')
    else:
        form = QuoteForm()
    
    return render(request, 'quotes/add_quote.html', {'form': form})


def add_source(request):
    """Добавление нового источника"""
    sources = Source.objects.all().order_by('type', 'name')
    
    if request.method == 'POST':
        form = SourceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Источник успешно добавлен!')
            return redirect('add_quote')
        else:

            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = SourceForm()
    
    return render(request, 'quotes/add_source.html', {
        'form': form,
        'sources': sources
    })


def popular_quotes(request):
    """Популярные цитаты по количеству лайков"""
    quotes = Quote.objects.order_by('-likes', '-views')[:10]
    
    return render(request, 'quotes/popular_quotes.html', {'quotes': quotes})


def dashboard(request):
    """Дашборд со статистикой"""
    quotes = Quote.objects.all()
    
    stats_data = quotes.aggregate(
        total_views=Sum('views') or 0,
        total_likes=Sum('likes') or 0,
        total_dislikes=Sum('dislikes') or 0
    )
    
    stats = {
        'total_quotes': quotes.count(),
        'total_sources': Source.objects.count(),
        'total_views': stats_data['total_views'],
        'total_likes': stats_data['total_likes'],
        'total_dislikes': stats_data['total_dislikes'],
        'most_popular': quotes.order_by('-likes', '-views').first(),
        'most_viewed': quotes.order_by('-views').first(),
    }
    
    return render(request, 'quotes/dashboard.html', {'stats': stats})