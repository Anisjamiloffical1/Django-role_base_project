from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Customer(models.Model):
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=200 )
    sales_rep = models.ForeignKey('SalesRepresentative', null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_customers')
    profile_pic = models.ImageField(
        upload_to='profile_pics/',  # Images will be saved in MEDIA_ROOT/profile_pics/
        null=True,
        blank=True,
        default='profile_pics/default.png'  # Default image path
    )
    phone = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    def __str__(self):
        return self.name
class SalesRepresentative(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    def __str__(self):
        return self.user.username
    

class Designer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    def __str__(self):
        return self.user.username

class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    def __str__(self):
        return self.user.username
# this use for name string like show me customer name in admin panel
    
class Tag(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

# for the class product
class Product(models.Model):
    CATEGORY = (
        ('Indoor', 'Indoor'),
        ('Out Door', 'Out Door'),
    )
    name = models.CharField(max_length=200)
    price = models.FloatField(null=True)
    category = models.CharField(max_length=200, null=True, choices=CATEGORY)
    description = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    tags = models.ManyToManyField(Tag)
    def __str__(self):
        return self.name



    

    

# # this use for customer order

class Order(models.Model):
    STATUS = (
        ('Pending', 'Pending'),
        ('Out for delivery', 'Out for delivery'),
        ('Delivered', 'Delivered'),
        ('Quote Requested', 'Quote Requested'),
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Released', 'Released'),
    )
    ORDER_TYPE = (
        ('Digitizing', 'Digitizing'),
        ('Vector', 'Vector'),
        ('Patch', 'Patch'),
        ('Quote', 'Quote'),
    )
    PAYMENT_STATUS = (
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Refunded', 'Refunded'),
    )
    customer = models.ForeignKey(Customer, null=True, on_delete=models.SET_NULL)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    order_type = models.CharField(max_length=50, choices=ORDER_TYPE, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    status = models.CharField(max_length=200, null=True, choices=STATUS)
    note = models.CharField(max_length=1000, null=True, blank=True)
    design_file = models.FileField(upload_to='designs/', null=True, blank=True)
    invoice_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    status = models.CharField(max_length=200, null=True)
    assigned_to = models.ForeignKey('SalesRepresentative', on_delete=models.SET_NULL, null=True, blank=True)
    released = models.BooleanField(default=False)  # For release_projects
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Pending')  # For follow-up payments
    date_completed = models.DateTimeField(null=True, blank=True)  # Optional: track completion time



    def __str__(self):
        return f"{self.product.name if self.product else 'No product'} ({self.order_type})"
    
    