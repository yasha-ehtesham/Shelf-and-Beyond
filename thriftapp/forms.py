from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import WebUser, Listing, Review, Inbox, PetAdoption


class SignupForm1(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = WebUser
        fields = ['username', 'password']


class SignupForm2(forms.ModelForm):  # signup2 form
    class Meta:
        model = WebUser
        fields = ['firstname', 'lastname', 'gender', 'email', 'phone', 'birthdate', 'bio']


# Login form
class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


# Zoie's forms
class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ['title', 'description', 'image', 'price', 'condition', 'author']  # status removed


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']


# Samin's form
class WebUserUpdateForm(forms.ModelForm):
    class Meta:
        model = WebUser
        fields = ['firstname', 'lastname', 'email', 'phone', 'birthdate', 'bio']


class InboxForm(forms.ModelForm):
    receiver = forms.ModelChoiceField(queryset=WebUser.objects.all(), widget=forms.HiddenInput())

    class Meta:
        model = Inbox
        fields = ['receiver', 'sender_name', 'message']
        widgets = {
            'sender_name': forms.TextInput(attrs={'placeholder': 'Your Name', 'required': True}),
            'message': forms.Textarea(attrs={'placeholder': 'Your Message...', 'rows': 6, 'required': True}),
        }


from django import forms
from .models import PetAdoption, AdoptionApplication

class PetAdoptionForm(forms.ModelForm):
    class Meta:
        model = PetAdoption
        fields = ['title', 'description', 'age', 'breed', 'food_habit', 'potty_trained', 'gender', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'potty_trained': forms.CheckboxInput(),
        }

class AdoptionApplicationForm(forms.ModelForm):
    class Meta:
        model = AdoptionApplication
        fields = ['name', 'phone_number', 'address', 'id_document']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 4}),
        }
