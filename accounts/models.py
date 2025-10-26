from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
# Create your models here.
class Customer(models.Model):
    user = models.OneToOneField(
        User, null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="customer_profile"
    )
    name = models.CharField(max_length=200)
    designer = models.ForeignKey(
        'Designer', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='orders'
    )
    profile_pic = models.ImageField(
        upload_to='profile_pics/',
        null=True,
        blank=True,
        default='profile_pics/default.png'
    )
    sales_rep = models.ForeignKey('SalesRepresentative', null=True, blank=True, on_delete=models.SET_NULL)

    phone = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.name


class SalesRepresentative(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="sales_rep_profile")
    name = models.CharField(max_length=200, null=True, blank=True)
    def __str__(self):
        return self.user.username

    def get_orders(self, status=None):
        qs = Order.objects.filter(customer__designer=self)  # optional, if you still want to fetch orders linked via designer
        if status:
            qs = qs.filter(status=status)
        return qs


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
    image = models.ImageField(upload_to='products/',null=True, blank=True) 
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
    PLACEMENT_CHOICES = [

        ('Apron', 'Apron'),
        ('Bags', 'Bags'),
        ('Cap', 'Cap'),
        ('Cap Side', 'Cap Side'),
        ('Cap Back', 'Cap Back'),
        ('Chest', 'Chest'),
        ('Gloves', 'Gloves'),
        ('Jacket Back', 'Jacket Back'),
        ('Patches', 'Patches'),
        ('Sleeve', 'Sleeve'),
        ('Towel', 'Towel'),
        ('Visor', 'Visor'),
        ('Other', 'Other'),
    ]
    FABRIC_CHOICES = [
        ('Blanket', 'Blanket'),
        ('Canvas', 'Canvas'),
        ('Canis', 'Canis'),
        ('Cotton Woven', 'Cotton Woven'),
        ('Denim', 'Denim'),
        ('Felt', 'Felt'),
        ('Flannel', 'Flannel'),
        ('Fleece', 'Fleece'),
        ('Leather', 'Leather'),
        ('Nylon', 'Nylon'),
        ('Pique', 'Pique'),
        ('Polyester', 'Polyester'),
        ('Silk', 'Silk'),
        ('Single Jersey', 'Single Jersey'),
        ('Towel', 'Towel'),
        ('Twill', 'Twill'),
        ('Other', 'Other'),
    ]
    FORMAT_CHOICES = [
        ('100', '100'),
        ('cdr', 'cdr'),
        ('cdn', 'cdn'),
        ('dsb', 'dsb'),
        ('dst', 'dst'),
        ('dsz', 'dsz'),
        ('emb', 'emb'),
        ('exp', 'exp'),
        ('jef', 'jef'),
        ('ksm', 'ksm'),
        ('ofm', 'ofm'),
        ('pes', 'pes'),
        ('pxf', 'pxf'),
        ('pof', 'pof'),
        ('tap', 'tap'),
        ('xxx', 'xxx'),
        ('other', 'Other'),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    order_type = models.CharField(max_length=50, choices=ORDER_TYPE, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    status = models.CharField(max_length=200, null=True, choices=STATUS)
    Additional_information = models.TextField(blank=True, null=True)
    design_file = models.FileField(upload_to='designs/', null=True, blank=True)
    invoice_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    fabric_material = models.CharField(max_length=100, blank=True, null=True, choices=FABRIC_CHOICES)
    Required_Format = models.CharField(max_length=100, blank=True, null=True, default='DST', choices=FORMAT_CHOICES)
    urgent = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0.00)
    Height = models.CharField(max_length=100, blank=True, null=True, default='standard')
    Width = models.CharField(max_length=100, blank=True, null=True, default='standard')
    total_colors = models.PositiveIntegerField(null=True ,blank=True)
    turnaround_time = models.CharField(max_length=100, blank=True, null=True)
    placement = models.CharField(max_length=100, blank=True, null=True, choices=PLACEMENT_CHOICES)
    released = models.BooleanField(default=False)  # For release_projects
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Pending')  # For follow-up payments
    date_completed = models.DateTimeField(null=True, blank=True)  # Optional: track completion time
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS, default='Pending')
    review_comment = models.TextField(blank=True, null=True)
    design_file = models.FileField(upload_to='designs/', blank=True, null=True)
    assigned_designer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='designer_orders')
    def save(self, *args, **kwargs):
        if self.customer and not self.assigned_designer:
        # auto-assign the designer from the customer
            if self.customer.designer:
            # if Designer model links to User:
                self.assigned_designer = self.customer.designer.user
            # OR if it links directly to User (depending on your model):
            # self.assigned_designer = self.customer.designer
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name if self.product else 'No product'} ({self.order_type})"
    
# class Invoice(models.Model):
#     order = models.ForeignKey(related_name='')
#     file_ppath = models.CharField
    
class UploadedFile(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

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

# for feed back 
class Feedback(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="feedbacks")
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Invoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('customer', 'year', 'month')  # one invoice per customer per month
        ordering = ['-year', '-month']

    def __str__(self):
        return f"Invoice: {self.customer.name} - {self.month}/{self.year}"

    def calculate_total(self):
        """Calculate total from all completed orders for that month"""
        total = Order.objects.filter(
            customer=self.customer,
            status="Completed",
            created_at__year=self.year,
            created_at__month=self.month
        ).aggregate(Sum('price'))['price__sum'] or 0
        self.total_amount = total
        self.save()
        return self.total_amount
    
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.groups.filter(name="SalesRepresentative").exists():
            SalesRepresentative.objects.create(user=instance, name=instance.username)
        elif instance.groups.filter(name="Customer").exists():
            Customer.objects.create(user=instance, name=instance.username)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "sales_rep_profile"):
        instance.sales_rep_profile.save()
    if hasattr(instance, "customer_profile"):
        instance.customer_profile.save()