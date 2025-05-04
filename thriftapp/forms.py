from django import forms
from .models import WebUser, Listing, Review, Inbox

from django.contrib.auth.forms import AuthenticationForm



class SignupForm1(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = WebUser
        fields = ['username', 'password']

class SignupForm2(forms.ModelForm): #signup2 form
    class Meta:
        model = WebUser
        fields = ['firstname', 'lastname', 'gender', 'email', 'phone', 'birthdate', 'bio']
          


#login form 
class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


#--------------------------------------------------------
#Zoie's forms
class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ['title', 'description', 'image', 'price', 'condition', 'author'] #status removed


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        
        
class InboxForm(forms.ModelForm):
    receiver = forms.ModelChoiceField(queryset=WebUser.objects.all(), widget=forms.HiddenInput())

    class Meta:
        model = Inbox
        fields = ['receiver', 'sender_name', 'message']
        widgets = {
            'sender_name': forms.TextInput(attrs={'placeholder': 'Your Name', 'required': True}),
            'message': forms.Textarea(attrs={'placeholder': 'Your Message...', 'rows': 6, 'required': True}),
        }