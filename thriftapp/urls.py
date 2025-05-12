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
    path('show_one_review/', views.show_one_review , name='show_one_review'),
    path('search_reviews', views.search_reviews , name='search_reviews'),

    path('add_to_cart/', views.add_to_cart, name = 'add_to_cart'),
    path('view_cart/', views.view_cart, name = 'view_cart'),
    path('remove_from_cart/', views.remove_from_cart, name='remove_from_cart'),
    
    # path('confirm_purchase/<int:listing_id>/', views.confirm_purchase, name='confirm_purchase'),
    # path('total_bill/', views.view_total_bill, name='view_total_bill'),
    
    # path('confirm_all/', views.confirm_all_purchases, name='confirm_all_purchases'),
    path('purchase_history/', views.view_purchase_history, name='view_purchase_history'),
    path('view_all_webusers/', views.view_all_webusers, name='view_all_webusers'),

    path('interaction_history/', views.interaction_history, name='interaction_history'),
    path('user/<int:user_id>/interactions/', views.admin_view_interaction_history, name='admin_view_interaction_history'),
    path('listing/<int:listing_id>/delete/', views.admin_delete_listing, name='admin_delete_listing'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),


    #zoie's urls
    path('seller_profile/<int:seller_id>/', views.seller_public_profile, name='seller_profile'),
    path('listing/create/', views.create_listing, name='create_listing'),
    path('manage_listings/', views.manage_listings, name='manage_listings'),
    path('send_message/<int:seller_id>/', views.send_message, name='send_message'),
    path('show_message/', views.show_message, name='show_message'),
    path('view_conversation/<int:other_user_id>/', views.view_conversation, name='view_conversation'),
    path('search/', views.search_results, name='search_results'),
    path('adopt/', views.adopt, name='adopt'),
    path('basket/view/', views.view_basket, name='view_basket'),
    path('basket/remove/', views.remove_from_basket, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('adopt/', views.adopt, name='adopt'),
    path('basket/view/', views.view_basket, name='view_basket'),
    path('basket/remove/', views.remove_from_basket, name='remove_from_basket'),
    path('adoption_checkout/', views.adoption_checkout, name='adoption_checkout'),
    path('adopt/success/', views.adopt_success, name='adopt_success'),
    path('listings/adoption/', views.show_adoption_listings, name='show_adoption_listings'),
    path('listings/adoption/details/', views.pet_adoption_details, name='pet_adoption_details'),
    path('manage_adoption_listings/', views.manage_adoption_listings, name='manage_adoption_listings'),
    path('manage-adoption-applications/', views.manage_adoption_applications, name='manage_adoption_applications'),
    path('pet_adoption/', views.pet_adoption, name='pet_adoption'),
    path('stats-and-trans/', views.stats_and_transactions_view, name='stats_and_transactions'),
    path('adoption_history/', views.view_adoption_history, name='view_adoption_history'),
    path('adoption-stats/', views.adoption_stats_view, name='adoption_stats'),


]
    
