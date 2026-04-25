from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
class Book(models.Model):
    """Book model - must be defined first"""
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='book_images/', blank=True, null=True)
    seller_name = models.CharField(max_length=200, blank=True, null=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='books')
    category = models.CharField(max_length=100, blank=True, null=True)
    language = models.CharField(max_length=50, default='English')
    isbn = models.CharField(max_length=20, blank=True, null=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # ========== STOCK MANAGEMENT FIELDS (ADD THESE) ==========
    stock = models.PositiveIntegerField(default=0, help_text="Number of copies available for sale")
    low_stock_threshold = models.PositiveIntegerField(default=5, help_text="Alert when stock falls below this number")
    is_active = models.BooleanField(default=True, help_text="Book is available for sale")
    
    updated_at = models.DateTimeField(auto_now=True)
    total_sales = models.IntegerField(default=0)
    monthly_sales = models.IntegerField(default=0)
    weekly_sales = models.IntegerField(default=0)
    is_bestseller = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    # ========== STOCK HELPER METHODS ==========
    @property
    def is_in_stock(self):
        """Check if book is in stock"""
        return self.stock > 0 and self.is_active
    
    @property
    def is_low_stock(self):
        """Check if stock is low (below threshold)"""
        return self.stock <= self.low_stock_threshold and self.stock > 0 and self.is_active
    
    @property
    def stock_status(self):
        """Get stock status as string"""
        if not self.is_active:
            return 'inactive'
        elif self.stock <= 0:
            return 'out_of_stock'
        elif self.stock <= self.low_stock_threshold:
            return 'low_stock'
        else:
            return 'in_stock'
    
    @property
    def stock_status_display(self):
        """Get stock status with icon and color for display"""
        statuses = {
            'inactive': {'text': 'Inactive', 'icon': 'fa-ban', 'color': '#94a3b8', 'bg': '#f1f5f9'},
            'out_of_stock': {'text': 'Out of Stock', 'icon': 'fa-times-circle', 'color': '#c62828', 'bg': '#ffebee'},
            'low_stock': {'text': f'Low Stock ({self.stock} left)', 'icon': 'fa-exclamation-triangle', 'color': '#ef6c00', 'bg': '#fff3e0'},
            'in_stock': {'text': f'In Stock ({self.stock} copies)', 'icon': 'fa-check-circle', 'color': '#2e7d32', 'bg': '#e8f5e9'}
        }
        return statuses.get(self.stock_status, statuses['out_of_stock'])
    
    def reduce_stock(self, quantity):
        """Reduce stock when an order is placed"""
        if self.stock >= quantity:
            self.stock -= quantity
            self.save()
            return True
        return False
    
    def increase_stock(self, quantity):
        """Increase stock when restocking"""
        self.stock += quantity
        self.save()
    
    def update_sales_stats(self, quantity):
        """Update sales statistics"""
        self.total_sales += quantity
        self.monthly_sales += quantity
        self.weekly_sales += quantity
        
        # Update bestseller status (more than 50 copies sold)
        if self.total_sales >= 50:
            self.is_bestseller = True
        
        self.save()
    
    def average_rating(self):
        """Calculate average rating from all reviews"""
        reviews = self.reviews.all()
        if reviews:
            total = sum(review.rating for review in reviews)
            return round(total / reviews.count(), 1)
        return 0
    
    def review_count(self):
        """Get total number of reviews"""
        return self.reviews.count()


class Cart(models.Model):
    """Cart model - references Book model"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'book']
    
    def __str__(self):
        return f"{self.user.username} - {self.book.title}"


class Address(models.Model):
    """Address model for user saved addresses"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.city}"


class Review(models.Model):
    """Review model for book ratings and comments"""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['book', 'user']  # One review per user per book
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.book.title} - {self.rating} stars"
    
def average_rating(self):
    reviews = self.reviews.all()
    if reviews:
        return sum(review.rating for review in reviews) / reviews.count()
    return 0
def review_count(self):
    return self.reviews.count()

class BookImage(models.Model):
    """Additional images for a book"""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='extra_images')
    image = models.ImageField(upload_to='book_images/')
    caption = models.CharField(max_length=200, blank=True, help_text="Optional caption for the image")
    is_featured = models.BooleanField(default=False, help_text="Set as featured image (overrides main book image)")
    order = models.PositiveIntegerField(default=0, help_text="Order to display images")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"Image for {self.book.title}"
    
    def delete(self, *args, **kwargs):
        # Delete the image file from storage when model instance is deleted
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)