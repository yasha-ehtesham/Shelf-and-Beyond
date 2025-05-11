from django.urls import path
from . import views

urlpatterns = [
    # Admin-related
    path('create_admin/', views.create_admin_user, name='create_admin_user'),
    path('admin_login/', views.admin_login, name='admin_login'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/manage_users/', views.manage_users, name='manage_users'),
    path('admin_notifications/', views.admin_notifications, name='admin_notifications'),

    path('notifications/', views.user_notifications, name='notifications'),

    # Auth and landing
    path('login/', views.login_step, name='login_step'),
    path('signup/', views.signup_step1, name='signup_step1'),
    path('signup/step2/', views.signup_step2, name='signup_step2'),
    path('', views.home, name='home_page'),
    path('login/welcome/', views.welcome_page, name='welcome_page'),
    path('logout/', views.logout_view, name='logout'),

    # Listings and Reviews
    path('show_listings/', views.show_listings, name='show_listings'),
    path('details_listing/', views.details_listing, name='details_listing'),
    path('show_one_review/', views.show_one_review, name='show_one_review'),
    path('search_reviews', views.search_reviews, name='search_reviews'),
    path('compare_prices/', views.compare_prices, name='compare_prices'),

    # Cart and Checkout
    path('add_to_cart/', views.add_to_cart, name='add_to_cart'),
    path('view_cart/', views.view_cart, name='view_cart'),
    path('remove_from_cart/', views.remove_from_cart, name='remove_from_cart'),
    path('confirm_all/', views.confirm_all_purchases, name='confirm_all_purchases'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),

    # Purchase History & Stats
    path('purchase_history/', views.view_purchase_history, name='view_purchase_history'),
    path('interaction_history/', views.interaction_history, name='interaction_history'),
    path('user/<int:user_id>/interactions/', views.admin_view_interaction_history, name='admin_view_interaction_history'),
    path('stats-and-trans/', views.stats_and_transactions_view, name='stats_and_transactions'),

    # Messaging
    path('message/send/<int:seller_id>/', views.send_message, name='send_message'),
    path('message_show/', views.show_message, name='show_message'),

    # Profile
    path('profile/', views.view_profile, name='view_profile'),
    path('profile/edit/', views.update_profile, name='update_profile'),

    # Pet Adoption
    path('pet_adoption/', views.pet_adoption, name='pet_adoption'),
    path('show_pet_adoption/', views.show_adoption_listings, name='show_adoption_listings'),
    path('pet_adoption_details/', views.pet_adoption_details, name='details_adoption_listing'),
    path('manage_adoption_listings', views.manage_adoption_listings, name='manage_adoption_listings'),
]
