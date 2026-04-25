from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum

# Import your models
from orders.models import Order

@receiver(post_save, sender=Order)
def update_book_sales_on_order(sender, instance, created, **kwargs):
    """Update book total_sales when an order is completed"""
    # Check if order status is completed/delivered and has book relationship
    if hasattr(instance, 'book') and instance.status in ['Delivered', 'Completed', 'COMPLETED']:
        # Calculate total sales for this book
        total_sold = Order.objects.filter(
            book=instance.book,
            status__in=['Delivered', 'Completed', 'COMPLETED']
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Update the book's total_sales field
        instance.book.total_sales = total_sold
        instance.book.save(update_fields=['total_sales'])
        
        # Optional: Print to console for debugging
        print(f"Updated {instance.book.title} total_sales to {total_sold}")