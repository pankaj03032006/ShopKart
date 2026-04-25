from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'books'
urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Book URLs - FIXED: using book_id instead of id
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('add-book/', views.add_book, name='add_book'),
    path('edit/<int:book_id>/', views.edit_book, name='edit_book'),
    path('delete-book/<int:id>/', views.delete_book, name='delete_book'),
    path('toggle-status/<int:book_id>/', views.toggle_book_status, name='toggle_book_status'),
    
    # Order URLs
    path('order-success/', views.order_success, name='order_success'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('order/<int:book_id>/', views.place_order, name='place_order'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('pay/<int:book_id>/', views.payment_page, name='payment'),
    path('payment-success/<int:book_id>/', views.payment_success, name='payment_success'),
    path('update-order/<int:order_id>/', views.update_order_status, name='update_order_status'),
    
    # Cart URLs
    path('add-to-cart/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('increase/<int:id>/', views.increase_quantity, name='increase_quantity'),
    path('decrease/<int:id>/', views.decrease_quantity, name='decrease_quantity'),
    path('remove-from-cart/<int:id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:book_id>/<str:action>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('get-cart-count/', views.get_cart_count, name='get_cart_count'),
    
    # Auth URL
    path('logout/', auth_views.LogoutView.as_view(next_page='books:home'), name='logout'),
    
    # Seller URLs
    path('sell-book/', views.sell_book, name='sell_book'),
    
    # Address URLs
    path('saved-addresses/', views.saved_addresses, name='saved_addresses'),
    path('add-address/', views.add_address, name='add_address'),
    path('edit-address/<int:address_id>/', views.edit_address, name='edit_address'),
    path('delete-address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('set-default-address/<int:address_id>/', views.set_default_address, name='set_default_address'),
    path('get-addresses/', views.get_addresses, name='get_addresses'),
    
    # Review URLs
    path('add-review/<int:book_id>/', views.add_review, name='add_review'),
    path('delete-review/<int:review_id>/', views.delete_review, name='delete_review'),
    
    # Utility URLs
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('check-auth/', views.check_auth, name='check_auth'),
    
    # Image Management URLs
    path('books/upload-images/', views.upload_book_images, name='upload_book_images'),
    path('books/delete-image/<int:image_id>/', views.delete_book_image, name='delete_book_image'),
    path('books/reorder-images/', views.reorder_images, name='reorder_images'),
    path('toggle-status/<int:book_id>/', views.toggle_book_status, name='toggle_book_status'),
    path('update-stock/<int:book_id>/', views.update_book_stock, name='update_book_stock'),
]