from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from .forms import SignupForm1, SignupForm2
from .forms import ListingForm, ReviewForm
from .models import WebUser, Role, AdminProfile, Listing, Review
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.messages import get_messages

import requests
from django.core.paginator import Paginator

from django.conf import settings

import os
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env

GOOGLE_BOOKS_API_KEY = os.getenv('GOOGLE_BOOKS_API_KEY')
NYT_API_KEY = os.getenv('NYT_API_KEY')


# Create your views here.
#-----------------------------------------------------------------------------
#yasha module 2 views 


def show_listings(request):
    listings = Listing.objects.all()   

    paginator = Paginator(listings, 4)  # Show 4 listings per page (adjust as needed)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'listings': listings,
        'page_obj': page_obj
    }
    return render(request, "show_listings.html", context)



def details_listing(request):
    listing_id = request.GET.get('listing_id')
    #fetch the listing from the database after collecting it from the URL parameter
    listing = Listing.objects.get(listing_id=listing_id)

    # Fetch book summary from Google Books API
    api_key = GOOGLE_BOOKS_API_KEY
    
    title = listing.title
    author = listing.author  # Make sure your Listing model has an author field!

    # Build a more specific query
    query = f"intitle:{title}+inauthor:{author}"
    api_url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={api_key}"

    response = requests.get(api_url)
    summary = None

    if response.status_code == 200:
        data = response.json()
        if data['totalItems'] > 0:
            volume_info = data['items'][0]['volumeInfo']
            summary = volume_info.get('description')

    # If not found, fallback to search by title only
    if not summary:
        query_title_only = f"intitle:{title}"
        api_url_title_only = f"https://www.googleapis.com/books/v1/volumes?q={query_title_only}&key={api_key}"

        response_title_only = requests.get(api_url_title_only)
        if response_title_only.status_code == 200:
            data_title_only = response_title_only.json()
            if data_title_only['totalItems'] > 0:
                volume_info = data_title_only['items'][0]['volumeInfo']
                summary = volume_info.get('description')

    # Final backup if still no summary found
    if not summary:
        summary = "Summary not found. Please check Goodreads or Amazon for more details."

    return render(request, 'details_listing.html', {'listing': listing, 'summary': summary})



def send_message(request):
    return render(request, 'send_message.html')


def show_one_review(request):
    return render(request, 'show_one_review.html')




#User -> Form -> Django View -> NYT API -> JSON -> Django View -> Template -> User sees Results

def search_reviews(request):
   
    reviews = None #In case user hasn't searched ye
    title = request.GET.get('query')  # Get 'query' from form
    

    if title:
        url = "https://api.nytimes.com/svc/books/v3/reviews.json" #endpoint
        params = {
            "title": title, 
            "api-key": NYT_API_KEY
        }
        response = requests.get(url, params=params) #GET request to the NYT API

        if response.status_code == 200:
            data = response.json() #Parse the JSON response into a Python dictionary using response.json()
            reviews = data.get('results', [])
        else:
            reviews = []

    return render(request, 'show_one_review.html', {'reviews': reviews, 'title': title})

#---------------------------------------------------------------------------------------------------
#yasha module 1 views

from django.contrib.auth.forms import UserCreationForm

def create_admin_user(request):


    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = True
            user.is_superuser = True
            user.save()

            # Create AdminProfile entry
            admin_role = Role.objects.get(role_name='admin')  # assumes 'admin' role exists
            AdminProfile.objects.create(user=user, role=admin_role)

            messages.success(request, 'Admin user created successfully!')
            return redirect('admin_login')
        else:
            messages.error(request, 'There was an error creating the admin user.')
    else:
        form = UserCreationForm()

    return render(request, 'registration/admin_signup.html', {'form': form})

def admin_login(request):
    if request.user.is_authenticated:
        # If already logged in AND admin, go to admin dashboard
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        else:
            return redirect('welcome_page')  # Regular user goes to user dashboard

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()

            if user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'You are not authorized to log in as admin.')
                return redirect('admin_login')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'registration/admin_login.html', {'form': form})

from django.contrib.auth.decorators import login_required, user_passes_test

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')
#-------------------------------------------------------------------------------------

def home(request):
    return render(request, "homepage.html", {})

def welcome_page(request):
    if 'user_id' not in request.session:
        return redirect('login_step')

    user = WebUser.objects.get(pk=request.session['user_id'])
    return render(request, "home.html", {'user': user})


def login_step(request):
    storage = get_messages(request)
    list(storage)  # Clear messages
    if request.method == 'POST': #if form is submitted
        username = request.POST.get('username') #POST is a dictionary here - containing data submitted using POST req
        password = request.POST.get('password') #retrieves the val of uname from the form 

        try:  #try to find matching user in db
            user = WebUser.objects.get(username=username, password=password)
            request.session['user_id'] = user.web_user_id  #adds the id to request.session
            return redirect('welcome_page')
        except WebUser.DoesNotExist:
            messages.error(request, 'Invalid username or password.')

    #if no post request
    return render(request, 'registration/login.html')

def signup_step1(request):
    if request.method == 'POST':
        form = SignupForm1(request.POST)
        if form.is_valid(): #valid info checker using django's form 
            request.session['username'] = form.cleaned_data['username']  #cleaned_data is a dictionary that contains validated form data.
            request.session['password'] = form.cleaned_data['password']
            return redirect('/signup/step2/')
    else:
        form = SignupForm1() #empty form
    return render(request, 'registration/signup.html', {'form': form}) #gives access to the form 


def signup_step2(request):
    if 'username' not in request.session or 'password' not in request.session:
        return redirect('signup_step1')  # Prevent direct access

    if request.method == 'POST':
        form = SignupForm2(request.POST)
        if form.is_valid():
            web_user = form.save(commit=False) #Create a WebUser instance from the form, but don’t save it to the database yet
            web_user.username = request.session['username'] #saving to the db
            web_user.password = request.session['password']
            
            # Assign role as "normal_user"
            normal_role = Role.objects.get(role_name='normal_user')
            web_user.role = normal_role

            web_user.save() #save the fully completed user to the database
            # Clear session data
            request.session.flush()
            return redirect('login_step')  # Redirect to login
    else:
        form = SignupForm2()
    return render(request, 'registration/signup2.html', {'form': form})

def logout_view(request):
    request.session.flush()  # Clear
    return redirect('home_page') 




#---------------------------------------------------------------
#---------------------------------------------------------------
#Zoie's views


def seller_public_profile(request, seller_id):
    seller = get_object_or_404(WebUser, pk=seller_id)  # pk = web_user_id
    return render(request, 'seller_profile.html', {'seller': seller})


def listings(request):
    all_listings = Listing.objects.all()
    return render(request, 'thriftapp/listings.html', {'listings': all_listings})



def create_listing(request):
    if 'user_id' not in request.session:
        return redirect('login_step')  # User must be logged in


    user = get_object_or_404(WebUser, pk=request.session['user_id'])

    if request.method == 'POST': #when form is filled
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = user  # Connect to logged-in user
            listing.status = 'available' #manually set - this was the previous error 
            listing.save()  # Save to database
            messages.success(request, "Listing created successfully!")
            return redirect('welcome_page')
        else:
            print("Form errors:", form.errors.as_json())
            messages.error(request, "Form is not valid.")
    else: #for GET request
        print("Page opened and form is empty")
        form = ListingForm() #empty form

    return render(request, 'create_listing.html', {'form': form})


def add_review(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.listing = listing
            # Assign current user as reviewer if logged in
            review.reviewer = WebUser.objects.get(pk=request.session['user_id'])
            review.save()
            return redirect('listing_detail', listing_id=listing_id)
    else:
        form = ReviewForm()
    return render(request, 'thriftapp/add_review.html', {'form': form})

def manage_listings(request):
    # Fetch all listings, regardless of whether the user is a buyer or seller
    # We'll assume the user might be a seller who has listings and a buyer who may be browsing them.
    #listings = Listing.objects.all()  # Show all listings

    user = WebUser.objects.get(pk=request.session['user_id'])
    listings = Listing.objects.filter(seller=user)

    # When the user marks a listing as sold or cancelled
    if request.method == 'POST':
        listing_id = request.POST.get('listing_id')
        action = request.POST.get('action')
        
        try:
            # Fetch the listing based on the ID
            listing = Listing.objects.get(id=listing_id)
            
            # Check the action and update the listing's status accordingly
            if action == 'sold':
                listing.status = 'sold'
            elif action == 'cancelled':
                listing.status = 'cancelled'
            listing.save()
        except Listing.DoesNotExist:
            return HttpResponse("Listing not found.")
        
        # After updating the status, redirect back to the listings management page
        return redirect('manage_listings')

    # Render the page with the listings context
    return render(request, 'manage_listings.html', {'listings': listings})

#------------------------------------------------------------------------------------------