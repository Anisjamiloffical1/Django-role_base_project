from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import OrderForm, CreateUserForm
from django.forms import inlineformset_factory
from .filters import OrderFilter
from django.contrib.auth.forms import UserCreationForm

# Create your views here.
def register_page(request):
    form = CreateUserForm()
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CreateUserForm()
    context = {'form': form}
    return render(request, 'accounts/register.html', context)


def login_page(request):
   
        
    context = {}
    return render(request, 'accounts/login.html')
# this function is used to show the home page
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
# create a function to show the products
def products(request):
    products = Product.objects.all()
    return render(request, 'accounts/products.html', {'products': products})
# # this function is used to show the customer details and their orders
def customer(request, pk):
    customer = Customer.objects.get(id=pk)
    orders = customer.order_set.all()
    order_counter = orders.count()
    myFilter = OrderFilter(request.GET, queryset=orders)
    orders = myFilter.qs  # Apply the filter to the queryset
    context ={
        'customer': customer,
        'orders' : orders,
        'order_counter': order_counter,
        'myFilter': myFilter
    }
    return render(request, 'accounts/customer.html', context=context)
# the commit function for just 1 item in the formset create 
def createOrder(request, pk):
    OrderFormSet = inlineformset_factory(Customer, Order, fields=('product', 'status') ,extra=6)
    customer = Customer.objects.get(id=pk)
    formset = OrderFormSet(queryset=Order.objects.none(), instance=customer) 
    # form = OrderForm()
    if request.method == 'POST':
        # form = OrderForm(request.POST)
        formset = OrderFormSet(request.POST, instance=customer)
        if formset.is_valid():
            formset.save()
            return redirect('/')
        # if form.is_valid():
            # form.save()
            # return redirect('/')
    else: 
        form = OrderForm(initial={'customer': customer})
    return render(request, 'accounts/order_form.html', {'formset': formset})

# this function is used to update the order
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

# this function is used to delete the order
def delete_order(request, pk):
    order = Order.objects.get(id=pk)
    if request.method == 'POST':
        order.delete()
        return redirect('/')
    context = {'item': order}
    return render(request, 'accounts/delete.html', context)