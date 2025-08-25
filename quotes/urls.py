from django.urls import path
from . import views

urlpatterns = [
    path('', views.random_quote, name='random_quote'),
    path('add/', views.add_quote, name='add_quote'),
    path('add/source/', views.add_source, name='add_source'),
    path('popular/', views.popular_quotes, name='popular_quotes'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('quote/<int:quote_id>/like/', views.like_quote, name='like_quote'),
    path('quote/<int:quote_id>/dislike/', views.dislike_quote, name='dislike_quote'),
]