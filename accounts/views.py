from django.utils import timezone 
from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import CustomerForm, OrderForm, CreateUserForm, SiteSettingForm, DesignFileForm,DesignerMessageForm,AdminSendMessageForm, FeedbackForm, SalesRepMessageForm, CustomerProfileForm
from django.forms import inlineformset_factory
from django.contrib import messages
from django.utils.dateparse import parse_date
from django.core.mail import EmailMessage
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
from django.http import HttpResponseForbidden
import os
from django.db.models import Q
from reportlab.pdfgen import canvas
from django.db.models import Sum
from django.utils.timezone import now
import calendar
from django.conf import settings
from django.db.models import Count, Sum, Q
from .utils import generate_monthly_invoice
from io import BytesIO
import csv


# Create your views here.
@unauthenticated_user
def register_page(request):
    designers = Designer.objects.all()  # for dropdown

    if request.method == 'POST':
        print("POST DATA:", request.POST)  # ✅ debug line
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        designer_id = request.POST.get('designer')

        # ✅ Check if username (email) already exists
        if User.objects.filter(username=email).exists():
            messages.error(request, 'This email is already registered.')
            return redirect('register')

        # ✅ Create user safely
        user_obj = User.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=email,
        )
        user_obj.set_password(password)
        user_obj.save()

        # ✅ Assign role (Group)
        try:
            group = Group.objects.get(name=role)
            user_obj.groups.add(group)
        except Group.DoesNotExist:
            messages.error(request, f"The role '{role}' does not exist.")
            return redirect('register')

        # ✅ Create related profile
        if role == 'customer':
            designer = None
            if designer_id and designer_id != "":
                designer = Designer.objects.filter(id=designer_id).first()
                print("🎨 Designer Selected:", designer)
            Customer.objects.create(
                user=user_obj,
                name=f"{first_name} {last_name}",
                designer=designer
            )
        elif role == 'sales_rep':
            SalesRepresentative.objects.create(user=user_obj)
        elif role == 'designer':
            Designer.objects.create(user=user_obj)
        elif role == 'admin':
            Admin.objects.create(user=user_obj)

        messages.success(request, "✅ Your account has been created successfully.")
        return redirect('login')

    return render(request, 'accounts/register.html', {'designers': designers})




@unauthenticated_user
def login_page(request):
    remembered_email = request.COOKIES.get('remembered_email', '')
    remembered_password = request.COOKIES.get('remembered_password', '')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('rememberMe')  # checkbox value

        user_obj = User.objects.filter(username=email).first()

        if not user_obj:
            messages.warning(request, 'Account not found.')
            return HttpResponseRedirect(request.path_info)

        user_obj = authenticate(username=email, password=password)

        if user_obj:
            login(request, user_obj)

            # Handle redirect by role
            group = None
            if user_obj.groups.exists():
                group = user_obj.groups.first().name

            # ✅ Prepare response with cookies
            if group == 'admin':
                response = redirect('home')
            elif group == 'customer':
                response = redirect('user-page')
            elif group == 'sales_rep':
                response = redirect('sales-dashboard')
            elif group == 'designer':
                response = redirect('designer-dashboard')
            else:
                messages.warning(request, "User group is not assigned.")
                return redirect('login')

            # ✅ Handle remember me
            if remember:
                response.set_cookie('remembered_email', email, max_age=60*60*24*30)
                response.set_cookie('remembered_password', password, max_age=60*60*24*30)
                request.session.set_expiry(60 * 60 * 24 * 30)  # session 30 days
            else:
                response.delete_cookie('remembered_email')
                response.delete_cookie('remembered_password')
                request.session.set_expiry(0)  # until browser closes

            return response

        messages.warning(request, "Invalid credentials.")
        return HttpResponseRedirect(request.path_info)

    return render(request, 'accounts/login.html', {
        'remembered_email': remembered_email,
        'remembered_password': remembered_password
    })
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
@allowed_users(allowed_roles=['admin', 'designer', 'sales_rep'])
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

    orders = customer.order_set.all()
    total_order = orders.count()
    delivered = orders.filter(status='Delivered').count()
    pending = orders.filter(status='Pending').count()

    context = {
        'customer': customer,   # ✅ add this
        'orders': orders,
        'total_order': total_order,
        'delivered': delivered,
        'pending': pending,
    }
    return render(request, 'accounts/user.html', context)

def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)  # remove sales_rep filter
    return render(request, "accounts/customer_detail.html", {"customer": customer})

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

##############
def admin_release_orders(request):
    # Completed orders (status = 'Completed')
    completed_orders = Order.objects.filter(status='Completed').order_by('-date_created')

    if request.method == "POST":
        order_id = request.POST.get("order_id")
        order = get_object_or_404(Order, id=order_id, status='Completed')

        # Mark as Released
        order.status = 'Released'
        order.save()

        # Send email to customer
        if order.customer and order.customer.email:
            subject = f"Your Order #{order.id} is Completed and Released"
            message = f"""
Dear {order.customer.name},

Your order #{order.id} has been completed and released by our admin team.

If you have already sent the payment, you can now enjoy your design!
If not, please send the payment at your earliest convenience to access your design.

Thank you for choosing Elite Digitizer.

Best regards,
Elite Digitizer Team
"""
            if order.design_file:
                message += f"\nDownload your design here: {request.build_absolute_uri(order.design_file.url)}"

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.customer.email])

        messages.success(request, f"Order #{order.id} released successfully!")

        return redirect('admin_release_orders')

    context = {
        'completed_orders': completed_orders
    }
    return render(request, 'accounts/admin_release_orders.html', context)

def admin_release_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, status='Completed')
    order.status = 'Released'
    order.save()
    messages.success(request, f"Order #{order.id} released successfully!")
    return redirect('admin_release_orders')











###############

@admin_only
def manage_orders(request):
    # ✅ Show all orders
    all_orders = Order.objects.all().order_by('-date_created')

    context = {
        'orders': all_orders
    }
    return render(request, 'accounts/manage_orders.html', context)

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
# for all order details of a customer like for inovices
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def customer_all_orders(request, pk):
    customer = get_object_or_404(Customer, id=pk)
    orders = Order.objects.filter(customer=customer).order_by('-date_created')

    print("Customer ID in URL:", pk)
    print("Database Customer ID:", customer.id)
    print("Orders count:", orders.count())

    context = {
        'customer': customer,
        'orders': orders,
        'total_order': orders.count(),
    }
    return render(request, 'accounts/customer_all_orders.html', context)



# # this function is used to show the customer details and their orders
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin', 'customer'])
def customer(request, pk, order_type):
    customer = get_object_or_404(Customer, id=pk)

    if order_type == "all":
        orders = Order.objects.filter(customer=customer).order_by('-date_created')
    else:
        orders = Order.objects.filter(customer=customer, order_type=order_type).order_by('-date_created')

    total_order = orders.count()

    context = {
        'customer': customer,
        'orders': orders,
        'order_type': order_type,
        'total_order': total_order
    }
    return render(request, 'accounts/customer.html', context)
# this feilds name for different order types
ORDER_FIELDS = {
    'digitizing': [
         'Order_name_PO', # remove the product field if not needed
        'Required_Format', 'fabric_material',
        'total_colors', 'placement',  'Height', 'Width',
        'Additional_information', 'design_file', 
    ],
    'vector': [
         'Order_name_PO', 
        'Required_Format',  'total_colors',
        'Additional_information', 'design_file', 
    ],
    'patch': [
        'Order_name_PO',  'patch_type',  'total_colors',
           'placement',
        'Height', 'Width', 'Additional_information', 'design_file',
        
    ],
    'quote': [
         'Order_name_PO', 'fabric_material', 'total_colors','Height', 'Width', 'Additional_information',
        'design_file', 
    ]
}

# the commit function for just 1 item in the formset create 
@login_required(login_url='login')
@allowed_users(allowed_roles=['customer', 'admin'])
# ✅ Step 2: Create order view for all types
def createOrder(request, pk, order_type=None):
    """Create order dynamically for Digitizing, Vector, Patch, or Quote"""
    customer = get_object_or_404(Customer, id=pk)

    # Normalize order_type input
    order_type = order_type.lower() if order_type else 'digitizing'

    # Pick correct fields based on order type (fallback to digitizing)
    fields = ORDER_FIELDS.get(order_type, ORDER_FIELDS['digitizing'])

    # Create formset dynamically
    OrderFormSet = inlineformset_factory(
        Customer,
        Order,
        fields=fields,
        extra=1,
        can_delete=False
    )

    if request.method == 'POST':
        formset = OrderFormSet(
            request.POST,
            request.FILES,
            instance=customer,
            queryset=Order.objects.none()
        )

        if formset.is_valid():
            orders = formset.save(commit=False)
            for order in orders:
                order.customer = customer
                order.order_type = order_type.capitalize()
                order.status = order.status or 'Pending'
                order.price = order.price or 0
                order.payment_status = order.payment_status or 'Pending'
                order.review_status = order.review_status or 'Pending'
                order.save()

                # ✅ Generate invoice PDF
                invoice_number = f"INV-{order.id:05d}"
                html_string = render_to_string('accounts/invoice_template.html', {
                    'order': order,
                    'customer': customer,
                    'invoice_number': invoice_number
                })

                invoice_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
                os.makedirs(invoice_dir, exist_ok=True)
                pdf_path = os.path.join(invoice_dir, f"{invoice_number}.pdf")
                HTML(string=html_string).write_pdf(pdf_path)

                order.invoice_file.name = f"invoices/{invoice_number}.pdf"
                order.save()

            return redirect('home')

    else:
        # Set order_type as initial data
        initial_data = [{'order_type': order_type.capitalize()}]
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
    if request.user.is_staff or request.user.groups.filter(name="admin").exists():
        # Admin sees ALL released orders
        released_orders = Order.objects.filter(status="Released").order_by("-date_created")
    else:
        # Customer sees only their released orders
        customer = get_object_or_404(Customer, user=request.user)
        released_orders = Order.objects.filter(
            customer=customer, status="Released"
        ).order_by("-date_created")

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

# @login_required
# def downloadInvoice(request, pk):
#     order = get_object_or_404(Order, id=pk, customer__user=request.user)
#     if order.invoice_file:
#         return redirect(order.invoice_file.url)
#     return redirect('order_history')

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
@receiver(post_save, sender=User)
def create_sales_rep(sender, instance, created, **kwargs):
    if created and instance.groups.filter(name="SalesRepresentative").exists():
        SalesRepresentative.objects.create(user=instance)

@login_required(login_url='login')
@allowed_users(allowed_roles=['customer'])
def accountSettings(request):
    customer, created = Customer.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerProfileForm(instance=customer)

    context = {'form': form, 'customer': customer}
    return render(request, 'accounts/account_settings.html', context)


# this function is used to show the sales dashboard for sales representatives
@login_required(login_url='login')
@allowed_users(allowed_roles=['sales_rep', 'admin'])
def sales_dashboard(request):
    sales_rep = SalesRepresentative.objects.get(user=request.user)
    # Optional fallback (uncomment if needed)
    #sales_rep, created = SalesRepresentative.objects.get_or_create(user=request.user)

    # 🧮 Dashboard metrics
    customers_count = Customer.objects.filter(sales_rep=sales_rep).count()
    quote_requests_count = Order.objects.filter(customer__sales_rep=sales_rep, status="Quote Requested").count()
    active_orders_count = Order.objects.filter(customer__sales_rep=sales_rep, status="Active").count()
    completed_orders_count = Order.objects.filter(customer__sales_rep=sales_rep, status="Completed").count()  # ✅ new
    released_projects_count = Order.objects.filter(customer__sales_rep=sales_rep, status="Released").count()

    # 🕐 Recent orders
    recent_orders = Order.objects.filter(customer__sales_rep=sales_rep).order_by('-date_created')[:5]

    # 🆕 Completed but not yet released (for release panel)
    completed_orders = Order.objects.filter(customer__sales_rep=sales_rep, status="Completed").order_by('-date_completed')

    context = {
        "customers_count": customers_count,
        "quote_requests_count": quote_requests_count,
        "active_orders_count": active_orders_count,
        "completed_orders_count": completed_orders_count,  # ✅ show in dashboard stats
        "released_projects_count": released_projects_count,
        "recent_orders": recent_orders,
        "completed_orders": completed_orders,  # ✅ list for release button
    }
    return render(request, "accounts/sales_dashboard.html", context)



@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, id=pk)
    context = {
        'customer': order.customer,
        'order': order
    }
    return render(request, 'accounts/order_detail.html', context=context)

@login_required
def sales_order_detail(request, order_id):
    # Get the SalesRepresentative linked to the logged-in user
    sales_rep = get_object_or_404(SalesRepresentative, user=request.user)

    # Query order correctly using SalesRepresentative instance
    order = get_object_or_404(Order, id=order_id, customer__sales_rep=sales_rep)

    return render(request, "accounts/sales_order_detail.html", {"order": order})

# the order released than auto email to customer your order is released

@login_required
def release_order(request, pk):
    sales_rep = get_object_or_404(SalesRepresentative, user=request.user)
    order = get_object_or_404(Order, id=pk, assigned_to=sales_rep, status="Completed")

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request method.")

    # Update status
    order.status = "Released"
    order.released_at = timezone.now()
    order.save()

    # Send email to customer
    if order.customer.email:
        subject = f"Your Order #{order.id} Has Been Released"
        message = f"Hello {order.customer.name},\n\nYour order #{order.id} has been completed and released.\n"
        if order.design_file:
            message += f"\nDesign File: {request.build_absolute_uri(order.design_file.url)}"
        if order.invoice_file:
            message += f"\nInvoice: {request.build_absolute_uri(order.invoice_file.url)}"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.customer.email])
    else:
        messages.warning(request, f"Order #{order.id} released, but no email sent (missing customer email).")

    messages.success(request, f"Order #{order.id} released successfully.")
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
    sales_rep = get_sales_rep(request)
    if not sales_rep:
        return redirect("sales-dashboard")

    # Only customers assigned to this sales rep
    customers = Customer.objects.filter(sales_rep=sales_rep)

    return render(request, 'accounts/sales/manage_customers.html', {
        'assigned_customers': customers
    })

@login_required(login_url="login")
@allowed_users(allowed_roles=["sales_rep", "admin"])



def release_projects(request):
    sales_rep = get_object_or_404(SalesRepresentative, user=request.user)

    # Get all completed orders waiting for release
    completed_orders = Order.objects.filter(
        customer__sales_rep=sales_rep,
        status='Completed'
    ).order_by('-date_created')

    if request.method == "POST":
        order_id = request.POST.get("order_id")
        order = get_object_or_404(
            Order, id=order_id, customer__sales_rep=sales_rep, status="Completed"
        )

        # Mark as released
        order.status = "Released"
        order.date_released = timezone.now()
        order.save()

        # Prepare email
        if order.customer.email:
            subject = f"Your Order #{order.id} is Ready!"
            message = (
                f"Dear {order.customer.name},\n\n"
                f"Your order #{order.id} has been completed and is now released.\n"
                "Please find your design and invoice attached below.\n\n"
                "Thank you for choosing us!\n\n"
                "Best regards,\n"
                f"{sales_rep.user.get_full_name() or 'Your Sales Representative'}"
            )

            email = EmailMessage(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [order.customer.email],
            )

            # Attach design file if exists
            if order.design_file and os.path.isfile(order.design_file.path):
                email.attach_file(order.design_file.path)

            # Attach invoice if exists
            if hasattr(order, 'invoice_file') and order.invoice_file and os.path.isfile(order.invoice_file.path):
                email.attach_file(order.invoice_file.path)

            # Send the email
            try:
                email.send()
                messages.success(request, f"Order #{order.id} released and email sent to {order.customer.email}.")
            except Exception as e:
                messages.error(request, f"Order released but email could not be sent: {e}")
        else:
            messages.warning(request, f"Order #{order.id} released, but customer email not available.")

        return redirect('release_projects')  # reload page after POST

    context = {
        'completed_orders': completed_orders,
    }
    return render(request, 'accounts/sales/release_projects.html', context)

# @login_required(login_url="login")
# @allowed_users(allowed_roles=["sales_rep", "admin"])
# def release_projects(request):
#     sales_rep = get_sales_rep(request)
#     if not sales_rep:
#         return redirect("sales-dashboard")

#     # Completed orders waiting for release
#     completed_orders = Order.objects.filter(
#         customer__sales_rep=sales_rep,
#         status="Completed"
#     ).order_by("-date_created")

#     if request.method == "POST":
#         order_id = request.POST.get("order_id")
#         order = get_object_or_404(
#             Order,
#             id=order_id,
#             customer__sales_rep=sales_rep,
#             status="Completed"
#         )

#         # Mark as Released
#         order.status = "Released"
#         order.date_released = timezone.now()
#         order.save()

#         # --- Send Email with Project File Attached ---
#         subject = f"Your Project #{order.id} is Now Released"
#         message = f"""
#         Dear {order.customer.name},

#         Your project (Order #{order.id}) has been released.
#         Please find the attached file.

#         Thank you for choosing us!
#         """

#         recipient_email = order.customer.email  

#         email = EmailMessage(
#             subject,
#             message,
#             settings.DEFAULT_FROM_EMAIL,
#             [recipient_email],
#         )

#         # Attach design file if exists
#         if order.design_file:
#             email.attach_file(order.design_file.path)  # design_file is a FileField

#         email.send(fail_silently=False)
#         # --- End Email ---

#         messages.success(request, f"Order #{order.id} released and sent to customer by email.")
#         return redirect("release_projects")

#     return render(request, "accounts/sales/release_projects.html", {
#         "completed_orders": completed_orders
#     })



def get_sales_rep(request):
    try:
        return SalesRepresentative.objects.get(user=request.user)
    except SalesRepresentative.DoesNotExist:
        return None
    
@login_required
@allowed_users(allowed_roles=["sales_rep"])
def communicate_sales_rep(request, order_id=None):
    order = get_object_or_404(Order, pk=order_id) if order_id else None
    messages_qs = DesignerMessage.objects.filter(receiver=request.user) | DesignerMessage.objects.filter(sender=request.user)

    if request.method == "POST":
        form = SalesRepMessageForm(request.POST, user=request.user)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            if order:
                msg.order = order
            msg.save()
            messages.success(request, "Message sent successfully!")
            return redirect("sales_rep_inbox")
    else:
        form = SalesRepMessageForm(user=request.user)

    return render(request, "accounts/sales/communicate_sales.html", {
        "form": form,
        "order": order,
        "messages": messages_qs.order_by("-timestamp"),
    })


@login_required
@allowed_users(allowed_roles=["sales_rep"])
def sales_rep_inbox(request):
    inbox = DesignerMessage.objects.filter(receiver=request.user).order_by("-timestamp")
    unread_count = inbox.filter(is_read=False).count()
    return render(request, "accounts/sales/inbox.html", {
        "messages": inbox,
        "unread_count": unread_count,
    })


@login_required
def monitor_quotes(request):
    sales_rep = get_sales_rep(request)
    if not sales_rep:
        return redirect("sales-dashboard")

    quote_requests = Order.objects.filter(
        customer__sales_rep=sales_rep,
        status="Quote Requested"
    ).order_by("-date_created")

    active_orders = Order.objects.filter(
        customer__sales_rep=sales_rep,
        status="Active"
    ).order_by("-date_created")

    return render(request, "accounts/sales/monitor_quotes.html", {
        "quote_requests": quote_requests,
        "active_orders": active_orders,
    })


@login_required
def track_orders(request):
    sales_rep = get_sales_rep(request)
    if not sales_rep:
        return redirect("sales-dashboard")

    quote_orders = Order.objects.filter(
        customer__sales_rep=sales_rep,
        status="Quote Requested"
    ).order_by("-date_created")

    return render(request, "accounts/sales/track_orders.html", {
        "quote_orders": quote_orders
    })



@login_required
def follow_up_payments(request):
    sales_rep = get_sales_rep(request)
    if not sales_rep:
        return redirect("sales-dashboard")

    released_orders = Order.objects.filter(
        customer__sales_rep=sales_rep,
        status="Released"
    ).order_by("-date_created")

    return render(request, "accounts/sales/follow_up.html", {
        "pending_orders": released_orders
    })
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
@login_required
def designer_dashboard(request):
    status = request.GET.get('status', None)

    # All orders assigned to this designer
    all_orders = Order.objects.filter(assigned_designer=request.user).order_by('-date_created')

    # Filter if a status is selected
    if status:
        all_orders = all_orders.filter(status=status)

    # Slice only the latest 5 for the dashboard preview
    recent_orders = all_orders[:5]

    # Counts for cards
    counts = {
        'total': all_orders.count(),
        'pending': all_orders.filter(status='Pending').count(),
        'completed': all_orders.filter(status='Completed').count()
    }

    return render(request, 'accounts/designer_dashboard.html', {
        'orders': recent_orders,     # dashboard shows latest 5
        'all_orders': all_orders,    # sidebar can loop through all
        'counts': counts,
        'status_filter': status
    })


@login_required(login_url='login')
@allowed_users(allowed_roles=['designer'])
def upload_design(request, pk):
    order = get_object_or_404(Order, id=pk, assigned_designer=request.user)

    if request.method == 'POST':
        form = DesignFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES.get('design_file')  # ✅ Safely access file

            # ✅ Check if file is provided
            if not file:
                messages.error(request, "Please select a design file before uploading.")
                return redirect(request.path)

            # ✅ Check file size (max 5 MB)
            max_size = 5 * 1024 * 1024  # 5 MB in bytes
            if file.size > max_size:
                messages.error(request, "File too large! Maximum allowed size is 5 MB.")
                return redirect(request.path)

            # ✅ Check file extension/type
            if not file.name.lower().endswith(('.ai', '.eps', '.svg')):
                messages.error(request, "Only AI, EPS, or SVG files are allowed!")
                return redirect(request.path)

            # ✅ Save file history
            UploadedFile.objects.create(
                order=order,
                file=file,
                uploaded_by=request.user
            )

            # ✅ Update order with new design file
            order.design_file = file
            order.save()

            messages.success(request, "Design uploaded successfully!")
            return redirect('designer-dashboard')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = DesignFileForm(instance=order)

    return render(request, 'accounts/upload_design.html', {
        'form': form,
        'order': order
    })
@login_required
def designer_manage_orders(request):
    # Get all orders assigned to this designer
    all_orders = Order.objects.filter(assigned_designer=request.user)

    # Get status filter
    status = request.GET.get('status', None)
    orders = all_orders.order_by('-date_created')

    if status:
        orders = orders.filter(status=status)

    # Add counters (always based on all orders, not the filtered set)
    counts = {
        'total': all_orders.count(),
        'pending': all_orders.filter(status='Pending').count(),
        'completed': all_orders.filter(status='Completed').count()
    }

    return render(request, 'accounts/design_manage_orders.html', {
        'orders': orders,
        'status_filter': status,
        'counts': counts
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
        messages.error(request, "Please upload the design file before marking as completed.")
        return redirect('upload_design', pk=order.id)

    order.status = 'Completed'
    order.date_completed = timezone.now()
    order.save()

    # Optional: notify sales rep
    sales_rep = getattr(order.customer, 'sales_rep', None)
    if sales_rep:
        print(f"Notify sales rep {sales_rep} that order #{order.id} is ready for release.")

    messages.success(request, f"Order #{order.id} marked as completed and waiting for Sales Rep release.")
    return redirect('designer-dashboard')
# this for relased direct to send email to client 

# def mark_design_completed(request, order_id):
#     # Get the order assigned to this designer
#     order = get_object_or_404(Order, id=order_id, assigned_designer=request.user)
    
#     # Ensure design file is uploaded first
#     if not order.design_file:
#         messages.error(request, "Please upload the design file before marking as completed!")
#         return redirect('upload_design', pk=order.id)
    
#     # Update order status to Released (since you want it automatically sent)
#     order.status = 'Released'
#     order.date_completed = timezone.now()
#     order.date_released = timezone.now()
#     order.save()

#     # Notify Sales Rep (optional)
#     sales_rep = getattr(order.customer, 'sales_rep', None)
#     if sales_rep:
#         try:
#             # Example: log or send a message if you have notify_user()
#             # notify_user(user=sales_rep.user, message=f"Order #{order.id} released by designer.")
#             print(f"Sales Rep Notified: Order #{order.id} released by designer.")
#         except Exception as e:
#             print(f"Could not notify sales rep: {e}")

#     # Send email to customer with design + invoice attached
#     if order.customer and order.customer.email:
#         subject = f"Your Order #{order.id} is Ready!"
#         message = f"""
# Dear {order.customer.name},

# Your order #{order.id} has been completed and released by our designer.

# Please find your design file attached below.
# If applicable, the invoice is also attached.

# Thank you for choosing Elite Digitizer!

# Best regards,  
# Elite Digitizer Team
# """

#         email = EmailMessage(
#             subject=subject,
#             body=message,
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             to=[order.customer.email],
#         )

#         # Attach design file if exists
#         if order.design_file and os.path.isfile(order.design_file.path):
#             email.attach_file(order.design_file.path)

#         # Attach invoice file if exists (optional field)
#         if hasattr(order, 'invoice_file') and order.invoice_file and os.path.isfile(order.invoice_file.path):
#             email.attach_file(order.invoice_file.path)

#         try:
#             email.send()
#             messages.success(
#                 request,
#                 f"Order #{order.id} released and email sent to {order.customer.email} with attachments."
#             )
#         except Exception as e:
#             messages.error(request, f"Order released but email could not be sent: {e}")
#     else:
#         messages.warning(request, f"Order #{order.id} released, but customer email not found.")

#     return redirect('designer-dashboard')

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
@allowed_users(allowed_roles=['admin', 'designer', 'sales_rep'])
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
    unread_count = notifications.filter(is_read=False).count()
    return render(request, 'accounts/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count
    })

@login_required
def mark_notification_read(request, pk):
    if request.method == "POST":
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'fail'}, status=400)

@login_required
@allowed_users(allowed_roles=['designer'])
def mark_thread_read(request, order_id):
    DesignerMessage.objects.filter(
        order_id=order_id,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)
    return JsonResponse({'status': 'success'})

def unread_notifications(request):
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
    else:
        unread_count = 0
    return {"navbar_unread_count": unread_count}

@login_required
def designer_feedback(request):
    feedbacks = Feedback.objects.filter(order__assigned_designer=request.user).order_by('-created_at')
    return render(request, "accounts/designer_feedback.html", {"feedbacks": feedbacks})

@login_required
def submit_feedback(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer__user=request.user)

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.order = order
            feedback.customer = request.user
            feedback.save()
            messages.success(request, "Your feedback has been submitted.")
            return redirect('released_orders')  # redirect back to released orders page
    else:
        form = FeedbackForm()

    return render(request, "accounts/submit_feedback.html", {"form": form, "order": order})


#
@login_required
def customer_invoices(request, pk):
    customer = get_object_or_404(Customer, id=pk)
    invoices = Invoice.objects.filter(customer=customer).order_by('-year', '-month')

    # Collect related orders for each invoice
    invoice_data = []
    for invoice in invoices:
        orders = Order.objects.filter(
            customer=customer,
            status="Completed",
            created_at__year=invoice.year,
            created_at__month=invoice.month
        )
        invoice_data.append({
            "invoice": invoice,
            "orders": orders
        })

    return render(request, "accounts/customer_invoices.html", {
        "customer": customer,
        "invoice_data": invoice_data
    })

@login_required
def invoice_detail(request, pk, year, month):
    customer = get_object_or_404(Customer, id=pk)
    invoice = get_object_or_404(Invoice, customer=customer, year=year, month=month)

    # Example: Generate PDF dynamically
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.id}.pdf"'

    p = canvas.Canvas(response)
    p.drawString(100, 800, f"Invoice #{invoice.id}")
    p.drawString(100, 780, f"Customer: {customer.name}")
    p.drawString(100, 760, f"Period: {month}/{year}")
    p.drawString(100, 740, f"Total: ${invoice.total_amount}")
    p.showPage()
    p.save()

    return response

# services 
def services(request):
    return render(request, "accounts/services.html")

def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        # Email to Admin
        admin_subject = f"New Contact Message from {name}"
        admin_message = f"""
        You received a new message:

        Name: {name}
        Email: {email}

        Message:
        {message}
        """

        # Email to User (confirmation)
        user_subject = "Thank you for contacting us!"
        user_message = f"""
        Hi {name},

        Thank you for reaching out to us. We have received your message and our team
        will get back to you as soon as possible.

        Here’s a copy of your message:
        {message}

        Regards,  
        The Support Team
        """

        try:
            # Send to Admin
            send_mail(
                admin_subject,
                admin_message,
                settings.DEFAULT_FROM_EMAIL,  # from
                [settings.ADMIN_EMAIL],       # to admin
                fail_silently=False,
            )

            # Send confirmation to User
            send_mail(
                user_subject,
                user_message,
                settings.DEFAULT_FROM_EMAIL,  # from
                [email],                      # to user
                fail_silently=False,
            )

            messages.success(request, "✅ Your message has been sent. A confirmation email has been sent to you.")
        except Exception as e:
            messages.error(request, f"❌ Error sending message: {e}")

    return render(request, "accounts/contact.html")


def about(request):
    return render(request, "accounts/about.html")


def customer_receivable_orders(request, pk):
    customer = get_object_or_404(Customer, id=pk)
    # Assuming payment_status='Pending' means not yet received
    orders = Order.objects.filter(customer=customer, payment_status='Pending').order_by('-date_created')

    context = {
        'customer': customer,
        'orders': orders,
        'total_order': orders.count(),
        'page_title': 'Receivable Orders',
    }
    return render(request, 'accounts/customer_orders_list.html', context)

def customer_received_orders(request, pk):
    customer = get_object_or_404(Customer, id=pk)
    # Assuming payment_status='Paid' means received
    orders = Order.objects.filter(customer=customer, payment_status='Paid').order_by('-date_created')

    context = {
        'customer': customer,
        'orders': orders,
        'total_order': orders.count(),
        'page_title': 'Received Orders',
    }
    return render(request, 'accounts/customer_orders_list.html', context)



def customer_invoices(request, pk):
    customer = get_object_or_404(Customer, id=pk)
    invoices = Invoice.objects.filter(customer=customer).order_by('-year', '-month')

    context = {
        'customer': customer,
        'invoices': invoices,
        'page_title': 'All Invoices',
    }
    return render(request, 'accounts/customer_invoices.html', context)

def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    orders = Order.objects.filter(
        customer=invoice.customer,
        date_created__year=invoice.year,
        date_created__month=invoice.month,
        status='Completed'
    )

    context = {
        'invoice': invoice,
        'orders': orders,
        'page_title': f"Invoice {invoice.month}/{invoice.year}"
    }
    return render(request, 'accounts/invoice_detail.html', context)