from django.contrib import admin
from django.urls import path
from screening import views
from screening.ocr_views import ocr
from screening.batch_views import screen_batch

urlpatterns = [path('admin/', admin.site.urls), path('api/session/', views.session), path('api/login/', views.login_view), path('api/logout/', views.logout_view), path('api/catalogue/', views.catalogue), path('api/rules/', views.rules), path('api/rules/<int:pk>/', views.rule_detail), path('api/screen/', views.screen), path('api/history/', views.history)]
urlpatterns += [path('api/ocr/', ocr)]
urlpatterns += [path('api/screen-batch/', screen_batch)]
