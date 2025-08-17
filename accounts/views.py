from django.utils import timezone 
from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import CustomerForm, OrderForm, CreateUserForm, SiteSettingForm, DesignFileForm,DesignerMessageForm,AdminSendMessageForm
from django.forms import inlineformset_factory
from django.contrib import messages
from django.utils.dateparse import parse_date
from django.http import FileResponse, JsonResponse
from .filters import OrderFilter
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.forms import UserCreationForm 
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .decorators import unauthenticated_user, allowed_users, admin_only
from django.contrib.auth.models import Group
from .notifications import notify_user
from django.template.loader import render_to_string
from weasyprint import HTML
from django.core.mail import send_mail
import os
from django.conf import settings
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
# admin message recive
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def admin_inbox(request):
    messages_received = DesignerMessage.objects.filter(receiver=request.user).order_by('-timestamp')
    unread_count = messages_received.filter(is_read=False).count()
    context = {
        'messages': messages_received,
        'unread_count': unread_count,
    }
    return render(request, 'accounts/admin_inbox.html', context)

@login_required
@allowed_users(allowed_roles=['admin', 'designer'])
def view_message(request, pk):
    message = get_object_or_404(DesignerMessage, pk=pk, receiver=request.user)

    # Mark message as read
    if not message.is_read:
        message.is_read = True
        message.save()

    return render(request, 'accounts/view_message.html', {'message': message})
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
    # Get all orders, newest first
    all_orders = Order.objects.all().order_by('-date_created')

    # Limit to last 5 orders for dashboard
    recent_orders = all_orders[:5]

    # Get all customers and last 5 users
    customers = Customer.objects.all().order_by('-date_created')
    users = User.objects.all().order_by('-date_joined')[:5]

    # Counts on all orders
    total_orders = all_orders.count()
    delivered_orders = all_orders.filter(status='Delivered').count()
    pending_orders = all_orders.filter(status='Pending').count()

    context = {
        'orders': recent_orders,         # ✅ only last 5 orders
        'customers': customers,
        'users': users,
        'total_customers': customers.count(),
        'total_order': total_orders,
        'delivered': delivered_orders,
        'pending': pending_orders,
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
@allowed_users(allowed_roles=['admin', 'customer'])
def customer(request, pk, order_type):
    customer = get_object_or_404(Customer, id=pk)
    orders = Order.objects.filter(customer=customer, order_type=order_type)
    total_order = orders.count()
    
    context = {
        'customer': customer,
        'orders': orders,
        'order_type': order_type,
        'total_order': total_order
    }
    return render(request, 'accounts/customer.html', context)

def order_detail(request, pk):
    order = get_object_or_404(Order, id=pk)
    return render(request, 'accounts/order_detail.html', {'order': order})
# the commit function for just 1 item in the formset create 
@login_required(login_url='login')
@allowed_users(allowed_roles=['customer', 'admin'])
def createOrder(request, pk, order_type=None):
    # Inline formset with all relevant fields from your new Order model
    OrderFormSet = inlineformset_factory(
        Customer,
        Order,
        fields=(
            'product',
            'order_type',
            'quantity',
            'urgent',
            'Required_Format',
            'turnaround_time',
            'fabric_material',
            'total_colors',
            'placement',
            'price',
            'status',
            'Additional_information',
            'design_file',
            'assigned_to',         # Sales Representative
            'assigned_designer',   # Designer
            'payment_status',
            'review_status',
            'review_comment',
        ),
        extra=1,
        can_delete=False
    )

    customer = get_object_or_404(Customer, id=pk)

    if request.method == 'POST':
        formset = OrderFormSet(request.POST, request.FILES, instance=customer)
        if formset.is_valid():
            orders = formset.save()

            for order in orders:
                order.customer = customer
                # Ensure defaults for required fields
                if not order.status:
                    order.status = 'Pending'
                if not order.price:
                    order.price = 0
                if not order.payment_status:
                    order.payment_status = 'Pending'
                if not order.review_status:
                    order.review_status = 'Pending'
                order.save()
                # Generate invoice number
                invoice_number = f"INV-{order.id:05d}"

                # Render invoice HTML
                html_string = render_to_string('accounts/invoice_template.html', {
                    'order': order,
                    'customer': customer,
                    'invoice_number': invoice_number
                })

                # Save invoice PDF
                invoice_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
                os.makedirs(invoice_dir, exist_ok=True)
                pdf_path = os.path.join(invoice_dir, f"{invoice_number}.pdf")

                HTML(string=html_string).write_pdf(pdf_path)

                # Save file path to model
                order.invoice_file.name = f"invoices/{invoice_number}.pdf"
                order.save()

            return redirect('home')

    else:
        initial_data = [{'order_type': order_type}] if order_type else [{}]
        formset = OrderFormSet(
            queryset=Order.objects.none(),
            instance=customer,
            initial=initial_data
        )

    return render(request, 'accounts/order_form.html', {
        'formset': formset,
        'order_type': order_type,
        'customer': customer
    })
@login_required
def customer_orders(request):
    customer = get_object_or_404(Customer, user=request.user)
    released_orders = Order.objects.filter(customer=customer, status="Released").order_by('-date_created')

    return render(request, "accounts/released_orders.html", {
        "released_orders": released_orders
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
    completed = orders.filter(status='Completed').count()  # ✅ Add this

    context = {
        'customers': customers,
        'orders': orders,   # this still has ALL orders
        'total_customers': total_customers,
        'total_orders': total_orders,
        'delivered': delivered,
        'pending': pending,
        'completed': completed,  # ✅ send to template
    }

    return render(request, 'accounts/sales_dashboard.html', context)
@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, id=pk)
    context = {
        'customer': order.customer,
        'order': order
    }
    return render(request, 'accounts/order_detail.html', context=context)
@login_required
def release_order(request, pk):
    sales_rep = get_object_or_404(SalesRepresentative, user=request.user)
    order = get_object_or_404(Order, id=pk, assigned_to=sales_rep, status="Completed")

    if request.method == "POST":
        order.status = "Released"
        order.save()

        # Send email to customer with file links
        if order.customer.email:
            subject = f"Your Order #{order.id} Has Been Released"
            message = f"Hello {order.customer.name},\n\n" \
                      f"Your order #{order.id} has been completed and released.\n"

            if order.design_file:
                message += f"\nDesign File: {request.build_absolute_uri(order.design_file.url)}"
            if order.invoice_file:
                message += f"\nInvoice: {request.build_absolute_uri(order.invoice_file.url)}"

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.customer.email])

        messages.success(request, f"Order #{order.id} released to {order.customer.name}.")
        return redirect("release_projects")

    return redirect("release_projects")

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

    # Completed orders waiting to be released
    completed_orders = Order.objects.filter(
        assigned_to=sales_rep,
        status='Completed'
    ).order_by('-date_created')

    if request.method == "POST":
        order_id = request.POST.get("order_id")
        order = get_object_or_404(Order, id=order_id, assigned_to=sales_rep, status="Completed")

        # Mark as released
        order.status = "Released"
        order.save()

        # Send email to customer (if email exists)
        if order.customer.email:
            subject = f"Your Order #{order.id} is Ready"
            message = "Dear {},\n\nYour design has been completed and released by our team.".format(order.customer.name)
            email_from = settings.DEFAULT_FROM_EMAIL
            recipient_list = [order.customer.email]

            # Optionally include file link
            if order.design_file:
                message += f"\n\nYou can download your design here: {request.build_absolute_uri(order.design_file.url)}"

            send_mail(subject, message, email_from, recipient_list)

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


# this function use for designer dashboard
def create_designer_group():
    group_name = "Designer"
    if not Group.objects.filter(name=group_name).exists():
        Group.objects.create(name=group_name)
        print(f"{group_name} group created successfully!")
    else:
        print(f"{group_name} group already exists.")

def setup_designer(request):
    # Create group if not exists
    create_designer_group()

    # Example: Assign the first user to designer group
    user = User.objects.first()
    designer_group = Group.objects.get(name="Designer")
    user.groups.add(designer_group)

    return render(request, "accounts/setup_success.html")

@login_required(login_url='login')
@allowed_users(allowed_roles=['designer'])
def designer_dashboard(request):
    status = request.GET.get('status', None)
    orders = Order.objects.filter(assigned_designer=request.user)
    
    if status:
        orders = orders.filter(status=status)
    
    counts = {
        'total': orders.count(),
        'pending': orders.filter(status='Pending').count(),
        'completed': orders.filter(status='Completed').count()
    }
    
    return render(request, 'accounts/designer_dashboard.html', {
        'orders': orders,
        'counts': counts,
        'status_filter': status
    })

@allowed_users(allowed_roles=['designer'])
def upload_design(request, pk):
    order = get_object_or_404(Order, id=pk, assigned_designer=request.user)
    
    if request.method == 'POST':
        form = DesignFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['design_file']
            if not file.name.lower().endswith(('.ai', '.eps', '.svg')):
                messages.error(request, "Only AI/EPS/SVG files allowed!")
            else:
                # Save to UploadedFile for history
                UploadedFile.objects.create(
                    order=order,
                    file=file,
                    uploaded_by=request.user
                )
                # Update main design reference
                order.design_file = file
                order.save()
                messages.success(request, "Design uploaded successfully!")
                return redirect('designer-dashboard')
    else:
        form = DesignFileForm()
    
    return render(request, 'accounts/upload_design.html', {
        'form': form,
        'order': order
    })
@login_required
def mark_completed(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = 'Completed'
    order.save()
    return redirect('sales-dashboard')

@login_required(login_url='login')
@allowed_users(allowed_roles=['designer'])
def mark_design_completed(request, order_id):
    order = get_object_or_404(Order, id=order_id, assigned_designer=request.user)
    
    if not order.design_file:
        messages.error(request, "Upload design file first!")
        return redirect('upload_design', pk=order.id)
    
    order.status = 'Completed'
    order.date_completed = timezone.now()
    order.save()
    
    # Notify sales rep
    if order.assigned_to:
        notify_user(
            user=order.assigned_to.user,
            message=f"Order #{order.id} was completed by designer"
        )
    
    messages.success(request, "Order marked as completed!")
    return redirect('designer-dashboard')

@login_required(login_url='login')
@allowed_users(allowed_roles=['designer'])
def communicate_with_sales_admin(request, order_id=None):
    order = get_object_or_404(Order, pk=order_id) if order_id else None
    
    if request.method == 'POST':
        form = DesignerMessageForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            if order:  # Auto-set order if coming from order page
                msg.order = order
                if order.assigned_to:  # Auto-set receiver to sales rep
                    msg.receiver = order.assigned_to.user
            msg.save()
            messages.success(request, "Message sent successfully!")
            return redirect('designer_inbox')
    else:
        initial = {'order': order.id} if order else {}
        form = DesignerMessageForm(user=request.user, initial=initial)
    
    return render(request, 'designer/communicate.html', {
        'form': form,
        'order': order
    })

def is_admin(user):
    return user.is_superuser or user.groups.filter(name='admin').exists()

@login_required
@user_passes_test(is_admin)
def admin_send_message(request):
    if request.method == 'POST':
        form = AdminSendMessageForm(request.POST)
        if form.is_valid():
            receiver = form.cleaned_data['receiver']
            content = form.cleaned_data['content']
            DesignerMessage.objects.create(
                sender=request.user,
                receiver=receiver,
                message=content,
            )
            return redirect('admin_inbox')  # Redirect to inbox or wherever you want
    else:
        form = AdminSendMessageForm()

    context = {'form': form}
    return render(request, 'accounts/admin_send_message.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['designer'])
def designer_inbox(request):
    order_id = request.GET.get('order_id')
    messages = DesignerMessage.objects.filter(receiver=request.user)
    
    if order_id:
        messages = messages.filter(order__id=order_id)
    
    return render(request, 'designer/inbox.html', {
        'messages': messages.order_by('-timestamp'),
        'order_filter': order_id
    })
@login_required

@allowed_users(allowed_roles=['designer'])
def message_thread(request, order_id):
    order = get_object_or_404(Order, pk=order_id, assigned_designer=request.user)
    messages = DesignerMessage.objects.filter(order=order).order_by('timestamp')
    
    if request.method == 'POST':
        form = DesignerMessageForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.receiver = order.assigned_to.user  # Auto-set to sales rep
            msg.order = order
            msg.save()
            
            # Notify recipient
            notify_user(
                user=msg.receiver,
                message=f"New message about Order #{order.id}",
                order=order
            )
            
            return redirect('message-thread', order_id=order.id)
    else:
        form = DesignerMessageForm(user=request.user)
    
    return render(request, 'designer/message_thread.html', {
        'order': order,
        'messages': messages,
        'form': form
    })

@login_required
@allowed_users(allowed_roles=['admin', 'designer'])
def view_message(request, pk):
    message = get_object_or_404(DesignerMessage, pk=pk, receiver=request.user)

    # Mark message as read
    if not message.is_read:
        message.is_read = True
        message.save()

    return render(request, 'designer/view_message.html', {'message': message})

# this function is used to show the notifications for the user
@login_required
def view_notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'accounts/notifications.html', {'notifications': notifications})

@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'ok'})

@login_required
@allowed_users(allowed_roles=['designer'])
def mark_thread_read(request, order_id):
    # Mark all messages in thread as read
    DesignerMessage.objects.filter(
        order_id=order_id,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)
    return JsonResponse({'status': 'success'})