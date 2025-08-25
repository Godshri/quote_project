from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Sum, F
from django.views.decorators.http import require_POST
import random
from .models import Quote, Source
from .forms import QuoteForm, SourceForm

def random_quote(request):
    # Получаем случайную цитату с учетом веса
    total_weight = Quote.objects.aggregate(total=Sum('weight'))['total'] or 0
    if total_weight > 0:
        random_weight = random.uniform(0, total_weight)
        current = 0
        quotes = Quote.objects.all()
        for quote in quotes:
            current += quote.weight
            if current >= random_weight:
                selected_quote = quote
                break
    else:
        selected_quote = None
    
    # Увеличиваем счетчик просмотров
    if selected_quote:
        selected_quote.views += 1
        selected_quote.save()
    
    return render(request, 'quotes/random_quote.html', {
        'quote': selected_quote,
        'total_quotes': Quote.objects.count()
    })

@require_POST
def like_quote(request, quote_id):
    quote = get_object_or_404(Quote, id=quote_id)
    quote.likes += 1
    quote.save()
    return JsonResponse({'likes': quote.likes, 'dislikes': quote.dislikes})

@require_POST
def dislike_quote(request, quote_id):
    quote = get_object_or_404(Quote, id=quote_id)
    quote.dislikes += 1
    quote.save()
    return JsonResponse({'likes': quote.likes, 'dislikes': quote.dislikes})

def add_quote(request):
    if request.method == 'POST':
        form = QuoteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('random_quote')
    else:
        form = QuoteForm()
    
    return render(request, 'quotes/add_quote.html', {'form': form})

def add_source(request):
    if request.method == 'POST':
        form = SourceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('add_quote')
    else:
        form = SourceForm()
    
    return render(request, 'quotes/add_source.html', {'form': form})

def popular_quotes(request):
    quotes = Quote.objects.annotate(
        popularity=F('likes') - F('dislikes')
    ).order_by('-popularity')[:10]
    
    return render(request, 'quotes/popular_quotes.html', {'quotes': quotes})

def dashboard(request):
    stats = {
        'total_quotes': Quote.objects.count(),
        'total_sources': Source.objects.count(),
        'total_views': Quote.objects.aggregate(total=Sum('views'))['total'] or 0,
        'total_likes': Quote.objects.aggregate(total=Sum('likes'))['total'] or 0,
        'most_popular': Quote.objects.annotate(
            popularity=F('likes') - F('dislikes')
        ).order_by('-popularity').first(),
    }
    
    return render(request, 'quotes/dashboard.html', {'stats': stats})