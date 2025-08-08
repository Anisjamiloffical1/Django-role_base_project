from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.products, name='products'),
    path('customer/<int:pk>/', views.customer, name='customer'),
    path('customer/create/', views.createCustomer, name='create_customer'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('sales/release/<int:pk>/', views.release_order, name='release_order'),
    path('create_order/<str:pk>/<str:order_type>/', views.createOrder, name='create_order'),
    path('order/history/', views.orderHistory, name='order_history'),
    path('order/<int:pk>/download_design/', views.downloadDesign, name='download_design'),
    path('order/<int:pk>/download_invoice/', views.downloadInvoice, name='download_invoice'),
    path('order/<int:pk>/print_invoice/', views.printInvoice, name='print_invoice'),
    path('orders/<int:pk>/invoice/', views.order_invoice, name='order_invoice'),
    path('update_order/<str:pk>/', views.updateOrder, name='update_order'),
    path('delete_order/<str:pk>/', views.delete_order, name='delete_order'),
    path('register/', views.register_page, name='register'),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('user/', views.user_page, name='user-page'),
    path('accounts/', views.accountSettings, name='account'),
    path('customer/update/<str:pk>/', views.updateCustomer, name='update_customer'),
    path('sales-dashboard/', views.sales_dashboard, name='sales-dashboard'),
    path('sales/mark-completed/<int:order_id>/', views.mark_completed, name='mark_completed'),
    path('manage-customers/', views.manage_customers, name='manage_customers'),
    path('release-projects/', views.release_projects, name='release_projects'),
    path('monitor-quotes/', views.monitor_quotes, name='monitor_quotes'),
    path('track-orders/', views.track_orders, name='track_orders'),
    path('communicate/', views.communicate_designers_admins, name='communicate_designers_admins'),
    path('follow-up/', views.follow_up_payments, name='follow_up_payments'),
    path('reset_password/', auth_views.PasswordResetView.as_view(template_name='password/password_reset.html'), name='reset_password'),
    path('reset_password_send/', auth_views.PasswordResetDoneView.as_view(template_name="password/password_reset_done.html"), name= 'password_reset_done'),
    path('reset/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(template_name="password/password_reset_confirm.html"), name='password_reset_confirm'),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name="password/password_reset_complete.html"), name='password_reset_complete'),
    
]