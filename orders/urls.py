from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_home, name='order_home'),
    path('place-order/<int:book_id>/', views.place_order, name='place_order'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),  # Add this line
    path('payment/<int:book_id>/', views.payment_page, name='payment_page'),
    path('order-success/<int:book_id>/', views.order_success, name='order_success'),
    path('payment-success/<int:book_id>/', views.payment_success, name='payment_success'),
    path('save-order/', views.save_order, name='save_order'),
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('track-order/<int:order_id>/', views.track_order, name='track_order'),
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
]