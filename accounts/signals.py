from django.db.models.signals import post_save
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from .models import *
from django.dispatch import receiver
from django.db.models.signals import post_migrate




def customer_profile(sender, instance, created, **kwargs):
    if created:
        group = Group.objects.get(name='customer')
        instance.groups.add(group)

        # Only create Customer, not another User
        Customer.objects.create(user=instance)
        print(f'Customer profile created for: {instance.username}')

def create_designer_group():
    group_name = "Designer"
    if not Group.objects.filter(name=group_name).exists():
        Group.objects.create(name=group_name)
        print(f"{group_name} group created successfully!")
    else:
        print(f"{group_name} group already exists.")