from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User
from .models import *
from django.contrib.auth.models import User, Group
import os

class CustomerForm(ModelForm):
    sales_rep = forms.ModelChoiceField(
        queryset=SalesRepresentative.objects.all(),
        required=True,
        label="Assign Sales Representative"
    )

    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'profile_pic', 'sales_rep']

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
    receiver = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name__in=["designer", "sales_rep"]),
        label="Send To"
    )
    content = forms.CharField(widget=forms.Textarea, label="Message")



class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write your feedback...'})
        }
class SalesRepMessageForm(forms.ModelForm):
    class Meta:
        model = DesignerMessage
        fields = ["receiver", "message"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Limit receivers to Admins + Designers
        self.fields["receiver"].queryset = User.objects.filter(
            groups__name__in=["admin", "designer"]
        )
class VectorOrderForm(forms.ModelForm):
    Vector_name = forms.CharField(
        label='Vector Name / PO *',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Vector Name or PO'})
    )

    class Meta:
        model = Order
        fields = [
            'Vector_name',           # custom field (not in model)
            'Required_Format',
            'total_colors',
            'Additional_information',
            'design_file',
            'urgent',
        ]

        widgets = {
            'Required_Format': forms.Select(choices=[
                ('ai', 'AI'),
                ('cdr', 'CDR'),
                ('eps', 'EPS'),
                ('others', 'Others'),
            ]),
            'Additional_information': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'Required_Format': 'Required Format *',
            'total_colors': 'Total Colors',
            'Additional_information': 'Additional Information',
            'design_file': 'Attachment',
            'urgent': 'Let us know if this vector is super RUSH!',
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Assign custom field value (store in Additional_information or a related place)
        instance.Additional_information = f"Vector Name/PO: {self.cleaned_data.get('Vector_name')}\n{instance.Additional_information or ''}"
        instance.order_type = 'Vector'
        if commit:
            instance.save()
        return instance
    
class DigitizingOrderForm(ModelForm):
    class Meta:
        model = Order
        fields = [
            'product',
            'quantity',
            'urgent',
            'Required_Format',
            'turnaround_time',
            'fabric_material',
            'total_colors',
            'placement',
            'Height',
            'Width',
            'Additional_information',
            'design_file',
        ]


class VectorOrderForm(ModelForm):
    class Meta:
        model = Order
        fields = [
            'Required_Format',
            'total_colors',
            'urgent',
            'Additional_information',
            'design_file',
        ]


class PatchOrderForm(ModelForm):
    class Meta:
        model = Order
        fields = [
            'quantity',
            'Height',
            'Width',
            'fabric_material',
            'urgent',
            'Additional_information',
            'design_file',
        ]


class QuoteOrderForm(ModelForm):
    class Meta:
        model = Order
        fields = [
            'product',
            'quantity',
            'Additional_information',
        ]