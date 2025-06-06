from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Role choices
ROLE_NAME = {
    ("normal_user", "Normal User"), 
    ("admin", "Admin")
}

class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=20, choices=ROLE_NAME)

    def __str__(self):
        return self.role_name


# Gender options
GENDER = [
    ('male', "Male"),
    ('female', 'Female'),
    ('prefer_not_to_say', 'Prefer not to say'),
    ('others', 'Others')
]


# AdminProfile links to built-in Django User
class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)


# Custom WebUser model
class WebUser(models.Model):
    web_user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=20, unique=True)
    firstname = models.CharField(max_length=25)
    lastname = models.CharField(max_length=25)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=11, unique=True)
    gender = models.CharField(max_length=20, choices=GENDER)
    password = models.CharField(max_length=10)
    birthdate = models.DateField()
    bio = models.TextField(blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.firstname} {self.lastname}: {self.email}"


# Book listing info
BOOK_CONDITIONS = [
    ('brand_new', 'Brand New'),
    ('almost_new', 'Almost New'),
    ('slight_worn_off', 'Slightly Worn off'),
    ('quite_worn_off', 'Quite Worn off')
]

STATUS_CHOICES = [
    ('available', 'Available'),
    ('sold', 'Sold'),
]

class Listing(models.Model):
    listing_id = models.AutoField(primary_key=True)
    author = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='listing_images/', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    condition = models.CharField(max_length=20, choices=BOOK_CONDITIONS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    listing_time = models.DateTimeField(auto_now_add=True)
    seller = models.ForeignKey(WebUser, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} - {self.status}"


# Review model
class Review(models.Model):
    review_id = models.AutoField(primary_key=True)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(WebUser, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.reviewer} - {self.rating}/5"


# Purchase-related models
class PurchaseGroup(models.Model):
    buyer = models.ForeignKey(WebUser, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        return sum(p.listing.price for p in self.purchase_set.all())


class Purchase(models.Model):
    purchase_id = models.AutoField(primary_key=True)
    buyer = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='purchases')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    seller = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='sales')
    purchase_date = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = [
        ('CONFIRMED', 'Confirmed'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='CONFIRMED')
    purchase_group = models.ForeignKey(PurchaseGroup, null=True, blank=True, on_delete=models.CASCADE)


# From samin-branch
class ExternalBookSource(models.Model):
    source_id = models.AutoField(primary_key=True)
    listing = models.ForeignKey('Listing', on_delete=models.CASCADE, related_name='external_sources')
    source_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    url = models.URLField()

    def __str__(self):
        return f"{self.source_name} - {self.price}"


class Notification(models.Model):
    recipient = models.ForeignKey(WebUser, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"To: {self.recipient.username} - {self.message[:30]}"


class Inbox(models.Model):
    sender = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(WebUser, on_delete=models.CASCADE, related_name='received_messages')
    sender_name = models.CharField(max_length=20)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver}"
    
from django.db import models

from django.db import models
from .models import WebUser

class PetAdoption(models.Model):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('adopted', 'Adopted'),
        ('cancelled', 'Cancelled'),
    )
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )

    listing_id = models.AutoField(primary_key=True)
    seller = models.ForeignKey(WebUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    age = models.IntegerField()
    breed = models.CharField(max_length=100)
    food_habit = models.CharField(max_length=100)
    potty_trained = models.BooleanField(default=False)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    image = models.ImageField(upload_to='pet_images/', blank=True, null=True)

    def __str__(self):
        return self.title

class AdoptionApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    pet = models.ForeignKey(PetAdoption, on_delete=models.CASCADE)
    applicant = models.ForeignKey(WebUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    id_document = models.ImageField(upload_to='id_documents/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    adoption_group = models.ForeignKey('AdoptionGroup', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} - {self.pet.title}"

class AdoptionGroup(models.Model):
    applicant = models.ForeignKey(WebUser, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Adoption Group for {self.applicant.username} at {self.timestamp}"
    
    def __str__(self):
        return self.title
    



