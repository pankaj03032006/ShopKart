from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Avg
from .models import Book, Cart, Address, BookImage, Review
from orders.models import Order
from accounts.models import Seller
from .forms import BookForm
import json
import razorpay
from django.contrib.admin.views.decorators import staff_member_required 
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from django.conf import settings


# ==================== HOME VIEW ====================
def home(request):
    query = request.GET.get('q')
    category = request.GET.get('category')
    sort = request.GET.get('sort')

    books = Book.objects.all()

    # SEARCH
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query)
        )

    # CATEGORY FILTER
    if category:
        books = books.filter(category=category)

    # SORTING
    if sort == 'low':
        books = books.order_by('price')
    elif sort == 'high':
        books = books.order_by('-price')

    return render(request, 'books/home.html', {'books': books})


# ==================== BOOK DETAIL VIEW ====================
def book_detail(request, book_id):
    """Display book details with multiple images"""
    
    # Get the book
    book = get_object_or_404(Book, id=book_id)
    
    # Calculate savings for the book
    if book.mrp and book.price and book.mrp > book.price:
        book.savings = book.mrp - book.price
    else:
        book.savings = 0
    
    # Get extra images for the book
    extra_images = book.extra_images.all()
    
    # Get reviews
    reviews = Review.objects.filter(book=book).order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    review_count = reviews.count()
    
    # Check if user has purchased this book (for review eligibility)
    has_purchased = False
    existing_review = None
    
    if request.user.is_authenticated:
        # Check if user has purchased this book
        try:
            from orders.models import OrderItem
            has_purchased = OrderItem.objects.filter(
                order__user=request.user,
                order__status='Delivered',
                book=book
            ).exists()
        except ImportError:
            has_purchased = False
        
        # Check if user already reviewed
        existing_review = Review.objects.filter(book=book, user=request.user).first()
    
    # Get related books (same category)
    related_books = Book.objects.filter(
        category=book.category,
        is_active=True
    ).exclude(id=book.id)[:8]
    
    context = {
        'book': book,
        'extra_images': extra_images,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'review_count': review_count,
        'has_purchased': has_purchased,
        'existing_review': existing_review,
        'related_books': related_books,
    }
    
    return render(request, 'books/book_detail.html', context)


# ==================== ADD BOOK VIEW ====================
@login_required
def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.seller = request.user
            book.save()
            return redirect('books:home')
    else:
        form = BookForm()

    return render(request, 'books/add_book.html', {'form': form})


# ==================== SELL BOOK VIEW (WITH MULTIPLE IMAGES) ====================
def seller_login_required(view_func):
    """Custom decorator that redirects to seller login page"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.urls import reverse
            next_url = request.get_full_path()
            return redirect(f"{reverse('accounts:seller_login')}?next={next_url}")
        return view_func(request, *args, **kwargs)
    return wrapper


@seller_login_required
def sell_book(request):
    """View for sellers to add new books to their inventory with multiple images"""
    try:
        seller = Seller.objects.get(user=request.user)
    except Seller.DoesNotExist:
        messages.error(request, 'Please register as a seller first')
        return redirect('accounts:seller_signup')
    
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title', '').strip()
            author = request.POST.get('author', '').strip()
            price = request.POST.get('price', '').strip()
            category = request.POST.get('category', '')
            description = request.POST.get('description', '').strip()
            image = request.FILES.get('image')
            stock = request.POST.get('stock', 0)
            language = request.POST.get('language', 'English')
            isbn = request.POST.get('isbn', '')
            mrp = request.POST.get('mrp', '')
            low_stock_threshold = request.POST.get('low_stock_threshold', 5)
            
            # Validation
            if not title:
                messages.error(request, 'Book title is required')
                return render(request, 'books/sell_book.html')
            
            if not author:
                messages.error(request, 'Author name is required')
                return render(request, 'books/sell_book.html')
            
            if not price:
                messages.error(request, 'Price is required')
                return render(request, 'books/sell_book.html')
            
            try:
                price = float(price)
                if price <= 0:
                    messages.error(request, 'Price must be greater than 0')
                    return render(request, 'books/sell_book.html')
            except ValueError:
                messages.error(request, 'Please enter a valid price')
                return render(request, 'books/sell_book.html')
            
            if not image:
                messages.error(request, 'Book image is required')
                return render(request, 'books/sell_book.html')
            
            # Validate stock
            try:
                stock = int(stock)
                if stock < 0:
                    stock = 0
            except ValueError:
                stock = 0
            
            # Validate low_stock_threshold
            try:
                low_stock_threshold = int(low_stock_threshold)
                if low_stock_threshold < 1:
                    low_stock_threshold = 5
            except ValueError:
                low_stock_threshold = 5
            
            # Create the book with stock
            book = Book.objects.create(
                title=title,
                author=author,
                price=price,
                category=category,
                description=description,
                image=image,
                seller=request.user,
                seller_name=request.user.get_full_name() or request.user.username,
                stock=stock,
                language=language,
                isbn=isbn,
                mrp=float(mrp) if mrp else None,
                low_stock_threshold=low_stock_threshold,
                is_active=True
            )
            
            # Handle extra images
            extra_images = request.FILES.getlist('extra_images')
            for extra_image in extra_images:
                if extra_image and extra_image.size <= 5 * 1024 * 1024:
                    BookImage.objects.create(
                        book=book,
                        image=extra_image,
                        caption=f"{title} - Additional image"
                    )
            
            messages.success(request, f'"{title}" has been successfully added to your store!')
            return redirect('accounts:seller_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error uploading book: {str(e)}')
            return render(request, 'books/sell_book.html')
    
    return render(request, 'books/sell_book.html')


# ==================== EDIT BOOK VIEW ====================
@login_required
def edit_book(request, book_id):
    """Edit book details"""
    try:
        book = Book.objects.get(id=book_id, seller=request.user)
    except Book.DoesNotExist:
        messages.error(request, 'Book not found or you do not have permission to edit it.')
        return redirect('accounts:seller_dashboard')
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title', '').strip()
            author = request.POST.get('author', '').strip()
            price = request.POST.get('price', '').strip()
            category = request.POST.get('category', '')
            description = request.POST.get('description', '').strip()
            stock = request.POST.get('stock', 0)
            is_active = request.POST.get('is_active') == 'on'
            language = request.POST.get('language', 'English')
            isbn = request.POST.get('isbn', '')
            mrp = request.POST.get('mrp', '')
            low_stock_threshold = request.POST.get('low_stock_threshold', 5)
            image = request.FILES.get('image')
            
            if not title or not author or not price:
                messages.error(request, 'Please fill all required fields')
                return render(request, 'books/edit_book.html', {'book': book})
            
            book.title = title
            book.author = author
            book.price = float(price)
            book.category = category
            book.description = description
            book.stock = int(stock) if stock else 0
            book.is_active = is_active
            book.language = language
            book.isbn = isbn
            book.low_stock_threshold = int(low_stock_threshold) if low_stock_threshold else 5
            
            if mrp:
                book.mrp = float(mrp)
            
            if image:
                book.image = image
            
            book.save()
            
            messages.success(request, f'"{title}" has been updated successfully!')
            return redirect('accounts:seller_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error updating book: {str(e)}')
            return render(request, 'books/edit_book.html', {'book': book})
    
    return render(request, 'books/edit_book.html', {'book': book})


# ==================== DELETE BOOK VIEW ====================
@login_required
def delete_book(request, id):
    """Delete a book - only the seller can delete their own books"""
    try:
        book = get_object_or_404(Book, id=id)
        
        if book.seller != request.user:
            messages.error(request, 'You are not authorized to delete this book')
            return redirect('accounts:seller_dashboard')
        
        book_title = book.title
        book.delete()
        messages.success(request, f'"{book_title}" has been deleted successfully!')
        
    except Book.DoesNotExist:
        messages.error(request, 'Book not found')
    except Exception as e:
        messages.error(request, f'Error deleting book: {str(e)}')
    
    return redirect('accounts:seller_dashboard')


# ==================== TOGGLE BOOK STATUS ====================
@login_required
def toggle_book_status(request, book_id):
    """Toggle book active/inactive status"""
    if request.method == 'POST':
        try:
            book = Book.objects.get(id=book_id, seller=request.user)
            book.is_active = not book.is_active
            book.save()
            
            status = "activated" if book.is_active else "deactivated"
            return JsonResponse({'success': True, 'message': f'Book {status} successfully!'})
        except Book.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Book not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


# ==================== IMAGE MANAGEMENT VIEWS ====================
@login_required
def upload_book_images(request):
    """Upload multiple images for a book"""
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        try:
            book = Book.objects.get(id=book_id)
            
            # Check if user is seller or admin
            if request.user != book.seller and not request.user.is_superuser:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            images = request.FILES.getlist('images')
            if not images:
                return JsonResponse({'error': 'No images provided'}, status=400)
            
            uploaded_images = []
            for index, image in enumerate(images):
                # Check file size (max 5MB)
                if image.size > 5 * 1024 * 1024:
                    continue
                
                # Check file type
                if not image.content_type.startswith('image/'):
                    continue
                
                book_image = BookImage.objects.create(
                    book=book,
                    image=image,
                    caption=f"{book.title} - Image {book.extra_images.count() + 1}",
                    order=book.extra_images.count()
                )
                uploaded_images.append({
                    'id': book_image.id,
                    'url': book_image.image.url,
                    'caption': book_image.caption
                })
            
            if uploaded_images:
                return JsonResponse({
                    'success': True,
                    'images': uploaded_images,
                    'message': f'{len(uploaded_images)} images uploaded successfully'
                })
            else:
                return JsonResponse({'error': 'No valid images uploaded'}, status=400)
                
        except Book.DoesNotExist:
            return JsonResponse({'error': 'Book not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def delete_book_image(request, image_id):
    """Delete a book image"""
    if request.method == 'POST':
        try:
            image = BookImage.objects.get(id=image_id)
            
            # Check if user is seller or admin
            if request.user != image.book.seller and not request.user.is_superuser:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            image.delete()
            
            # Reorder remaining images
            remaining_images = image.book.extra_images.all()
            for idx, img in enumerate(remaining_images):
                img.order = idx
                img.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Image deleted successfully'
            })
        except BookImage.DoesNotExist:
            return JsonResponse({'error': 'Image not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def reorder_images(request):
    """Reorder book images"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_ids = data.get('image_ids', [])
            
            for order, image_id in enumerate(image_ids):
                image = BookImage.objects.get(id=image_id)
                # Check permission
                if request.user != image.book.seller and not request.user.is_superuser:
                    continue
                image.order = order
                image.save()
            
            return JsonResponse({'success': True, 'message': 'Images reordered successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


# ==================== ORDER VIEWS ====================
@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-id')
    return render(request, 'books/my_orders.html', {'orders': orders})


@login_required
def place_order(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    if request.method == 'POST':
        address = request.POST.get('address')
        phone = request.POST.get('phone')

        order = Order.objects.create(
            user=request.user,
            book=book,
            address=address,
            phone=phone
        )

        return redirect('order_success', order_id=order.id)

    return render(request, 'orders/place_order.html', {'book': book})


@login_required
def order_success(request, order_id):
    order = Order.objects.get(id=order_id)
    return render(request, 'orders/order_success.html', {'order': order})


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status != 'Delivered':
        order.status = 'Cancelled'
        order.save()

    return redirect('my_orders')


@login_required
def update_order_status(request, order_id):
    order = Order.objects.get(id=order_id)

    if order.book.seller != request.user:
        return redirect('books:home')

    if request.method == 'POST':
        status = request.POST.get('status')
        order.status = status
        order.save()

    return redirect('seller_dashboard')


# ==================== PAYMENT VIEWS ====================
def payment_page(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    payment = client.order.create({
        "amount": int(book.price * 100),
        "currency": "INR",
        "payment_capture": 1
    })

    return render(request, 'books/payment.html', {
        'book': book,
        'payment': payment,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID
    })


@login_required
def payment_success(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    payment_id = request.GET.get('payment_id')
    order_id = request.GET.get('order_id')
    signature = request.GET.get('signature')
    
    order = Order.objects.filter(razorpay_order_id=order_id).first()
    
    if not order:
        order = Order.objects.create(
            user=request.user,
            book=book,
            quantity=1,
            price=book.price,
            address=request.session.get('delivery_address', 'Address not provided'),
            phone=request.session.get('delivery_phone', 'Not provided'),
            recipient_name=request.session.get('delivery_name', request.user.username),
            payment_id=payment_id,
            razorpay_order_id=order_id,
            status='Processing'
        )
    else:
        order.payment_id = payment_id
        order.status = 'Processing'
        order.save()
    
    context = {
        'book': book,
        'order': order,
        'payment_id': payment_id,
    }
    
    return render(request, 'books/payment_success.html', context)


# ==================== CART VIEWS (SESSION-BASED) ====================
def add_to_cart(request, book_id):
    """Add a book to cart using session"""
    book = get_object_or_404(Book, id=book_id)
    
    cart = request.session.get('cart', {})
    
    if isinstance(cart, list):
        cart = {}
    
    book_id_str = str(book_id)
    if book_id_str in cart:
        cart[book_id_str] += 1
    else:
        cart[book_id_str] = 1
    
    request.session['cart'] = cart
    request.session.modified = True
    
    cart_count = sum(cart.values())
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'{book.title} added to cart!',
            'cart_count': cart_count,
            'quantity': cart[book_id_str]
        })
    else:
        messages.success(request, f'{book.title} added to cart successfully!')
        return redirect('books:cart')


def cart_view(request):
    """Display cart page using session"""
    cart = request.session.get('cart', {})
    
    if isinstance(cart, list):
        cart = {}
    
    cart_items = []
    total = 0
    
    for book_id, quantity in cart.items():
        try:
            book = Book.objects.get(id=book_id)
            subtotal = book.price * quantity
            total += subtotal
            cart_items.append({
                'book': book,
                'quantity': quantity,
                'subtotal': subtotal
            })
        except Book.DoesNotExist:
            del cart[book_id]
            request.session['cart'] = cart
            continue
    
    return render(request, 'books/cart.html', {
        'cart_items': cart_items,
        'total': total
    })


def update_cart_quantity(request, book_id, action):
    """Update cart quantity via AJAX using session"""
    if request.method == 'POST':
        try:
            cart = request.session.get('cart', {})
            
            if isinstance(cart, list):
                cart = {}
            
            book_id_str = str(book_id)
            
            if action == 'increase':
                if book_id_str in cart:
                    cart[book_id_str] += 1
                else:
                    cart[book_id_str] = 1
                    
            elif action == 'decrease':
                if book_id_str in cart:
                    cart[book_id_str] -= 1
                    if cart[book_id_str] <= 0:
                        del cart[book_id_str]
            
            request.session['cart'] = cart
            request.session.modified = True
            
            book = get_object_or_404(Book, id=book_id)
            new_total = 0
            for bid, qty in cart.items():
                try:
                    b = Book.objects.get(id=bid)
                    new_total += b.price * qty
                except:
                    pass
            
            cart_count = sum(cart.values())
            
            if book_id_str in cart:
                item_total = book.price * cart[book_id_str]
                return JsonResponse({
                    'success': True,
                    'deleted': False,
                    'new_quantity': cart[book_id_str],
                    'item_total': item_total,
                    'subtotal': new_total,
                    'cart_count': cart_count
                })
            else:
                return JsonResponse({
                    'success': True,
                    'deleted': True,
                    'subtotal': new_total,
                    'cart_count': cart_count
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


def remove_from_cart(request, id):
    """Remove item from cart using session"""
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        
        if isinstance(cart, list):
            cart = {}
        
        if str(id) in cart:
            del cart[str(id)]
        
        request.session['cart'] = cart
        request.session.modified = True
        
        new_total = 0
        for book_id, quantity in cart.items():
            try:
                book = Book.objects.get(id=book_id)
                new_total += book.price * quantity
            except:
                pass
        
        cart_count = sum(cart.values())
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'cart_count': cart_count,
                'subtotal': new_total
            })
        
        messages.success(request, 'Item removed from cart')
        return redirect('books:cart')
    
    return redirect('books:cart')


def get_cart_count(request):
    """Get cart count for AJAX requests using session"""
    cart = request.session.get('cart', {})
    
    if isinstance(cart, list):
        cart = {}
    
    count = sum(cart.values())
    return JsonResponse({'success': True, 'count': count})


def increase_quantity(request, id):
    """Increase item quantity in cart"""
    cart = request.session.get('cart', {})
    book_id_str = str(id)
    
    if book_id_str in cart:
        cart[book_id_str] += 1
    
    request.session['cart'] = cart
    request.session.modified = True
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        book = get_object_or_404(Book, id=id)
        new_total = 0
        for bid, qty in cart.items():
            try:
                b = Book.objects.get(id=bid)
                new_total += b.price * qty
            except:
                pass
        return JsonResponse({
            'success': True,
            'new_quantity': cart[book_id_str],
            'item_total': book.price * cart[book_id_str],
            'subtotal': new_total,
            'cart_count': sum(cart.values())
        })
    
    return redirect('books:cart')


def decrease_quantity(request, id):
    """Decrease item quantity in cart"""
    cart = request.session.get('cart', {})
    book_id_str = str(id)
    
    if book_id_str in cart:
        cart[book_id_str] -= 1
        if cart[book_id_str] <= 0:
            del cart[book_id_str]
    
    request.session['cart'] = cart
    request.session.modified = True
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        new_total = 0
        for bid, qty in cart.items():
            try:
                b = Book.objects.get(id=bid)
                new_total += b.price * qty
            except:
                pass
        
        if book_id_str in cart:
            book = get_object_or_404(Book, id=id)
            return JsonResponse({
                'success': True,
                'new_quantity': cart[book_id_str],
                'item_total': book.price * cart[book_id_str],
                'subtotal': new_total,
                'cart_count': sum(cart.values()),
                'deleted': False
            })
        else:
            return JsonResponse({
                'success': True,
                'deleted': True,
                'subtotal': new_total,
                'cart_count': sum(cart.values())
            })
    
    return redirect('books:cart')


# ==================== ADDRESS MANAGEMENT VIEWS ====================
@login_required
def saved_addresses(request):
    """Display user's saved addresses"""
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'books/saved_addresses.html', {'addresses': addresses})


@login_required
def add_address(request):
    """Add a new address via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            is_first = not Address.objects.filter(user=request.user).exists()
            
            address = Address.objects.create(
                user=request.user,
                name=data.get('name'),
                address=data.get('address'),
                city=data.get('city'),
                state=data.get('state'),
                pincode=data.get('pincode'),
                phone=data.get('phone'),
                email=data.get('email', ''),
                is_default=is_first
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Address saved successfully!',
                'address': {
                    'id': address.id,
                    'name': address.name,
                    'address': address.address,
                    'city': address.city,
                    'state': address.state,
                    'pincode': address.pincode,
                    'phone': address.phone,
                    'email': address.email,
                    'is_default': address.is_default
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def edit_address(request, address_id):
    """Edit an existing address"""
    if request.method == 'POST':
        try:
            address = get_object_or_404(Address, id=address_id, user=request.user)
            data = json.loads(request.body)
            
            address.name = data.get('name', address.name)
            address.address = data.get('address', address.address)
            address.city = data.get('city', address.city)
            address.state = data.get('state', address.state)
            address.pincode = data.get('pincode', address.pincode)
            address.phone = data.get('phone', address.phone)
            address.email = data.get('email', address.email)
            address.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Address updated successfully!'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def delete_address(request, address_id):
    """Delete an address"""
    if request.method == 'POST':
        try:
            address = get_object_or_404(Address, id=address_id, user=request.user)
            address.delete()
            return JsonResponse({'success': True, 'message': 'Address deleted successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def set_default_address(request, address_id):
    """Set an address as default"""
    if request.method == 'POST':
        try:
            Address.objects.filter(user=request.user).update(is_default=False)
            
            address = get_object_or_404(Address, id=address_id, user=request.user)
            address.is_default = True
            address.save()
            
            return JsonResponse({'success': True, 'message': 'Default address updated!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def get_addresses(request):
    """Get all addresses for the current user (AJAX)"""
    addresses = Address.objects.filter(user=request.user)
    addresses_data = []
    for addr in addresses:
        addresses_data.append({
            'id': addr.id,
            'name': addr.name,
            'address': addr.address,
            'city': addr.city,
            'state': addr.state,
            'pincode': addr.pincode,
            'phone': addr.phone,
            'email': addr.email,
            'is_default': addr.is_default
        })
    return JsonResponse({'success': True, 'addresses': addresses_data})


# ==================== REVIEW VIEWS ====================
@login_required
def add_review(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    has_purchased = Order.objects.filter(
        user=request.user,
        book=book,
        status='Delivered'
    ).exists()
    
    if not has_purchased:
        messages.error(request, 'You can only review books you have purchased and received.')
        return redirect('books:book_detail', book_id=book_id)
    
    existing_review = Review.objects.filter(book=book, user=request.user).first()
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        title = request.POST.get('title', '').strip()
        comment = request.POST.get('comment', '').strip()
        
        if not rating:
            messages.error(request, 'Please select a rating')
            return redirect('books:add_review', book_id=book_id)
        
        if not comment:
            messages.error(request, 'Please write a review comment')
            return redirect('books:add_review', book_id=book_id)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                messages.error(request, 'Rating must be between 1 and 5')
                return redirect('books:add_review', book_id=book_id)
        except ValueError:
            messages.error(request, 'Invalid rating value')
            return redirect('books:add_review', book_id=book_id)
        
        if existing_review:
            existing_review.rating = rating
            existing_review.title = title
            existing_review.comment = comment
            existing_review.save()
            messages.success(request, 'Your review has been updated successfully!')
        else:
            Review.objects.create(
                book=book,
                user=request.user,
                rating=rating,
                title=title,
                comment=comment
            )
            messages.success(request, 'Thank you for your review! It has been posted.')
        
        return redirect('books:book_detail', book_id=book_id)
    
    context = {
        'book': book,
        'existing_review': existing_review,
        'has_purchased': has_purchased,
    }
    return render(request, 'books/add_review.html', context)


@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    book_id = review.book.id
    review.delete()
    messages.success(request, 'Your review has been deleted.')
    return redirect('books:book_detail', book_id=book_id)


# ==================== UTILITY VIEWS ====================
def search_suggestions(request):
    query = request.GET.get('q')

    books = Book.objects.filter(
        Q(title__icontains=query) |
        Q(author__icontains=query)
    )[:5]

    data = []
    for book in books:
        data.append({
            'id': book.id,
            'title': book.title
        })

    return JsonResponse(data, safe=False)


def check_auth(request):
    """Check if user is authenticated"""
    return JsonResponse({'is_authenticated': request.user.is_authenticated})

# books/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import Book
import json

@login_required
@require_http_methods(["POST"])
# def toggle_book_status(request, book_id):
#     """Toggle book active/inactive status"""
#     try:
#         book = Book.objects.get(id=book_id, seller=request.user)
#         book.is_active = not book.is_active
#         book.save()
        
#         status = "activated" if book.is_active else "deactivated"
#         return JsonResponse({
#             'success': True,
#             'message': f'Book {status} successfully!',
#             'is_active': book.is_active
#         })
#     except Book.DoesNotExist:
#         return JsonResponse({
#             'success': False,
#             'error': 'Book not found or you do not have permission to edit it.'
#         }, status=404)
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)

@login_required
@require_http_methods(["POST"])
def update_book_stock(request, book_id):
    """Update book stock"""
    try:
        data = json.loads(request.body)
        additional_stock = int(data.get('stock', 0))
        
        if additional_stock <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Please enter a valid number greater than 0'
            }, status=400)
        
        book = Book.objects.get(id=book_id, seller=request.user)
        book.stock += additional_stock
        book.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Added {additional_stock} copies. New stock: {book.stock}',
            'new_stock': book.stock
        })
    except Book.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Book not found or you do not have permission to edit it.'
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
    

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from .models import  Book, Report, SellerVerification, SystemSettings
from orders.models import Order

from datetime import datetime, timedelta

@staff_member_required
def admin_dashboard(request):
    """Main admin dashboard view"""
    context = {
        # User Stats
        'total_users': User.objects.count(),
        'active_sellers': User.objects.filter(role='Seller', is_active=True).count(),
        'active_buyers': User.objects.filter(role='Buyer', is_active=True).count(),
        
        # Book Stats
        'total_books': Book.objects.filter(is_deleted=False).count(),
        'reported_books': Book.objects.filter(is_reported=True).count(),
        'pending_verifications': SellerVerification.objects.filter(status='pending').count(),
        'pending_verifications_list': SellerVerification.objects.filter(status='pending').select_related('seller'),
        
        # Order Stats
        'total_orders': Order.objects.count(),
        'books_sold': Order.objects.filter(status='Delivered').aggregate(Sum('quantity'))['quantity__sum'] or 0,
        'total_revenue': Order.objects.filter(status='Delivered').aggregate(Sum('price'))['price__sum'] or 0,
        
        # Orders list
        'orders': Order.objects.select_related('user', 'book', 'book__seller').order_by('-created_at')[:100],
        
        # Books list
        'books': Book.objects.filter(is_deleted=False).select_related('seller').order_by('-created_at'),
        
        # Users list
        'users': User.objects.all().order_by('-date_joined'),
        
        # Reports list
        'reports': Report.objects.filter(status='pending').select_related('reported_by').order_by('-created_at'),
        
        # System Settings
        'settings': SystemSettings.load(),
        
        # Recent Activity (implement based on your activity logging)
        'recent_activities': [],  # Add your activity model here
        
        # Completion Rate
        'completion_rate': calculate_completion_rate(),
    }
    return render(request, 'admin/dashboard.html', context)

@staff_member_required
def admin_toggle_user_status(request, user_id):
    """Block or unblock a user"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        action = request.POST.get('action')
        
        if action == 'block':
            user.is_active = False
            message = f'User {user.username} has been blocked'
        elif action == 'unblock':
            user.is_active = True
            message = f'User {user.username} has been unblocked'
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        user.save()
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@staff_member_required
def admin_delete_user(request, user_id):
    """Permanently delete a user"""
    if request.method == 'DELETE':
        user = get_object_or_404(User, id=user_id)
        
        # Don't allow deleting yourself
        if user.id == request.user.id:
            return JsonResponse({'error': 'Cannot delete your own account'}, status=400)
        
        username = user.username
        user.delete()
        return JsonResponse({'success': True, 'message': f'User {username} deleted'})
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@staff_member_required
def admin_toggle_book_status(request, book_id):
    """Activate or deactivate a book"""
    if request.method == 'POST':
        book = get_object_or_404(Book, id=book_id)
        action = request.POST.get('action')
        
        if action == 'activate':
            book.is_active = True
            message = f'Book "{book.title}" has been activated'
        elif action == 'deactivate':
            book.is_active = False
            message = f'Book "{book.title}" has been deactivated'
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        book.save()
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@staff_member_required
def admin_delete_book(request, book_id):
    """Permanently delete a book (soft delete with admin override)"""
    if request.method == 'DELETE':
        book = get_object_or_404(Book, id=book_id)
        title = book.title
        book.is_deleted = True  # Soft delete
        book.is_active = False
        book.save()
        return JsonResponse({'success': True, 'message': f'Book "{title}" deleted'})
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@staff_member_required
def admin_update_order_status(request, order_id):
    """Update order status from admin panel"""
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        
        if new_status not in ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        order.status = new_status
        order.save()
        
        return JsonResponse({'success': True, 'message': f'Order #{order_id} status updated to {new_status}'})
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@staff_member_required
def admin_verify_seller(request, verification_id):
    """Approve or reject a seller verification request"""
    if request.method == 'POST':
        verification = get_object_or_404(SellerVerification, id=verification_id)
        action = request.POST.get('action')
        
        if action == 'approve':
            verification.status = 'approved'
            verification.seller.is_verified = True
            verification.seller.save()
            message = f'Seller {verification.seller.username} has been verified'
        elif action == 'reject':
            verification.status = 'rejected'
            message = f'Seller {verification.seller.username} verification rejected'
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        verification.save()
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@staff_member_required
def admin_resolve_report(request, report_id):
    """Resolve a reported item"""
    if request.method == 'POST':
        report = get_object_or_404(Report, id=report_id)
        action = request.POST.get('action')
        
        if action == 'dismiss':
            report.status = 'dismissed'
            message = 'Report dismissed'
        elif action == 'remove':
            report.status = 'resolved'
            # Mark the reported item as inactive
            if report.reported_book:
                report.reported_book.is_active = False
                report.reported_book.save()
            message = 'Reported item has been removed'
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        report.save()
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@staff_member_required
def admin_update_settings(request):
    """Update platform settings"""
    if request.method == 'POST':
        settings = SystemSettings.load()
        
        settings.commission_rate = float(request.POST.get('commission_rate', settings.commission_rate))
        settings.low_stock_threshold = int(request.POST.get('low_stock_threshold', settings.low_stock_threshold))
        settings.cancel_deadline = int(request.POST.get('cancel_deadline', settings.cancel_deadline))
        settings.admin_email = request.POST.get('admin_email', settings.admin_email)
        
        settings.save()
        return JsonResponse({'success': True, 'message': 'Settings updated successfully'})
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

def calculate_completion_rate():
    """Calculate order completion rate"""
    total = Order.objects.count()
    if total == 0:
        return 100
    
    completed = Order.objects.filter(status='Delivered').count()
    return round((completed / total) * 100, 1)