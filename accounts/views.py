from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.db import IntegrityError
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from books.models import Book
from orders.models import Order
from .models import Seller
import re


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email', '')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('/accounts/signup/')
        else:
            User.objects.create_user(username=username, password=password, email=email)
            messages.success(request, "Account created successfully! Please login.")
            return redirect('/accounts/login/')

    return render(request, 'accounts/signup.html')


def customer_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back {user.username}!')
            return redirect('/')  # Changed from 'home' to '/'
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('/accounts/login/')
    
    return render(request, 'accounts/customer_login.html')


def seller_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        fullname = request.POST.get('fullname', '').strip()
        phone = request.POST.get('phone', '').strip()
        shop_name = request.POST.get('shopname', '').strip()
        address = request.POST.get('address', '').strip()
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return redirect('/accounts/seller-signup/')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('/accounts/seller-signup/')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            return redirect('/accounts/seller-signup/')
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=fullname
            )
            
            seller = Seller.objects.create(
                user=user,
                shop_name=shop_name if shop_name else f"{fullname}'s Book Store",
                phone=phone,
                address=address,
                is_approved=True
            )
            
            messages.success(request, 'Seller account created successfully! Please login.')
            return redirect('/accounts/seller-login/')
            
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return redirect('/accounts/seller-signup/')
    
    return render(request, 'accounts/seller_signup.html')


def seller_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            try:
                seller = Seller.objects.get(user=user)
                if seller.is_approved:
                    login(request, user)
                    messages.success(request, f'Welcome back seller {user.username}!')
                    return redirect('/accounts/seller-dashboard/')
                else:
                    messages.warning(request, 'Your seller account is pending approval.')
                    return redirect('/accounts/seller-pending/')
            except Seller.DoesNotExist:
                messages.error(request, 'You are not registered as a seller.')
                return redirect('/accounts/seller-signup/')
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('/accounts/seller-login/')
    
    return render(request, 'accounts/seller_login.html')


# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models  # Add this import
from django.db.models import Sum, Q, F  # You can also import specific aggregations
from books.models import Book
from orders.models import Order  # Adjust this import based on your Order model location
from .models import Seller

# Your existing code...

@login_required
def seller_dashboard(request):
    try:
        seller = Seller.objects.get(user=request.user)
    except Seller.DoesNotExist:
        messages.error(request, 'Please register as a seller first')
        return redirect('accounts:seller_signup')
    
    # Get seller's books
    books = Book.objects.filter(seller=request.user).order_by('-created_at')
    
    # Get orders for seller's books
    orders = Order.objects.filter(book__seller=request.user).order_by('-created_at')
    
    # Calculate statistics
    total_books = books.count()
    total_orders = orders.count()
    total_earnings = orders.filter(status='Delivered').aggregate(total=models.Sum('price'))['total'] or 0
    
    pending_orders = orders.filter(status='Pending').count()
    processing_orders = orders.filter(status='Processing').count()
    shipped_orders = orders.filter(status='Shipped').count()
    delivered_orders = orders.filter(status='Delivered').count()
    cancelled_orders = orders.filter(status='Cancelled').count()
    
    # Stock statistics
    in_stock_books = books.filter(stock__gt=0, is_active=True).count()
    low_stock_books = books.filter(stock__lte=models.F('low_stock_threshold'), stock__gt=0, is_active=True).count()
    out_of_stock_books = books.filter(stock=0, is_active=True).count()
    inactive_books = books.filter(is_active=False).count()
    
    # Total stock value (sum of stock quantities)
    total_stock_value = books.aggregate(total=models.Sum('stock'))['total'] or 0
    
    # Low stock alerts (books that need restocking)
    low_stock_alerts = books.filter(
        stock__lte=models.F('low_stock_threshold'), 
        stock__gt=0, 
        is_active=True
    )
    
    context = {
        'books': books,
        'orders': orders,
        'total_books': total_books,
        'total_orders': total_orders,
        'total_earnings': total_earnings,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        'in_stock_books': in_stock_books,
        'low_stock_books': low_stock_books,
        'out_of_stock_books': out_of_stock_books,
        'inactive_books': inactive_books,
        'total_stock_value': total_stock_value,
        'low_stock_alerts': low_stock_alerts,
    }
    
    return render(request, 'accounts/seller_dashboard.html', context)

@login_required
def check_seller_status(request):
    try:
        seller = Seller.objects.get(user=request.user)
        return JsonResponse({
            'has_seller': True,
            'seller_id': seller.id,
            'is_approved': seller.is_approved,
            'shop_name': seller.shop_name
        })
    except Seller.DoesNotExist:
        return JsonResponse({
            'has_seller': False,
            'error': 'No seller profile found'
        })
    
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@require_http_methods(["POST"])
def save_location(request):
    try:
        data = json.loads(request.body)
        location = data.get('location')
        
        # Save to session
        request.session['user_location'] = location
        
        # If user is authenticated, save to database
        if request.user.is_authenticated:
            # Add location field to your UserProfile model if needed
            # request.user.profile.location = location
            # request.user.profile.save()
            pass
        
        return JsonResponse({'success': True, 'location': location})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
    from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@login_required
def change_password(request):
    """View for changing user password"""
    if request.method == 'POST':
        try:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                data = json.loads(request.body)
                current_password = data.get('current_password')
                new_password = data.get('new_password')
                confirm_password = data.get('confirm_password')
            else:
                current_password = request.POST.get('current_password')
                new_password = request.POST.get('new_password')
                confirm_password = request.POST.get('confirm_password')
            
            if not current_password or not new_password or not confirm_password:
                return JsonResponse({'success': False, 'error': 'All fields are required'}, status=400)
            
            if not request.user.check_password(current_password):
                return JsonResponse({'success': False, 'error': 'Current password is incorrect'}, status=400)
            
            if new_password != confirm_password:
                return JsonResponse({'success': False, 'error': 'New passwords do not match'}, status=400)
            
            if len(new_password) < 8:
                return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters long'}, status=400)
            
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            
            return JsonResponse({'success': True, 'message': 'Password changed successfully!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return render(request, 'accounts/change_password.html')