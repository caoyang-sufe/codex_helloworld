"""
URL configuration for webapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from gameapp import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.game, name="home"),
    path("game", views.game, name="game"),
    path("game/", views.game, name="game-slash"),
    path("handbook", views.handbook, name="handbook"),
    path("handbook/", views.handbook, name="handbook-slash"),
    path("api/cards", views.api_cards, name="api-cards"),
    path("api/game/new", views.api_game_new, name="api-game-new"),
    path("api/game/action", views.api_game_action, name="api-game-action"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
