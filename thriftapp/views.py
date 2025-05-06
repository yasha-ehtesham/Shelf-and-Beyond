from django.shortcuts import render, redirect, get_object_or_404
from .forms import SignupForm1, SignupForm2
from .forms import ListingForm, ReviewForm, InboxForm
from .models import WebUser, Role, AdminProfile, Listing, Review, Purchase, PurchaseGroup, Inbox
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.messages import get_messages

import requests
from django.core.paginator import Paginator

from django.conf import settings

import os
from dotenv import load_dotenv

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum
from decimal import Decimal

load_dotenv()  # Load variables from .env

GOOGLE_BOOKS_API_KEY = os.getenv('GOOGLE_BOOKS_API_KEY')
NYT_API_KEY = os.getenv('NYT_API_KEY')


# Create your views here.
#------------------------------------------------------------------------


@login_required
def admin_delete_listing(request, listing_id):
    # Ensure that only admins can delete
    if not request.user.is_superuser:
        return redirect('show_listings')  # Redirect if not an admin
    
    listing = get_object_or_404(Listing, pk=listing_id)

    
    listing.is_deleted = True
    listing.save()

    

    return redirect('show_listings')  # Redirect back to the listings page


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_view_interaction_history(request, user_id):
    user = get_object_or_404(WebUser, pk=user_id)

    listings_created = Listing.objects.filter(seller=user)
    books_sold = Purchase.objects.filter(seller=user).select_related('buyer', 'listing')
    books_bought = Purchase.objects.filter(buyer=user).select_related('seller', 'listing')

    context = {
        'target_user': user,
        'listings_created': listings_created,
        'books_sold': books_sold,
        'books_bought': books_bought,
    }
    return render(request, 'admin_view_interaction_history.html', context)




def interaction_history(request):
    web_user_id = request.session.get('user_id')
    if not web_user_id:
      return redirect('login_step') 
    
    user = WebUser.objects.get(pk=web_user_id)

    # Listings created by the user
    listings_created = Listing.objects.filter(seller=user)

    # Books sold by the user (others bought from this user)
    books_sold = Purchase.objects.filter(seller=user).select_related('buyer', 'listing')

    # Books bought by the user (this user bought from others)
    books_bought = Purchase.objects.filter(buyer=user).select_related('seller', 'listing')

    context = {
        'listings_created': listings_created,
        'books_sold': books_sold,
        'books_bought': books_bought,
    }
    return render(request, 'interaction_history.html', context)






#-------------------------------------------------------------------------
@user_passes_test(lambda u: u.is_superuser)
def view_all_webusers(request):
    webusers = WebUser.objects.select_related('role').all().order_by('web_user_id') #perform a SQL JOIN and fetch the related role objects in the same query as the WebUser objects
    return render(request, 'view_all_users.html', {'webusers': webusers})



@login_required #Ensures the user is authenticated (i.e.- logged in).
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    total_books_listed = Listing.objects.count()
    total_books_sold = Purchase.objects.count()
    total_revenue = Purchase.objects.aggregate(total=Sum('listing__price'))['total'] or 0

    # Assuming system earns 10% commission
    commission_rate = Decimal('0.10')
    system_earnings = total_revenue * commission_rate

    context = {
        'total_books_listed': total_books_listed,
        'total_books_sold': total_books_sold,
        'total_revenue': total_revenue,
        'system_earnings': system_earnings
    }

    return render(request, 'admin_dashboard.html', context)

#--------------------------------------------------------------------------
#adding to cart views below

def add_to_cart(request):
    listing_id = request.GET.get('cart_item')
    listing = Listing.objects.get(listing_id=listing_id)

    # Initialize cart if it doesn't exist
    cart = request.session.get('cart', [])

    if listing_id not in cart:
        cart.append(listing_id)
        request.session['cart'] = cart  # Save updated cart to session

    context = {
        "listing": listing
    }

    return render(request, "add_to_cart.html", context)


def view_cart(request):
    web_user_id = request.session.get('user_id')
    if not web_user_id:
        return redirect('login_step')  # Or your custom login view

    web_user = get_object_or_404(WebUser, pk=web_user_id)

    cart = request.session.get('cart', [])
    # listings = Listing.objects.filter(listing_id__in=cart)
    purchased_ids = Purchase.objects.filter(buyer=web_user).values_list('listing__listing_id', flat=True)
    listings = Listing.objects.filter(listing_id__in=cart).exclude(listing_id__in=purchased_ids)
    
    return render(request, "view_cart.html", {
        'listings': listings,
        'purchased_ids': purchased_ids
    })


def confirm_all_purchases(request):
    web_user_id = request.session.get('user_id')
    if not web_user_id:
        return redirect('login_step')

    web_user = get_object_or_404(WebUser, pk=web_user_id)
    cart = request.session.get('cart', [])
    if not cart:
        return redirect('view_cart')

    listings = Listing.objects.filter(listing_id__in=cart)

    # Create a new group for this checkout session
    group = PurchaseGroup.objects.create(buyer=web_user)

    for listing in listings:
        # Avoid double-purchasing
        if not Purchase.objects.filter(buyer=web_user, listing=listing).exists():
            Purchase.objects.create(
                buyer=web_user,
                listing=listing,
                seller=listing.seller,
                purchase_group=group
            )
            listing.status = 'sold'  # 👈 mark as sold
            listing.save()

    # Clear cart after successful grouped purchase
    request.session['cart'] = []

    return redirect('view_purchase_history')



def view_total_bill(request):
    web_user_id = request.session.get('user_id')
    if not web_user_id:
        return redirect('login_step')

    web_user = get_object_or_404(WebUser, pk=web_user_id)

    cart = request.session.get('cart', [])
    # Only consider purchases that are:
    # - in the cart
    # - confirmed (exist in Purchase model for this user)
    purchases = Purchase.objects.filter(
        buyer=web_user,
        listing__listing_id__in=cart
    )

    total_bill = sum(purchase.listing.price for purchase in purchases)

    return render(request, "view_total_bill.html", {
        'total_bill': total_bill
    })


def view_purchase_history(request):
    web_user_id = request.session.get('user_id')
    if not web_user_id:
        return redirect('login_step')

    web_user = get_object_or_404(WebUser, pk=web_user_id)

    groups = PurchaseGroup.objects.filter(buyer=web_user).order_by('-timestamp')

    return render(request, "purchase_history.html", {
        'groups': groups
    })


def remove_from_cart(request):
    listing_id = request.POST.get('listing_id')
    cart = request.session.get('cart', [])
    if listing_id and listing_id in cart:
        cart.remove(listing_id)
        request.session['cart'] = cart
    return redirect('view_cart')  # or your cart page URL name



#-----------------------------------------------------------------------------
#yasha module 2 views 


def show_listings(request):

    listings = Listing.objects.filter(is_deleted=False)  # Only show listings that are not deleted 

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

# @login_required
# @user_passes_test(lambda u: u.is_superuser)
# def admin_dashboard(request):
#     return render(request, 'admin_dashboard.html')
#-------------------------------------------------------------------------------------

def home(request):
    return render(request, "homepage.html", {})

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

def send_message(request, seller_id):
    seller = WebUser.objects.get(web_user_id=seller_id)
    buyer = WebUser.objects.get(pk=request.session['user_id'])
    
    if request.method == 'POST':
        form = InboxForm(request.POST)
        print(form.is_valid())
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = buyer
            message.receiver = seller
            message.save()
            return redirect('welcome_page')
    else:
        form = InboxForm(initial={'receiver': seller})

    return render(request, 'send_message.html', {'form': form, 'seller': seller})


def show_message(request):
    user = WebUser.objects.get(pk=request.session['user_id'])
    
    messages = Inbox.objects.filter(
        Q(sender=user) | Q(receiver=user)
    ).order_by('-timestamp')
    
    return render(request, 'show_message.html', {'messages': messages})

def welcome_page(request):
    if 'user_id' not in request.session:
        return redirect('login_step')

    user = WebUser.objects.get(pk=request.session['user_id'])

    # Metrics
    total_books_listed = Listing.objects.filter(seller=user).count()
    books_sold = Purchase.objects.filter(seller=user, status='DELIVERED').count()
    books_purchased = Purchase.objects.filter(buyer=user).count()
    earnings = Purchase.objects.filter(seller=user, status='DELIVERED').aggregate(
        total_earnings=Sum('listing__price')
    )['total_earnings'] or 0

    # Transactions
    pending_transactions = Purchase.objects.filter(
        Q(buyer=user) | Q(seller=user), status='CONFIRMED'
    ).select_related('listing', 'buyer', 'seller').order_by('-purchase_date')
    active_transactions = Purchase.objects.filter(
        Q(buyer=user) | Q(seller=user), status='SHIPPED'
    ).select_related('listing', 'buyer', 'seller').order_by('-purchase_date')
    completed_transactions = Purchase.objects.filter(
        Q(buyer=user) | Q(seller=user), status='DELIVERED'
    ).select_related('listing', 'buyer', 'seller').order_by('-purchase_date')

    context = {
        'user': user,
        'total_books_listed': total_books_listed,
        'books_sold': books_sold,
        'books_purchased': books_purchased,
        'earnings': earnings,
        'pending_transactions': pending_transactions,
        'active_transactions': active_transactions,
        'completed_transactions': completed_transactions,
    }

    # request.session['web_user_id'] = user.web_user_id
    return render(request, "home.html", context)

from django.contrib import messages
from .models import WebUser, PetAdoption  # Updated to reflect the new model name
from .forms import PetAdoptionForm  # Updated to reflect the new form

def pet_adoption(request):
    if 'user_id' not in request.session:
        return redirect('login_step')  # User must be logged in

    user = get_object_or_404(WebUser, pk=request.session['user_id'])

    if request.method == 'POST':  # When form is filled
        form = PetAdoptionForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = user  # Connect to logged-in user
            listing.status = 'available'  # Manually set status

            # Save the image if uploaded
            if 'image' in request.FILES:
                listing.image = request.FILES['image']  # Save uploaded image
            listing.save()  # Save to database
            messages.success(request, "Pet listing created successfully!")
            return redirect('pet_adoption')  # Redirect after success
        else:
            print("Form errors:", form.errors.as_json())
            messages.error(request, "Form is not valid.")
    else:  # For GET request
        print("Page opened and form is empty")
        form = PetAdoptionForm()  # Empty form

    return render(request, 'pet_adoption.html', {'form': form})

from django.core.paginator import Paginator
from .models import PetAdoption  # Ensure you import the PetAdoption model

def show_adoption_listings(request):
    # Query PetAdoption objects instead of Listing
    pet_adoptions = PetAdoption.objects.all()   

    paginator = Paginator(pet_adoptions, 4)  # Show 4 listings per page (adjust as needed)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj
    }
    return render(request, "show_adoption_listings.html", context)

from .models import PetAdoption

def pet_adoption_details(request):
    listing_id = request.GET.get('listing_id')
    listing = get_object_or_404(PetAdoption, listing_id=listing_id)
    context = {
        'listing': listing
    }
    return render(request, 'pet_adoption_details.html', context)



from django.http import HttpResponse
from .models import PetAdoption
from .forms import PetAdoptionForm

def manage_adoption_listings(request):
    user = WebUser.objects.get(pk=request.session['user_id'])
    pet_adoptions = PetAdoption.objects.filter(seller=user)

    if request.method == 'POST':
        listing_id = request.POST.get('listing_id')
        action = request.POST.get('action')
        try:
            listing = PetAdoption.objects.get(id=listing_id)
            if action == 'adopted':
                listing.status = 'Adopted'
            elif action == 'cancelled':
                listing.status = 'Cancelled'
            listing.save()
        except PetAdoption.DoesNotExist:
            return HttpResponse("Listing not found.")
        return redirect('manage_adoption_listings')

    return render(request, 'manage_adoption_listings.html', {'pet_adoptions': pet_adoptions})

def search_results(request):
    query = request.GET.get('q', '')
    listings = []
    purchases = []
    
    if query:
        # Search listings (books)
        listings = Listing.objects.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(description__icontains=query)
        ).select_related('seller')
        
        # Search purchases (orders) - only for logged-in users
        if request.user.is_authenticated:
            purchases = Purchase.objects.filter(
                Q(listing__title__icontains=query) |
                Q(listing__author__icontains=query),
                buyer__user=request.user
            ).select_related('listing', 'buyer', 'seller')
    
    context = {
        'query': query,
        'listings': listings,
        'purchases': purchases,
    }
    return render(request, 'search_results.html', context)
