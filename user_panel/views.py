from django.shortcuts import render,get_object_or_404,redirect
from authentication.models import Product, Category, Brand,Address,Wishlist,Cart,Order,OrderItem,Wallet, Transaction,Variant,ProductImage,Offer
from django.contrib.auth.decorators import user_passes_test
from .decorators import active_user_required
from .forms import UserEditForm,AddressForm
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
import json
import logging
logger = logging.getLogger(__name__)
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.db import transaction
from django.views.decorators.csrf import csrf_protect   
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image as ReportLabImage
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,Image
import os
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.views.decorators.cache import never_cache
from decimal import Decimal
from django.db.models import Min
from django.db.models import Prefetch, Sum



@active_user_required
def home(request):
    # Fetch categories with try-except for robustness
    try:
        mobile_category = Category.objects.filter(name__iexact='Mobile', status=True).first()
        laptop_category = Category.objects.filter(name__iexact='Laptop', status=True).first()
        
        # Products with prefetch for performance
        mobiles = (Product.objects.filter(category=mobile_category, status=True)
                  .prefetch_related('variants__images') 
                  if mobile_category else Product.objects.none())
        
        laptops = (Product.objects.filter(category=laptop_category, status=True)
                  .prefetch_related('variants__images')
                  if laptop_category else Product.objects.none())
        
        brands = Brand.objects.filter(status=True)
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        mobiles = Product.objects.none()
        laptops = Product.objects.none()
        brands = Brand.objects.none()

    context = {
        'mobiles': mobiles,
        'laptops': laptops,
        'brands': brands
    }
    return render(request, 'home.html', context)


@active_user_required
def shop_page(request):
    
    mobiles = Product.objects.filter(category__name='Mobile', category__status=True, status=True)
    laptops = Product.objects.filter(category__name='Laptop', category__status=True, status=True)
    
    
    category = request.GET.get('category', None)  
    brand = request.GET.get('brand', None)  
    sort = request.GET.get('sort', None)  
    
    
    if category:
        mobiles = mobiles.filter(category__name=category) if category == 'Mobile' else Product.objects.none()
        laptops = laptops.filter(category__name=category) if category == 'Laptop' else Product.objects.none()
    
    if brand:
        mobiles = mobiles.filter(brand__name=brand)
        laptops = laptops.filter(brand__name=brand)
  
    if sort:
        if sort == 'price_low':
            mobiles = mobiles.annotate(min_price=Min('variants__price')).order_by('min_price')
            laptops = laptops.annotate(min_price=Min('variants__price')).order_by('min_price')
        elif sort == 'price_high':
            mobiles = mobiles.annotate(min_price=Min('variants__price')).order_by('-min_price')
            laptops = laptops.annotate(min_price=Min('variants__price')).order_by('-min_price')
        elif sort == 'a_z':
            mobiles = mobiles.order_by('name')
            laptops = laptops.order_by('name')
        elif sort == 'z_a':
            mobiles = mobiles.order_by('-name')
            laptops = laptops.order_by('-name')
    
    unique_brands = Brand.objects.values_list('name', flat=True).distinct()
    
    context = {
        'mobiles': mobiles,
        'laptops': laptops,
        'sort': sort,
        'category': category,
        'brand': brand,
        'unique_brands': unique_brands,  
    }
    return render(request, 'shop.html', context)


@active_user_required
def search_products(request):
    query = request.GET.get('query', '')
    mobiles = Product.objects.none()
    laptops = Product.objects.none()
    sort = request.GET.get('sort', '')
    category = request.GET.get('category', '')
    brand = request.GET.get('brand', '')
    # Check if user is admin
    is_admin = request.user.is_staff or request.user.is_superuser
    if query:
        try:
            categories = list(Category.objects.all().values('id', 'name'))   
            mobile_category = Category.objects.filter(name__iexact='mobile').first()
            if not mobile_category:
                mobile_category = Category.objects.filter(name__iexact='Mobile').first() or \
                                Category.objects.filter(name__iexact='Phones').first()
            laptop_category = Category.objects.filter(name__iexact='laptop').first()
            if not laptop_category:
                laptop_category = Category.objects.filter(name__iexact='Laptop').first() or \
                                Category.objects.filter(name__iexact='Laptops').first()
            # For non-admin users, exclude hidden products
            product_filter = {}
            if not is_admin:
                product_filter['is_hidden'] = False
            if mobile_category and laptop_category:
                mobiles = Product.objects.filter(name__icontains=query, category=mobile_category, **product_filter)
                laptops = Product.objects.filter(name__icontains=query, category=laptop_category, **product_filter)
            else:
                all_products = Product.objects.filter(name__icontains=query, **product_filter)
                for product in all_products:
                    if product.category:
                        if product.category.name.lower() in ['mobile', 'phones']:
                            mobiles = mobiles | Product.objects.filter(id=product.id)
                        elif product.category.name.lower() in ['laptop', 'laptops']:
                            laptops = laptops | Product.objects.filter(id=product.id)
            if category:
                if category == 'Mobile':
                    laptops = Product.objects.none()
                elif category == 'Laptop':
                    mobiles = Product.objects.none()
            if brand:
                mobiles = mobiles.filter(brand__name=brand)
                laptops = laptops.filter(brand__name=brand)
            if sort:
                if sort == 'price_low':
                    mobiles = mobiles.order_by('price')
                    laptops = laptops.order_by('price')
                elif sort == 'price_high':
                    mobiles = mobiles.order_by('-price')
                    laptops = laptops.order_by('-price')
                elif sort == 'a_z':
                    mobiles = mobiles.order_by('name')
                    laptops = laptops.order_by('name')
                elif sort == 'z_a':
                    mobiles = mobiles.order_by('-name')
                    laptops = laptops.order_by('-name')
        except Exception as e:
            print(f"Error in search: {str(e)}")
    unique_brands = Product.objects.values_list('brand__name', flat=True).distinct()
    context = {
        'mobiles': mobiles,
        'laptops': laptops,
        'query': query,
        'sort': sort,
        'category': category,
        'brand': brand,
        'unique_brands': unique_brands,
        'is_admin': is_admin,  # Pass to template to show admin-specific UI if needed
    }
    return render(request, 'search_results.html', context)


def brand_products(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    products = Product.objects.filter(brand=brand, status=True)
    return render(request, 'brand_products.html', {'brand': brand, 'products': products})


@active_user_required
def mobile_details(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'quantity': product.stock   
        })
    return render(request, 'mobile product page.html', {'product': product})

@active_user_required
def laptop_detail(request, laptop_id):
    from django.utils import timezone
    
    laptop = get_object_or_404(Product, id=laptop_id, category__name='Laptop')
    
    # Get offers for this laptop with a more generic approach
    offers = Offer.objects.filter(
        product=laptop,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    )
    
    # Get related models - laptops from the same brand
    related_models = Product.objects.filter(
        category__name='Laptop',
        brand=laptop.brand
    ).exclude(id=laptop.id)[:4]
    
    return render(request, 'laptop_detail page.html', {
        'laptop': laptop,
        'offers': offers,
        'related_models': related_models
    })
    
def account_profile(request):
    return render(request, 'account_details.html', {'user': request.user})

@login_required
def update_account_profile(request):
    logger.info(f"Request received: {request.method}, Headers: {dict(request.headers)}")
    
    if not request.user.is_authenticated:
        logger.warning("User not authenticated")
        return JsonResponse({"success": False, "errors": {"auth": ["User not authenticated"]}}, status=401)

    if request.method == "POST":
        logger.debug(f"POST data: {request.POST}, FILES: {request.FILES}")
        form = UserEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()
            logger.info(f"Profile updated for user: {user.username}, Profile Image: {user.profile_image}")
            
            # Temporarily force JSON response for POST requests
            return JsonResponse({
                "success": True,
                "username": user.username,
                "email": user.email,
                "profile_image": user.profile_image.url if user.profile_image else None
            })
        else:
            logger.error(f"Form validation failed: {form.errors}")
            return JsonResponse({"success": False, "errors": form.errors.as_json()}, status=400)
    else:
        logger.info("Rendering profile form")
        return render(request, "account_profile.html", {"form": UserEditForm(instance=request.user)})
            

def manage_address(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'manage_address.html', {'addresses': addresses})

def add_address(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        city = request.POST.get('city')
        district = request.POST.get('district')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')
        phone = request.POST.get('phone')
        landmark = request.POST.get('landmark', '')
        alternative_phone = request.POST.get('alternative_phone', '')

        if not all([name, city, district, state, pincode, phone]):
            return JsonResponse({
                'success': False,
                'message': 'All required fields must be filled.'
            }, status=400)

        address = Address(
            user=request.user,
            name=name,
            city=city,
            district=district,
            state=state,
            pincode=pincode,
            phone=phone,
            landmark=landmark,
            alternative_phone=alternative_phone
        )
        address.save()
    return render(request, 'add_address.html')

def edit_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user) 

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect('manage_address')  
    else:
        form = AddressForm(instance=address)

    return render(request, 'edit_address.html', {'form': form})

def delete_address(request, pk):
    if request.method == 'POST':
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

def add_to_cart(request, variant_id):
    # Fetch the variant instead of product
    variant = get_object_or_404(Variant, id=variant_id)
    product = variant.product

    # Check product and category availability
    if not product.status or product.is_deleted or not product.category.status:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'This product is unavailable.'})
        messages.error(request, "This product is unavailable.")
        return redirect('shop')
    
    # Check stock
    if variant.stock <= 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'This product is out of stock.'})
        messages.error(request, "This product is out of stock.")
        return redirect('home')
    
     # Handle wishlist removal if needed
    wishlist_id = None
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.body:
        try:
            data = json.loads(request.body)
            wishlist_id = data.get('wishlist_id')
        except json.JSONDecodeError:
            pass  
    
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product,
        variant=variant,
        defaults={'quantity': 1}
    )
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Remove from wishlist if applicable
    if wishlist_id:
        Wishlist.objects.filter(id=wishlist_id, user=request.user).delete()
    else:
        Wishlist.objects.filter(user=request.user, product=product).delete()
    
    # Get counts for response
    cart_count = Cart.objects.filter(user=request.user).count()  # Unique items
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    if not created:
        # Check stock using variant.stock, not product.quantity
        if cart_item.quantity < variant.stock:
            cart_item.quantity += 1
            cart_item.save()
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f"{product.name} quantity increased in cart!",
                    'cart_count': cart_count,
                    'wishlist_count': wishlist_count
                })
            messages.success(request, f"{product.name} quantity increased in cart!")
        else:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot add more, stock limit reached.',
                    'cart_count': cart_count,
                    'wishlist_count': wishlist_count
                })
            messages.warning(request, "Cannot add more, stock limit reached.")
    else:
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': f"{product.name} added to cart!",
                'cart_count': cart_count,
                'wishlist_count': wishlist_count
            })
        messages.success(request, f"{product.name} added to cart!")
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': 'Action completed.',
            'cart_count': cart_count,
            'wishlist_count': wishlist_count
        })
    return redirect('home')

def get_default_variant(request, product_id):
    """Get the first available variant for a product."""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect('home')
        
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Check if product is available
        if not product.status or product.is_deleted or not product.category.status:
            return JsonResponse({
                'success': False, 
                'message': 'This product is unavailable.'
            })
            
        # Get first variant with stock
        variant = product.variants.filter(stock__gt=0).first()
        
        if variant:
            return JsonResponse({
                'success': True,
                'variant_id': variant.id,
                'message': 'Default variant found.'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'This product is out of stock.'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error getting product variant.',
            'error': str(e)
        })
    
import logging
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)

@login_required
@require_POST
def add_to_cart_with_variant(request, variant_id):
    try:
        logger.info(f"Add to cart request from {request.user} for variant {variant_id}")
        print("hey")
        # Get variant with related data in one query
        variant = Variant.objects.select_related(
            'product',
            'product__category'
        ).get(id=variant_id)
        
        # Validate product status
        if not variant.product.status or not variant.product.category.status:
            logger.warning(f"Product {variant.product.id} is unavailable")
            return JsonResponse({
                'success': False,
                'message': 'This product is currently unavailable',
                'status': 'unavailable'
            }, status=400)
        
        # Validate stock
        if variant.stock <= 0:
            logger.warning(f"Variant {variant_id} out of stock")
            return JsonResponse({
                'success': False,
                'message': 'This product is out of stock',
                'status': 'out_of_stock',
                'stock': 0
            }, status=400)
        
        with transaction.atomic():
            # Get or create cart item
            cart_item, created = Cart.objects.get_or_create(
                user=request.user,
                variant=variant,
                defaults={'quantity': 1, 'product': variant.product}
            )
            
            if not created:
                # Check stock before increasing quantity
                if cart_item.quantity >= variant.stock:
                    logger.warning(f"Stock limit reached for variant {variant_id}")
                    return JsonResponse({
                        'success': False,
                        'message': 'Cannot add more items. Stock limit reached.',
                        'status': 'max_quantity',
                        'stock': variant.stock,
                        'current_quantity': cart_item.quantity
                    }, status=400)
                
                cart_item.quantity += 1
                cart_item.save()
            
            logger.info(f"Cart updated for {request.user}. New quantity: {cart_item.quantity}. New stock: {variant.stock}")
            
            return JsonResponse({
                'success': True,
                'message': 'Added to cart successfully!',
                'stock': variant.stock,
                'current_quantity': cart_item.quantity,
                'cart_count': Cart.objects.filter(user=request.user).count(),
                'is_new_item': created
            })
            
    except Variant.DoesNotExist:
        logger.error(f"Variant {variant_id} not found")
        return JsonResponse({
            'success': False,
            'message': 'Product variant not found',
            'status': 'not_found'
        }, status=404)
        
    except Exception as e:
        logger.error(f"Error in add_to_cart: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.',
            'status': 'error'
        }, status=500)
    
@require_POST
@login_required
def update_cart_quantity(request, product_id, action):
    try:
        cart_item = get_object_or_404(Cart, user=request.user, product_id=product_id)
        variant = cart_item.variant
        
        if action == 'increase':
            if cart_item.quantity >= variant.stock:
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot add more. Stock limit reached.',
                    'stock': variant.stock
                }, status=400)
            
            cart_item.quantity += 1
            cart_item.save()
            
        elif action == 'decrease':
            if cart_item.quantity <= 1:
                cart_item.delete()
            else:
                cart_item.quantity -= 1
                cart_item.save()
        
        # Recalculate totals
        cart_items = Cart.objects.filter(user=request.user)
        subtotal = sum(item.quantity * item.variant.price for item in cart_items)
        delivery_charge = 0  # Adjust as needed
        total_price = subtotal + delivery_charge
        
        return JsonResponse({
            'success': True,
            'quantity': cart_item.quantity if cart_item.quantity > 0 else 0,
            'subtotal': str(subtotal),
            'delivery_charge': str(delivery_charge),
            'total_price': str(total_price),
            'cart_count': cart_items.count(),
            'stock': variant.stock,
            'message': 'Quantity updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('variant__product')
    
    subtotal = sum(item.quantity * item.variant.price for item in cart_items)
    delivery_charge = 0 if subtotal > 0 else 0
    total_price = subtotal + delivery_charge

    out_of_stock = any(item.variant.stock < item.quantity for item in cart_items)  

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'total_price': total_price,
        'out_of_stock': out_of_stock
    })

@require_POST
@login_required
def remove_from_cart(request, product_id):
    try:
        # Find all cart items for this user and product
        cart_items = Cart.objects.filter(user=request.user, variant__product_id=product_id)
        
        if not cart_items.exists():
            return JsonResponse({
                'success': False,
                'message': 'Cart item not found.'
            }, status=404)
        
        # Get the product name from the first item
        product_name = cart_items.first().variant.product.name
        
        # Delete all matching cart items
        deleted_count, _ = cart_items.delete()
        
        # Recalculate cart details
        remaining_cart_items = Cart.objects.filter(user=request.user)
        subtotal = sum(item.quantity * item.variant.price for item in remaining_cart_items)
        delivery_charge = 0  # Adjust as needed
        total_price = subtotal + delivery_charge
        cart_count = remaining_cart_items.count()

        print(f"Removed {deleted_count} cart item(s). Remaining cart count: {cart_count}")

        return JsonResponse({
            'success': True,
            'subtotal': str(subtotal),
            'delivery_charge': str(delivery_charge),
            'total_price': str(total_price),
            'cart_count': cart_count,
            'message': f"{product_name} removed from cart."
        })
    except Exception as e:
        print(f"Error removing cart item: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

# def getCheckout(request):

#     return render(request,"checkout.html")



def checkout(request):
    try:
        # Ensure user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to proceed to checkout.")
            return redirect('login')  # Adjust to your login URL name

        cart_items = Cart.objects.filter(user=request.user)
        
        # Log debug information
        logger.debug(f"Cart items count: {cart_items.count()}")
        
        # Check if cart is empty
        if not cart_items.exists():
            messages.warning(request, "Your cart is empty.")
            return redirect('cart')  # Redirect back to cart page

        # Check for out-of-stock items
        out_of_stock_items = []
        for item in cart_items:
            if item.quantity > item.variant.stock:
                out_of_stock_items.append(item.variant.product.name)
                messages.error(request, f"{item.variant.product.name} has insufficient stock.")

        if out_of_stock_items:
            return redirect('cart')

        subtotal = sum(item.quantity * item.variant.price for item in cart_items)
        delivery_charge = 0 if subtotal > 0 else 0 
        total_price = subtotal + delivery_charge

        addresses = Address.objects.filter(user=request.user)

        # Log URLs for debugging
        logger.debug(f"Add Address URL: {reverse('add_address')}")
        logger.debug(f"Place Order URL: {reverse('place_order')}")

        context = {
            'cart_items': cart_items,
            'subtotal': subtotal,
            'delivery_charge': delivery_charge,
            'total_price': total_price,
            'addresses': addresses,
        }
        return render(request, 'checkout.html', context)

    except Exception as e:
        logger.error(f"Error in checkout view: {str(e)}")
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('cart')
    
# views.py (user side)
import logging
import json
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

@csrf_exempt
def place_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            payment_method = data.get('payment_method')
            shipping_address_id = data.get('shipping_address')

            if not payment_method or not shipping_address_id:
                return JsonResponse({'success': False, 'message': 'Invalid data'}, status=400)

            user = request.user
            address = Address.objects.get(id=shipping_address_id, user=user)
            cart_items = Cart.objects.filter(user=user)
            
            if not cart_items.exists():
                return JsonResponse({'success': False, 'message': 'Cart is empty'}, status=400)

            # Detailed stock checking
            insufficient_stock_items = []
            
            # First pass: Check stock availability
            for cart_item in cart_items:
                variant = cart_item.variant
                logger.info(f"Stock Check: {variant} - Requested: {cart_item.quantity}, Available: {variant.stock}")
                
                if cart_item.quantity > variant.stock:
                    insufficient_stock_items.append({
                        'name': f"{variant.product.name} ({variant.ram}GB/{variant.storage}GB/{variant.color})",
                        'requested': cart_item.quantity,
                        'available': variant.stock
                    })

            # If any items have insufficient stock, return detailed error
            if insufficient_stock_items:
                return JsonResponse({
                    'success': False,
                    'message': 'Insufficient stock',
                    'details': insufficient_stock_items
                }, status=400)

            with transaction.atomic():
                # Calculate total price
                total_price = sum(item.variant.price * item.quantity for item in cart_items)
                
                # Create order
                order = Order.objects.create(
                    user=user,
                    shipping_address=address,
                    payment_method=payment_method.upper(),
                    total_price=total_price
                )
                
                # Process each cart item
                for cart_item in cart_items:
                    variant = cart_item.variant
                    
                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        variant=variant,
                        quantity=cart_item.quantity,
                        price=variant.price
                    )
                    
                    # Reduce variant stock
                    variant.stock -= cart_item.quantity
                    variant.save(update_fields=['stock'])
                
                # Clear the cart
                cart_items.delete()

            return JsonResponse({
                'success': True,
                'order_id': order.id
            })
        
        except Address.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invalid shipping address'}, status=400)
        except Exception as e:
            logger.error(f"Order placement error: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)


def order_success(request, order_id):
    """Display the order success page after a successful order placement."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order_id': order.id,
        'order': order,
        'message': f'Your order #{order.id} has been placed successfully!',
        'total_price': order.total_price,
        'payment_method': order.payment_method,
        'shipping_address': order.shipping_address, 
        'order_items': order.items.all()
    }
    
    return render(request, 'order_success.html', context)

@login_required
@never_cache
def order_details(request):
    user_orders = Order.objects.filter(user=request.user).order_by('-created_at')

    paginator = Paginator(user_orders, 5)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    print(f"User orders fetched at {timezone.now()}: {[(o.id, o.status) for o in page_obj]}")
    return render(request, 'order_details.html', {'page_obj': page_obj})

@login_required
def get_order_statuses(request):
    try:
        # Get all orders for the current user
        user_orders = Order.objects.filter(user=request.user)
        
        # Create a dictionary of order ID to status
        statuses = {str(order.id): order.status for order in user_orders}
        
        return JsonResponse({
            "success": True,
            "statuses": statuses
        })
    except Exception as e:
        print(f"Error fetching order statuses: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        })


@login_required
def order_fulldetail_view(request, order_id):
    try:
        # Get the order
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Get order items directly through the related name
        order_items = order.items.all().select_related('product', 'variant')
        
        # Debug: Check if order items exist
        print(f"Order #{order.id} - Total Price: {order.total_price}, Status: {order.status}")
        print(f"Number of Order Items Found: {order_items.count()}")
        for item in order_items:
            print(f"OrderItem - Product: {item.product}, Variant: {item.variant}, Quantity: {item.quantity}, Price: {item.price}")
        
        # Initialize lists and values
        order_items_with_images = []
        subtotal = Decimal('0.00')
        
        # Process each order item
        for item in order_items:
            # Calculate subtotal
            item_price = item.price or Decimal('0.00')
            subtotal += item.quantity * item_price
            
            # Get variant details if available
            variant_details = "N/A"
            try:
                if item.variant:
                    variant_details = f"{item.variant.ram}GB/{item.variant.storage}GB/{item.variant.color}"
            except AttributeError as e:
                print(f"Error fetching variant details for item {item.id}: {str(e)}")
                variant_details = "Custom variant"
            
            # Get product image
            image = None
            try:
                if item.variant and item.variant.images.exists():
                    image = item.variant.images.first()
                    print(f"Found image for variant {item.variant}: {image.image.url if image else 'No image'}")
                if not image and item.product:
                    image = ProductImage.objects.filter(product=item.product, variant__isnull=True).first()
                    print(f"Found image for product {item.product}: {image.image.url if image else 'No image'}")
            except Exception as e:
                print(f"Error fetching image for item {item.id}: {str(e)}")
                image = None
            
            # Get product name
            product_name = "Unknown Product"
            try:
                product_name = item.product.name if item.product else "Unknown Product"
            except Exception as e:
                print(f"Error fetching product name for item {item.id}: {str(e)}")
            
            # Add to our items list
            order_items_with_images.append({
                'item': item,
                'image': image,
                'product_name': product_name,
                'variant_details': variant_details
            })
        
        # Calculate totals
        shipping_fee = order.shipping_fee or Decimal('0.00')
        grand_total = subtotal + shipping_fee
        
        context = {
            'order': order,
            'order_items_with_images': order_items_with_images,
            'subtotal': subtotal,
            'shipping_fee': shipping_fee,
            'grand_total': grand_total,
        }
        
        # Debug: Print the final list
        print(f"Order Items Count: {len(order_items_with_images)}")
        for item_data in order_items_with_images:
            print(f"Product: {item_data['product_name']}, Variant: {item_data['variant_details']}, Quantity: {item_data['item'].quantity}, Price: {item_data['item'].price}")
        
        return render(request, 'order_fulldetail.html', context)
    
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('order_details')
    except Exception as e:
        # Log the error for debugging
        print(f"Error in order_fulldetail_view: {str(e)}")
        messages.error(request, "An error occurred while fetching order details.")
        return redirect('order_details')

def generate_invoice_pdf(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        total_price = order.calculate_total_price()
        shipping_fee = order.shipping_fee
        subtotal = total_price - shipping_fee

        # Create the HttpResponse object with PDF headers
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_Order_{order_id}.pdf"'

        # Create the PDF object
        doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name='Title',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1,  # Center alignment
            spaceAfter=12,
        )
        header_style = ParagraphStyle(
            name='Header',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=6,
        )
        normal_style = styles['BodyText']

        # Add title
        elements.append(Paragraph("Phonix - Order Invoice", title_style))
        logger.debug(f"Added title for Order #{order_id}")

        # Add order details
        elements.append(Paragraph(f"Order ID: #{order.id}", header_style))
        elements.append(Paragraph(f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        elements.append(Paragraph(f"Status: {order.status}", normal_style))
        elements.append(Spacer(1, 20))

        # Add order items table
        table_data = [["Image", "Product", "Quantity", "Price"]]
        for item in order.items.all():
            product_name = item.product.name if len(item.product.name) <= 40 else item.product.name[:37] + "..."
            
            # Safely handle product image
            img = None
            try:
                if item.variant and item.variant.images.exists():
                    product_image = item.variant.images.first()  # Use variant images instead of product
                    image_path = product_image.image.path
                    logger.debug(f"Checking image for {product_name}, Path: {image_path}")
                    if os.path.exists(image_path):
                        img = ReportLabImage(image_path, width=50, height=50)
                        logger.debug(f"Image exists for {product_name} at {image_path}")
                    else:
                        logger.warning(f"Image file missing for {product_name} at {image_path}")
                        img = Paragraph("No Image", normal_style)
                else:
                    logger.debug(f"No images for {product_name} or variant {item.variant}")
                    img = Paragraph("No Image", normal_style)
            except Exception as e:
                logger.error(f"Error processing image for {product_name}: {str(e)}")
                img = Paragraph("Image Error", normal_style)

            # Ensure price is valid
            price = item.price if item.price is not None else 0.00
            table_data.append([img, product_name, str(item.quantity), f"₹{price:.2f}"])

        # Create the table
        table = Table(table_data, colWidths=[60, 240, 80, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))

        # Add order summary
        elements.append(Paragraph("Order Summary", header_style))
        elements.append(Paragraph(f"Subtotal: ₹{subtotal:.2f}", normal_style))
        elements.append(Paragraph(f"Shipping Fee: ₹{shipping_fee:.2f}", normal_style))
        elements.append(Paragraph(f"Grand Total: ₹{total_price:.2f}", header_style))

        # Add footer
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("Thank you for shopping with Phonix!", normal_style))

        # Build the PDF
        logger.debug(f"Building PDF with {len(elements)} elements for Order #{order_id}")
        doc.build(elements)
        logger.info(f"Successfully generated PDF for Order #{order_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to generate PDF for Order #{order_id}: {str(e)}", exc_info=True)
        # Return a simple error PDF instead of raising a 500 error
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Error_Invoice_Order_{order_id}.pdf"'
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = [Paragraph(f"Error generating invoice: {str(e)}", getSampleStyleSheet()['BodyText'])]
        doc.build(elements)
        return response
    
def is_admin(user):
    return user.is_staff or user.is_superuser           

@login_required
@csrf_protect
def cancel_order(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.status in ["Pending", "Confirmed", "Shipped"]:
            try:
                with transaction.atomic():
                    order.status = "Cancelled"
                    order.save()
                    stock_updates = {}
                    for item in order.items.all():
                        # Check if the OrderItem has a Variant
                        if item.variant:
                            variant = item.variant
                            print(f"Before increment - Variant: {variant}, Stock: {variant.stock}, Item Quantity: {item.quantity}")
                            variant.stock += item.quantity  # Increment variant stock
                            print(f"After increment (pre-save) - Variant: {variant}, Stock: {variant.stock}")
                            variant.save()  # Save the updated stock
                            variant.refresh_from_db()  # Confirm the save
                            print(f"After save - Variant: {variant}, Stock: {variant.stock}")
                            stock_updates[variant.id] = variant.stock
                        else:
                            # Fallback to Product stock if no Variant (unlikely in your setup, but for safety)
                            product = item.product
                            print(f"Before increment - Product: {product.name}, Stock: {product.stock}, Item Quantity: {item.quantity}")
                            product.stock += item.quantity
                            print(f"After increment (pre-save) - Product: {product.name}, Stock: {product.stock}")
                            product.save()
                            product.refresh_from_db()
                            print(f"After save - Product: {product.name}, Stock: {product.stock}")
                            stock_updates[product.id] = product.stock
                    return JsonResponse({
                        "success": True,
                        "message": "Order cancelled successfully!",
                        "stock_updates": stock_updates
                    })
            except Exception as e:
                print(f"Transaction error: {e}")
                return JsonResponse({"success": False, "message": f"Transaction failed: {str(e)}"}, status=500)
        return JsonResponse({"success": False, "message": "Order cannot be cancelled!"}, status=400)

    return JsonResponse({"success": False, "message": "Invalid request!"}, status=400)


@login_required
@require_POST
def return_order(request, order_id):
    try:
        # Get the order
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Check if the order is eligible for return (must be in Delivered status)
        if order.status != "Delivered":
            return JsonResponse({
                "success": False,
                "message": "This order is not eligible for return. Only delivered orders can be returned."
            })
        
        # Get reason from request data
        data = json.loads(request.body)
        reason = data.get('reason', '')
        
        if not reason or len(reason.strip()) == 0:
            return JsonResponse({
                "success": False,
                "message": "Please provide a reason for the return."
            })
        
        # Use a transaction to ensure atomicity
        with transaction.atomic():
            # Update order status to Return Requested
            order.status = "Return Requested"
            order.save()
            
            # Increment stock for each variant in the order
            for item in order.items.all():
                if item.variant:  # Check if variant exists
                    variant = item.variant
                    variant.stock += item.quantity  # Increment the variant's stock
                    variant.save()
                    print(f"Incremented stock for {variant} by {item.quantity}. New stock: {variant.stock}")
                else:
                    print(f"No variant found for OrderItem {item.id}. Stock not updated.")
        
        # Optionally, store the return reason in a ReturnRequest model
        # If you don't have this model, you could create it to track return reasons
        
        return JsonResponse({
            "success": True,
            "message": "Return request submitted successfully. Stock updated."
        })
    except Order.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Order not found or does not belong to you."
        })
    except Exception as e:
        print(f"Error processing return request: {str(e)}")
        return JsonResponse({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        })
    
    
@login_required
@csrf_protect
@require_POST
def approve_return(request, order_id):
    print(f"Approve return endpoint hit for Order {order_id} at {timezone.now()}")
    try:
        order = Order.objects.get(id=order_id)
        print(f"Order {order_id} found - Current status: {order.status}")

        if order.status != "Return Requested":
            print(f"Order {order_id} not eligible for return - Status: {order.status}")
            return JsonResponse({"success": False, "message": "Order is not in Return Requested status"})

        print(f"Approving return for Order {order_id} - Current status: {order.status}")

        # Use a transaction to ensure atomicity
        with transaction.atomic():
            # Update order status
            order.status = "Returned"
            order.save()

            # Process return (this will handle wallet and transaction creation)
            order.process_return()

        updated_order = Order.objects.get(id=order_id)
        wallet = Wallet.objects.get(user=order.user)
        
        # Find the latest transaction for this order
        latest_transaction = Transaction.objects.filter(
            order=order, 
            transaction_type="CREDIT"
        ).order_by('-created_at').first()

        print(f"Return approved - Order {order_id} now: {updated_order.status}")

        return JsonResponse({
            "success": True, 
            "message": "Return approved and refund processed",
            "status": updated_order.status,
            "wallet_balance": float(wallet.balance),
            "transaction_id": latest_transaction.id if latest_transaction else None
        })
    except Order.DoesNotExist:
        return JsonResponse({"success": False, "message": "Order not found"})
    except Exception as e:
        print(f"Error approving return for order {order_id}: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)})
    
# This view seems redundant given approve_return handles the full order return
# If intended for a different purpose, clarify its use case
@login_required
@csrf_exempt
@require_POST
def return_product(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        # Assuming this is for a specific use case outside order context
        product.quantity += 1  # Adjust this logic if tied to an order
        product.save()
        return JsonResponse({
            "success": True,
            "message": "Product stock increased successfully.",
            "new_quantity": product.quantity
        })
    except Exception as e:
        return JsonResponse({"success": False, "message": f"An error occurred: {str(e)}"}, status=500)
    
def product_stock(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return JsonResponse({'stock': product.stock})

@csrf_exempt
@login_required
def add_to_wishlist(request, product_id):
    logger.info(f"add_to_wishlist called with product_id: {product_id}, Method: {request.method}, User: {request.user}")
    if request.method != 'POST':
        logger.error("Invalid request method")
        return JsonResponse({'success': False, 'message': 'Invalid request method'})

    try:
        product = Product.objects.get(id=product_id)
        logger.info(f"Product found: {product.name}")
        wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
        logger.info(f"Wishlist item created: {created}, ID: {wishlist_item.id}")

        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        logger.info(f"Wishlist count: {wishlist_count}")

        if created:
            logger.info("Item added to wishlist")
            return JsonResponse({
                'success': True,
                'message': 'Added to Wishlist!',
                'wishlist_count': wishlist_count
            })
        else:
            wishlist_item.delete()
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
            logger.info("Item removed from wishlist")
            return JsonResponse({
                'success': True,
                'message': 'Removed from Wishlist!',
                'wishlist_count': wishlist_count
            })
    except Product.DoesNotExist:
        logger.error(f"Product not found: {product_id}")
        return JsonResponse({'success': False, 'message': 'Product not found'})
    except Exception as e:
        logger.error(f"Error in add_to_wishlist: {str(e)}")
        return JsonResponse({'success': False, 'message': str(e)})
    
@login_required
def remove_from_wishlist(request, wishlist_id):
    if request.method == 'POST':
        try:
            wishlist_item = Wishlist.objects.get(id=wishlist_id, user=request.user)
            wishlist_item.delete()
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
            return JsonResponse({
                'success': True,
                'message': 'Removed from Wishlist!',
                'wishlist_count': wishlist_count
            })
        except Wishlist.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Item not found in wishlist'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def get_wishlist_items(request):
    items = Wishlist.objects.filter(user=request.user).values(
        'product__name',
        'product__image',  # Add this
        'product__price',  # Optional: more fields
        'product__stock'   # Optional: more fields
    )
    logger.info(f"Wishlist items for {request.user}: {list(items)}")
    return JsonResponse({'items': list(items)})

@login_required
def get_cart_count(request):
    cart_count = Cart.objects.filter(user=request.user).count()  # Adjust based on your Cart model
    return JsonResponse({'cart_count': cart_count})

@login_required
def get_wishlist_count(request):
    wishlist_count = Wishlist.objects.filter(user=request.user).count()  # Use database model
    logger.info(f"Wishlist count for {request.user}: {wishlist_count}")
    return JsonResponse({"wishlist_count": wishlist_count})

# In views.py, modify the wallet_view function
@login_required
def wallet_view(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all().select_related(
        'order'
    ).prefetch_related(
        'order__items',
        'order__items__product',
        'order__items__variant'
    ).order_by('-created_at')
    
    for transaction in transactions:
        print(f"Transaction ID: {transaction.id}")
        print(f"Type: {transaction.transaction_type}")
        print(f"Amount: {transaction.amount}")
        print(f"Order: {transaction.order_id if transaction.order else 'No Order'}")
        print(f"Description: {transaction.description}")
        
        # If it's a returned order, print more details
        if transaction.order and transaction.order.status == 'Returned':
            print("Returned Order Details:")
            for item in transaction.order.items.all():
                print(f"  - Product: {item.product.name}")
                if item.variant:
                    print(f"    Variant: {item.variant.ram}/{item.variant.storage}/{item.variant.color}")
                print(f"    Quantity: {item.quantity}")
    
    return render(request, 'wallet.html', {
        'wallet': wallet,
        'transactions': transactions,
    })

@login_required
@require_POST
def add_to_wallet(request):
    try:
        amount = Decimal(request.POST.get('amount', '0'))
        if amount <= 0:
            return JsonResponse({'success': False, 'message': 'Amount must be positive'})
        
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        wallet.add_funds(amount)
        return JsonResponse({
            'success': True,
            'new_balance': str(wallet.balance),
        })
    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'An error occurred'})

@login_required
def test_return_order(request, order_id):
    """Temporary view to test the return process"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        order.status = 'Returned'
        order.save()  # This should trigger the process_return method
        return JsonResponse({'success': True, 'message': 'Order marked as returned'})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})
    
@login_required
def process_return_request(request, order_id):
    # Your existing code to validate the return request
    
    # Update the order status
    order = Order.objects.get(id=order_id, user=request.user)
    order.status = 'Returned'
    order.save()  # This should now trigger the process_return method
    
    # Redirect or return a response
    return redirect('order_details')

@login_required
def test_return_refund(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        print(f"Testing return for order #{order_id}, current status: {order.status}")
        if order.status not in ['Delivered', 'Shipped']:
            return JsonResponse({'success': False, 'message': 'This order is not eligible for return'})
        order.status = 'Returned'
        order.save()
        return JsonResponse({'success': True, 'message': 'Order returned and refund processed successfully'})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
    
def test_order_return(self):
    # Create a user
    user = CustomUser.objects.create(email='test@example.com', username='testuser')
    
    # Create a wallet for the user
    wallet = Wallet.objects.create(user=user, balance=0.00)
    
    # Create an order
    order = Order.objects.create(
        user=user,
        total_price=100.00,
        status='Delivered',
        payment_method='Wallet'
    )
    
    # Add items to the order
    product = Product.objects.create(name='Test Product', price=50.00)
    OrderItem.objects.create(order=order, product=product, quantity=2, price=50.00)
    
    # Mark the order as returned
    order.status = 'Returned'
    order.save()
    
    # Verify that the wallet balance is updated
    wallet.refresh_from_db()
    self.assertEqual(wallet.balance, Decimal('100.00'))
    
    # Verify that the transaction history contains the refund details
    transaction = Transaction.objects.filter(order=order).first()
    self.assertIsNotNone(transaction)
    self.assertIn('Refund for returned order', transaction.description)

def add_funds(self, amount, description=None, order=None):
    """Add funds to the wallet and create a transaction."""
    if amount <= 0:
        raise ValueError("Amount must be positive")
    self.balance += Decimal(str(amount))
    self.save()
    
    # Use provided description or default
    if description is None:
        description = "Funds added to wallet"
    
    # Create transaction record
    transaction = Transaction.objects.create(
        wallet=self,
        amount=amount,
        transaction_type='CREDIT',
        description=description,
        order=order
    )
    
    return transaction

# Add this to your views.py
@login_required
def force_return_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        old_status = order.status
        order.status = 'Returned'
        order.save()
        
        # Check if transaction was created
        transaction = Transaction.objects.filter(order=order).last()
        
        if transaction:
            return JsonResponse({
                'success': True, 
                'message': f'Order status changed from {old_status} to Returned. Transaction created: {transaction.id}'
            })
        else:
            return JsonResponse({
                'success': False, 
                'message': 'Order status changed but no transaction was created'
            })
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})