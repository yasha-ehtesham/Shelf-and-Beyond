from django.shortcuts import render, redirect, get_object_or_404
from .forms import SignupForm1, SignupForm2
from .forms import ListingForm, ReviewForm, InboxForm
from .models import WebUser, Role, AdminProfile, Listing, Review, Purchase, PurchaseGroup, Inbox, AdoptionGroup
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Max
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.messages import get_messages
from django.db.models import Q, Max
from decimal import Decimal
import requests
from django.db.models import Q, Sum
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.conf import settings
from functools import wraps
import os
import stripe
import requests
from dotenv import load_dotenv

from .forms import SignupForm1,SignupForm2, ListingForm, ReviewForm, InboxForm, PetAdoptionForm, WebUserUpdateForm
from .models import WebUser, Role, AdminProfile,Listing, Review, Purchase, PurchaseGroup, Inbox, Notification, PetAdoption

# Load environment variables
load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
GOOGLE_BOOKS_API_KEY = os.getenv('GOOGLE_BOOKS_API_KEY')
NYT_API_KEY = os.getenv('NYT_API_KEY')

# Custom decorator to check for session-based WebUser login
def session_user_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('user_id'):
            messages.error(request, "You must be logged in to view this page.")
            return redirect('login_step')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# Create your views here.
#------------------------------------------------------------------------


@csrf_exempt
def checkout(request):
    web_user_id = request.session.get('user_id')
    if not web_user_id:
        return redirect('login_step')

    web_user = get_object_or_404(WebUser, pk=web_user_id)
    cart = request.session.get('cart', [])
    if not cart:
        return redirect('view_cart')

    listings = Listing.objects.filter(listing_id__in=cart)
    
    # Generate line_items for Stripe
    line_items = []
    for item in listings:
        line_items.append({
            'price_data': {
                'currency': 'bdt',
                'unit_amount': int(item.price) * 100,  # Stripe uses smallest currency unit
                'product_data': {
                    'name': item.title,
                },
            },
            'quantity': 1,
        })

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=request.build_absolute_uri('/checkout/success/'),
        cancel_url=request.build_absolute_uri('/checkout/cancel/'),
    )

    return redirect(session.url, code=303)

def checkout_success(request):
    web_user_id = request.session.get('user_id')
    if not web_user_id:
        return redirect('login_step')

    web_user = get_object_or_404(WebUser, pk=web_user_id)

    cart = request.session.get('cart', [])
    if not cart:
        return render(request, "checkout_success.html", {
            'message': "Your cart was already empty or purchases were already confirmed."
        })

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
            listing.status = 'sold'
            listing.save()

    # Clear cart
    request.session['cart'] = []

    return render(request, "checkout_success.html", {
        'message': "Payment successful! Your purchases have been confirmed."
    })


def checkout_cancel(request):
    return render(request, "checkout_cancel.html")



#-----------------------------------------------------------------------


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

from django.shortcuts import render, redirect
from django.db.models import Q, Max
from .models import WebUser, Inbox
from .forms import InboxForm
import logging

# Set up logging
logger = logging.getLogger(__name__)

def send_message(request, seller_id):
    try:
        seller = WebUser.objects.get(web_user_id=seller_id)
        buyer = WebUser.objects.get(pk=request.session['user_id'])
    except WebUser.DoesNotExist:
        logger.error("User not found: seller_id=%s, user_id=%s", seller_id, request.session.get('user_id'))
        return render(request, 'send_message.html', {'error': "User not found."})

    # Prevent sending messages to self
    if seller == buyer:
        logger.info("Self-messaging attempt by user: %s", buyer.username)
        return render(request, 'send_message.html', {
            'form': InboxForm(initial={'receiver': seller, 'sender_name': buyer.username}),
            'seller': seller,
            'error': "You cannot send a message to yourself."
        })

    if request.method == 'POST':
        form = InboxForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = buyer
            message.receiver = seller
            message.sender_name = form.cleaned_data['sender_name'] or buyer.username
            message.save()
            logger.info("Message sent from %s to %s: %s", buyer.username, seller.username, message.message)
            return redirect('show_message')
        else:
            logger.error("Form validation failed in send_message: %s", form.errors.as_json())
    else:
        form = InboxForm(initial={'receiver': seller, 'sender_name': buyer.username})

    return render(request, 'send_message.html', {'form': form, 'seller': seller})

def show_message(request):
    try:
        user = WebUser.objects.get(pk=request.session['user_id'])
    except WebUser.DoesNotExist:
        logger.error("User not found: user_id=%s", request.session.get('user_id'))
        return render(request, 'show_message.html', {'error': "User not found."})

    # Get all messages where the user is either sender or receiver
    messages = Inbox.objects.filter(
        Q(sender=user) | Q(receiver=user)
    ).order_by('-timestamp')

    # Group messages by conversation (unique sender/receiver pairs)
    conversations = []
    seen_pairs = set()

    for msg in messages:
        other_user = msg.receiver if msg.sender == user else msg.sender
        pair = tuple(sorted([user.web_user_id, other_user.web_user_id]))
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            # Get the latest message for this conversation
            latest_message = Inbox.objects.filter(
                Q(sender=user, receiver=other_user) | Q(sender=other_user, receiver=user)
            ).order_by('-timestamp').first()
            conversations.append({
                'other_user': other_user,
                'latest_message': latest_message,
            })

    return render(request, 'show_message.html', {'conversations': conversations})

def view_conversation(request, other_user_id):
    try:
        user = WebUser.objects.get(pk=request.session['user_id'])
        other_user = WebUser.objects.get(web_user_id=other_user_id)
    except WebUser.DoesNotExist:
        logger.error("User not found: user_id=%s, other_user_id=%s", request.session.get('user_id'), other_user_id)
        return render(request, 'inbox.html', {'error': "User not found."})

    # Prevent messaging self
    if user == other_user:
        logger.info("Self-messaging attempt by user: %s", user.username)
        return render(request, 'inbox.html', {
            'messages': [],
            'other_user': other_user,
            'form': InboxForm(initial={'receiver': other_user, 'sender_name': user.username}),
            'error': "You cannot send a message to yourself."
        })

    # Get all messages between the user and other_user
    messages = Inbox.objects.filter(
        Q(sender=user, receiver=other_user) | Q(sender=other_user, receiver=user)
    ).order_by('timestamp')

    if request.method == 'POST':
        form = InboxForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = user
            message.receiver = other_user
            message.sender_name = form.cleaned_data['sender_name'] or user.username
            message.save()
            logger.info("Reply sent from %s to %s: %s", user.username, other_user.username, message.message)
            return redirect('view_conversation', other_user_id=other_user_id)
        else:
            logger.error("Form validation failed in view_conversation: %s", form.errors.as_json())
    else:
        form = InboxForm(initial={'receiver': other_user, 'sender_name': user.username})

    return render(request, 'inbox.html', {
        'messages': messages,
        'other_user': other_user,
        'form': form,
    })

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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from .models import WebUser, PetAdoption, AdoptionApplication
from .forms import PetAdoptionForm, AdoptionApplicationForm
from django.http import HttpResponse

def is_admin(user):
    return user.is_staff

def pet_adoption(request):
    if 'user_id' not in request.session:
        return redirect('login_step')
    user = get_object_or_404(WebUser, pk=request.session['user_id'])
    if request.method == 'POST':
        form = PetAdoptionForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = user
            listing.status = 'available'
            if 'image' in request.FILES:
                listing.image = request.FILES['image']
            listing.save()
            messages.success(request, "Pet listing created successfully!")
            return redirect('pet_adoption')
        else:
            messages.error(request, "Form is not valid.")
    else:
        form = PetAdoptionForm()
    return render(request, 'pet_adoption.html', {'form': form})

def show_adoption_listings(request):
    pet_adoptions = PetAdoption.objects.all()
    paginator = Paginator(pet_adoptions, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "show_adoption_listings.html", {'page_obj': page_obj})

def pet_adoption_details(request):
    listing_id = request.GET.get('listing_id')
    listing = get_object_or_404(PetAdoption, listing_id=listing_id)
    return render(request, 'pet_adoption_details.html', {'listing': listing})

def adopt(request):
    if 'user_id' not in request.session:
        return redirect('login_step')
    listing_id = request.GET.get('basket_item')
    if listing_id:
        basket = request.session.get('basket', [])
        if listing_id not in basket:
            basket.append(listing_id)
            request.session['basket'] = basket
            messages.success(request, "Pet added to your adoption basket!")
        else:
            messages.info(request, "This pet is already in your basket.")
    return redirect('view_basket')

def view_basket(request):
    basket = request.session.get('basket', [])
    listings = PetAdoption.objects.filter(listing_id__in=basket)
    return render(request, 'view_basket.html', {'listings': listings})

def remove_from_basket(request):
    if request.method == 'POST':
        listing_id = request.POST.get('listing_id')
        basket = request.session.get('basket', [])
        if listing_id and listing_id in basket:
            basket.remove(listing_id)
            request.session['basket'] = basket
        return redirect('view_basket')
    return redirect('view_basket')

def adoption_checkout(request):
    if 'user_id' not in request.session:
        return redirect('login_step')
    user = get_object_or_404(WebUser, pk=request.session['user_id'])
    basket = request.session.get('basket', [])
    if not basket:
        messages.error(request, "Your adoption basket is empty.")
        return redirect('view_basket')
    if request.method == 'POST':
        form = AdoptionApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            group = AdoptionGroup.objects.create(applicant=user)
            for listing_id in basket:
                pet = get_object_or_404(PetAdoption, listing_id=listing_id)
                if pet.status != 'available':
                    messages.error(request, f"{pet.title} is no longer available.")
                    continue
                application = form.save(commit=False)
                application.pet = pet
                application.applicant = user
                application.adoption_group = group
                application.save()
                pet.status = 'pending'
                pet.save()
            request.session['basket'] = []
            messages.success(request, "Adoption application submitted successfully!")
            return redirect('adopt_success')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = AdoptionApplicationForm(initial={'name': user.username})
    pets = PetAdoption.objects.filter(listing_id__in=basket)
    return render(request, 'adoption_checkout.html', {'form': form, 'pets': pets})

def adopt_success(request):
    return render(request, 'adopt.html')

def manage_adoption_listings(request):
    if 'user_id' not in request.session:
        return redirect('login_step')
    user = get_object_or_404(WebUser, pk=request.session['user_id'])
    pet_adoptions = PetAdoption.objects.filter(seller=user)
    if request.method == 'POST':
        listing_id = request.POST.get('listing_id')
        action = request.POST.get('action')
        try:
            listing = PetAdoption.objects.get(listing_id=listing_id)
            if action == 'adopted':
                listing.status = 'adopted'
            elif action == 'cancelled':
                listing.status = 'cancelled'
            listing.save()
        except PetAdoption.DoesNotExist:
            return HttpResponse("Listing not found.")
        return redirect('manage_adoption_listings')
    # Add pagination
    paginator = Paginator(pet_adoptions, 4)  # 4 listings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'manage_adoption_listings.html', {'page_obj': page_obj})

from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from .models import AdoptionApplication
from .views import is_admin

@user_passes_test(is_admin)
def manage_adoption_applications(request):
    applications = AdoptionApplication.objects.all()
    paginator = Paginator(applications, 4)  # 4 applications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.method == 'POST':
        application_id = request.POST.get('application_id')
        action = request.POST.get('action')
        application = get_object_or_404(AdoptionApplication, id=application_id)
        if action == 'approve':
            application.status = 'approved'
            application.pet.status = 'adopted'
            application.pet.save()
        elif action == 'reject':
            application.status = 'rejected'
            application.pet.status = 'available'
            application.pet.save()
        application.save()
        messages.success(request, f"Application {action}d successfully!")
        # Preserve the current page in the redirect
        return redirect(f"{request.path}?page={page_number or 1}")
    
    return render(request, 'admin_manage_adoption.html', {'page_obj': page_obj})

def view_adoption_history(request):
    if 'user_id' not in request.session:
        return redirect('login_step')
    user = get_object_or_404(WebUser, pk=request.session['user_id'])
    groups = AdoptionGroup.objects.filter(applicant=user).order_by('-timestamp')
    return render(request, 'adoption_history.html', {'groups': groups})

def adoption_stats_view(request):
    if 'user_id' not in request.session:
        return redirect('login_step')
    
    user = get_object_or_404(WebUser, pk=request.session['user_id'])
    
    # Adoption Stats
    total_pets_listed = PetAdoption.objects.filter(seller=user).count()
    pets_adopted_out = PetAdoption.objects.filter(seller=user, status='adopted').count()
    pets_adopted_by_you = AdoptionApplication.objects.filter(applicant=user, status='approved').count()
    applications_submitted = AdoptionApplication.objects.filter(applicant=user).count()
    
    # Successful Adoptions (both as adopter and seller)
    successful_adoptions_as_adopter = AdoptionApplication.objects.filter(applicant=user, status='approved')
    successful_adoptions_as_seller = AdoptionApplication.objects.filter(pet__seller=user, status='approved')
    successful_adoptions = (successful_adoptions_as_adopter | successful_adoptions_as_seller).distinct().order_by('-created_at')
    
    context = {
        'total_pets_listed': total_pets_listed,
        'pets_adopted_out': pets_adopted_out,
        'pets_adopted_by_you': pets_adopted_by_you,
        'applications_submitted': applications_submitted,
        'successful_adoptions': successful_adoptions,
    }
    
    return render(request, 'adoption_stats.html', context)


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



def stats_and_transactions_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return render(request, 'login_required.html')  # or redirect to login

    user = get_object_or_404(WebUser, pk=user_id)

    # Metrics
    total_books_listed = Listing.objects.filter(seller=user).count()
    books_sold = Purchase.objects.filter(seller=user, status='CONFIRMED').count()
    books_purchased = Purchase.objects.filter(buyer=user).count()
    earnings = Purchase.objects.filter(seller=user, status='CONFIRMED').aggregate(
        total_earnings=Sum('listing__price')
    )['total_earnings'] or 0

    # Transactions
    transactions = Purchase.objects.filter(
        Q(buyer=user) | Q(seller=user), status='CONFIRMED'
    ).select_related('listing', 'buyer', 'seller').order_by('-purchase_date')
    

    context = {
        'user': user,
        'total_books_listed': total_books_listed,
        'books_sold': books_sold,
        'books_purchased': books_purchased,
        'earnings': earnings,
        'transactions': transactions,
    }

    return render(request, 'stats_and_trans.html', context)

#------------------------------------------------------------------------------------------
#Samin's views
##M1 F2&3 
@session_user_required
def update_profile(request):
    user_id = request.session.get('user_id')
    user = WebUser.objects.get(pk=user_id)

    if request.method == 'POST':
        form = WebUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('view_profile')
    else:
        form = WebUserUpdateForm(instance=user)

    return render(request, 'update_profile.html', {'form': form})
@login_required
@user_passes_test(lambda u: u.is_superuser)
def manage_users(request):
    users = WebUser.objects.all()
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role_id = request.POST.get('role_id')
        user = WebUser.objects.get(pk=user_id)
        role = Role.objects.get(pk=role_id)
        user.role = role
        user.save()
        messages.success(request, f"Updated role for {user.username}")
        return redirect('manage_users')
    return render(request, 'admin_manage_users.html', {'users': users, 'roles': Role.objects.all()})

@session_user_required
def view_profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "You are not logged in. Please log in.")
        return redirect('login_step')

    try:
        user = WebUser.objects.get(pk=user_id)
    except WebUser.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('login_step')

    return render(request, 'view_profile.html', {'user': user})

# M2 F3 
@session_user_required
def compare_prices(request):
    # Fetch all unique book titles that have listings
    unique_titles = Listing.objects.values_list('title', flat=True).distinct()

    books_with_listings = []

    for title in unique_titles:
        listings = Listing.objects.filter(title=title, status='available')

        if listings.exists():
            books_with_listings.append({
                'title': title,
                'listings': [
                    {
                        'seller_name': listing.seller.username, 
                        'price': listing.price,
                        'condition': listing.condition,
                    }
                    for listing in listings
                ]
            })

    return render(request, 'compare_prices.html', {'books_with_listings': books_with_listings})

@session_user_required
def user_notifications(request):
    user_id = request.session.get('user_id')
    user = WebUser.objects.get(pk=user_id)
    notifications = Notification.objects.filter(recipient=user).order_by('-timestamp')
    return render(request, 'user_notifications.html', {'notifications': notifications})
from django.contrib import messages
from django.shortcuts import redirect, render
from thriftapp.models import WebUser, Notification

from django.contrib.auth.decorators import login_required


@login_required
def admin_notifications(request):
    #  Only allow Django superusers
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized access.")
        return redirect('welcome_page')

    # Try to find a matching WebUser (silent fallback if not found)
    web_admin = WebUser.objects.filter(username=request.user.username).first()

    if not web_admin:
        notifications = []  # No notifications to show
    else:
        notifications = Notification.objects.filter(recipient=web_admin).order_by('-created_at')

    return render(request, 'admin_notifications.html', {'notifications': notifications})


#@login_required
#def admin_notifications(request):
   # user_id = request.session.get('user_id')
    #user = get_object_or_404(WebUser, pk=user_id)

    #if user.role.role_name != 'admin':
        #messages.error(request, "Unauthorized access.")
        #return redirect('welcome_page')

   # notifications = Notification.objects.filter(recipient=user).order_by('-created_at')
    #return render(request, 'admin_notifications.html', {'notifications': notifications})

