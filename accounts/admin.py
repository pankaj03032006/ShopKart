from django.contrib import admin
from .models import Seller


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'shop_name', 'phone', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['user__username', 'shop_name', 'phone']
    list_editable = ['is_approved']  # This allows you to edit approval directly from the list
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['approve_sellers', 'reject_sellers']
    
    def approve_sellers(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} seller(s) approved successfully.")
    approve_sellers.short_description = "Approve selected sellers"
    
    def reject_sellers(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f"{queryset.count()} seller(s) rejected.")
    reject_sellers.short_description = "Reject selected sellers"

