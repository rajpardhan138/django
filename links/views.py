from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.contrib.auth import login, logout
from .middlewares import auth, guest
from django.views.decorators.csrf import csrf_exempt
import random, string, logging, pdb
from .models import ShortLink, ClickStats
import user_agents
import geoip2.database
from django.http import JsonResponse
from django.conf import settings
from time import sleep
import qrcode
from io import BytesIO
from django.contrib import messages
# Create your views here.

logger = logging.getLogger(__name__)

def design(request):
    return render(request, 'pages/auth/login.html')

@guest
def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request,user)
            return redirect('dashboard')
    else:
        initial_data = {'username':'', 'password1':'','password2':""}
        form = UserCreationForm(initial=initial_data)
    return render(request, 'pages/auth/register.html',{'form':form})

@guest
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request,user)
            return redirect('dashboard')
    else:
        initial_data = {'username':'', 'password':''}
        form = AuthenticationForm(initial=initial_data)
    return render(request, 'pages/auth/login.html',{'form':form}) 

@auth
def dashboard_view(request):
    user_links = ShortLink.objects.filter(user=request.user).order_by('-id')
    base_url = settings.BASE_URL
    # logger.debug(f'User Links: {user_links}')

    return render(request, 'pages/dashboard.html', {'user_links': user_links , 'base_url': base_url})

def logout_view(request):
    logout(request)
    return redirect('login')

def generate_short_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

@csrf_exempt
@auth
def create_link(request):
    try:
        if request.method == 'POST':
            short_code = request.POST.get('short_code')
            name = request.POST.get('name')
            ios_url = request.POST.get('ios_url')
            android_url = request.POST.get('android_url')
            i_pad_url = request.POST.get('i_pad_url')
            non_google_huawei_url = request.POST.get('non_google_huawei_url')
            fallback_url = request.POST.get('fallback_url')
            customize_url = request.POST.get('customize_url')

            # Check if short_code already exists
            existing_link = ShortLink.objects.filter(short_code=short_code).first()

            if existing_link:
                # If exists, update the existing record
                existing_link.name = name
                existing_link.ios_url = ios_url
                existing_link.android_url = android_url
                existing_link.i_pad_url = i_pad_url
                existing_link.non_google_huawei_url = non_google_huawei_url
                existing_link.fallback_url = fallback_url
                existing_link.customize_url = customize_url
                existing_link.save()
            else:
                # If doesn't exist, create a new record
                ShortLink.objects.create(
                    name=name,
                    ios_url=ios_url,
                    android_url=android_url,
                    i_pad_url=i_pad_url,
                    non_google_huawei_url=non_google_huawei_url,
                    fallback_url=fallback_url,
                    customize_url=customize_url,
                    short_code=short_code,
                    user=request.user
                )
            messages.success(request, 'Link Updated successfully.', extra_tags='success')
        else:
            short_code = generate_short_code()
            while ShortLink.objects.filter(short_code=short_code).exists():
                short_code = generate_short_code()

            ShortLink.objects.create(
                name= "",
                ios_url= "",
                android_url= "",
                i_pad_url= "",
                non_google_huawei_url= "",
                fallback_url= "",
                customize_url= "",
                short_code= short_code,
                user=request.user
            )
            messages.success(request, 'Link created successfully. Please customize the link.', extra_tags='success')
            
    except Exception as e:
        messages.error(request, 'An error occurred while creating the link.', extra_tags='danger')
    return redirect('dashboard')


def redirect_view(request, short_code):   
    try:
        # Fetch the short link
        short_link = ShortLink.objects.get(short_code=short_code)

        # Increment the click count
        short_link.click_count += 1
        short_link.save()
        
        # Parse user agent for device information
        user_agent = user_agents.parse(request.META['HTTP_USER_AGENT'])

        device_type = "Mobile" if user_agent.is_mobile else "Tablet" if user_agent.is_tablet else "Desktop"
        os_family = user_agent.os.family
        browser = user_agent.browser.family
        
        # Get referrer URL
        referrer = request.META.get('HTTP_REFERER', None)
        
        # Extract UTM parameters
        utm_source = request.GET.get('utm_source', None)
        utm_medium = request.GET.get('utm_medium', None)
        utm_campaign = request.GET.get('utm_campaign', None)
        
        # Determine user's country (requires GeoIP database)
        country = "Unknown"
        try:
            with geoip2.database.Reader('GeoLite2-City.mmdb') as reader:
                ip = get_client_ip(request)
                response = reader.city(ip)
                country = response.country.name
        except Exception as e:
            print(f"GeoIP error: {e}")
        
        # Log the click stats
        ClickStats.objects.create(
            short_link=short_link,
            device_type=device_type,
            os_family=os_family,
            browser=browser,
            referrer=referrer,
            country=country,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
        )
        
        # Redirect to the appropriate URL
        if user_agent.is_mobile:
            if user_agent.is_ios:
                return HttpResponseRedirect(short_link.ios_url or short_link.fallback_url)
            elif user_agent.is_android:
                return HttpResponseRedirect(short_link.android_url or short_link.fallback_url)
            else:
                return HttpResponseRedirect(short_link.fallback_url)  # Other mobile devices
        elif user_agent.is_tablet:
            return HttpResponseRedirect(short_link.fallback_url)  # Treat tablets as fallback
        elif user_agent.is_pc:
            return HttpResponseRedirect(short_link.fallback_url)  # Handle desktop devices
        else:
            return HttpResponseRedirect(short_link.fallback_url)  # Handle unknown devices

    except ShortLink.DoesNotExist:
        return JsonResponse({'error': 'Short link not found'}, status=404)

def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def detect_device(request):
    # Ensure `request.user_agent` comes from django-user-agents
    user_agent = user_agents.parse(request.META['HTTP_USER_AGENT'])

    device_info = {}

    if user_agent.is_mobile:
        if user_agent.is_ios:
            device_info = {'device': 'iOS'}
        elif user_agent.is_android:
            device_info = {'device': 'Android'}
        else:
            device_info = {'device': 'Other mobile'}
    elif user_agent.is_tablet:
        device_info = {'device': 'Tablet'}
    elif user_agent.is_pc:
        device_info = {'device': 'Desktop'}
    else:
        device_info = {'device': 'Unknown'}

    return JsonResponse(device_info)

# View to fetch the link data (called by AJAX)
@auth
def get_links_data(request, short_code):
    try:
        # Fetch the link data from the ShortLink model
        link_data = ShortLink.objects.get(user=request.user, short_code=short_code)
        
        # Prepare the data to return
        data = {
            'name': link_data.name,
            'customize_url': link_data.customize_url,
            'short_code': link_data.short_code,
            'ios_url': link_data.ios_url,
            'android_url': link_data.android_url,
            'i_pad_url': link_data.i_pad_url,
            'non_google_huawei_url': link_data.non_google_huawei_url,
            'fallback_url': link_data.fallback_url,
            'click_count': link_data.click_count,
        }
        
        # Return data as JSON response
        return JsonResponse({'link': data})
    except ShortLink.DoesNotExist:
        return JsonResponse({'error': 'Link not found'}, status=404)

# View to download the QR code dynamically (in PNG, PNG Small, or SVG format)
@auth
def download_qr(request, short_code, format):
    try:
        # Fetch the link data using the short code
        link_data = get_object_or_404(ShortLink, user=request.user, short_code=short_code)
        
        # Create the URL for the QR code (it will redirect to the short link)
        qr_url = f"{request.scheme}://{request.get_host()}/{link_data.short_code}"
        
        # Get the size parameter (small, medium, or large)
        size = request.GET.get('size', 'medium')  # Default to medium if no size is specified

        # Set the box_size and border based on the size parameter
        if size == 'small':
            box_size = 5
            border = 2
        elif size == 'large':
            box_size = 15
            border = 6
        else:
            box_size = 10
            border = 4  # Default to medium size

        # Generate the QR code image
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=box_size, border=border)
        qr.add_data(qr_url)
        qr.make(fit=True)

        # Handle the format (either 'svg' or 'png')
        if format == 'svg':
            # Generate SVG output
            svg_response = HttpResponse(content_type='image/svg+xml')
            img = qr.make_image(fill='black', back_color='white').convert('RGB')
            img.save(svg_response, 'SVG')
            
            # Set the Content-Disposition header to download
            svg_response['Content-Disposition'] = f'attachment; filename="{short_code}.svg"'
            return svg_response
        
        elif format == 'png':
            # Return PNG image
            png_response = HttpResponse(content_type='image/png')
            img = qr.make_image(fill='black', back_color='white')
            img.save(png_response, 'PNG')
            
            # Set the Content-Disposition header to download
            png_response['Content-Disposition'] = f'attachment; filename="{short_code}.png"'
            return png_response
        
        else:
            return JsonResponse({'error': 'Invalid format requested'}, status=400)
    
    except ShortLink.DoesNotExist:
        return JsonResponse({'error': 'Link not found'}, status=404)
@auth   
def generate_qr(request, short_code):
    try:
        # Fetch the link data using the short code
        link_data = ShortLink.objects.get(user=request.user, short_code=short_code)
        
        # Create the URL for the QR code (it will redirect to the short link)
        qr_url = f"{request.scheme}://{request.get_host()}/{link_data.short_code}"

        # Generate the QR code image
        qr_image = qrcode.make(qr_url)
        
        # Save the image to a BytesIO object
        qr_io = BytesIO()
        qr_image.save(qr_io, format='PNG')
        qr_io.seek(0)

        # Encode the image as a base64 string
        import base64
        qr_base64 = base64.b64encode(qr_io.read()).decode('utf-8')
        
        # Return the QR code as a base64 string
        return JsonResponse({'qr_code': f"data:image/png;base64,{qr_base64}"})

    except ShortLink.DoesNotExist:
        return JsonResponse({'error': 'Link not found'}, status=404)
    
@auth
def delete_link(request, short_code):
    try:
        # Fetch the link data using the short code
        link_data = ShortLink.objects.get(user=request.user, short_code=short_code)
        
        # Delete the link
        link_data.delete()
        
        # Add success message
        messages.success(request, 'Link deleted successfully.', extra_tags='success')
        
    except ShortLink.DoesNotExist:
        # Add error message if link not found
        messages.error(request, 'Link not found.', extra_tags='danger')
    
    # Redirect to dashboard
    return redirect('dashboard')
    
