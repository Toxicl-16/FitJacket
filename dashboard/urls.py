from django.urls import path
from . import views
urlpatterns = [
    path('', views.dashboard, name='Dashboard'),
    path('goal-history/', views.goal_history, name='GoalHistory'),
    path('favorite/', views.mark_favorite, name='FavoriteHistory'),
    path('progress/', views.progress_view, name='progress'),
]
