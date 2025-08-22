from django.urls import path
from . import views
from django.contrib.auth import views as auth_views



urlpatterns = [
    path('', views.home, name='home'),
    path("manage-orders/", views.manage_orders, name="manage_orders"),
    path('anis/', views.some_view, name='some_view'),# ths is for testing purpose
    path('users/', views.manage_users, name='manage_users'),
    path('users/edit/<int:pk>/', views.edit_user, name='edit_user'),
    path('users/delete/<int:pk>/', views.delete_user, name='delete_user'),
    path('products/', views.products, name='products'),
    path('review-file/<int:pk>/', views.review_file, name='review_file'),
    path('customer/<int:pk>/<str:order_type>/', views.customer, name='customer_orders'),
    path("customer/<int:pk>/", views.customer_detail, name="customer"),
    path("designer/manage-orders/", views.designer_manage_orders, name="design_manage_orders"),   #this
    path('customer/create/', views.createCustomer, name='create_customer'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('sales/release/<int:pk>/', views.release_order, name='release_order'),
    path('create_order/<int:pk>/<str:order_type>/', views.createOrder, name='create_order'),
    path('order/history/', views.orderHistory, name='order_history'),
    path('order/<int:pk>/download_design/', views.downloadDesign, name='download_design'),
    # path('order/<int:pk>/download_invoice/', views.downloadInvoice, name='download_invoice'),
    path('order/<int:pk>/print_invoice/', views.printInvoice, name='print_invoice'),
    path('orders/<int:pk>/invoice/', views.order_invoice, name='order_invoice'),
    path('update_order/<str:pk>/', views.updateOrder, name='update_order'),
    path('delete_order/<str:pk>/', views.delete_order, name='delete_order'),
    path('register/', views.register_page, name='register'),
    path('login/', views.login_page, name='login'),
    path('reports/', views.report_view, name='report_view'),
    path('admin-release-orders/', views.admin_release_orders, name='admin_release_orders'),# for admin relased orders show
    path('admin-release-orders/<int:order_id>/', views.admin_release_order, name='admin_release_order'),# relased order to customer
    path('reports/export/csv/', views.export_report_csv, name='export_report_csv'),
    path('logout/', views.logout_page, name='logout'),
    path('user/', views.user_page, name='user-page'),
    path('admin-inbox/', views.admin_inbox, name='admin_inbox'),
    path('message/<int:pk>/', views.view_message, name='view_message'),
    path('accounts/', views.accountSettings, name='account'),
    path('customer/update/<str:pk>/', views.updateCustomer, name='update_customer'),
    path('settings/', views.manage_settings, name='manage_settings'),
    path('sales/dashboard/', views.sales_dashboard, name='sales-dashboard'),
    path('sales/customers/', views.manage_customers, name='manage_customers'),
    path('sales/release-projects/', views.release_projects, name='release_projects'),
    path('sales/monitor-quotes/', views.monitor_quotes, name='monitor_quotes'),
    path('sales/track-orders/', views.track_orders, name='track_orders'),
    path('sales/communicate/', views.communicate_designers_admins, name='communicate_designers_admins'),
    path('sales/follow-up/', views.follow_up_payments, name='follow_up_payments'),
    path("sales/order/<int:order_id>/", views.sales_order_detail, name="sales_order_detail"),
    path('sales/mark-completed/<int:order_id>/', views.mark_completed, name='mark_completed'),
    path('reset_password/', auth_views.PasswordResetView.as_view(template_name='password/password_reset.html'), name='reset_password'),
    path('reset_password_send/', auth_views.PasswordResetDoneView.as_view(template_name="password/password_reset_done.html"), name= 'password_reset_done'),
    path('reset/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(template_name="password/password_reset_confirm.html"), name='password_reset_confirm'),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name="password/password_reset_complete.html"), name='password_reset_complete'),
    path('designer/dashboard/', views.designer_dashboard, name='designer-dashboard'),
    path('designer/upload/<int:pk>/', views.upload_design, name='upload_design'),
    path('orders/<int:order_id>/mark-completed/', views.mark_completed, name='mark-completed'),
    path('orders/<int:order_id>/mark-design-completed/', views.mark_design_completed, name='mark-design-completed'),
    path('designer/communicate/', views.communicate_with_sales_admin, name='communicate_with_sales_admin'),
    path('designer/inbox/', views.designer_inbox, name='designer_inbox'),
    path('admin-send-message/', views.admin_send_message, name='admin_send_message'),
    path('notifications/', views.view_notifications, name='view_notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path("messages/mark-thread/<int:order_id>/", views.mark_thread_read, name="mark_thread_read"),
    path("customer/released-orders/", views.customer_orders, name="released_orders"),
    path("designer/feedback/", views.designer_feedback, name="designer_feedback"),
    path("customer/order/<int:order_id>/feedback/", views.submit_feedback, name="submit_feedback"),
    # Monthly Invoices
    path('customer/<int:pk>/invoices/', views.customer_invoices, name='customer_invoices'),
    path('customer/<int:pk>/invoices/<int:year>/<int:month>/', views.invoice_detail, name='invoice_detail'),

  
]
    
    
    
