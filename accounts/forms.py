from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User
from .models import *
from django.contrib.auth.models import User, Group

class CustomerForm(ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'
        exclude = ['user']

class OrderForm(ModelForm):
    class Meta:
        model = Order        
        fields = '__all__'

class CreateUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class SiteSettingForm(forms.ModelForm):
    class Meta:
        model = SiteSetting
        fields = '__all__'



class DesignFileForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['design_file', 'status']

class DesignerMessageForm(forms.ModelForm):
    class Meta:
        model = DesignerMessage
        fields = ['receiver', 'order', 'subject', 'message']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'receiver': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get users only in sales_rep or admin groups
        sales_group = Group.objects.get(name='sales_rep')
        admin_group = Group.objects.get(name='admin')
        allowed_users = User.objects.filter(groups__in=[sales_group, admin_group]).distinct()
        self.fields['receiver'].queryset = allowed_users