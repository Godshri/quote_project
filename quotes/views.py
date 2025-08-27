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
        
        random_weight = random.uniform(0, total_weight)
        
        # Агрегируем для оптимизации поиска
        quotes = Quote.objects.values_list('id', 'weight').order_by('-weight')
        
        current = 0
        selected_quote_id = None
        
        for quote_id, weight in quotes:
            current += weight
            if current >= random_weight:
                selected_quote_id = quote_id
                break
        
        # Если по какой-то причине цитата не выбрана, берем последнюю
        if selected_quote_id is None and quotes:
            selected_quote_id = quotes.last()[0]
        
        selected_quote = Quote.objects.get(id=selected_quote_id) if selected_quote_id else None
    
    if selected_quote:
        selected_quote.views += 1
        selected_quote.save()
        
        # Сохраняем информацию о просмотре в сессии
        if 'viewed_quotes' not in request.session:
            request.session['viewed_quotes'] = {}
        
        viewed_quotes = request.session['viewed_quotes']
        viewed_quotes[str(selected_quote.id)] = {
            'can_vote': True,
            'voted': False
        }
        request.session['viewed_quotes'] = viewed_quotes
        request.session.modified = True
    
    return render(request, 'quotes/random_quote.html', {
        'quote': selected_quote,
        'total_quotes': Quote.objects.count()
    })


def can_user_vote(request, quote_id):
    """Проверяет, может ли пользователь голосовать за цитату"""
    if 'viewed_quotes' not in request.session:
        return False
    
    viewed_quotes = request.session['viewed_quotes']
    quote_key = str(quote_id)
    
    if quote_key not in viewed_quotes:
        return False
    
    return viewed_quotes[quote_key].get('can_vote', False) and not viewed_quotes[quote_key].get('voted', False)


@require_POST
def like_quote(request, quote_id):
    """Лайк цитаты с проверкой ограничений"""
    quote = get_object_or_404(Quote, id=quote_id)
    
    if not can_user_vote(request, quote_id):
        return JsonResponse({
            'success': False, 
            'error': 'Вы уже голосовали за эту цитату или не просматривали её',
            'likes': quote.likes, 
            'dislikes': quote.dislikes
        })
    
    quote.likes += 1
    quote.save()
    
    # Обновляем вес цитаты на основе рейтинга
    update_quote_weight(quote)
    
    # Отмечаем, что пользователь проголосовал
    viewed_quotes = request.session['viewed_quotes']
    viewed_quotes[str(quote_id)]['voted'] = True
    viewed_quotes[str(quote_id)]['can_vote'] = False
    request.session['viewed_quotes'] = viewed_quotes
    request.session.modified = True
    
    return JsonResponse({
        'success': True,
        'likes': quote.likes, 
        'dislikes': quote.dislikes,
        'weight': quote.weight
    })


@require_POST
def dislike_quote(request, quote_id):
    """Дизлайк цитаты с проверкой ограничений"""
    quote = get_object_or_404(Quote, id=quote_id)
    
    if not can_user_vote(request, quote_id):
        return JsonResponse({
            'success': False, 
            'error': 'Вы уже голосовали за эту цитату',
            'likes': quote.likes, 
            'dislikes': quote.dislikes
        })
        
    
    quote.dislikes += 1
    quote.save()
    
    # Обновляем вес цитаты на основе рейтинга
    update_quote_weight(quote)
    
    # Отмечаем, что пользователь проголосовал
    viewed_quotes = request.session['viewed_quotes']
    viewed_quotes[str(quote_id)]['voted'] = True
    viewed_quotes[str(quote_id)]['can_vote'] = False
    request.session['viewed_quotes'] = viewed_quotes
    request.session.modified = True
    
    return JsonResponse({
        'success': True,
        'likes': quote.likes, 
        'dislikes': quote.dislikes,
        'weight': quote.weight
    })


def update_quote_weight(quote):
    """Обновляет вес цитаты на основе её рейтинга"""
    # Базовый вес
    base_weight = 10
    
    # Рейтинг
    rating = quote.likes - quote.dislikes
    
    # Минимальный рейтинг для избежания отрицательных весов
    min_rating = -5
    
    # Обновляем вес: базовый вес + рейтинг
    # Обеспечиваем минимальный вес 1 для всех цитат
    new_weight = max(1, base_weight + max(min_rating, rating))
    
    # Можно добавить нелинейную зависимость для большего влияния рейтинга:
    # new_weight = max(1, base_weight + (rating * 2))
    
    quote.weight = new_weight
    quote.save()


def add_quote(request):
    """Добавление новой цитаты"""
    if request.method == 'POST':
        form = QuoteForm(request.POST)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.weight = 1
            quote.save()
            messages.success(request, 'Цитата успешно добавлена!')
            return redirect('random_quote')
        else:
            # Добавляем сообщения об ошибках для каждой ошибки формы
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
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
            # Добавляем сообщения об ошибках для каждой ошибки формы
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = SourceForm()
    
    return render(request, 'quotes/add_source.html', {
        'form': form,
        'sources': sources
    })


def popular_quotes(request):
    """Популярные цитаты по рейтингу"""
    quotes = Quote.objects.annotate(
        popularity=F('likes') - F('dislikes')
    ).order_by('-popularity', '-views')[:10]
    
    return render(request, 'quotes/popular_quotes.html', {'quotes': quotes})


def dashboard(request):
    """Дашборд со статистикой"""
    quotes = Quote.objects.all()
    
    stats = {
        'total_quotes': quotes.count(),
        'total_sources': Source.objects.count(),
        'total_views': quotes.aggregate(total=Sum('views'))['total'] or 0,
        'total_likes': quotes.aggregate(total=Sum('likes'))['total'] or 0,
        'total_dislikes': quotes.aggregate(total=Sum('dislikes'))['total'] or 0,
        'most_popular': quotes.annotate(
            popularity=F('likes') - F('dislikes')
        ).order_by('-popularity').first(),
        'most_viewed': quotes.order_by('-views').first(),
    }
    
    return render(request, 'quotes/dashboard.html', {'stats': stats})