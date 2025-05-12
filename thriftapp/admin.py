from django.contrib import admin
from .models import Role, WebUser, AdminProfile, Listing, Review, Purchase, PurchaseGroup, Inbox, PetAdoption, AdoptionApplication, AdoptionGroup

admin.site.register(Role)
admin.site.register(WebUser)
admin.site.register(AdminProfile)
admin.site.register(Listing)
admin.site.register(Review)
admin.site.register(Purchase)
admin.site.register(PurchaseGroup)
admin.site.register(Inbox)
admin.site.register(PetAdoption)
admin.site.register(AdoptionApplication)
admin.site.register(AdoptionGroup)