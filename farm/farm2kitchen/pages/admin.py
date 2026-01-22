from django.contrib import admin
from .models import OrderItem, Profile, Product, Order, CartItem
# Register your models here.
from .models import Farmer
from .models import Hotel

admin.site.register(Farmer)
admin.site.register(Hotel)

# This makes the models visible in the Admin Panel
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'is_approved')
    list_filter = ('role', 'is_approved')
    search_fields = ('user__username', 'phone')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'farmer', 'category', 'price_per_kg', 'is_active')
    list_filter = ('category', 'is_active')

class OrderAdmin(admin.ModelAdmin):
    # OLD (Error): list_display = ('id', 'product', 'status')
    
    # NEW (Fixed): Only list fields that definitely exist
    list_display = ('id', 'status') 

admin.site.register(Order, OrderAdmin)


admin.site.register(CartItem)

admin.site.register(OrderItem)