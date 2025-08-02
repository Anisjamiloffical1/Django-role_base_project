from django.shortcuts import render
from .models import *

# Create your views here.
def home(request):
    orders = Order.objects.all()
    customers = Customer.objects.all()
    total_customers = customers.count()
    total_order = orders.count()
    delivered = orders.filter(status='Delivered').count()
    pending = orders.filter(status='Pending').count()
    context = {
        'orders': orders,
        'customers': customers,
        'total_customers' : total_customers,
        'total_order' : total_order,
        'delivered' : delivered,
        'pending' : pending

    }

    return render(request, 'accounts/dashboard.html', context=context)

def products(request):
    products = Product.objects.all()
    return render(request, 'accounts/products.html', {'products': products})

def customer(request, pk):
    customer = Customer.objects.get(id=pk)
    orders = customer.order_set.all()
    order_counter = orders.count()
    context ={
        'customer': customer,
        'orders' : orders,
        'order_counter': order_counter
    }
    return render(request, 'accounts/customer.html', context=context)