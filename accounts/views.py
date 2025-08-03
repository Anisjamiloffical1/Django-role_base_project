from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import OrderForm, CreateUserForm
from django.forms import inlineformset_factory
from django.contrib import messages
from .filters import OrderFilter
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .decorators import unauthenticated_user, allowed_users, admin_only
from django.contrib.auth.models import Group

# Create your views here.
@unauthenticated_user
def register_page(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_obj = User.objects.create(first_name=first_name, last_name=last_name, email=email, username=email)
        user_obj.set_password(password)
        user_obj.save()
        group = Group.objects.get(name='customer')
        user_obj.groups.add(group)
        Customer.objects.create(user=user_obj)
        messages.success(request, "You Account Created been successfully.")
        return redirect('login')
    return render(request, 'accounts/register.html')

@unauthenticated_user
def login_page(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_obj = User.objects.filter(username = email)
        if not user_obj.exists():
            messages.warning(request, 'Account not Found')
            return HttpResponseRedirect(request.path_info)    
        user_obj = authenticate(username = email , password = password)
        if user_obj:
            login(request, user_obj)
            return redirect('home')
        messages.warning(request, "invalid Creadentials")
        return HttpResponseRedirect(request.path_info)
    return render(request, 'accounts/login.html')

def logout_page(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')
@login_required(login_url='login')
@allowed_users(allowed_roles=['customer'])
def user_page(request):
    orders = request.user.customer.order_set.all()
    total_order = orders.count()
    delivered = orders.filter(status='Delivered').count()
    pending = orders.filter(status='Pending').count()
    print('orders', orders,)
    context = {'orders': orders,
               'total_order': total_order,
               'delivered': delivered,
               'pending': pending}
    return render(request, 'accounts/user.html', context)

# this function is used to show the home page
@login_required(login_url='login')
@admin_only
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
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def products(request):
    products = Product.objects.all()
    return render(request, 'accounts/products.html', {'products': products})
# # this function is used to show the customer details and their orders
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
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
@login_required(login_url='login')
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
@login_required(login_url='login')
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
@login_required(login_url='login')
def delete_order(request, pk):
    order = Order.objects.get(id=pk)
    if request.method == 'POST':
        order.delete()
        return redirect('/')
    context = {'item': order}
    return render(request, 'accounts/delete.html', context)