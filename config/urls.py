from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path
from guilds import views,discord_auth
urlpatterns=[path('healthz/',views.health),path('recover/',views.recover),path('events/shared/<uuid:token>/',views.ally_event),path('onboard/',views.onboard),path('auth/discord/',discord_auth.begin),path('auth/discord/callback/',discord_auth.callback),path('',views.index),path('login/',auth.LoginView.as_view()),path('logout/',auth.LogoutView.as_view()),path('admin/',admin.site.urls),path('api/<int:guild_id>/state/',views.state),path('api/<int:guild_id>/<str:module>/<str:name>/',views.action),path('ocr/<int:guild_id>/',views.ocr_view),path('recap/<uuid:token>/',views.recap)]
