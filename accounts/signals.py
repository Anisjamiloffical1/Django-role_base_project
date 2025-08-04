from django.db.models.signals import post_save
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from .models import *


def customer_profile(sender, instance, created, **kwargs):
    if created:
        group = Group.objects.get(name='customer')
        instance.groups.add(group)

        # Only create Customer, not another User
        Customer.objects.create(user=instance)
        print(f'Customer profile created for: {instance.username}')