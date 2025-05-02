from django.urls import path
from . import views

urlpatterns = [
    
    path('create_admin/', views.create_admin_user, name='create_admin_user'),
    path('admin_login/', views.admin_login, name='admin_login'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('login/', views.login_step, name='login_step'),
    path('signup/', views.signup_step1, name='signup_step1'),
    path('signup/step2/', views.signup_step2, name='signup_step2'),
    path('', views.home, name='home_page'), #public view
    path('login/welcome/', views.welcome_page, name="welcome_page" ),
    path('logout/', views.logout_view, name='logout'),

    #api-yasha
    path('show_listings/', views.show_listings, name="show_listings"),
    path('details_listing/', views.details_listing, name="details_listing"),


    path('send_message/', views.send_message, name='send_message'), #empty for now
    

    path('show_one_review/', views.show_one_review , name='show_one_review'),
    path('search_reviews', views.search_reviews , name='search_reviews'),

    #zoie's urls
    path('seller_profile/<int:seller_id>/', views.seller_public_profile, name='seller_profile'),
   


    path('listing/create/', views.create_listing, name='create_listing'),
    path('manage_listings/', views.manage_listings, name='manage_listings'),
]