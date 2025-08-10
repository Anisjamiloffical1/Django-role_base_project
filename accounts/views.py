from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import CustomerForm, OrderForm, CreateUserForm, SiteSettingForm
from django.forms import inlineformset_factory
from django.contrib import messages
from django.utils.dateparse import parse_date
from django.http import FileResponse
from .filters import OrderFilter
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.forms import UserCreationForm 
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .decorators import unauthenticated_user, allowed_users, admin_only
from django.contrib.auth.models import Group
from django.db.models import Count, Sum, Q

from io import BytesIO
import csv


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

            #  Redirect based on role
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
# this are the functions to manage the settings of the site
@login_required(login_url='login')
@allowed_users(['admin'])
def manage_settings(request):
    setting, created = SiteSetting.objects.get_or_create(id=1)
    
    if request.method == 'POST':
        form = SiteSettingForm(request.POST, request.FILES, instance=setting)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated successfully.")
            return redirect('manage_settings')
    else:
        form = SiteSettingForm(instance=setting)

    return render(request, 'accounts/manage_settings.html', {'form': form})
def some_view(request):
    settings = SiteSetting.objects.all().first()
    return render(request, 'accounts/sitting_template.html', {'settings': settings})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def manage_users(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'accounts/admin/manage_users.html', {'users': users})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def edit_user(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user_obj.first_name = request.POST.get('first_name')
        user_obj.last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        if User.objects.exclude(pk=user_obj.pk).filter(username=email).exists():
            messages.error(request, "Email already in use.")
        else:
            user_obj.email = email
            user_obj.username = email  # keep username synced
            role = request.POST.get('role')
            user_obj.groups.clear()
            group = Group.objects.get(name=role)
            user_obj.groups.add(group)
            user_obj.save()
            messages.success(request, "User updated successfully.")
            return redirect('manage_users')

    current_role = user_obj.groups.first().name if user_obj.groups.exists() else None
    return render(request, 'accounts/admin/edit_user.html', {'user_obj': user_obj, 'current_role': current_role})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def delete_user(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user_obj.delete()
        messages.success(request, "User deleted successfully.")
        return redirect('manage_users')
    return render(request, 'accounts/admin/delete_user.html', {'user_obj': user_obj})

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
    # Get one customer (just an example)
    customer = Customer.objects.first()

    # Get all orders for that customer, ordered by newest first
    all_orders = Order.objects.filter(customer=customer).order_by('-date_created')

    # Slice the last 5 orders for showing in template
    last_five_orders = all_orders[:5]

    # Get all customers and last 5 users (example)
    customers = Customer.objects.all().order_by('-date_created')[:5]
    users = User.objects.all().order_by('-date_joined')[:5]

    # Counts on all orders (not sliced)
    total_orders = all_orders.count()
    delivered_orders = all_orders.filter(status='Delivered').count()
    pending_orders = all_orders.filter(status='Pending').count()

    context = {
        'orders': last_five_orders,    # only last 5 for display
        'customers': customers,
        'users': users,
        'total_customers': customers.count(),
        'total_order': total_orders,
        'delivered': delivered_orders,
        'pending': pending_orders,
        'customer': customer
    }

    return render(request, 'accounts/dashboard.html', context)
def upload_file(request, order_id):
    order = Order.objects.get(id=order_id)

    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        UploadedFile.objects.create(order=order, file=file)
        return redirect('some_view')

    return render(request, 'upload.html', {'order': order})

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def review_file(request, pk):
    print(f"Received pk: {pk}")
    
    # Get the uploaded file
    uploaded_file = get_object_or_404(UploadedFile, pk=pk)
    
    # Get its parent order
    order = uploaded_file.order  

    if request.method == 'POST':
        status = request.POST.get('status')
        comment = request.POST.get('comment')

        order.review_status = status
        order.review_comment = comment
        order.save()
        return redirect('home')

    return render(request, 'accounts/review_file.html', {
        'order': order,
        'file': uploaded_file
    })
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
def createOrder(request, pk, order_type=None):
    OrderFormSet = inlineformset_factory(
        Customer,
        Order,
        fields=('product', 'order_type', 'status', 'note', 'design_file', 'invoice_file'),
        extra=6,
        can_delete=False
    )

    customer = get_object_or_404(Customer, id=pk)

    if request.method == 'POST':
        formset = OrderFormSet(request.POST, request.FILES, instance=customer)

        if formset.is_valid():
            formset.save()
            return redirect('home')

    else:
        
        initial_data = [{'order_type': order_type}] * 6 if order_type else [{}] * 6

        formset = OrderFormSet(
            queryset=Order.objects.none(),
            instance=customer,
            initial=initial_data
        )

    return render(request, 'accounts/order_form.html', {
        'formset': formset,
        'order_type': order_type
    })
@login_required
def orderHistory(request):
    customer = get_object_or_404(Customer, user=request.user)
    orders = Order.objects.filter(customer=customer).order_by('-date_created')
    return render(request, 'accounts/order_history.html', {'orders': orders})

@login_required
def downloadDesign(request, pk):
    order = get_object_or_404(Order, id=pk, customer__user=request.user)
    if order.design_file:
        return redirect(order.design_file.url)
    return redirect('order_history')

@login_required
def downloadInvoice(request, pk):
    order = get_object_or_404(Order, id=pk, customer__user=request.user)
    if order.invoice_file:
        return redirect(order.invoice_file.url)
    return redirect('order_history')

@login_required
def printInvoice(request, pk):
    order = get_object_or_404(Order, id=pk, customer__user=request.user)
    return render(request, 'accounts/print_invoice.html', {'order': order})

def order_invoice(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if order.invoice_file:
        return FileResponse(order.invoice_file.open(), as_attachment=False)
    else:
        return HttpResponse("No invoice found", status=404)

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

def updateCustomer(request, pk):
    customer = get_object_or_404(Customer, id=pk)
    form = CustomerForm(instance=customer)

    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            return redirect('customer', pk=customer.id)  # or your detail view name

    return render(request, 'accounts/customer_form.html', {
        'form': form,
        'customer': customer 
    })
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def createCustomer(request):
    form = CustomerForm()
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manage_customers') 
    context = {'form': form}
    return render(request, 'accounts/create_customer_form.html', context)


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
def order_detail(request, pk):
    order = get_object_or_404(Order, id=pk)
    return render(request, 'accounts/order_detail.html', {'order': order})
@login_required
def release_order(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        order.status = 'Released'  # or whatever status you use
        order.save()
        messages.success(request, f"Order #{order.id} has been released successfully!")
    
    return redirect('release_projects')  # Redirect back to list

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
    # Only show orders assigned to the logged-in sales rep
    quote_requests = Order.objects.filter(
        assigned_to__user=request.user,
        status="Quote Requested"
    ).order_by('-date_created')

    active_orders = Order.objects.filter(
        assigned_to__user=request.user,
        status="Active"
    ).order_by('-date_created')

    context = {
        'quote_requests': quote_requests,
        'active_orders': active_orders,
    }
    return render(request, 'accounts/sales/monitor_quotes.html', context)

@login_required
def track_orders(request):
    return render(request, 'accounts/sales/track_orders.html')

@login_required
def communicate_designers_admins(request):
    return render(request, 'accounts/sales/communicate.html')

@login_required
def follow_up_payments(request):
    return render(request, 'accounts/sales/follow_up.html')
# this area is used to generate reports for admin and sales reps , 
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'sales_rep'])
def report_view(request):
    # Get filter inputs from GET params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    sales_rep_username = request.GET.get('sales_rep')

    orders = Order.objects.all()

    # Filter by date range if provided
    if start_date:
        orders = orders.filter(date_created__date__gte=parse_date(start_date))
    if end_date:
        orders = orders.filter(date_created__date__lte=parse_date(end_date))

    # Filter by sales rep username if provided
    if sales_rep_username:
        orders = orders.filter(assigned_to__user__username=sales_rep_username)

    # Aggregate orders count by status (after filters)
    orders_by_status = orders.values('status').annotate(count=Count('id'))

    # Build Q filter for revenue_by_sales_rep aggregation
    filter_q = Q(assigned_customers__order__status='Completed')

    if start_date:
        filter_q &= Q(assigned_customers__order__date_created__date__gte=parse_date(start_date))
    if end_date:
        filter_q &= Q(assigned_customers__order__date_created__date__lte=parse_date(end_date))
    if sales_rep_username:
        filter_q &= Q(assigned_customers__order__assigned_to__user__username=sales_rep_username)

    # Aggregate revenue and completed orders by sales rep (after filters)
    revenue_by_sales_rep = (
        SalesRepresentative.objects
        .annotate(
            total_revenue=Sum('assigned_customers__order__product__price', filter=filter_q),
            total_orders=Count('assigned_customers__order', filter=filter_q)
        )
        .values('user__username', 'total_revenue', 'total_orders')
    )

    # For filter dropdown, get all sales rep usernames
    all_sales_reps = SalesRepresentative.objects.all().values_list('user__username', flat=True)

    context = {
        'orders_by_status': orders_by_status,
        'revenue_by_sales_rep': revenue_by_sales_rep,
        'all_sales_reps': all_sales_reps,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'sales_rep_username': sales_rep_username,
        }
    }
    return render(request, 'accounts/report.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'sales_rep'])
def export_report_csv(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    sales_rep_username = request.GET.get('sales_rep')

    def clean_val(val):
        if val and val.lower() != 'none':
            return val
        return None

    start_date = clean_val(start_date)
    end_date = clean_val(end_date)
    sales_rep_username = clean_val(sales_rep_username)

    orders = Order.objects.all()
    if start_date:
        orders = orders.filter(date_created__date__gte=parse_date(start_date))
    if end_date:
        orders = orders.filter(date_created__date__lte=parse_date(end_date))
    if sales_rep_username:
        orders = orders.filter(assigned_to__user__username=sales_rep_username)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="report.csv"'

    writer = csv.writer(response)

    # Write Report Title & Filter Info
    writer.writerow(['Order Report'])
    filters_applied = []
    if start_date:
        filters_applied.append(f"Start Date: {start_date}")
    if end_date:
        filters_applied.append(f"End Date: {end_date}")
    if sales_rep_username:
        filters_applied.append(f"Sales Rep: {sales_rep_username}")
    writer.writerow(filters_applied)
    writer.writerow([])

    # Section 1: Orders by Status
    writer.writerow(['Orders by Status'])
    writer.writerow(['Status', 'Number of Orders'])
    orders_by_status = orders.values('status').annotate(count=Count('id')).order_by('status')
    for item in orders_by_status:
        writer.writerow([item['status'], item['count']])
    writer.writerow([])

    # Section 2: Revenue & Completed Orders by Sales Rep
    writer.writerow(['Sales Representative Summary'])
    writer.writerow(['Sales Representative', 'Completed Orders', 'Total Revenue'])

    q_filters = Q(assigned_customers__order__status='Completed')
    if start_date:
        q_filters &= Q(assigned_customers__order__date_created__gte=parse_date(start_date))
    if end_date:
        q_filters &= Q(assigned_customers__order__date_created__lte=parse_date(end_date))
    if sales_rep_username:
        q_filters &= Q(assigned_customers__order__assigned_to__user__username=sales_rep_username)

    revenue_by_sales_rep = (
        SalesRepresentative.objects
        .annotate(
            total_revenue=Sum('assigned_customers__order__product__price', filter=q_filters),
            total_orders=Count('assigned_customers__order', filter=q_filters),
        )
        .values('user__username', 'total_revenue', 'total_orders')
        .order_by('user__username')
    )

    for rep in revenue_by_sales_rep:
        writer.writerow([
            rep['user__username'],
            rep['total_orders'] or 0,
            f"${rep['total_revenue']:.2f}" if rep['total_revenue'] else "$0.00",
        ])
    writer.writerow([])

    # Section 3: Overall Totals
    writer.writerow(['Overall Totals'])
    total_orders = orders.count()
    total_completed_orders = orders.filter(status='Completed').count()
    total_revenue = orders.filter(status='Completed').aggregate(
        total=Sum('product__price')
    )['total'] or 0
    writer.writerow(['Total Orders', total_orders])
    writer.writerow(['Total Completed Orders', total_completed_orders])
    writer.writerow(['Total Revenue', f"${total_revenue:.2f}"])

    return response