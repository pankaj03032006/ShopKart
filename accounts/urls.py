from django.urls import path
from . import views

urlpatterns = [
    
    path('signup/', views.signup, name='signup'),
    path('login/', views.customer_login, name='login'),
    path('seller-login/', views.seller_login, name='seller_login'),
    path('seller-signup/', views.seller_signup, name='seller_signup'),
    path('seller-dashboard/', views.seller_dashboard, name='seller_dashboard'),
    # path('seller-pending/', views.seller_pending, name='seller_pending'),
    path('check-seller-status/', views.check_seller_status, name='check_seller_status'),
    path('save-location/', views.save_location, name='save_location'),
    path('change-password/', views.change_password, name='change_password'),
]