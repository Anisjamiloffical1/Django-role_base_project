from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Tag)
admin.site.register(SalesRepresentative)
admin.site.register(Designer)
admin.site.register(Admin)
admin.site.register(UploadedFile)
admin.site.register(SiteSetting)
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product', 'order_type', 'status', 'date_created')
    list_filter = ('status', 'order_type')
