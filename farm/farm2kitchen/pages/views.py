from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db import transaction # Important for safe database saving
from django.contrib.auth.decorators import login_required
from narwhals import Decimal
from streamlit import context
from .models import Order, OrderItem # Ensure these are imported
from django.db import transaction

# Import your models
from .models import Farmer, Hotel, Product
# Import your form (Make sure you have created forms.py, otherwise comment this line out)
# from .forms import ProductForm 


def is_superuser_check(user):
    return user.is_authenticated and user.is_superuser

# --- 1. STATIC PAGE VIEWS ---
def home(request):
    return render(request, 'pages/home.html')

def login_hotel(request):
    return render(request, "pages/login_hotel.html")

def login_farmer(request):
    return render(request, "pages/login_farmer.html")

def register_view(request):
    return render(request, "pages/register.html")



@login_required
def profile(request):
    # 1. Get the Farmer Object from the Database
    # This assumes the logged-in user is a farmer.
    try:
        farmer_data = request.user.farmer 
    except:
        # Fallback if not a farmer (e.g., if a Hotel logs in)
        return redirect('home')

    # 2. Handle Edit (Saving Changes)
    if request.method == 'POST':
        try:
            # Update fields in the FARMER table
            farmer_data.f_name = request.POST.get('f_name')
            farmer_data.l_name = request.POST.get('l_name')
            farmer_data.phone = request.POST.get('phone')
            farmer_data.address = request.POST.get('address')
            
            # If you have a farm name field, update it too
            if request.POST.get('farm_name'):
                farmer_data.farm_name = request.POST.get('farm_name')
                
            farmer_data.save()
            
            # Update the main User table email as well (usually common)
            request.user.email = request.POST.get('email')
            request.user.save()

            messages.success(request, "Profile details updated successfully!")
            return redirect('profile')

        except Exception as e:
            messages.error(request, f"Update failed: {str(e)}")

    context = {
        'farmer': farmer_data, # Pass the specific farmer data to HTML
        'user': request.user   # Pass the main user account (for username/email)
    }
    return render(request, 'pages/profile.html', context)

# --- 3. REGISTRATION API (FIXED) ---
@csrf_exempt
def register_api(request):
    if request.method == 'POST':
        print("--- Register API Triggered ---")
        
        # 1. Get data using the names EXACTLY as sent by your JavaScript
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')       # "Farmer" or "Hotel"
        
        # JS sends 'full_name' and 'entity_name' (farm/hotel name)
        full_name = request.POST.get('full_name') 
        entity_name = request.POST.get('entity_name') 
        phone = request.POST.get('phone')

        print(f"Data Received: {email} | {role} | {entity_name} | {full_name}")

        # 2. Check if email exists
        if User.objects.filter(username=email).exists():
            return HttpResponse("Email already registered")

        try:
            with transaction.atomic(): # Safe saving
                # Create the Login User
                user = User.objects.create_user(username=email, email=email, password=password)
                print(f"--- User Created: {user.username} ---")

                # Create the Specific Profile
                if role == 'Farmer':
                    # Note: Ensure your models.py fields match these names (full_name, farm_name)
                    Farmer.objects.create(
                        user=user, 
                        full_name=full_name, 
                        farm_name=entity_name, 
                        phone=phone,
                        email=email,
                        password=password
                    )
                    print("--- Farmer Table Updated ---")
                
                elif role == 'Hotel':
                    Hotel.objects.create(
                        user=user, 
                        full_name=full_name, 
                        hotel_name=entity_name, 
                        phone=phone,
                        email=email,
                        password=password
                    )
                    print("--- Hotel Table Updated ---")

            return HttpResponse("success")
        
        except Exception as e:
            print(f"--- CRITICAL ERROR: {e} ---")
            return HttpResponse(f"Server Error: {e}")

    return HttpResponse("Invalid request")

# --- 4. DASHBOARD VIEWS ---
def dashboard_view(request):
    products_list = Product.objects.all()
    
    context = {
        "products": products_list,
        # "form": form
    }
    return render(request, "pages/manage_products.html", context)

# Imports needed (Add to top)
from django.db.models import Sum
from .models import Order, Product, OrderItem

# --- 1. UPDATE DASHBOARD VIEW (To send Stats & Orders) ---
@login_required(login_url='login_farmer')
def farmer_dashboard_view(request):
    try:
        farmer_profile = request.user.farmer
    except:
        return redirect('home') # Safety check if user isn't a farmer

    # A. Calculate Stats
    items_count = Product.objects.filter(farmer=request.user).count()
    total_orders_count = Order.objects.filter(farmer=farmer_profile).count()
    
    # Calculate Total Sales (Sum of accepted/delivered orders)
    # Since total_amount is a property, we calculate in Python
    completed_orders = Order.objects.filter(farmer=farmer_profile, status__in=['Accepted', 'Ready', 'Delivered'])
    total_sales = sum(order.total_amount for order in completed_orders)

    # B. Get Pending Orders (For the "Incoming Orders" section)
    pending_orders = Order.objects.filter(farmer=farmer_profile, status='Pending').order_by('-created_at')

    context = {
        'items_count': items_count,
        'orders_count': total_orders_count,
        'total_sales': total_sales,
        'pending_orders': pending_orders, # Sending orders to HTML
    }
    return render(request, 'pages/farmer_dashboard.html', context)

# --- 2. NEW API: ACCEPT/DENY ORDER ---
# In pages/views.py

@login_required
@csrf_exempt
def update_order_status_api(request, order_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action') 

            # 1. Get the Order
            order = get_object_or_404(Order, id=order_id, farmer=request.user.farmer)
            
            if action == 'accept':
                order.status = 'Accepted'
                order.save()
                return JsonResponse({'message': 'Order Accepted!'})

            elif action == 'deny':
                # 2. RESTOCK LOGIC (Fixed for Float types)
                for order_item in order.order_items.all():
                    # Find the product
                    product = Product.objects.filter(
                        name=order_item.item_name, 
                        farmer=request.user 
                    ).first()

                    if product:
                        # --- THE FIX IS HERE ---
                        # We convert both to float to avoid the Type Error
                        current_qty = float(product.quantity_available)
                        restock_qty = float(order_item.quantity)
                        
                        product.quantity_available = current_qty + restock_qty
                        product.save()
                
                order.status = 'Denied'
                order.save()
                return JsonResponse({'message': 'Order Denied.'})

        except Exception as e:
            print(f"ORDER ERROR: {e}") 
            return JsonResponse({'error': f"Server Error: {str(e)}"}, status=400)
            
    return JsonResponse({'error': 'Invalid request'}, status=400)

def manage_produce_view(request):
    return render(request, "pages/manage_produce.html")

def order_requests_view(request):
    return render(request, "pages/order_requests.html")

# Add these imports at the top if missing
from django.db.models import Sum
from .models import Order, Product

@login_required
def hotel_dashboard(request):
    # 1. Security Check
    if not hasattr(request.user, 'hotel'):
        return redirect('home')
    
    hotel = request.user.hotel

    # 2. Fetch Products
    # Sorted by '-id' because 'created_at' does not exist in your Product model
    products = Product.objects.filter(is_active=True).order_by('-id')

    # --- 3. CALCULATE STATS ---
    
    # A. Pending Orders Count
    pending_orders_count = Order.objects.filter(hotel=hotel, status='Pending').count()

    # B. Connected Farmers
    connected_farmers_count = Order.objects.filter(hotel=hotel).values('farmer').distinct().count()

    # C. Total Spend (FIXED)
    # Since 'total_amount' is not a DB column, we fetch the orders and sum them in Python
    completed_orders = Order.objects.filter(hotel=hotel, status__in=['Accepted', 'Delivered'])
    
    # Calculate sum using Python list comprehension
    total_spend = sum(order.total_amount for order in completed_orders)

    context = {
        'products': products,
        'pending_orders_count': pending_orders_count,
        'connected_farmers_count': connected_farmers_count,
        'total_spend': total_spend,
    }
    return render(request, "pages/hotel_dashboard.html", context)
    
@login_required(login_url='login_hotel') # Protect this page
def browse_farmer(request):
    # 1. Fetch all farmers from the database
    farmers = Farmer.objects.all()

    # 2. Send them to the template
    context = {
        'farmers': farmers
    }
    return render(request, 'pages/browse_farmer.html', context)

def my_cart(request):
    return render(request , "pages/my_cart.html")

# In pages/views.py

@login_required
def hotel_profile(request):
    # 1. Get the Hotel Object
    try:
        hotel = request.user.hotel
    except:
        return redirect('home') # Redirect if user is not a hotel

    # 2. Handle Edit (Saving Changes)
    if request.method == 'POST':
        try:
            # Update Hotel fields
            hotel.hotel_name = request.POST.get('hotel_name')
            hotel.phone = request.POST.get('phone')
            hotel.address = request.POST.get('address')
            hotel.save()
            
            # Update User fields (Email)
            request.user.email = request.POST.get('email')
            request.user.save()

            messages.success(request, "Profile updated successfully!")
            return redirect('hotel_profile') # Refresh page

        except Exception as e:
            messages.error(request, f"Update failed: {str(e)}")

    context = {
        'hotel': hotel,
        'user': request.user
    }
    return render(request, 'pages/hotel_profile.html', context)

def smart_login_view(request):
    if request.method == 'POST':
        email = request.POST.get('username')  # The input name in HTML
        password = request.POST.get('password')

        # 1. Check if Email/Password matches Auth User table
        user = authenticate(request, username=email, password=password)

        if user is not None:
            # 2. Log them in
            login(request, user)

            # 3. Check Role & Redirect
            # Django checks if this user ID exists in the 'farmer' table
            if hasattr(user, 'farmer'):
                return redirect('farmer_dashboard')
            
            # Django checks if this user ID exists in the 'hotel' table
            elif hasattr(user, 'hotel'):
                return redirect('hotel_dashboard')
            
            # Fallback for admins or users with no profile
            else:
                return redirect('home')

        else:
            messages.error(request, "Invalid email or password.")
            # If you are using a modal, we usually reload home 
            # and let JS show the error, or redirect to a dedicated login page.
            return redirect('home') 

    # If someone tries to go to /login/ directly, just show home
    return redirect('home')

from django.contrib.auth.decorators import user_passes_test

# 1. Define the check: Must be a Superuser
def is_superuser(user):
    return user.is_authenticated and user.is_superuser

# 2. The View with the redirect logic
# 'login_url' tells Django: "If they aren't logged in, send them HERE."
# Imports needed
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.contrib import messages

# --- SECURE ADMIN LOGIN VIEW ---
# In pages/views.py

# pages/views.py

from django.contrib.auth.views import LoginView
from django.shortcuts import redirect # Make sure this is imported
from django.urls import reverse

class CustomAdminLogin(LoginView):
    template_name = 'admin/login.html'
    redirect_field_name = None 
    
    extra_context = {
        'site_header': 'Farm2Hotels Administration',
        'site_title': 'Farm2Hotels Admin',
    }

    # --- NEW: Handle users who are ALREADY logged in ---
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin_dashboard')
            # If they are logged in but NOT an admin, log them out or send home
            # (Optional) return redirect('home') 
        return super().dispatch(request, *args, **kwargs)
    # ---------------------------------------------------

    def form_valid(self, form):
        # This handles the moment they click "Log In"
        user = form.get_user()
        if not user.is_superuser:
            form.add_error(None, "Access Denied: You are not authorized.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('admin_dashboard')
def manage_farmers(request):
    farmers = Farmer.objects.all()
    context = {'farmers': farmers}
    return render(request, 'pages/manage_farmers.html', context)

def manage_hotels(request):
    hotels = Hotel.objects.all()
    context = {'hotels': hotels}
    return render(request, 'pages/manage_hotels.html', context)

# In pages/views.py
from .forms import UserRegistrationForm
from .models import Farmer, Hotel
from django.contrib import messages

# In pages/views.py

# In pages/views.py

@user_passes_test(is_superuser_check)
def add_farmer(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # 1. Create User
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            # Optional: Save full name to user.first_name just for admin display
            user.first_name = form.cleaned_data['full_name'] 
            user.save()
            
            # 2. Create Farmer Profile using 'full_name'
            Farmer.objects.create(
                user=user,
                full_name=form.cleaned_data['full_name'],      # Matches your DB
                farm_name=form.cleaned_data['business_name'],  # Maps to farm_name
                phone=form.cleaned_data['phone'],
                email=user.email
            )
            messages.success(request, "Farmer added successfully!")
            return redirect('manage_farmers')
        else:
            print("FORM ERRORS:", form.errors)
    else:
        form = UserRegistrationForm()
    
    return render(request, 'pages/add_farmer.html', {'form': form})

@user_passes_test(is_superuser_check)
def add_hotel(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # 1. Create User
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.first_name = form.cleaned_data['full_name']
            user.save()
            
            # 2. Create Hotel Profile using 'full_name'
            Hotel.objects.create(
                user=user,
                full_name=form.cleaned_data['full_name'],       # Matches your DB
                hotel_name=form.cleaned_data['business_name'],  # Maps to hotel_name
                phone=form.cleaned_data['phone'],
                email=user.email
            )
            messages.success(request, "Hotel added successfully!")
            return redirect('manage_hotels')
        else:
             print("FORM ERRORS:", form.errors)
    else:
        form = UserRegistrationForm()

    return render(request, 'pages/add_hotel.html', {'form': form})

from django.shortcuts import render
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from datetime import timedelta
import json
from .models import Order, Profile, Product
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.models import User
from .forms import AddFarmerForm, AddHotelForm # Import the forms we just made
from django.contrib import messages
import csv
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
# ... existing views ...
from .forms import AddFarmerForm, AddHotelForm # <--- Add AddHotelForm here
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages # To show error messages


# ... existing views ...

def delete_user(request, user_id):
    # Get the user or show 404 error
    user = get_object_or_404(User, id=user_id)
    
    # Check role to decide where to redirect after deleting
    # We use a try/except block in case the user has no profile
    try:
        role = user.profile.role
    except:
        role = 'farmer' # Default fallback

    # Delete the user (This deletes Profile, Products, and Orders automatically)
    user.delete()
    
    # Redirect back to the correct page
    if role == 'hotel':
        return redirect('manage_hotels')
    return redirect('manage_farmers')


def manage_products(request):
    products = Product.objects.all()
    # We pass 'products' to the HTML file
    return render(request, 'pages/manage_products.html', {'products': products})

# Don't forget the delete logic we added earlier!
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('manage_products')


def export_report(request):
    # 1. Get the time period from the URL (default to 'monthly')
    period = request.GET.get('period', 'monthly')

    # 2. Calculate the date range
    today = timezone.now()
    if period == 'weekly':
        start_date = today - timedelta(days=7)
        filename = "report_weekly.csv"
    elif period == 'yearly':
        start_date = today - timedelta(days=365)
        filename = "report_yearly.csv"
    else: # monthly
        start_date = today - timedelta(days=30)
        filename = "report_monthly.csv"

    # 3. Create the CSV Response Object
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # 4. Create the CSV Writer
    writer = csv.writer(response)

    # 5. Write the Header Row
    writer.writerow(['Date Joined', 'Username', 'Role', 'Email', 'Phone', 'Status'])

    # 6. Query the Database (Filter by date joined)
    # Note: We are filtering Profile based on the User's join date
    users = Profile.objects.select_related('user').filter(user__date_joined__gte=start_date)

    # 7. Write the Data Rows
    for profile in users:
        writer.writerow([
            profile.user.date_joined.strftime("%Y-%m-%d %H:%M"), # Date
            profile.user.username,                               # Name
            profile.role.capitalize(),                           # Role (Farmer/Hotel)
            profile.user.email,                                  # Email
            profile.phone,                                       # Phone
            "Active" if profile.is_approved else "Pending"       # Status
        ])

    return response

#register form for farmer and hotel

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # 1. Create User
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            # 2. Create Profile
            Profile.objects.create(
                user=user,
                role=form.cleaned_data['role'],
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                is_approved=True  # Auto-approve for now so you can test easily
            )
            
            messages.success(request, 'Account created! Please login.')
            return redirect('login')
    else:
        form = RegisterForm()
    
    return render(request, 'pages/register.html', {'form': form})

from .forms import RegisterForm


# pages/views.py
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Product, Farmer

# pages/views.py
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt # Optional if using CSRF token in header
from .models import Product

# pages/views.py



@login_required
def clear_inventory(request):
    if request.method == 'POST':
        Product.objects.filter(farmer=request.user).delete()
        return JsonResponse({'status': 'cleared'})

def add_product_page(request):
    return render(request, 'pages/add_product.html')

from .models import CartItem


import json
from decimal import Decimal, InvalidOperation


@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        try:
            # 1. Parse Data
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)

            # Handle Quantity
            qty_raw = str(data.get('quantity', '1')).strip()
            if not qty_raw: qty_raw = '1'
            
            try:
                user_quantity = Decimal(qty_raw)
            except:
                return JsonResponse({'error': 'Invalid number'}, status=400)

            if user_quantity <= 0:
                return JsonResponse({'error': 'Quantity must be > 0'}, status=400)

            # 2. Get Product
            product_obj = get_object_or_404(Product, id=product_id)
            available_stock = Decimal(str(product_obj.quantity_available))
            # --- FIX 1: Use 'quantity_available' (not quantity) ---
            # And convert Float to Decimal safely
            if not product_obj.is_active:
                return JsonResponse({'error': 'This item is currently unavailable.'}, status=400)
            
            if available_stock <= 0:
                return JsonResponse({'error': 'This item is Out of Stock.'}, status=400)

            # 3. Security Check
            if not hasattr(request.user, 'hotel'):
                 return JsonResponse({'error': 'Only Hotels can add to cart.'}, status=403)
            
            # 4. Check Existing Cart
            # Ensure we filter by 'product' (or 'produce' if you kept that name)
            existing_item = CartItem.objects.filter(hotel=request.user.hotel, product=product_obj).first()
            current_cart_qty = existing_item.quantity if existing_item else Decimal('0')
            
            total_requested = current_cart_qty + user_quantity
            
            if total_requested > available_stock:
                # --- FIX 2: Removed 'product_obj.unit', used 'kg' instead ---
                return JsonResponse({
                    'error': f'Insufficient stock. Only {available_stock} kg available.'
                }, status=400)

            # 5. Save to Cart
            cart_item, created = CartItem.objects.get_or_create(
                hotel=request.user.hotel, 
                product=product_obj, 
                defaults={'quantity': user_quantity} 
            )
            
            if not created:
                cart_item.quantity += user_quantity
                cart_item.save()
            
            # --- FIX 3: Removed 'product_obj.unit', used 'kg' instead ---
            return JsonResponse({'message': f'Added {user_quantity} kg to cart!'})

        except Exception as e:
            print(f"CART ERROR: {str(e)}") # This helps you see errors in terminal
            return JsonResponse({'error': f"Server Error: {str(e)}"}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)
@login_required
def my_cart(request):
    if not hasattr(request.user, 'hotel'):
        return redirect('home')

    # Fetch items
    cart_items = CartItem.objects.filter(hotel=request.user.hotel).select_related('product')

    grand_total = Decimal('0.00')
    
    for item in cart_items:
        # FIX: Use 'price_per_kg' instead of 'price'
        price = item.product.price_per_kg 
        
        # Calculate row total
        item.total_cost = price * item.quantity
        grand_total += item.total_cost

    context = {
        'cart_items': cart_items,
        'grand_total': grand_total
    }
    return render(request, "pages/my_cart.html", context)

# --- 1. CHECKOUT API (Place Order) ---
@login_required
def checkout_api(request):
    if request.method == 'POST':
        try:
            hotel_user = request.user.hotel
            cart_items = CartItem.objects.filter(hotel=hotel_user)

            if not cart_items.exists():
                return JsonResponse({'error': 'Cart is empty'}, status=400)

            with transaction.atomic(): # Safe Database Transaction
                # A. Group items by Farmer (Since you might have multiple farmers in one cart)
                # For simplicity, we will create ONE order per Farmer found in the cart
                
                # 1. Get unique farmers from cart
                farmers = set(item.product.farmer for item in cart_items)

                for farmer_user in farmers:
                    # 2. Get the actual Farmer Profile object
                    # (Assuming your Farmer model is linked to User)
                    farmer_profile = farmer_user.farmer 

                    # 3. Create the Order
                    order = Order.objects.create(
                        hotel=hotel_user,
                        farmer=farmer_profile,
                        status='Pending'
                    )

                    # 4. Filter items for this specific farmer
                    farmer_items = cart_items.filter(product__farmer=farmer_user)

                    for item in farmer_items:
                        # 5. Create Order Item
                        OrderItem.objects.create(
                            order=order,
                            item_name=item.product.name,
                            quantity=item.quantity,
                            price_at_purchase=item.product.price_per_kg # or .price
                        )

                        # 6. DEDUCT STOCK
                        product = item.product
                        product.quantity_available = Decimal(str(product.quantity_available)) - item.quantity
                        product.save()
                        
                        # 7. Remove from Cart
                        item.delete()

            return JsonResponse({'message': 'Order placed successfully! Check "My Orders".'})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

# --- 2. CANCEL ORDER ---
@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, hotel=request.user.hotel)
    
    # Only allow cancel if Pending
    if order.status == 'Pending':
        # Optional: RESTOCK items (Add quantity back)
        for item in order.order_items.all():
            # Find the original product by name (since OrderItem saves name, not ID usually)
            # Or if you kept a Foreign Key, use that. 
            # Assuming strictly based on your previous model:
            try:
                prod = Product.objects.get(name=item.item_name, farmer=order.farmer.user)
                prod.quantity_available += Decimal(str(item.quantity))
                prod.save()
            except Product.DoesNotExist:
                pass # Product might have been deleted, just ignore

        order.delete()
        messages.success(request, "Order Cancelled.")
    else:
        messages.error(request, "Cannot cancel a processed order.")
    
    return redirect('orders')

# --- 3. VIEW ORDERS PAGE ---
@login_required
def orders(request):
    if hasattr(request.user, 'hotel'):
        # Show Hotel's orders
        my_orders = Order.objects.filter(hotel=request.user.hotel).order_by('-created_at')
    elif hasattr(request.user, 'farmer'):
        # Show Farmer's orders
        my_orders = Order.objects.filter(farmer=request.user.farmer).order_by('-created_at')
    else:
        my_orders = []
        
    return render(request, "pages/orders.html", {'orders': my_orders})

# Add these imports if not already there
from django.shortcuts import get_object_or_404
from decimal import Decimal

# --- 1. UPDATE CART QUANTITY (+ / -) ---
@login_required
def update_cart_api(request, item_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action') # 'increase' or 'decrease'
            
            # Get the cart item
            cart_item = get_object_or_404(CartItem, id=item_id, hotel=request.user.hotel)
            product = cart_item.product
            
            if action == 'increase':
                # Check Stock Limit before adding
                if cart_item.quantity + 1 <= product.quantity_available:
                    cart_item.quantity += Decimal('1')
                    cart_item.save()
                else:
                    return JsonResponse({'error': f'Stock limit reached! Only {product.quantity_available} available.'}, status=400)

            elif action == 'decrease':
                # Don't let it go below 1 (User should use delete button for that)
                if cart_item.quantity > 1:
                    cart_item.quantity -= Decimal('1')
                    cart_item.save()
                else:
                    return JsonResponse({'error': 'Minimum quantity is 1. Use the remove button to delete.'}, status=400)

            return JsonResponse({'message': 'Updated'})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

# --- 2. REMOVE ITEM (Trash Can) ---
@login_required
def remove_cart_item(request, item_id):
    if request.method == 'DELETE':
        try:
            cart_item = get_object_or_404(CartItem, id=item_id, hotel=request.user.hotel)
            cart_item.delete()
            return JsonResponse({'message': 'Item removed'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'Invalid method'}, status=400)

# Add this import if missing
from django.shortcuts import render, get_object_or_404

@login_required
def farmer_products_view(request, farmer_id):
    # 1. Get the specific Farmer profile
    farmer_profile = get_object_or_404(Farmer, id=farmer_id)
    
    # 2. Get products belonging to this farmer's USER account
    # (Since Product model links to User, not Farmer model directly)
    products = Product.objects.filter(farmer=farmer_profile.user)
    
    context = {
        'farmer': farmer_profile,
        'products': products
    }
    return render(request, 'pages/farmer_products.html', context)

# In pages/views.py

@login_required
def farmer_inventory_api(request):
    # --- GET: Fetch List ---
    if request.method == 'GET':
        products = Product.objects.filter(farmer=request.user).values(
            'id', 'name', 'category', 'quantity_available', 'price_per_kg', 'is_active'
        )
        return JsonResponse(list(products), safe=False)

    # --- POST: Add Product ---
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Use float() instead of Decimal() to match your database
            Product.objects.create(
                farmer=request.user,
                name=data.get('name'),
                category=data.get('category'),
                quantity_available=float(data.get('qty')), 
                price_per_kg=float(data.get('price')),
                is_active=True
            )
            return JsonResponse({'message': 'Product added!'})
        except Exception as e:
            print(f"ADD ERROR: {e}") # Check Terminal for this
            return JsonResponse({'error': str(e)}, status=400)

    # --- PUT: Update Product ---
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            # Fetch product safely
            product = get_object_or_404(Product, id=data.get('id'), farmer=request.user)
            
            # Use float() here too
            product.quantity_available = float(data.get('qty'))
            product.price_per_kg = float(data.get('price'))
            product.save()
            
            return JsonResponse({'message': 'Updated successfully!'})
        except Exception as e:
            print(f"UPDATE ERROR: {e}") # Check Terminal for this
            return JsonResponse({'error': str(e)}, status=400)

    # --- DELETE: Remove Product ---
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            prod_id = data.get('id')
            
            if not prod_id:
                return JsonResponse({'error': 'Product ID missing'}, status=400)

            product = get_object_or_404(Product, id=prod_id, farmer=request.user)
            product.delete()
            
            return JsonResponse({'message': 'Deleted successfully!'})
        except Exception as e:
            print(f"DELETE ERROR: {e}") # Check Terminal for this
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid method'}, status=400)
# --- 2. TOGGLE STATUS (Available / Unavailable) ---
@login_required
@csrf_exempt
def toggle_product_status(request, product_id):
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id, farmer=request.user)
            # Toggle the status
            product.is_active = not product.is_active
            product.save()
            return JsonResponse({'status': product.is_active})
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
            
    return JsonResponse({'error': 'Invalid method'}, status=400)

# In pages/views.py

# ... imports ...

@user_passes_test(lambda u: u.is_superuser, login_url='home')
def admin_dashboard(request):
    # ... logic ...
    return render(request, 'pages/admin_dashboard.html')

def admin_delete_user(request, user_id):
    # ... logic ...
    return redirect('manage_hotels') or redirect('manage_farmers')