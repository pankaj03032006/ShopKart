from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from books.models import Book
from datetime import datetime, timedelta
import random
import string

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='orders')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='orders')
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    recipient_name = models.CharField(max_length=100, default='')
    payment_id = models.CharField(max_length=200, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=50, default='Pending', choices=STATUS_CHOICES)
    tracking_id = models.CharField(max_length=100, blank=True, null=True)
    estimated_delivery = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """Override save to generate tracking ID and estimated delivery for new orders"""
        if not self.tracking_id and self.id is None:
            self.tracking_id = self.generate_tracking_id()
            self.set_estimated_delivery()
        super().save(*args, **kwargs)
    
    def update_book_sales(self):
        """Update book sales statistics"""
        if self.status == 'Delivered':
            # Update total sales
            self.book.total_sales += self.quantity
            
            # Update monthly sales (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            self.book.monthly_sales = Order.objects.filter(
                book=self.book,
                status='Delivered',
                created_at__gte=thirty_days_ago
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            # Update weekly sales (last 7 days)
            seven_days_ago = timezone.now() - timedelta(days=7)
            self.book.weekly_sales = Order.objects.filter(
                book=self.book,
                status='Delivered',
                created_at__gte=seven_days_ago
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            self.book.save()
    
    def __str__(self):
        return f"Order #{self.id} - {self.book.title}"
    
    @property
    def is_reviewed(self):
        """Check if the user has already reviewed this book"""
        from books.models import Review
        return Review.objects.filter(book=self.book, user=self.user).exists()
    
    def get_status_icon(self):
        """Get icon for current status"""
        icons = {
            'Pending': 'fa-clock',
            'Processing': 'fa-cog',
            'Shipped': 'fa-truck',
            'Out for Delivery': 'fa-truck-fast',
            'Delivered': 'fa-check-circle',
            'Cancelled': 'fa-ban'
        }
        return icons.get(self.status, 'fa-question-circle')
    
    def get_status_color(self):
        """Get color for current status"""
        colors = {
            'Pending': '#ef6c00',
            'Processing': '#1565c0',
            'Shipped': '#7b1fa2',
            'Out for Delivery': '#ff9800',
            'Delivered': '#2e7d32',
            'Cancelled': '#c62828'
        }
        return colors.get(self.status, '#5b6e7c')
    
    def generate_tracking_id(self):
        """Generate a unique tracking ID"""
        prefix = 'SHOP'
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"{prefix}{random_part}"
    
    def set_estimated_delivery(self):
        """Set estimated delivery date (7 days from now)"""
        self.estimated_delivery = datetime.now().date() + timedelta(days=7)
    
    def get_timeline_steps(self):
        """Get timeline steps for tracking"""
        steps = [
            {'status': 'Pending', 'icon': 'fa-clock', 'description': 'Order placed and waiting for confirmation'},
            {'status': 'Processing', 'icon': 'fa-cog', 'description': 'Order is being processed'},
            {'status': 'Shipped', 'icon': 'fa-truck', 'description': 'Order has been shipped'},
            {'status': 'Out for Delivery', 'icon': 'fa-truck-fast', 'description': 'Order is out for delivery'},
            {'status': 'Delivered', 'icon': 'fa-check-circle', 'description': 'Order has been delivered'},
        ]
        return steps
    
    def get_current_step(self):
        """Get current step index for tracking timeline"""
        steps = ['Pending', 'Processing', 'Shipped', 'Out for Delivery', 'Delivered']
        if self.status == 'Cancelled':
            return -1
        try:
            return steps.index(self.status)
        except ValueError:
            return 0
    
    @property
    def payment_method(self):
        """Get payment method"""
        if self.payment_id:
            return 'Online'
        return 'COD'