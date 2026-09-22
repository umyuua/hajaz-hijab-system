import re
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.core.management import call_command

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Customer, Notification


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sender@example.com",
    PUBLIC_BASE_URL="http://testserver",
)
class EmailVerificationTests(TestCase):
    signup_data = {
        "username": "newcustomer",
        "full_name": "New Customer",
        "email": "customer@example.com",
        "phone": "0123456789",
        "password": "password1",
        "confirm_password": "password1",
    }

    def test_signup_sends_verification_email_and_link_activates_user(self):
        response = self.client.post(reverse("register"), self.signup_data)

        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(email="customer@example.com")
        self.assertFalse(user.is_active)
        self.assertTrue(Customer.objects.filter(user=user).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["customer@example.com"])

        match = re.search(r"http://testserver(/verify-email/\S+)", mail.outbox[0].body)
        self.assertIsNotNone(match)
        verification_response = self.client.get(match.group(1))

        self.assertRedirects(verification_response, reverse("login"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_unverified_user_cannot_login(self):
        self.client.post(reverse('register'), self.signup_data)
        self.client.post(reverse('login'), {
            'username': 'newcustomer', 'password': 'password1',
        })
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_resend_and_public_url(self):
        self.client.post(reverse('register'), self.signup_data)
        with override_settings(PUBLIC_BASE_URL='https://shop.example.com'):
            self.client.post(reverse('resend_verification'), {
                'email': 'customer@example.com',
            })
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('https://shop.example.com/verify-email/', mail.outbox[-1].body)

    def test_invalid_link_does_not_activate(self):
        self.client.post(reverse('register'), self.signup_data)
        self.client.get(reverse('verify_email', kwargs={'uidb64': 'invalid', 'token': 'invalid'}))
        self.assertFalse(User.objects.get(username='newcustomer').is_active)

    def test_email_required(self):
        data = dict(self.signup_data, email='')
        self.client.post(reverse('register'), data)
        self.assertFalse(User.objects.filter(username='newcustomer').exists())

    def test_notification_email_after_commit(self):
        user = User.objects.create_user('verified', email='customer@example.com')
        with self.captureOnCommitCallbacks(execute=True):
            Notification.objects.create(user=user, message='Your order has shipped.')
            self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].body, 'Your order has shipped.')

    def test_configuration_checks_sender_and_saves_locally(self):
        with tempfile.TemporaryDirectory() as directory:
            with override_settings(BASE_DIR=Path(directory)), \
                 patch('builtins.input', side_effect=['sender@example.com', 'https://shop.example.com']), \
                 patch('getpass.getpass', return_value='app password'), \
                 patch('store.management.commands.configure_email.get_connection') as connection:
                call_command('configure_email', skip_checks=True)
                connection.return_value.open.assert_called_once()
                connection.return_value.close.assert_called_once()
                config = json.loads((Path(directory) / 'email_config.local.json').read_text())
                self.assertEqual(config['EMAIL_HOST_USER'], 'sender@example.com')
                self.assertEqual(config['PUBLIC_BASE_URL'], 'https://shop.example.com')
