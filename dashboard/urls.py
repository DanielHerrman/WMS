from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('login/', LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='/dashboard/login/'), name='logout'),
    path('', views.client_dashboard, name='client_dashboard'),
    path('zakazka/<int:pk>/', views.manufacturing_detail, name='manufacturing_detail'),
]