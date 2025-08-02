from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import OrderForm

# Create your views here.
def home(request):
    customer = Customer.objects.first()
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
        'pending' : pending,
        'customer': customer

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

def createOrder(request, pk):
    customer = Customer.objects.get(id=pk)
    form = OrderForm()
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')
    else: 
        form = OrderForm(initial={'customer': customer})
    return render(request, 'accounts/order_form.html', {'form': form})


def updateOrder(request, pk):
    order = Order.objects.get(id=pk)
    form = OrderForm(instance=order)
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect('/')
    else:
        form = OrderForm(instance=order)
    context = {'form': form}



    return render(request, 'accounts/order_form.html', context)


def delete_order(request, pk):
    order = Order.objects.get(id=pk)
    if request.method == 'POST':
        order.delete()
        return redirect('/')
    context = {'item': order}
    return render(request, 'accounts/delete.html', context)