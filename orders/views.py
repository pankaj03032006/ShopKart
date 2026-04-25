from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def order_home(request):
    return render(request, 'orders/orders.html')


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from books.models import Book
from orders.models import Order
import json

from datetime import datetime, timedelta
import random
import string
from datetime import datetime, timedelta
import random
import string

@login_required
def place_order(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        payment_method = request.POST.get('payment_method', 'online')
        
        if not address or not phone:
            messages.error(request, 'Please provide delivery address and phone number')
            return redirect('place_order', book_id=book_id)
        
        # Generate tracking ID
        tracking_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        
        # Calculate estimated delivery (7 days from now)
        estimated_delivery = datetime.now().date() + timedelta(days=7)
        
        order = Order.objects.create(
            user=request.user,
            book=book,
            quantity=1,
            price=book.price,
            address=address,
            phone=phone,
            recipient_name=name if name else request.user.username,
            status='Pending' if payment_method == 'online' else 'Confirmed',
            tracking_id=tracking_id,
            estimated_delivery=estimated_delivery
        )
        
        request.session['delivery_address'] = address
        request.session['delivery_phone'] = phone
        request.session['delivery_name'] = name if name else request.user.username
        
        if payment_method == 'cod':
            messages.success(request, f'Order #{order.id} placed successfully! You will pay on delivery.')
            return redirect('my_orders')
        else:
            messages.success(request, f'Order #{order.id} created successfully! Please complete payment.')
            return redirect('payment', book_id=book_id)
    
    return render(request, 'orders/place_order.html', {'book': book})
@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, "orders/my_orders.html", {"orders": orders})

from django.shortcuts import get_object_or_404, redirect
from orders.models import Order

# def cancel_order(request, order_id):
#     order = get_object_or_404(Order)

#     order.delete()

#     return redirect('my_orders')
from django.shortcuts import render, get_object_or_404
from .models import Book, Order

def payment_page(request, book_id):
    """Payment page view"""
    book = get_object_or_404(Book, id=book_id)
    return render(request, 'orders/payment.html', {'book': book})

def order_success(request, book_id):
    """Order success page after COD"""
    book = get_object_or_404(Book, id=book_id)
    return render(request, 'orders/order_success.html', {'book': book})

def payment_success(request, book_id):
    """Payment success page after online payment"""
    book = get_object_or_404(Book, id=book_id)
    return render(request, 'books/payment_success.html', {'book': book})

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Order, Book
import json


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from orders.models import Order
from books.models import Book
import json

@csrf_exempt
@login_required
def save_order(request):
    """Save order after successful payment"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            book_id = data.get('book_id')
            payment_id = data.get('payment_id')
            order_id = data.get('order_id')
            address = data.get('address')
            phone = data.get('phone')
            recipient_name = data.get('recipient_name', '')
            amount = data.get('amount')
            
            book = Book.objects.get(id=book_id)
            
            # Check if order already exists
            existing_order = Order.objects.filter(razorpay_order_id=order_id).first()
            
            if existing_order:
                # Update existing order with payment info
                existing_order.payment_id = payment_id
                existing_order.status = 'Processing'
                existing_order.save()
                order = existing_order
            else:
                # Create new order with all required fields
                order = Order.objects.create(
                    user=request.user,
                    book=book,
                    quantity=1,
                    price=amount if amount else book.price,  # IMPORTANT: Add price
                    address=address or request.session.get('delivery_address', ''),
                    phone=phone or request.session.get('delivery_phone', ''),
                    recipient_name=recipient_name or request.session.get('delivery_name', ''),
                    payment_id=payment_id,
                    razorpay_order_id=order_id,
                    status='Processing'
                )
            
            return JsonResponse({'success': True, 'order_id': order.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from books.models import Book
from .models import Order
import json

@login_required
def cancel_order(request, order_id):
    """Cancel an order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Only allow cancellation if order is not delivered or already cancelled
    if order.status == 'Delivered':
        messages.error(request, 'Cannot cancel a delivered order.')
    elif order.status == 'Cancelled':
        messages.warning(request, 'Order is already cancelled.')
    else:
        order.status = 'Cancelled'
        order.save()
        messages.success(request, f'Order #{order.id} has been cancelled successfully.')
    
    return redirect('my_orders')

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Order
import json

@csrf_exempt
@login_required
def update_order_status(request, order_id):
    """Update order status via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status')
            
            order = Order.objects.get(id=order_id)
            
            # Check if the logged-in user is the seller of this book
            if order.book.seller == request.user:
                order.status = new_status
                order.save()
                return JsonResponse({
                    'success': True, 
                    'message': f'Order status updated to {new_status}',
                    'new_status': new_status
                })
            else:
                return JsonResponse({
                    'success': False, 
                    'error': 'You are not authorized to update this order'
                }, status=403)
                
        except Order.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Order not found'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False, 
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=400)
    
    return JsonResponse({
        'success': False, 
        'error': 'Invalid request method'
    }, status=405)

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Order

@login_required
def track_order(request, order_id):
    """Track order status"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Define order status steps
    status_steps = [
        {'status': 'Pending', 'icon': 'fa-clock', 'description': 'Order placed and waiting for confirmation'},
        {'status': 'Processing', 'icon': 'fa-cog', 'description': 'Order is being processed'},
        {'status': 'Shipped', 'icon': 'fa-truck', 'description': 'Order has been shipped'},
        {'status': 'Out for Delivery', 'icon': 'fa-truck-fast', 'description': 'Order is out for delivery'},
        {'status': 'Delivered', 'icon': 'fa-check-circle', 'description': 'Order has been delivered'},
    ]
    
    # Calculate current step
    current_step = 0
    for i, step in enumerate(status_steps):
        if step['status'] == order.status:
            current_step = i
            break
        elif order.status == 'Cancelled':
            current_step = -1
            break
    
    # Generate tracking timeline
    tracking_updates = [
        {'date': order.created_at, 'status': 'Order Placed', 'description': f'Order #{order.id} was placed successfully'},
    ]
    
    if order.status in ['Processing', 'Shipped', 'Out for Delivery', 'Delivered']:
        tracking_updates.append({'date': order.updated_at, 'status': order.status, 'description': f'Order status updated to {order.status}'})
    
    context = {
        'order': order,
        'status_steps': status_steps,
        'current_step': current_step,
        'tracking_updates': tracking_updates,
    }
    return render(request, 'orders/track_order.html', context)

# orders/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import Order
import json

@login_required
@require_http_methods(["POST"])
def update_order_status(request, order_id):
    """Update order status"""
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        # Validate status
        valid_statuses = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'error': 'Invalid status value'
            }, status=400)
        
        # Get order and verify seller owns the book in the order
        order = Order.objects.get(id=order_id)
        
        # Check if the logged-in user is the seller of the book in this order
        if order.book.seller != request.user:
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to update this order'
            }, status=403)
        
        order.status = new_status
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Order status updated to {new_status}'
        })
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Order not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid data format'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)