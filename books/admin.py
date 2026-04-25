from django.contrib import admin
from .models import Book, BookImage, Cart, Address, Review

class BookImageInline(admin.TabularInline):
    """Inline form for book images"""
    model = BookImage
    extra = 3  # Show 3 empty image fields by default
    fields = ['image', 'caption', 'is_featured', 'order']
    show_change_link = True
    classes = ['collapse']  # Collapsible section
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('order', 'created_at')

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'price', 'seller_name', 'stock', 'stock_status_display', 'category', 'is_active', 'is_bestseller', 'created_at']
    list_filter = ['category', 'created_at', 'is_active', 'is_bestseller', 'language']
    search_fields = ['title', 'author', 'seller_name', 'isbn']
    readonly_fields = ['created_at', 'updated_at', 'total_sales', 'monthly_sales', 'weekly_sales']
    list_editable = ['price', 'stock', 'is_active']
    list_per_page = 25
    
    # Add fieldsets for better organization
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'author', 'description', 'category', 'language', 'isbn')
        }),
        ('Pricing', {
            'fields': ('price', 'mrp', 'seller_name')
        }),
        ('Stock Management', {
            'fields': ('stock', 'low_stock_threshold', 'is_active', 'is_bestseller', 'is_new_arrival'),
            'classes': ('collapse',)
        }),
        ('Sales Statistics', {
            'fields': ('total_sales', 'monthly_sales', 'weekly_sales'),
            'classes': ('collapse',)
        }),
        ('Images', {
            'fields': ('image',),
            'description': 'Main book image'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    # Add inline images
    inlines = [BookImageInline]
    
    # Custom method for stock status display in list
    def stock_status_display(self, obj):
        """Display stock status with color coding"""
        status = obj.stock_status
        if status == 'in_stock':
            return f'✅ In Stock ({obj.stock})'
        elif status == 'low_stock':
            return f'⚠️ Low Stock ({obj.stock})'
        elif status == 'out_of_stock':
            return '❌ Out of Stock'
        else:
            return '⛔ Inactive'
    stock_status_display.short_description = 'Stock Status'
    
    # Actions for bulk operations
    actions = ['make_active', 'make_inactive', 'mark_as_bestseller', 'mark_as_new_arrival']
    
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} book(s) marked as active.")
    make_active.short_description = "Mark selected books as active"
    
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} book(s) marked as inactive.")
    make_inactive.short_description = "Mark selected books as inactive"
    
    def mark_as_bestseller(self, request, queryset):
        queryset.update(is_bestseller=True)
        self.message_user(request, f"{queryset.count()} book(s) marked as bestseller.")
    mark_as_bestseller.short_description = "Mark as bestseller"
    
    def mark_as_new_arrival(self, request, queryset):
        queryset.update(is_new_arrival=True)
        self.message_user(request, f"{queryset.count()} book(s) marked as new arrival.")
    mark_as_new_arrival.short_description = "Mark as new arrival"

@admin.register(BookImage)
class BookImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'book', 'thumbnail_preview', 'caption', 'is_featured', 'order', 'created_at']
    list_filter = ['is_featured', 'created_at', 'book']
    search_fields = ['book__title', 'caption']
    list_editable = ['order', 'is_featured', 'caption']
    list_per_page = 20
    
    def thumbnail_preview(self, obj):
        """Display thumbnail preview in admin list"""
        if obj.image:
            from django.utils.html import mark_safe
            return mark_safe(f'<img src="{obj.image.url}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px;" />')
        return 'No Image'
    thumbnail_preview.short_description = 'Preview'
    
    fieldsets = (
        ('Image Information', {
            'fields': ('book', 'image', 'caption', 'is_featured', 'order')
        }),
    )

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'quantity', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'book__title']
    list_per_page = 20

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'city', 'state', 'pincode', 'phone', 'is_default']
    list_filter = ['is_default', 'city', 'state']
    search_fields = ['user__username', 'name', 'phone', 'pincode']
    list_editable = ['is_default']
    list_per_page = 20

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['book', 'user', 'rating', 'title', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['book__title', 'user__username', 'title', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 20
    
    fieldsets = (
        ('Review Information', {
            'fields': ('book', 'user', 'rating', 'title', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )