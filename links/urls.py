from django.urls import path 
from . import views
from .views import get_links_data
from .views import download_qr
 

urlpatterns = [
    path('design/',views.design,name='design'),
    path('auth/register/',views.register_view,name='register'),
    path('auth/login/',views.login_view,name='login'),
    path('auth/logout/',views.logout_view,name='logout'),
    path('',views.dashboard_view,name='dashboard'),
    path('dashboard/',views.dashboard_view,name='dashboard'),
    path('create_link/', views.create_link, name='create_link'),
    path('<str:short_code>/', views.redirect_view, name='redirect_view'),
    path('get-links-data/<str:short_code>/', views.get_links_data, name='get_links_data'),
    path('download-qr/<str:short_code>/<str:format>/', download_qr, name='download_qr'),
    path('generate-qr/<str:short_code>/', views.generate_qr, name='generate_qr'),
    path('delete-link/<str:short_code>/', views.delete_link, name='delete_link'),
]