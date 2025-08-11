from django.contrib.auth.models import User
from .models import Notification

def notify_user(user, message, order=None):
    """Create and send a notification to a user"""
    Notification.objects.create(
        user=user,
        message=message,
        order=order
    )
    # Optional: Add email/signal logic here

def get_unread_count(user):
    return Notification.objects.filter(user=user, is_read=False).count()