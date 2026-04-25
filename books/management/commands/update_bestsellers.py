from django.core.management.base import BaseCommand
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from books.models import Book
from orders.models import Order

class Command(BaseCommand):
    help = 'Update bestseller and new arrival status for books'
    
    def handle(self, *args, **options):
        self.stdout.write('Updating book statuses...')
        
        # Update total_sales first
        self.stdout.write('\n📊 Updating total sales...')
        for book in Book.objects.all():
            total_sold = Order.objects.filter(
                Q(book=book) | Q(items__book=book),  # Handle both direct and through OrderItem
                status__in=['Delivered', 'Completed', 'COMPLETED']
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            if hasattr(book, 'items'):
                # If using OrderItem
                from orders.models import OrderItem
                total_sold = OrderItem.objects.filter(
                    book=book,
                    order__status__in=['Delivered', 'Completed', 'COMPLETED']
                ).aggregate(total=Sum('quantity'))['total'] or 0
            
            book.total_sales = total_sold
            book.save(update_fields=['total_sales'])
        
        self.stdout.write(self.style.SUCCESS('✓ Total sales updated'))
        
        # Update bestsellers (top 10 selling books of all time)
        self.stdout.write('\n⭐ Updating bestsellers...')
        top_books = Book.objects.filter(total_sales__gt=0).order_by('-total_sales')[:10]
        
        # Reset all bestseller flags
        Book.objects.all().update(is_bestseller=False)
        
        # Mark new bestsellers
        for book in top_books:
            book.is_bestseller = True
            book.save(update_fields=['is_bestseller'])
            self.stdout.write(f'  ✓ {book.title} - {book.total_sales} sales')
        
        self.stdout.write(self.style.SUCCESS(f'✓ Marked {top_books.count()} bestsellers'))
        
        # Update new arrivals (books added in last 30 days)
        self.stdout.write('\n🆕 Updating new arrivals...')
        recent_date = timezone.now() - timedelta(days=30)
        
        # Reset all new arrival flags
        Book.objects.all().update(is_new_arrival=False)
        
        # Mark new arrivals
        new_books = Book.objects.filter(created_at__gte=recent_date)
        new_books.update(is_new_arrival=True)
        
        self.stdout.write(self.style.SUCCESS(f'✓ Marked {new_books.count()} new arrivals'))
        
        # Display summary
        self.stdout.write('\n📊 SUMMARY:')
        self.stdout.write('-' * 50)
        self.stdout.write(f'Total Books: {Book.objects.count()}')
        self.stdout.write(f'Bestsellers: {Book.objects.filter(is_bestseller=True).count()}')
        self.stdout.write(f'New Arrivals: {Book.objects.filter(is_new_arrival=True).count()}')
        
        # Display top 5 bestsellers
        self.stdout.write('\n🏆 TOP 5 BESTSELLERS:')
        for idx, book in enumerate(top_books[:5], 1):
            self.stdout.write(f"{idx}. {book.title} - {book.total_sales} copies sold")
        
        self.stdout.write(self.style.SUCCESS('\n✅ Update completed successfully!'))