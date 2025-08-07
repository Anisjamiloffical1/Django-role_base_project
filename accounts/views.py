from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import CustomerForm, OrderForm, CreateUserForm
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
        role = request.POST.get('role')  # Get role from form

        user_obj = User.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=email,
        )
        user_obj.set_password(password)
        user_obj.save()

        group = Group.objects.get(name=role)
        user_obj.groups.add(group)

        # Create related profile if needed
        if role == 'customer':
            Customer.objects.create(user=user_obj)
        elif role == 'sales_rep':
            SalesRepresentative.objects.create(user=user_obj)
        elif role == 'designer':
            Designer.objects.create(user=user_obj)
        elif role == 'admin':
            Admin.objects.create(user=user_obj)

        messages.success(request, "Your account has been created successfully.")
        return redirect('login')
    return render(request, 'accounts/register.html')

@unauthenticated_user
def login_page(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user_obj = User.objects.filter(username=email).first()

        if not user_obj:
            messages.warning(request, 'Account not found.')
            return HttpResponseRedirect(request.path_info)

        user_obj = authenticate(username=email, password=password)

        if user_obj:
            login(request, user_obj)

            # 🔐 Redirect based on role
            group = None
            if user_obj.groups.exists():
                group = user_obj.groups.first().name

            if group == 'admin':
                return redirect('home')
            elif group == 'customer':
                return redirect('user-page')
            elif group == 'sales_rep':
                return redirect('sales-dashboard')
            elif group == 'designer':
                return redirect('designer-dashboard')
            else:
                messages.warning(request, "User group is not assigned.")
                return redirect('login')

        messages.warning(request, "Invalid credentials.")
        return HttpResponseRedirect(request.path_info)

    return render(request, 'accounts/login.html')

def logout_page(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')
@login_required(login_url='login')
@allowed_users(allowed_roles=['customer'])
def user_page(request):
    customer, created = Customer.objects.get_or_create(user=request.user)
    orders = request.user.customer.order_set.all()
    total_order = orders.count()
    delivered = orders.filter(status='Delivered').count()
    pending = orders.filter(status='Pending').count()
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
    OrderFormSet = inlineformset_factory(
        Customer,
        Order,
        fields=('product', 'order_type', 'status', 'note', 'design_file', 'invoice_file'),
        extra=6,
        can_delete=False
    )
    customer = Customer.objects.get(id=pk)

    if request.method == 'POST':
        formset = OrderFormSet(request.POST, request.FILES, instance=customer)
        if formset.is_valid():
            formset.save()
            return redirect('/')
    else:
        formset = OrderFormSet(queryset=Order.objects.none(), instance=customer)

    return render(request, 'accounts/order_form.html', {'formset': formset})

# this function is used to update the order
@login_required(login_url='login')
def updateOrder(request, pk):
    order = Order.objects.get(id=pk)
    
    if request.method == 'POST':
        #  Add request.FILES here to support file upload
        form = OrderForm(request.POST, request.FILES, instance=order)
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


@login_required(login_url='login')
@allowed_users(allowed_roles=['customer'])
def accountSettings(request):
    customer = request.user.customer
    form = CustomerForm(instance=customer)

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")

    context = {'form': form}
    return render(request, 'accounts/account_settings.html', context)


# this function is used to show the sales dashboard for sales representatives
@login_required(login_url='login')
@allowed_users(allowed_roles=['sales_rep'])
def sales_dashboard(request):
    sales_rep = request.user.salesrepresentative
    customers = Customer.objects.filter(sales_rep=sales_rep)

    orders = Order.objects.filter(customer__in=customers)

    total_customers = customers.count()
    total_orders = orders.count()
    delivered = orders.filter(status='Delivered').count()
    pending = orders.filter(status='Pending').count()

    context = {
        'customers': customers,
        'orders': orders,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'delivered': delivered,
        'pending': pending,
    }

    return render(request, 'accounts/sales_dashboard.html', context)

@login_required
def mark_completed(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = 'Completed'
    order.save()
    return redirect('sales-dashboard')


# --------
@login_required
def manage_customers(request):
    try:
        sales_rep = SalesRepresentative.objects.get(user=request.user)
    except SalesRepresentative.DoesNotExist:
        sales_rep = None

    customers = Customer.objects.filter(sales_rep=sales_rep)
    return render(request, 'accounts/sales/manage_customers.html', {'assigned_customers': customers})

@login_required
def release_projects(request):
    sales_rep = get_object_or_404(SalesRepresentative, user=request.user)

    # Filter orders assigned to this sales rep and with status 'Completed'
    completed_orders = Order.objects.filter(
        assigned_to=sales_rep,
        status='Completed'
    ).order_by('-date_created')
    print("Logged in as:", request.user)
    print("Sales Rep:", sales_rep)
    print("Completed Orders:", completed_orders)

    context = {
        'completed_orders': completed_orders
    }

    return render(request, 'accounts/sales/release_projects.html', context)


@login_required
def monitor_quotes(request):
    return render(request, 'accounts/sales/monitor_quotes.html')

@login_required
def track_orders(request):
    return render(request, 'accounts/sales/track_orders.html')

@login_required
def communicate_designers_admins(request):
    return render(request, 'accounts/sales/communicate.html')

@login_required
def follow_up_payments(request):
    return render(request, 'accounts/sales/follow_up.html')