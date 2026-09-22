from django.conf import settings
import smtplib
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class EmailDeliveryNotConfigured(Exception):
    """Raised before attempting SMTP when no sender credentials exist."""


def email_delivery_error(error):
    """Show actionable delivery errors without exposing SMTP replies or credentials."""
    if isinstance(error, EmailDeliveryNotConfigured):
        return 'Email sender settings are missing. Run configure_email and restart the server.'
    if isinstance(error, smtplib.SMTPAuthenticationError):
        return 'Gmail rejected the sender login. Run configure_email with a current App Password, then restart the server.'
    if isinstance(error, smtplib.SMTPRecipientsRefused):
        return 'The email provider rejected the recipient address. Check your email address and try again.'
    if isinstance(error, smtplib.SMTPSenderRefused):
        return 'The email provider rejected the sender address. The sender must match your configured Gmail account.'
    if isinstance(error, smtplib.SMTPDataError):
        return 'The email provider rejected the verification message. Check the sender account for sending limits or security alerts.'
    if isinstance(error, (OSError, smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError)):
        return 'Cannot connect to the email provider. Check your internet connection and try again.'
    return 'Unable to send the verification email (error type: ' + type(error).__name__ + '). Please report this error type.'


def send_verification_email(request, user):
    """Send an expiring activation link for a newly registered customer."""
    if (
        settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend'
        and (not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD)
    ):
        raise EmailDeliveryNotConfigured(
            'SMTP sender credentials have not been configured.'
        )

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verification_path = reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
    public_base_url = settings.PUBLIC_BASE_URL.rstrip('/')
    verification_url = (
        f'{public_base_url}{verification_path}'
        if public_base_url else request.build_absolute_uri(verification_path)
    )
    context = {'user': user, 'verification_url': verification_url}
    text_body = render_to_string('emails/verify_email.txt', context)
    html_body = render_to_string('emails/verify_email.html', context)

    message = EmailMultiAlternatives(
        subject='Verify your Hajaz Hijab account',
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(html_body, 'text/html')
    if message.send(fail_silently=False) != 1:
        raise RuntimeError('The email backend did not accept the verification email.')
