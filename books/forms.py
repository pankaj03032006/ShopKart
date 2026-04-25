from django import forms
from .models import Book

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'price', 'description', 'image', 'category', 'language', 'isbn', 'mrp']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter book title'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter author name'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter book description', 'rows': 4}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Fiction, Academic'}),
            'language': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., English, Hindi'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ISBN number'}),
            'mrp': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Original MRP'}),
        }