from django.apps import AppConfig

class BooksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'books'
    
    def ready(self):
        # Import signals when the app is ready
        import books.signals