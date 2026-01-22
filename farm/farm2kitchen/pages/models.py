from django.db import models
from django.contrib.auth.models import User


class Farmer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    farm_name = models.CharField(max_length=100) # View saves 'entity_name' here
    phone = models.CharField(max_length=15)
    email = models.EmailField(default="True")
    password = models.CharField(max_length=100, default="True") 

    def __str__(self):
        return self.farm_name

class Hotel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    hotel_name = models.CharField(max_length=100) # View saves 'entity_name' here
    phone = models.CharField(max_length=15)
    email = models.EmailField(default="True")
    password = models.CharField(max_length=100 , default="True")

    def __str__(self):
        return self.hotel_name
    
class Profile(models.Model):
    ROLE_CHOICES = (('farmer', 'Farmer'), ('hotel', 'Hotel'), ('admin', 'Admin'))
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False) # Admin must approve them

    def __str__(self):
        return f"{self.user.username} ({self.role})"

# 2. PRODUCT MODEL (What farmers sell)
class Product(models.Model):
    CATEGORY_CHOICES = (('Veg', 'Vegetables'), ('Fruit', 'Fruits'), ('Grain', 'Grains'), ('Dairy', 'Dairy'))
    
    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products', default="True")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='')
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    quantity_available = models.FloatField(default=0.0) # in kg
    is_active = models.BooleanField(default=True) # Admin can hide product
    

    def __str__(self):
        return f"{self.name} - ₹{self.price_per_kg}/kg"

# 3. ORDER MODEL (Transactions)
# --- 4. ORDERS (Data from Screenshot 170202) ---
class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Ready', 'Ready'),
        ('Delivered', 'Delivered'),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, default=None) # Orders grouped by farmer
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_amount(self):
        # Automatically calculates the final "Total Amount" (e.g., 2900)
        return sum(item.item_total for item in self.order_items.all())

    def __str__(self):
        return f"Order #{self.id} - {self.farmer.farm_name}"
    
# --- 3. SHOPPING CART (Data from Screenshot 170107) ---
class CartItem(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2) # e.g., 30.00 kg

    @property
    def subtotal(self):
        # Dynamically calculates the 1200 seen in your cart image
        return self.quantity * self.produce.price_per_kg
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    item_name = models.CharField(max_length=100) # Snapshots name at time of order
    quantity = models.DecimalField(max_digits=10, decimal_places=2) # e.g., 50 kg
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2) # e.g., 40.00

    @property
    def item_total(self):
        # e.g., 50kg * 40 = 2000
        return self.quantity * self.price_at_purchase