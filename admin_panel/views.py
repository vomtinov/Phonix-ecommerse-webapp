from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
import logging
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from authentication.models import Category,Product,Brand,Variant,ProductImage,Order,Offer
from .forms import ProductForm,VariantForm,VariantImageFormSet,OfferForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.http import JsonResponse  # Add this import
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.db import transaction
from django.views.decorators.cache import never_cache
from django.utils import timezone

User = get_user_model()  # Get the custom user model
 
#this view for admin login
def admin_login(request):
    if request.method == "POST":
        email = request.POST.get("email")  
        password = request.POST.get("password")
        
        if not email or not password:
            messages.error(request, "Email and password are required")
            return render(request, "admin_login.html")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Invalid user")
            return render(request, "admin_login.html")

        if user.is_superuser and not user.is_staff:
            messages.error(request, "Invalid user")
            return render(request, "admin_login.html")

        user = authenticate(request, username=email, password=password)  

        if user is None:
            messages.error(request, "Invalid email or password")  
            return render(request, "admin_login.html")

        if not user.is_staff:
            messages.error(request, "You do not have admin access")
            return render(request, "admin_login.html")

        login(request, user)
        return redirect("admin_panel")

    return render(request, "admin_login.html")

#this view for admin panel
def admin_panel(request):
    if not request.user.is_staff:
        return redirect("admin_login")
    return render(request, "admin_panel.html")

#this view for admin dashboard
def dashboard_view(request):
    return render(request, "dashboard.html")

#this view for displaying all users 
def users_view(request):
    if not request.user.is_staff:
        return redirect("admin_login")

    search_query = request.GET.get("search", "")
    clear = request.GET.get("clear", "no")
    if clear == "yes" or not search_query:
        search_query = ""

    users = User.objects.filter(username__icontains=search_query, is_staff=False).order_by("-id")

    paginator = Paginator(users, 5)  
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "users.html", {"users": page_obj})

#this view for blocking the user
def block_user(request, user_id):
    if not request.user.is_staff:
        return redirect("admin_login")

    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    
    messages.success(request, f"{user.username} has been blocked successfully!")
    return redirect("users")

#this view for un-blocking the user
def unblock_user(request, user_id):
    if not request.user.is_staff:
        return redirect("admin_login")

    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()

    messages.success(request, f"{user.username} has been unblocked successfully!")
    return redirect("users")         

#this view for category list
def category_list(request):
    if not request.user.is_staff:
        return redirect("admin_login")

    search_query = request.GET.get("search", "")
    clear = request.GET.get("clear", "no")  

    if clear == "yes" or not search_query:
        search_query = ""

    categories = Category.objects.filter(name__icontains=search_query, is_deleted=False).order_by("-created_at" )

    paginator = Paginator(categories, 5)  
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "category.html", {"categories": page_obj, "request": request})

#this view for add-category list
def add_category(request):
    if not request.user.is_staff:
        return redirect("admin_login")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        status = request.POST.get("status", "1") 

        if not name or not description:
            messages.error(request, "All fields are required!")
            return redirect("add_category")

        status_value = True if status == "1" else False

        if Category.objects.filter(name=name, is_deleted=False).exists():
            messages.error(request, "Category name already exists and is not deleted!")
            return redirect("add_category")

        try:
            Category.objects.create(name=name, description=description, status=status_value, is_deleted=False)
            messages.success(request, "Category added successfully!")
            return redirect("category_list")  
        except Exception as e:
            messages.error(request, f"An error occurred while adding the category: {str(e)}")
            return redirect("add_category")

    return render(request, "add_category.html")

#this view for edit-category list
def edit_category(request, category_id):
    if not request.user.is_staff:
        return redirect("admin_login")

    category = get_object_or_404(Category, id=category_id, is_deleted=False)
    
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        status = 'status' in request.POST  

        if not name or not description:
            messages.error(request, "All fields are required!")
            return render(request, "edit_category.html", {"category": category})

        if Category.objects.filter(name=name, is_deleted=False).exclude(id=category_id).exists():
            messages.error(request, "Category name already exists!")
            return render(request, "edit_category.html", {"category": category})

        category.name = name
        category.description = description
        category.status = status
        category.save()

        messages.success(request, "Category updated successfully!")
        return redirect("category_list")

    return render(request, "edit_category.html", {"category": category})

#this view for delete-category list
def delete_category(request, category_id):
    if not request.user.is_staff:
        return redirect("admin_login")

    category = get_object_or_404(Category, id=category_id)
    confirm = request.GET.get('confirm', 'no')  

    if confirm == 'yes':
        category.is_deleted = True
        category.save()
        messages.success(request, "Category soft-deleted successfully!")
        return redirect("category_list")
    else:
        
        return render(request, "confirm_action.html", {
            "category": category,
            "action": "delete",
            "object_type": "Category",
            "return_url": "category_list",
            "next_url": f"/delete_category/{category_id}/?confirm=yes"
        })

#this view for brand list
def brand_list(request):
    brands = Brand.objects.all().order_by('-id')  
    return render(request, 'brand_list.html', {'brands': brands})

#this view for add brand list
def add_brand(request):
    if request.method == "POST":
        name = request.POST.get('name')
        description = request.POST.get('description')
        status = request.POST.get('status') == '1'  

        Brand.objects.create(name=name, description=description, status=status)
        return redirect('brand_list')

    return render(request, 'add_brand.html')


#this view for edit-brand list
def edit_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    if request.method == "POST":
        brand.name = request.POST.get('name')
        brand.description = request.POST.get('description')
        new_status = request.POST.get('status') == '1'
        old_status = brand.status
        
        if not new_status:
            Product.objects.filter(brand=brand).update(status=False)
        elif new_status and not old_status:
            Product.objects.filter(brand=brand).update(status=True)
            
        brand.status = new_status
        brand.save()
        return redirect('brand_list')
    return render(request, 'edit_brand.html', {'brand': brand})


#this view for product list
def product_list(request):
    products = Product.objects.filter(is_deleted=False).prefetch_related('variants__images')
    print(f"Products found: {products.count()}")
    for product in products:
        for variant in product.variants.all():
            for image in variant.images.all():
                print(f"Product List - Image URL: {image.image.url}")
    return render(request, 'product_list.html', {'products': products})

def add_product(request):
    categories = Category.objects.all()
    brands = Brand.objects.all()
    if request.method == "POST":
        print("POST data:", request.POST)
        print("FILES:", request.FILES)
        # Product form
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            # Extract variant data from arrays
            rams = request.POST.getlist('ram[]')
            storages = request.POST.getlist('storage[]')
            colors = request.POST.getlist('color[]')
            prices = request.POST.getlist('price[]')
            stocks = request.POST.getlist('stock[]')
            if not rams:
                product.delete()
                messages.error(request, "At least one variant is required.")
                return render(request, 'add_product.html', {
                    'form': form,
                    'categories': categories,
                    'brands': brands,
                })
            # Process each variant
            for i in range(len(rams)):
                variant_data = {
                    'ram': rams[i],
                    'storage': storages[i],
                    'color': colors[i],
                    'price': prices[i],
                    'stock': stocks[i],
                }
                variant_form = VariantForm(variant_data)
                if variant_form.is_valid():
                    variant = variant_form.save(commit=False)
                    variant.product = product
                    variant.save()
                    # Handle images for this variant
                    image_files = request.FILES.getlist(f'variant_images_{i+1}[]')
                    if len(image_files) < 3 or len(image_files) > 6:
                        variant.delete()
                        product.delete()
                        messages.error(request, f"Variant {i+1} must have between 3 and 6 images.")
                        return render(request, 'add_product.html', {
                            'form': form,
                            'categories': categories,
                            'brands': brands,
                        })
                    for image_file in image_files:
                        ProductImage.objects.create(
                            variant=variant,
                            image=image_file
                        )
                else:
                    print("Variant form errors:", variant_form.errors)
                    product.delete()
                    messages.error(request, f"Errors in Variant {i+1}: {variant_form.errors}")
                    return render(request, 'add_product.html', {
                        'form': form,
                        'categories': categories,
                        'brands': brands,
                    })
            messages.success(request, "Product and variants added successfully!")
            return redirect('product_list')
        else:
            print("Product form errors:", form.errors)
            messages.error(request, "Please correct the errors in the product details.")
    else:
        form = ProductForm()
    context = {
        'form': form,
        'categories': categories,
        'brands': brands,
    }
    return render(request, 'add_product.html', context)

#this view for edit-product list
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_deleted=False)
    categories = Category.objects.all()
    brands = Brand.objects.all()
    variants = product.variants.all()

    if request.method == "POST":
        product.name = request.POST.get("name")
        product.description = request.POST.get("description")
        product.category_id = request.POST.get("category")
        product.brand_id = request.POST.get("brand")
        product.save()
        print(f"Save called for Product: {product.name}")

        rams = request.POST.getlist('ram[]')
        storages = request.POST.getlist('storage[]')
        colors = request.POST.getlist('color[]')
        prices = request.POST.getlist('price[]')
        stocks = request.POST.getlist('stock[]')
        variant_ids = request.POST.getlist('variant_id[]')

        # Debug all FILES keys
        print(f"FILES received: {request.FILES.keys()}")

        for i in range(len(rams)):
            variant_data = {
                'ram': rams[i],
                'storage': storages[i],
                'color': colors[i],
                'price': prices[i],
                'stock': stocks[i],
            }
            if i < len(variant_ids) and variant_ids[i]:  # Existing variant
                variant = Variant.objects.get(id=variant_ids[i], product=product)
                for key, value in variant_data.items():
                    setattr(variant, key, value)
                variant.save()
                # Handle images for existing variant
                image_files = request.FILES.getlist(f'variant_images_{i+1}[]')
                print(f"Variant {variant.id} (existing) - Expected key: 'variant_images_{i+1}[]', Found {len(image_files)} files")
                for image_file in image_files:
                    img = ProductImage(variant=variant, image=image_file)
                    img.save()
                    print(f"New image saved for existing variant: {img.image.url}")
            else:  # New variant
                variant = Variant(product=product, **variant_data)
                variant.save()
                image_files = request.FILES.getlist(f'variant_images_{i+1}[]')
                print(f"Variant {variant.id} (new) - Expected key: 'variant_images_{i+1}[]', Found {len(image_files)} files")
                for image_file in image_files:
                    img = ProductImage(variant=variant, image=image_file)
                    img.save()
                    print(f"New image saved for new variant: {img.image.url}")

        removed_images = request.POST.get("removed_images", "").split(",")
        for image_id in removed_images:
            if image_id.isdigit():
                ProductImage.objects.filter(id=int(image_id)).delete()

        messages.success(request, "Product updated successfully!")
        return redirect('product_list')

    print(f"Variants found: {variants.count()}")
    for variant in variants:
        print(f"Variant {variant.id} has {variant.images.count()} images")
        for image in variant.images.all():
            print(f"Edit Product - Image URL: {image.image.url}")

    context = {
        'product': product,
        'categories': categories,
        'brands': brands,
        'variants': variants,
    }
    return render(request, 'edit_product.html', context)

#this view for add-varient list
@csrf_exempt
def add_variant(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = VariantForm(request.POST,request.FILES)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product
            variant.save()
            return JsonResponse({"success": True, "message": "Variant added successfully!"})
    
        else:
            print("Form errors:", form.errors)
            return JsonResponse({"success": False, "error": form.errors})
    
    return render(request, 'add_variant.html', {'product': product})

logger = logging.getLogger(__name__)

#this view for delete-product list
@require_POST
def delete_product(request, product_id):
    try:
        # Log the incoming request details
        logger.info(f"Delete product request received for product {product_id}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request body: {request.body}")

        # Fetch the product
        product = get_object_or_404(Product, id=product_id)
        
        # Soft delete
        product.is_deleted = True
        product.status = False
        product.save()
        
        logger.info(f"Product {product_id} soft deleted")
        return JsonResponse({
            "success": True, 
            "message": f"Product '{product.name}' deleted successfully!"
        })
    
    except Exception as e:
        logger.error(f"Error in delete_product: {str(e)}")
        return JsonResponse({
            "success": False, 
            "error": str(e)
        }, status=500)
    
import json

#this view for toggle-status list
@require_POST
def toggle_product_status(request, product_id):
    try:
        # Log the incoming request details
        logger.info(f"Toggle status request received for product {product_id}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request body: {request.body}")
        
        # Try to parse the request body
        try:
            data = json.loads(request.body)
            logger.info(f"Parsed data: {data}")
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from request body")
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

        # Fetch the product
        product = get_object_or_404(Product, id=product_id)
        
        # Toggle status
        product.status = not product.status
        product.save()
        
        logger.info(f"Product {product_id} status updated to {product.status}")
        return JsonResponse({
            "success": True, 
            "status": product.status
        })
    
    except Exception as e:
        logger.error(f"Error in toggle_product_status: {str(e)}")
        return JsonResponse({
            "success": False, 
            "error": str(e)
        }, status=500)

@never_cache
def order_list(request):
    orders_queryset = Order.objects.all().order_by('-created_at')
    raw_statuses = Order.objects.values('id', 'status')
    print(f"Raw DB statuses at {timezone.now()}: {list(raw_statuses)}")
    
    # Add pagination - 5 orders per page
    paginator = Paginator(orders_queryset, 5)
    page = request.GET.get('page', 1)
    
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        orders = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        orders = paginator.page(paginator.num_pages)
    
    print(f"Orders fetched at {timezone.now()}: {[(order.id, order.status) for order in orders]}")
    return render(request, 'order.html', {'orders': orders})

@csrf_exempt  # Remove if using CSRF token
def update_order_status(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})
    
    order_id = request.POST.get("order_id")
    status = request.POST.get("status")
    print(f"Received update request - Order {order_id} to {status}")
    
    try:
        order = Order.objects.get(id=order_id)
        old_status = order.status
        print(f"Before update - Order {order_id}: {old_status}")
        if old_status != status:
            order.status = status  # Same as shell
            if status == "Cancelled" and old_status in ["Pending", "Confirmed", "Shipped"]:
                for item in order.items.all():
                    product = item.product
                    print(f"Incrementing stock - Product {product.id}: {product.stock} + {item.quantity}")
                    product.stock += item.quantity
                    product.quantity = product.stock
                    product.save()
            order.save()  # Same as shell
            # Verify immediately
            updated_order = Order.objects.get(id=order_id)
            print(f"After save - Order {order_id}: {updated_order.status}")           
            if updated_order.status != status:
                print(f"WARNING: Status mismatch - Expected {status}, Got {updated_order.status}")
        return JsonResponse({"success": True, "status": updated_order.status})
    except Order.DoesNotExist:
        return JsonResponse({"success": False, "error": "Order not found"})
    except Exception as e:
        print(f"Error updating order {order_id}: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)})

# views.py (admin side)
@login_required
@csrf_protect
@require_POST
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
        
        # Update order status
        order.status = "Returned"
        order.save()
        
        # Return inventory to stock
        for item in order.items.all():
            product = item.product
            print(f"Incrementing stock - Product {product.id}: {product.stock} + {item.quantity}")
            product.stock += item.quantity
            product.quantity = product.stock  # Sync quantity with stock
            product.save()
        
        updated_order = Order.objects.get(id=order_id)
        print(f"Return approved - Order {order_id} now: {updated_order.status}")
        
        return JsonResponse({
            "success": True, 
            "message": "Return approved", 
            "status": updated_order.status
        })
    except Order.DoesNotExist:
        return JsonResponse({"success": False, "message": "Order not found"})
    except Exception as e:
        print(f"Error approving return for order {order_id}: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)})
    
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order_fulldetail.html', {'order': order})

# views.py (admin side)
def get_product_quantities(request):
    # Fetch stock from Variant model, linked to non-deleted Products
    variants = Variant.objects.filter(product__is_deleted=False).values('product__id', 'stock')
    # Aggregate stock by product ID (e.g., sum stock across all variants)
    stocks = {}
    for variant in variants:
        product_id = str(variant['product__id'])
        stock = variant['stock']
        if product_id in stocks:
            stocks[product_id] += stock  # Sum stock if multiple variants
        else:
            stocks[product_id] = stock
    print(f"Stocks fetched: {stocks}")
    return JsonResponse({'stocks': stocks})  # Ensure key is 'stocks' to match JS

@staff_member_required
def offer_management(request):
    """
    Manage offers with filtering by type (Category or Product)
    """
    offer_type = request.GET.get('type', 'CATEGORY')
    
    # Validate offer type
    if offer_type not in ['CATEGORY', 'PRODUCT']:
        offer_type = 'CATEGORY'
    
    # Filter offers based on type
    if offer_type == 'CATEGORY':
        offers = Offer.objects.filter(scope='CATEGORY').select_related('category')
    else:
        offers = Offer.objects.filter(scope='PRODUCT').select_related('product')
    
    context = {
        'offers': offers,
        'offer_type': offer_type
    }
    return render(request, 'offer.html', context)

    @staff_member_required
    def add_offer(request):
        """
        Add a new offer (Category or Product)
        """
        if request.method == 'POST':
            form = OfferForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('offer_management')
        else:
            form = OfferForm()
        
        return render(request, 'add_offer.html', {'form': form})

@staff_member_required
def edit_offer(request, offer_id):
    """
    Edit an existing offer
    """
    offer = get_object_or_404(Offer, id=offer_id)
    
    if request.method == 'POST':
        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            return redirect('offer_management')
    else:
        form = OfferForm(instance=offer)
    
    return render(request, 'edit_offer.html', {'form': form})

@staff_member_required
@require_http_methods(["POST"])
def delete_offer(request, offer_id):
    """
    Delete an offer
    """
    try:
        with transaction.atomic():
            offer = get_object_or_404(Offer, id=offer_id)
            offer.delete()
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Offer deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=400)
    
def add_offer(request):
    """
    View to handle adding a new offer.
    Displays the form on GET request and processes it on POST request.
    """
    # Fetch categories and products for the form dropdowns
    categories = Category.objects.all()
    products = Product.objects.all()

    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            try:
                # Save the offer
                offer = form.save()
                messages.success(request, f"Offer '{offer.name}' created successfully!")
                return redirect('offer_management')  # Redirect to offer list page
            except Exception as e:
                messages.error(request, f"Error creating offer: {str(e)}")
        else:
            # If form is invalid, display errors
            messages.error(request, "Please correct the errors below.")
    else:
        # For GET request, initialize an empty form
        form = OfferForm()

    # Context for template
    context = {
        'form': form,
        'categories': categories,
        'products': products,
    }
    return render(request, 'add_offer.html', context)
    
#this view for admin-logout
def admin_logout(request):
    logout(request)
    return redirect("admin_login")
