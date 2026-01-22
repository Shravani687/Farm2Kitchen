# pages/urls.py
from django.urls import path

from .views import  dashboard_view, delete_user, export_report, home, orders,  smart_login_view, update_order_status_api # <--- Import login_api
from .views import register_api,register_view, dashboard_view,  farmer_dashboard_view, manage_produce_view, order_requests_view, login_hotel,login_farmer
from .views import hotel_dashboard, browse_farmer, my_cart, hotel_profile, profile , manage_farmers, manage_hotels,add_farmer, add_hotel # <--- Import hotel_dashboard_view
from .views import add_product_page,  add_to_cart, checkout_api, cancel_order , update_cart_api, remove_cart_item, farmer_products_view
from .views import farmer_inventory_api, toggle_product_status, admin_dashboard, admin_delete_user  # <--- Import admin_dashboard_view and admin_delete_user
urlpatterns = [
    path('', home, name='home'),
   path('pages/delete/<int:user_id>/',delete_user, name='delete_user'),
    #path('api/login/', login_api, name='login_api'), # <--- Add this line
    path('api/register/', register_api, name='register_api'),
    path('register/', register_view, name='register'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('farmer-dashboard/', farmer_dashboard_view, name='farmer_dashboard'), # <--- NEW PATH
    #path('api/login/', login_api, name='login_api'),
    path('my-produce/', manage_produce_view, name='manage_produce'),
    path('orders_request/', order_requests_view, name='order_requests'),
    #path('api/login/', login_api, name='login_api'),
    path('login/hotel',login_hotel, name='login_hotel'),
    path('login/farmer', login_farmer, name='login_farmer'),
    path('hotel-dashboard/', hotel_dashboard, name='hotel_dashboard'), # <--- NEW PATH
    path('browse-farmer/', browse_farmer, name='browse_farmer'),
    path('my-cart/', my_cart, name='my_cart'),
    path('hotel-profile/', hotel_profile, name='hotel_profile'),
    path('login/smart/', smart_login_view, name='smart_login'),
    path('orders/', orders, name='orders'),
    path('profile/', profile, name='profile'),
    path('manage_farmers/', manage_farmers, name='manage_farmers'),
    path('manage_hotels/', manage_hotels, name='manage_hotels'),
   path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
   path('api/admin/delete-user/<int:user_id>/', admin_delete_user, name='admin_delete_user'),
    path('manage_products/', dashboard_view, name='manage_products'),
    path('add_farmer/',add_farmer, name='add_farmer'),
    path('add_hotel/',add_hotel, name='add_hotel'),
    path('export_report/', export_report, name='export_report'),
    path('add_product/', add_product_page, name='add_product'), # The Page
    path('api/add-to-cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('api/checkout/', checkout_api, name='checkout_api'),
    path('cancel-order/<int:order_id>/', cancel_order, name='cancel_order'),
    path('my-orders/',orders, name='orders'),
    path('api/update-cart/<int:item_id>/',update_cart_api, name='update_cart_api'),
    path('api/remove-item/<int:item_id>/', remove_cart_item, name='remove_cart_item'),
    path('farmer-products/<int:farmer_id>/', farmer_products_view, name='farmer_products'),
    path('api/inventory/', farmer_inventory_api, name='farmer_inventory_api'),
    path('api/inventory/status/<int:product_id>/', toggle_product_status, name='toggle_product_status'),
    path('api/order-status/<int:order_id>/', update_order_status_api, name='update_order_status'),

]