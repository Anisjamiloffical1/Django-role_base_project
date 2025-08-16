from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User
from .models import *
from django.contrib.auth.models import User, Group
import os

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
        fields = ['design_file', 'status',]

class DesignerMessageForm(forms.ModelForm):
    class Meta:
        model = DesignerMessage
        fields = ['receiver', 'order', 'subject', 'message', 'attachment']  # Now includes attachment
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'receiver': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.Select(attrs={'class': 'form-control'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),  # Add this
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Get users only in sales_rep or admin groups
        sales_group = Group.objects.get(name='sales_rep')
        admin_group = Group.objects.get(name='admin')
        allowed_users = User.objects.filter(groups__in=[sales_group, admin_group]).distinct()
        self.fields['receiver'].queryset = allowed_users
        
        # Filter orders to only those assigned to current designer
        if user and user.groups.filter(name='designer').exists():
            self.fields['order'].queryset = Order.objects.filter(
                assigned_designer=user
            )
        else:
            self.fields['order'].queryset = Order.objects.none()

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            # Validate file size (5MB max)
            max_size = 5 * 1024 * 1024
            if attachment.size > max_size:
                raise forms.ValidationError("File too large (max 5MB)")
            
            # Validate file types
            valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.ai', '.eps']
            ext = os.path.splitext(attachment.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError("Unsupported file type. Allowed: PDF, JPG, PNG, AI, EPS")
        return attachment
class AdminSendMessageForm(forms.Form):
    receiver = forms.ModelChoiceField(queryset=User.objects.filter(groups__name='designer'), label="Send To")
    content = forms.CharField(widget=forms.Textarea, label="Message")