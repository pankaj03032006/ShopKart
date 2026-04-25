from django.contrib import admin
from django.urls import path, include

# ✅ ADD THESE
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('books.urls')),
  path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('orders/', include('orders.urls')),
]

# ✅ ADD THIS AT BOTTOM
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)