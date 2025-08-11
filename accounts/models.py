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
    REVIEW_STATUS = (
    ('Pending', 'Pending'),
    ('Approved', 'Approved'),
    ('Rejected', 'Rejected'),
)
    customer = models.ForeignKey(Customer, null=True, on_delete=models.SET_NULL)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    order_type = models.CharField(max_length=50, choices=ORDER_TYPE, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    status = models.CharField(max_length=200, null=True, choices=STATUS)
    note = models.CharField(max_length=1000, null=True, blank=True)
    design_file = models.FileField(upload_to='designs/', null=True, blank=True)
    invoice_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    
    assigned_to = models.ForeignKey('SalesRepresentative', on_delete=models.SET_NULL, null=True, blank=True)
    released = models.BooleanField(default=False)  # For release_projects
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Pending')  # For follow-up payments
    date_completed = models.DateTimeField(null=True, blank=True)  # Optional: track completion time
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS, default='Pending')
    review_comment = models.TextField(blank=True, null=True)
    design_file = models.FileField(upload_to='designs/', blank=True, null=True)
    assigned_designer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='designer_orders')


    def __str__(self):
        return f"{self.product.name if self.product else 'No product'} ({self.order_type})"
    
class UploadedFile(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for {self.order} uploaded at {self.uploaded_at}"
    
class SiteSetting(models.Model):
    site_name = models.CharField(max_length=255, default="My Company")
    contact_email = models.EmailField(default="info@example.com")
    logo = models.ImageField(upload_to='settings/', null=True, blank=True)
    enable_notifications = models.BooleanField(default=True)
    default_order_status = models.CharField(max_length=100, default='Pending')
    
    def __str__(self):
        return "Site Settings"

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"

class DesignerMessage(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to='message_attachments/', null=True, blank=True) 
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.sender} to {self.receiver} - {self.subject}"
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)

def get_unread_notifications_count(self):
    return self.notification_set.filter(is_read=False).count()

User.add_to_class('unread_notifications_count', property(get_unread_notifications_count))
    