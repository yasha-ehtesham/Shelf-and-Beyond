from django.test import TestCase, Client
from django.urls import reverse
from .models import WebUser, Role, PetAdoption, AdoptionApplication, AdoptionGroup
from django.core.files.uploadedfile import SimpleUploadedFile

class AdoptionFeatureTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.role = Role.objects.create(role_name='normal_user')
        self.user = WebUser.objects.create(
            username='testuser',
            firstname='Test',
            lastname='User',
            email='test@example.com',
            phone='1234567890',
            gender='male',
            password='testpass',
            birthdate='1990-01-01',
            role=self.role
        )
        self.pet = PetAdoption.objects.create(
            seller=self.user,
            title='Test Pet',
            description='A lovely pet',
            age=2,
            breed='Labrador',
            food_habit='Dry food',
            potty_trained=True,
            gender='male',
            status='available'
        )
        self.client.session['user_id'] = self.user.web_user_id
        self.client.session.save()

    def test_add_to_basket(self):
        response = self.client.get(reverse('adopt'), {'basket_item': self.pet.listing_id})
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.pet.listing_id), self.client.session.get('basket', []))

    def test_view_basket(self):
        self.client.session['basket'] = [str(self.pet.listing_id)]
        self.client.session.save()
        response = self.client.get(reverse('view_basket'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pet.title)

    def test_adoption_checkout(self):
        self.client.session['basket'] = [str(self.pet.listing_id)]
        self.client.session.save()
        response = self.client.post(reverse('adoption_checkout'), {
            'name': 'Test User',
            'phone_number': '1234567890',
            'address': '123 Test St',
            'id_document': SimpleUploadedFile('id.jpg', b'file_content', content_type='image/jpeg')
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AdoptionApplication.objects.exists())
        self.assertTrue(AdoptionGroup.objects.exists())

    def test_view_adoption_history(self):
        group = AdoptionGroup.objects.create(applicant=self.user)
        AdoptionApplication.objects.create(
            pet=self.pet,
            applicant=self.user,
            name='Test User',
            phone_number='1234567890',
            address='123 Test St',
            id_document='id_documents/test.jpg',
            adoption_group=group
        )
        response = self.client.get(reverse('view_adoption_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pet.title)