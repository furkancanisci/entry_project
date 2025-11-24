from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import connection
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from rest_framework import viewsets, permissions
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Shop, Device, EntryExitRecord, UserPermission, Customer, Role, UserRole, Goal, DailyEntry
from .serializers import ShopSerializer, EntryExitRecordSerializer


# Helper function to get shops that a user can access
def get_user_shops(user):
    """
    Get shops that a user can access based on the new access control logic:
    - If user is superuser, they can see all shops that belong to the customer 
      organization that their assigned shop is part of
    - Regular users can only see data related to their directly assigned shop
    """
    if not user.shop_id:
        return Shop.objects.none()  # type: ignore
    
    try:
        user_shop = Shop.objects.get(id=user.shop_id)  # type: ignore
    except Shop.DoesNotExist:  # type: ignore
        return Shop.objects.none()  # type: ignore
    except Exception as e:
        # Log any other unexpected errors
        import logging
        logging.error(f"get_user_shops error for user {user.id}: {str(e)}")
        return Shop.objects.none()  # type: ignore
    
    if user.is_superuser:
        # Superuser can see all shops belonging to the same customer organization
        # Handle case where customer_id might be None
        if user_shop.customer_id is None:
            return Shop.objects.filter(id=user.shop_id)  # type: ignore
        return Shop.objects.filter(customer_id=user_shop.customer_id)  # type: ignore
    else:
        # Regular user can only see their assigned shop
        return Shop.objects.filter(id=user.shop_id)  # type: ignore

class ShopDevicesView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)  # type: ignore
            
            # Get shops that user can access
            shops = get_user_shops(user)
            
            if not shops.exists():
                return Response({"error": "Mağaza bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
            
            # Get the first shop (or handle shop selection logic)
            shop = shops.first()
            
            # Mağazanın cihazlarını al
            devices = Device.objects.filter(shop=shop)  # type: ignore
            
            # Mağaza ve cihaz bilgilerini hazırla
            shop_data = {
                'id': shop.id,
                'name': shop.name,
                'devices': []
            }
            
            for device in devices:
                device_data = {
                    'id': device.id,
                    'name': device.name,
                    'device_id': device.device_id,
                    'last_heartbeat': device.last_heartbeat.isoformat() if device.last_heartbeat else None
                }
                shop_data['devices'].append(device_data)
            
            return Response(shop_data)
            
        except User.DoesNotExist:  # type: ignore
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Shop.DoesNotExist:  # type: ignore
            return Response({"error": "Mağaza bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from datetime import timedelta, time, datetime
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User, Shop, EntryExitRecord

class DailyRecordView(APIView):
    def get(self, request, user_id):
        try:
            # Kullanıcıyı getir
            user = User.objects.get(id=user_id)
            
            # Get shops that user can access
            shops = get_user_shops(user)
            
            if not shops.exists():
                return Response(
                    {"error": "Mağaza bulunamadı."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # SwiftUI select box'tan gönderilen shop_id varsa seçimi uygula, yoksa varsayılan olarak ilkini al
            shop_id = request.query_params.get("shop_id")
            if shop_id:
                # Check if the shop belongs to the user's accessible shops
                shop = shops.filter(id=shop_id).first()
                if not shop:
                    return Response(
                        {"error": "Belirtilen mağaza bulunamadı."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                shop = shops.first()
            
            # Sadece bugüne ait kayıtları almak için tarih aralığını belirle
            today = timezone.now().date()
            start_date = timezone.make_aware(datetime.combine(today, time.min))
            end_date = timezone.make_aware(datetime.combine(today, time.max))
        
            records = EntryExitRecord.objects.filter(  # type: ignore
                shop=shop,
                created_at__range=[start_date, end_date]
            ).order_by('-created_at')
            
            # Günlük giriş-çıkış sayılarını ve detayları gün bazında hesapla
            daily_data = {}
            for record in records:
                date_str = record.created_at.strftime('%Y-%m-%d')
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        'entry_count': 0,
                        'exit_count': 0,
                        'records': []
                    }
                if record.is_entry:
                    daily_data[date_str]['entry_count'] += 1
                else:
                    daily_data[date_str]['exit_count'] += 1
                
                daily_data[date_str]['records'].append({
                    'id': record.id,
                    'shop_id': shop.id,
                    'shop_name': shop.name,
                    'device_id': record.device.id if record.device else None,
                    'device_name': record.device.name if record.device else None,
                    'date': record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_entry': record.is_entry
                })
            
            # Günlük veriyi hazırla (sadece bugün)
            today_data = daily_data.get(today.strftime('%Y-%m-%d'), {
                'entry_count': 0,
                'exit_count': 0,
                'records': []
            })
        
            return Response({
                'date': today.strftime('%Y-%m-%d'),
                'entry_count': today_data['entry_count'],
                'exit_count': today_data['exit_count'],
                'records': today_data['records']
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:  # type: ignore
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User, Shop
# from .serializers import ShopSerializer # Shop modeliniz için bir serializer oluşturmanız GEREKİR

# Serializer örneği (models.py ile aynı dosyada veya ayrı bir serializers.py olabilir)
# from rest_framework import serializers
# from .models import Shop, Device
#
# class DeviceSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Device
#         fields = '__all__' # veya listelemek istediğiniz alanlar
#
# class ShopSerializer(serializers.ModelSerializer):
#     devices = DeviceSerializer(many=True, read_only=True) # Device listesini dahil et
#     class Meta:
#         model = Shop
#         fields = '__all__' # veya listelemek istediğiniz alanlar (id, name, devices en az)


class ShopListView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)

            # Get shops that user can access
            if user.is_superuser:
                # Superusers can see all shops in their customer organization
                shops = get_user_shops(user)
                shop_data = shops.values('id', 'name')  # type: ignore
            else:
                # Regular users can only see their assigned shop
                shops = get_user_shops(user)
                shop_data = shops.values('id', 'name')  # type: ignore

            if not shops.exists():
                return Response([], status=status.HTTP_200_OK)

            return Response(list(shop_data), status=status.HTTP_200_OK)

        except User.DoesNotExist:  # type: ignore
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class AddDeviceView(APIView):
    def post(self, request):
        try:
            # Gerekli alanları kontrol et
            if not all(key in request.data for key in ['shop_id', 'device_id', 'name']):
                return Response({"error": "Eksik alanlar var."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Mağazayı bul
            shop = Shop.objects.get(id=request.data['shop_id'])  # type: ignore
            
            # Cihazı oluştur
            device = Device.objects.create(  # type: ignore
                shop=shop,
                device_id=request.data['device_id'],
                name=request.data['name']
            )
            
            return Response({
                "message": "Cihaz başarıyla eklendi.",
                "device": {
                    "id": device.id,
                    "name": device.name,
                    "device_id": device.device_id
                }
            }, status=status.HTTP_201_CREATED)
            
        except Shop.DoesNotExist:  # type: ignore
            return Response({"error": "Mağaza bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Shop, Device, EntryExitRecord
from datetime import datetime

class AddEntryExitRecordView(APIView):
    def post(self, request):
        try:
            # Gelen veri bir liste olmalı
            records_data = request.data  # Beklenen: [{...}, {...}, ...]

            if not isinstance(records_data, list):
                return Response({"error": "Gönderilen veri bir liste olmalı."}, status=status.HTTP_400_BAD_REQUEST)

            created_records = []

            for record_data in records_data:
                # Zorunlu alanları kontrol et
                if 'shop_id' not in record_data or 'device_id' not in record_data or 'isentry' not in record_data or 'isexit' not in record_data or 'created_at' not in record_data:
                    return Response({"error": "Eksik alanlar var. Her kayıt 'shop_id', 'device_id', 'isentry', 'isexit' ve 'created_at' alanlarını içermelidir."},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Mağaza ve cihazı bul
                try:
                    shop = Shop.objects.get(id=record_data['shop_id'])  # type: ignore
                except Shop.DoesNotExist:  # type: ignore
                    return Response({"error": f"Mağaza bulunamadı: ID {record_data['shop_id']}"},
                                    status=status.HTTP_404_NOT_FOUND)

                try:
                    device = Device.objects.get(id=record_data['device_id'])  # type: ignore
                except Device.DoesNotExist:  # type: ignore
                    return Response({"error": f"Cihaz bulunamadı: ID {record_data['device_id']}"},
                                    status=status.HTTP_404_NOT_FOUND)

                # Giriş/çıkış ve tarih alanlarını işle
                is_entry = record_data['isentry']
                is_exit = record_data['isexit']
                try:
                    created_at = datetime.strptime(record_data['created_at'], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return Response({"error": f"Geçersiz tarih formatı: {record_data['created_at']}. YYYY-MM-DD HH:MM:SS formatını kullanın."},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Yeni kayıt oluştur
                record = EntryExitRecord.objects.create(  # type: ignore
                    shop=shop,
                    device=device,
                    is_entry=is_entry,
                    is_exit=is_exit,
                    created_at=created_at
                )

                created_records.append({
                    "id": record.id,
                    "shop_id": shop.id,
                    "device_id": device.id,
                    "date": record.created_at.isoformat(),
                    "is_entry": record.is_entry,
                    "is_exit": record.is_exit
                })

            return Response({
                "message": "Kayıtlar başarıyla eklendi.",
                "records": created_records
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # Eğer next parametresi varsa ve güvenli bir URL ise onu kullan
            next_url = request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts=settings.ALLOWED_HOSTS):
                return redirect(next_url)
            # Aksi takdirde varsayılan yönlendirme
            return redirect('home')
        else:
            messages.error(request, 'Geçersiz kullanıcı adı veya şifre.')
    
    return render(request, 'entryapp/login.html')


@login_required
def shops_view(request):
    user = request.user
    # Get shops that user can access
    shops = get_user_shops(user).order_by('-created_at')  # type: ignore
    return render(request, 'entryapp/shops.html', {'shops': shops})


@login_required
def statistics_view(request):
    # Get shops that user can access
    user = request.user
    shops = get_user_shops(user).order_by('-created_at')  # type: ignore
    
    return render(request, 'entryapp/statistics.html', {'shops': shops})


@login_required
def analysis_view(request):
    # Get shops that user can access
    user = request.user
    shops = get_user_shops(user).order_by('-created_at')  # type: ignore
    
    return render(request, 'entryapp/analysis.html', {
        'user_id': request.user.id,
        'shops': shops
    })


@login_required
def heatmap_view(request):
    # Get shops that user can access
    user = request.user
    shops = get_user_shops(user).order_by('-created_at')  # type: ignore
    
    return render(request, 'entryapp/heatmap.html', {'shops': shops})


@login_required
def users_roles_view(request):
    # Only superusers can access this page
    if not request.user.is_superuser:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok.')
        return redirect('home')
    
    # Get the user's shop
    if not request.user.shop_id:
        messages.error(request, 'Kullanıcının atanmış bir mağazası bulunmuyor.')
        return redirect('home')
    
    try:
        user_shop = Shop.objects.get(id=request.user.shop_id)  # type: ignore
    except Shop.DoesNotExist:  # type: ignore
        messages.error(request, 'Kullanıcının atanmış mağazası bulunamadı.')
        return redirect('home')
    
    # Get all customers and their associated shops (only for the user's customer organization)
    customers = Customer.objects.filter(id=user_shop.customer_id).order_by('name')  # type: ignore
    
    # Get all shops grouped by customer (only shops in the same customer organization)
    customer_shops = {}
    for customer in customers:
        customer_shops[customer.id] = list(Shop.objects.filter(customer_id=customer.id).order_by('name'))  # type: ignore
    
    # Get all users grouped by shop (only users in the same customer organization)
    shop_users = {}
    shops = Shop.objects.filter(customer_id=user_shop.customer_id)  # type: ignore
    for shop in shops:
        shop_users[shop.id] = list(User.objects.filter(shop_id=shop.id).order_by('username'))  # type: ignore
    
    # Get all roles from database
    roles = Role.objects.all().order_by('name')  # type: ignore
    
    # Get user roles for display
    user_roles = {}
    for shop in shops:
        for user in User.objects.filter(shop_id=shop.id):  # type: ignore
            user_roles[user.id] = list(UserRole.objects.filter(user=user).select_related('role'))  # type: ignore
    
    context = {
        'customers': list(customers),
        'customer_shops': customer_shops,
        'shop_users': shop_users,
        'roles': list(roles),
        'user_roles': user_roles
    }
    
    return render(request, 'entryapp/users_roles.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {"error": "Kullanıcı adı ve şifre gereklidir."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # Get shop name based on user's shop_id
            shop_name = None
            if user.shop_id:
                try:
                    shop = Shop.objects.get(id=user.shop_id)  # type: ignore
                    shop_name = shop.name
                except Shop.DoesNotExist:  # type: ignore
                    shop_name = None
            
            return Response({
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "joined_date": user.date_joined.strftime("%Y-%m-%d"),
                "shop_name": shop_name,
                "is_superuser": user.is_superuser,
                "is_staff": user.is_staff
            })
        else:
            return Response(
                {"error": "Geçersiz kullanıcı adı veya şifre."},
                status=status.HTTP_401_UNAUTHORIZED
            )


@method_decorator(csrf_exempt, name='dispatch')
class APILoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {"error": "Kullanıcı adı ve şifre gereklidir."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # Get shop name based on user's shop_id
            shop_name = None
            if user.shop_id:
                try:
                    shop = Shop.objects.get(id=user.shop_id)  # type: ignore
                    shop_name = shop.name
                except Shop.DoesNotExist:  # type: ignore
                    shop_name = None

            response_data = {
                'access': access_token,
                'refresh': refresh_token,
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'joined_date': user.date_joined.strftime("%Y-%m-%d"),
                'shop_name': shop_name,
                'is_superuser': user.is_superuser,
                'is_staff': user.is_staff
            }
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Geçersiz kullanıcı adı veya şifre."},
                status=status.HTTP_401_UNAUTHORIZED
            )

@login_required
def devices_view(request):
    devices = Device.objects.all()  # type: ignore
    shops = Shop.objects.all()  # type: ignore
    return render(request, 'entryapp/devices.html', {
        'devices': devices,
        'shops': shops
    })

@login_required
def users_view(request):
    return render(request, 'entryapp/users.html')

@login_required
def profile_view(request):
    if request.method == 'POST':
        # Profil güncelleme işlemi
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        
        # Şifre değişikliği
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        if current_password and new_password:
            if user.check_password(current_password):
                user.set_password(new_password)
            else:
                messages.error(request, 'Mevcut şifre yanlış.')
                return redirect('profile')
        
        user.save()
        messages.success(request, 'Profil başarıyla güncellendi.')
        return redirect('profile')
    
    return render(request, 'entryapp/profile.html')

class ShopViewSet(viewsets.ModelViewSet):
    queryset = Shop.objects.all()  # type: ignore
    serializer_class = ShopSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Shop.objects.all().order_by('-created_at')  # type: ignore
        elif user.is_author:
            return Shop.objects.filter(id=user.shop_id).order_by('-created_at')  # type: ignore
        else:
            return Shop.objects.filter(id=user.shop_id).order_by('-created_at')  # type: ignore

class EntryExitRecordViewSet(viewsets.ModelViewSet):
    queryset = EntryExitRecord.objects.all()  # type: ignore
    serializer_class = EntryExitRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EntryExitRecord.objects.all().order_by('-created_at')  # type: ignore

class HomeView(TemplateView):
    template_name = 'entryapp/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get shops with proper access control
        shops = get_user_shops(user)  # type: ignore
        context['shops'] = shops.values('id', 'name')  # type: ignore
        
        # Get devices with proper access control
        if user.is_superuser:
            context['devices'] = Device.objects.filter(shop__in=shops).values('id', 'name', 'device_id', 'shop_id')  # type: ignore
        else:
            context['devices'] = Device.objects.filter(shop_id=user.shop_id).values('id', 'name', 'device_id', 'shop_id')  # type: ignore
        
        # Get records with proper access control
        if user.is_superuser:
            records = EntryExitRecord.objects.filter(shop__in=shops).order_by('-created_at')[:10]  # type: ignore
        else:
            records = EntryExitRecord.objects.filter(shop_id=user.shop_id).order_by('-created_at')[:10]  # type: ignore
        
        # Kayıtları düzgün bir şekilde serileştir
        formatted_records = []
        for record in records:
            formatted_records.append({
                'id': record.id,
                'shop_id': record.shop.id if record.shop else None,
                'shop_name': record.shop.name if record.shop else '',
                'device_id': record.device.id if record.device else None,
                'device_name': record.device.name if record.device else '',
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_entry': record.is_entry
            })
        
        context['records'] = formatted_records
        return context

class ShopsView(TemplateView):
    template_name = 'entryapp/shops.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shops'] = Shop.objects.all().order_by('-created_at')  # type: ignore
        return context

class DevicesView(TemplateView):
    template_name = 'entryapp/devices.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['devices'] = Device.objects.all().order_by('-created_at')  # type: ignore
        context['shops'] = Shop.objects.all()  # type: ignore
        return context

class StatisticsView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            # Log user info for debugging
            import logging
            logging.info(f"StatisticsView called for user {user_id}, is_superuser: {user.is_superuser}, shop_id: {user.shop_id}")
            
            # Filter by shop for both superusers and regular users
            if user.is_superuser:
                # Superuser can see all data in their customer organization
                user_shops = get_user_shops(user)
                logging.info(f"Superuser shops count: {user_shops.count()}")
                total_devices = Device.objects.filter(shop__in=user_shops).count()  # type: ignore
                # For superusers, count users in the same customer organization
                if user_shops.exists():
                    customer_id = user_shops.first().customer_id  # type: ignore
                    if customer_id:
                        total_users = User.objects.filter(shop_id__in=user_shops.values_list('id', flat=True)).count()
                    else:
                        total_users = User.objects.filter(shop_id=user.shop_id).count() if user.shop_id else 0
                else:
                    total_users = 0
                total_shops: int = user_shops.count()  # type: ignore
                daily_entries = EntryExitRecord.objects.filter(  # type: ignore
                    shop__in=user_shops,
                    created_at__date=timezone.now().date()
                ).count()
            else:
                # Regular user can only see data for their assigned shop
                if not user.shop_id:
                    logging.info("Regular user has no shop_id")
                    return Response({
                        'total_devices': 0,
                        'total_users': 0,
                        'total_shops': 0,
                        'daily_entries': 0
                    }, status=status.HTTP_200_OK)
                
                # Check if the shop exists
                try:
                    shop = Shop.objects.get(id=user.shop_id)  # type: ignore
                    logging.info(f"Regular user shop found: {shop.name}")
                except Shop.DoesNotExist:  # type: ignore
                    logging.info("Regular user shop does not exist")
                    return Response({
                        'total_devices': 0,
                        'total_users': 0,
                        'total_shops': 0,
                        'daily_entries': 0
                    }, status=status.HTTP_200_OK)
                
                total_devices = Device.objects.filter(shop_id=user.shop_id).count()  # type: ignore
                total_users = User.objects.filter(shop_id=user.shop_id).count()
                total_shops: int = 1  # Just their assigned shop
                daily_entries = EntryExitRecord.objects.filter(  # type: ignore
                    shop_id=user.shop_id,
                    created_at__date=timezone.now().date()
                ).count()
            
            logging.info(f"Statistics response: devices={total_devices}, users={total_users}, shops={total_shops}, entries={daily_entries}")
            return Response({
                'total_devices': total_devices,
                'total_users': total_users,
                'total_shops': total_shops,
                'daily_entries': daily_entries
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:  # type: ignore
            import logging
            logging.error(f"StatisticsView error: User {user_id} not found")
            return Response({'error': 'Kullanıcı bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Log the actual error for debugging
            import logging
            logging.error(f"StatisticsView error for user {user_id}: {str(e)}", exc_info=True)
            return Response({'error': 'İstatistikler yüklenirken bir hata oluştu.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@login_required
@require_http_methods(["POST"])
def add_shop(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        
        try:
            shop = Shop.objects.create(  # type: ignore
                name=name,
                address=address,
                phone=phone,
                email=email
            )
            messages.success(request, 'Mağaza başarıyla eklendi.')
            return redirect('shops')
        except Exception as e:
            messages.error(request, f'Mağaza eklenirken bir hata oluştu: {str(e)}')
            return redirect('shops')

@login_required
@require_http_methods(["POST"])
def update_shop(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)
    if request.method == 'POST':
        try:
            shop.name = request.POST.get('name')
            shop.address = request.POST.get('address')
            shop.phone = request.POST.get('phone')
            shop.email = request.POST.get('email')
            shop.save()
            messages.success(request, 'Mağaza başarıyla güncellendi.')
            return redirect('shops')
        except Exception as e:
            messages.error(request, f'Mağaza güncellenirken bir hata oluştu: {str(e)}')
            return redirect('shops')

@login_required
@require_http_methods(["POST"])
def delete_shop(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)
    try:
        shop.delete()
        messages.success(request, 'Mağaza başarıyla silindi.')
    except Exception as e:
        messages.error(request, f'Mağaza silinirken bir hata oluştu: {str(e)}')
    return redirect('shops')

@login_required
@require_http_methods(["POST"])
def add_device(request):
    if request.method == 'POST':
        shop_id = request.POST.get('shop')
        mac_address = request.POST.get('mac_address')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            shop = Shop.objects.get(id=shop_id)  # type: ignore
            Device.objects.create(  # type: ignore
                shop=shop,
                mac_address=mac_address,
                is_active=is_active
            )
            messages.success(request, 'Cihaz başarıyla eklendi.')
        except Exception as e:
            messages.error(request, f'Cihaz eklenirken bir hata oluştu: {str(e)}')
        
        return redirect('devices')
    return redirect('devices')

@login_required
@require_http_methods(["POST"])
def update_device(request, device_id):
    if request.method == 'POST':
        try:
            device = Device.objects.get(id=device_id)  # type: ignore
            shop_id = request.POST.get('shop')
            mac_address = request.POST.get('mac_address')
            is_active = request.POST.get('is_active') == 'on'
            
            shop = Shop.objects.get(id=shop_id)  # type: ignore
            device.shop = shop
            device.mac_address = mac_address
            device.is_active = is_active
            device.save()
            
            messages.success(request, 'Cihaz başarıyla güncellendi.')
        except Exception as e:
            messages.error(request, f'Cihaz güncellenirken bir hata oluştu: {str(e)}')
        
        return redirect('devices')
    return redirect('devices')

@login_required
@require_http_methods(["POST"])
def delete_device(request, device_id):
    if request.method == 'POST':
        try:
            device = Device.objects.get(id=device_id)  # type: ignore
            device.delete()
            messages.success(request, 'Cihaz başarıyla silindi.')
        except Exception as e:
            messages.error(request, f'Cihaz silinirken bir hata oluştu: {str(e)}')
    
    return redirect('devices')

@login_required
def support_view(request):
    if request.method == 'POST':
        # Destek talebi oluşturma
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        user = request.user
        
        # Burada destek talebini veritabanına kaydedebilir veya e-posta gönderebilirsiniz
        messages.success(request, 'Destek talebiniz başarıyla gönderildi. En kısa sürede size dönüş yapacağız.')
        return redirect('support')
    
    return render(request, 'entryapp/support.html')

@login_required
def permissions_view(request):
    # Sadece admin kullanıcılar erişebilir
    if not request.user.is_staff:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok.')
        return redirect('home')
    
    users = User.objects.all().exclude(id=request.user.id)  # type: ignore
    return render(request, 'entryapp/permissions.html', {'users': users})

@login_required
@require_http_methods(["POST"])
def update_permissions(request, user_id):
    # Sadece admin kullanıcılar erişebilir
    if not request.user.is_staff:
        messages.error(request, 'Bu işlem için yetkiniz yok.')
        return redirect('home')
    
    try:
        user = User.objects.get(id=user_id)  # type: ignore
        permission, created = UserPermission.objects.get_or_create(user=user)  # type: ignore
        
        # İzinleri güncelle
        permission.can_manage_shops = request.POST.get('can_manage_shops') == 'on'
        permission.can_manage_devices = request.POST.get('can_manage_devices') == 'on'
        permission.can_view_statistics = request.POST.get('can_view_statistics') == 'on'
        permission.can_manage_users = request.POST.get('can_manage_users') == 'on'
        permission.save()
        
        messages.success(request, f'{user.username} kullanıcısının izinleri başarıyla güncellendi.')
    except Exception as e:
        messages.error(request, f'İzinler güncellenirken bir hata oluştu: {str(e)}')
    
    return redirect('permissions')

@login_required
def home_view(request):
    user = request.user
    
    # Son 24 saatteki kayıtları al with proper access control
    last_24_hours = datetime.now() - timedelta(hours=24)
    if user.is_superuser:
        user_shops = get_user_shops(user)
        records = EntryExitRecord.objects.filter(  # type: ignore
            shop__in=user_shops,
            created_at__gte=last_24_hours
        ).order_by('-created_at')
        shops = user_shops
        devices = Device.objects.filter(shop__in=user_shops)  # type: ignore
        users = User.objects.filter(shop__in=user_shops)
    else:
        # Filter by shop for regular users
        if user.shop_id:
            records = EntryExitRecord.objects.filter(  # type: ignore
                shop_id=user.shop_id,
                created_at__gte=last_24_hours
            ).order_by('-created_at')
            shops = Shop.objects.filter(id=user.shop_id)  # type: ignore
            devices = Device.objects.filter(shop_id=user.shop_id)  # type: ignore
            users = User.objects.filter(shop_id=user.shop_id)
        else:
            records = EntryExitRecord.objects.none()  # type: ignore
            shops = Shop.objects.none()  # type: ignore
            devices = Device.objects.none()  # type: ignore
            users = User.objects.none()
    
    context = {
        'records': records,
        'shops': shops,
        'devices': devices,
        'users': users
    }
    return render(request, 'entryapp/home.html', context)

from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

@method_decorator(login_required(login_url='login'), name='dispatch')
class IndexView(TemplateView):
    template_name = 'entryapp/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    

def privacy_policy_view(request):
    return render(request, 'entryapp/privacy_policy.html')


class RecentRecordsView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            # Log user info for debugging
            import logging
            logging.info(f"RecentRecordsView called for user {user_id}, is_superuser: {user.is_superuser}, shop_id: {user.shop_id}")
            
            # Get recent records based on user type
            if user.is_superuser:
                # Superuser can see all records in their customer organization
                user_shops = get_user_shops(user)
                logging.info(f"Superuser shops count: {user_shops.count()}")
                records = EntryExitRecord.objects.filter(shop__in=user_shops).order_by('-created_at')[:10]  # type: ignore
            else:
                # Regular user can only see records from their assigned shop
                if not user.shop_id:
                    logging.info("Regular user has no shop_id")
                    return Response({'records': []}, status=status.HTTP_200_OK)
                
                # Check if the shop exists
                try:
                    shop = Shop.objects.get(id=user.shop_id)  # type: ignore
                    logging.info(f"Regular user shop found: {shop.name}")
                except Shop.DoesNotExist:  # type: ignore
                    logging.info("Regular user shop does not exist")
                    return Response({'records': []}, status=status.HTTP_200_OK)
                
                records = EntryExitRecord.objects.filter(shop_id=user.shop_id).order_by('-created_at')[:10]  # type: ignore
            
            # Format records data
            records_data = []
            for record in records:
                records_data.append({
                    'date': record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'shop_name': record.shop.name if record.shop else '',
                    'device_name': record.device.name if record.device else None,
                    'is_entry': record.is_entry
                })
            
            logging.info(f"RecentRecords response count: {len(records_data)}")
            return Response({'records': records_data}, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:  # type: ignore
            import logging
            logging.error(f"RecentRecordsView error: User {user_id} not found")
            return Response({'error': 'Kullanıcı bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Log the actual error for debugging
            import logging
            logging.error(f"RecentRecordsView error for user {user_id}: {str(e)}", exc_info=True)
            return Response({'error': 'Son kayıtlar yüklenirken bir hata oluştu.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def logout_view(request):
    logout(request)
    messages.success(request, 'Başarıyla çıkış yaptınız.')
    return redirect('login')

@login_required
def records_view(request):
    user = request.user
    if user.is_superuser:
        user_shops = get_user_shops(user)
        records = EntryExitRecord.objects.filter(shop__in=user_shops).order_by('-created_at')  # type: ignore
    else:
        # Filter by shop for regular users
        if user.shop_id:
            records = EntryExitRecord.objects.filter(shop_id=user.shop_id).order_by('-created_at')  # type: ignore
        else:
            records = EntryExitRecord.objects.none()  # type: ignore
    
    return render(request, 'entryapp/records.html', {
        'records': records
    })

class DeviceEntryExitAPIView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        try:
            data = request.data
            if not isinstance(data, list):
                return Response(
                    {"error": "Data must be a list of records"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            created_records = []
            for record in data:
                # Validate required fields
                required_fields = ['shopid', 'deviceid', 'isentry', 'isexit', 'rssi', 'created_at']
                if not all(field in record for field in required_fields):
                    return Response(
                        {"error": f"Missing required fields. Required: {required_fields}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                try:
                    # Convert shopid and deviceid to integers
                    shop_id = int(record['shopid'])
                    device_id = int(record['deviceid'])

                    shop = Shop.objects.get(id=shop_id)  # type: ignore
                    device = Device.objects.get(id=device_id)  # type: ignore

                    # Parse created_at string to datetime
                    try:
                        created_at = datetime.strptime(record['created_at'], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        return Response(
                            {"error": f"Invalid datetime format for created_at. Use YYYY-MM-DD HH:MM:SS"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    entry_record = EntryExitRecord.objects.create(  # type: ignore
                        shop=shop,
                        device=device,
                        is_entry=bool(record['isentry']),
                        is_exit=bool(record['isexit']),
                        rssi=int(record['rssi']),
                        created_at=created_at
                    )
                    created_records.append(entry_record)

                except (Shop.DoesNotExist, Device.DoesNotExist) as e:  # type: ignore
                    return Response(
                        {"error": f"Shop or Device not found: {str(e)}"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                except ValueError as e:
                    return Response(
                        {"error": f"Invalid data format: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            serializer = EntryExitRecordSerializer(created_records, many=True)
            return Response({
                "message": f"{len(created_records)} records successfully added.",
                "records": serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(csrf_exempt, name='dispatch')
class GoalsAPIView(APIView):
    """
    API endpoint for retrieving user goals.
    Returns goal information including target entries, date ranges, and associated shop data.
    """

    def get(self, request, user_id):
        """Get all goals for a specific user and shop"""
        try:
            # Verify requesting user exists
            requesting_user = User.objects.get(id=user_id)
            
            # Get shop_id from query parameters (required)
            shop_id = request.query_params.get('shop_id')
            if not shop_id:
                return Response({
                    "error": "shop_id parametresi gereklidir."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                shop_id = int(shop_id)
            except (ValueError, TypeError):
                return Response({
                    "error": "Geçersiz shop_id formatı."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user can access this shop
            accessible_shops = get_user_shops(requesting_user)
            try:
                selected_shop = accessible_shops.get(id=shop_id)
            except Shop.DoesNotExist:  # type: ignore
                return Response({
                    "error": "Belirtilen mağaza bulunamadı veya bu kullanıcıya ait değil."
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get ALL goals for the selected shop (not just user's goals)
            goals = Goal.objects.filter(shop=selected_shop, deleted_by__isnull=True).order_by('-created_at')  # type: ignore
            
            # Prepare goals data
            goals_data = []
            for goal in goals:
                # Get daily entries for this goal
                daily_entries = DailyEntry.objects.filter(goal=goal).order_by('date')  # type: ignore
                
                # Calculate totals for this goal
                total_target = len(daily_entries) * goal.target_entries_per_day
                total_actual = sum(entry.actual_entries for entry in daily_entries)
                
                # Calculate completion percentage
                completion_percentage = 0
                if total_target > 0:
                    completion_percentage = round((total_actual / total_target) * 100)
                
                # Prepare chart data
                dates = [entry.date.strftime('%d-%m-%Y') for entry in daily_entries]
                actual_counts = [entry.actual_entries for entry in daily_entries]
                target_counts = [goal.target_entries_per_day] * len(daily_entries)
                
                goals_data.append({
                    'id': goal.id,
                    'user_id': goal.user.id,
                    'user_username': goal.user.username,
                    'shop_id': goal.shop.id,
                    'shop_name': goal.shop.name,
                    'target_entries_per_day': goal.target_entries_per_day,
                    'start_date': goal.start_date.strftime('%Y-%m-%d'),
                    'end_date': goal.end_date.strftime('%Y-%m-%d'),
                    'created_at': goal.created_at.isoformat(),
                    'updated_at': goal.updated_at.isoformat(),
                    'total_target': total_target,
                    'total_actual': total_actual,
                    'completion_percentage': completion_percentage,
                    'dates': dates,
                    'actual_counts': actual_counts,
                    'target_counts': target_counts
                })
            
            # Get daily entry count for today
            from django.utils import timezone
            today = timezone.now().date()
            daily_entry_count = EntryExitRecord.objects.filter(  # type: ignore
                shop=selected_shop,
                created_at__date=today,
                is_entry=True
            ).count()
            
            # Get current day's target from active goals
            current_day_target = 0
            today_goals = goals.filter(
                start_date__lte=today,
                end_date__gte=today
            )
            
            if today_goals.exists():
                # Use the target from the first active goal for today
                current_day_target = today_goals.first().target_entries_per_day
            
            return Response({
                'goals': goals_data,
                'daily_entry_count': daily_entry_count,
                'current_day_target': current_day_target,
                'selected_shop_id': selected_shop.id,
                'selected_shop_name': selected_shop.name
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:  # type: ignore
            return Response({
                "error": "Kullanıcı bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in goals API: {str(e)}", exc_info=True)
            return Response({
                "error": f"Hedefler alınırken hata oluştu: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(login_required, name='dispatch')
class GoalsView(TemplateView):
    template_name = 'entryapp/goals.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get shops that user can access
        accessible_shops = get_user_shops(user)
        
        if not accessible_shops.exists():
            messages.error(self.request, 'Erişilebilir mağaza bulunamadı.')
            context['goals'] = []
            context['accessible_shops'] = []
            context['goals_data'] = []
            context['total_target_entries'] = 0
            context['total_actual_entries'] = 0
            context['completion_percentage'] = 0
            context['daily_entry_count'] = 0
            context['current_day_target'] = 0
            return context
            
        # Get selected shop from query parameters or default to user's assigned shop
        selected_shop_id = self.request.GET.get('shop_id')
        if selected_shop_id:
            try:
                selected_shop_id = int(selected_shop_id)
                # Check if the selected shop is in the accessible shops
                if not accessible_shops.filter(id=selected_shop_id).exists():
                    selected_shop_id = user.shop_id
            except (ValueError, TypeError):
                selected_shop_id = user.shop_id
        else:
            selected_shop_id = user.shop_id
            
        try:
            selected_shop = accessible_shops.get(id=selected_shop_id)
        except Shop.DoesNotExist:  # type: ignore
            selected_shop = accessible_shops.first()
        
        # Get ALL goals for the selected shop (not just user's goals)
        goals = Goal.objects.filter(shop=selected_shop, deleted_by__isnull=True).order_by('-created_at')  # type: ignore
        
        # Initialize totals for overall statistics
        total_target_entries = 0
        total_actual_entries = 0
        
        # Prepare data for charts
        goals_data = []
        for goal in goals:
            try:
                # Get or create daily entries for this goal
                daily_entries = DailyEntry.objects.filter(goal=goal).order_by('date')  # type: ignore
                
                # If no daily entries exist, create them from actual database records
                if not daily_entries.exists():
                    from datetime import timedelta
                    current_date = goal.start_date
                    while current_date <= goal.end_date:
                        # For future dates, set actual entries to 0
                        from django.utils import timezone
                        if current_date > timezone.now().date():
                            actual_entries = 0
                        else:
                            # Count actual entries for this date from EntryExitRecord
                            actual_entries = EntryExitRecord.objects.filter(  # type: ignore
                                shop=goal.shop,
                                created_at__date=current_date,
                                is_entry=True
                            ).count()
                        
                        # Create daily entry record
                        daily_entry = DailyEntry.objects.create(  # type: ignore
                            goal=goal,
                            date=current_date,
                            actual_entries=actual_entries
                        )
                        current_date += timedelta(days=1)
                    
                    # Refresh the daily entries query
                    daily_entries = DailyEntry.objects.filter(goal=goal).order_by('date')  # type: ignore
                
                # For existing goals, update the actual entries from the database to ensure accuracy
                else:
                    updated = False
                    for daily_entry in daily_entries:
                        # For future dates, set actual entries to 0
                        from django.utils import timezone
                        if daily_entry.date > timezone.now().date():
                            actual_entries = 0
                        else:
                            # Count actual entries for this date from EntryExitRecord
                            actual_entries = EntryExitRecord.objects.filter(  # type: ignore
                                shop=goal.shop,
                                created_at__date=daily_entry.date,
                                is_entry=True
                            ).count()
                        
                        # Update the daily entry if it's different
                        if daily_entry.actual_entries != actual_entries:
                            daily_entry.actual_entries = actual_entries
                            daily_entry.save()
                            updated = True
                    
                    # Refresh the daily entries query after updates
                    if updated:
                        daily_entries = DailyEntry.objects.filter(goal=goal).order_by('date')  # type: ignore
                
                # Prepare chart data with correct date formatting
                dates = [entry.date.strftime('%d-%m-%Y') for entry in daily_entries]  # Changed to DD-MM-YYYY format
                actual_counts = [entry.actual_entries for entry in daily_entries]
                target_counts = [goal.target_entries_per_day] * len(daily_entries)
                
                # Calculate totals for this goal
                total_target = len(daily_entries) * goal.target_entries_per_day
                total_actual = sum(actual_counts)
                
                # Calculate completion percentage
                completion_percentage = 0
                if total_target > 0:
                    completion_percentage = round((total_actual / total_target) * 100)
                
                # Add to overall totals
                total_target_entries += total_target
                total_actual_entries += total_actual
                
                goals_data.append({
                    'goal': goal,
                    'dates': dates,
                    'actual_counts': actual_counts,
                    'target_counts': target_counts,
                    'total_target': total_target,
                    'total_actual': total_actual,
                    'completion_percentage': completion_percentage
                })
            except Exception as e:
                # Log the error for debugging
                import logging
                logging.error(f"Error processing goal {goal.id}: {str(e)}")
                # Continue with the next goal instead of breaking the entire loop
                continue
        
        # Calculate overall completion percentage
        completion_percentage = 0
        if total_target_entries > 0:
            completion_percentage = round((total_actual_entries / total_target_entries) * 100)
            
        # Get daily entry count for today
        from django.utils import timezone
        today = timezone.now().date()
        daily_entry_count = EntryExitRecord.objects.filter(  # type: ignore
            shop=selected_shop,
            created_at__date=today,
            is_entry=True
        ).count()
        
        # Get current day's target from active goals
        current_day_target = 0
        today_goals = goals.filter(
            start_date__lte=today,
            end_date__gte=today
        )
        
        if today_goals.exists():
            # Use the target from the first active goal for today
            current_day_target = today_goals.first().target_entries_per_day
        
        context['goals'] = goals
        context['goals_data'] = goals_data
        context['accessible_shops'] = accessible_shops
        context['selected_shop'] = selected_shop
        context['total_target_entries'] = total_target_entries
        context['total_actual_entries'] = total_actual_entries
        context['completion_percentage'] = completion_percentage
        context['daily_entry_count'] = daily_entry_count
        context['current_day_target'] = current_day_target
        return context

    def post(self, request, *args, **kwargs):
        user = request.user
        action = request.POST.get('action')
        
        # Handle goal deletion
        if action == 'delete':
            goal_id = request.POST.get('goal_id')
            if goal_id:
                try:
                    goal = Goal.objects.get(id=goal_id)  # type: ignore
                    # Check if user has permission to delete this goal
                    accessible_shops = get_user_shops(user)
                    if goal.shop in accessible_shops:
                        goal.deleted_by = user
                        goal.save()
                        messages.success(request, 'Hedef başarıyla silindi.')
                    else:
                        messages.error(request, 'Bu hedefi silme yetkiniz yok.')
                except Goal.DoesNotExist:  # type: ignore
                    messages.error(request, 'Hedef bulunamadı.')
            return redirect('goals')
        
        # Handle goal creation
        # Get form data
        target_entries = request.POST.get('target_entries')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        shop_id = request.POST.get('shop_id')
        
        if not target_entries or not start_date or not end_date:
            messages.error(request, 'Tüm alanları doldurmalısınız.')
            return redirect('goals')
        
        try:
            target_entries = int(target_entries)
        except ValueError:
            messages.error(request, 'Hedef giriş sayısı geçerli bir sayı olmalıdır.')
            return redirect('goals')
        
        # Get shops that user can access
        accessible_shops = get_user_shops(user)
        
        if not accessible_shops.exists():
            messages.error(request, 'Erişilebilir mağaza bulunamadı.')
            return redirect('goals')
        
        # Validate shop selection
        if shop_id:
            try:
                shop_id = int(shop_id)
                # Check if the selected shop is in the accessible shops
                shop = accessible_shops.get(id=shop_id)
            except (ValueError, Shop.DoesNotExist):  # type: ignore
                messages.error(request, 'Geçersiz mağaza seçimi.')
                return redirect('goals')
        else:
            # Default to user's assigned shop
            if not user.shop_id:
                messages.error(request, 'Kullanıcının atanmış bir mağazası bulunmuyor.')
                return redirect('goals')
            
            try:
                shop = accessible_shops.get(id=user.shop_id)
            except Shop.DoesNotExist:  # type: ignore
                messages.error(request, 'Kullanıcının atanmış mağazası bulunamadı.')
                return redirect('goals')
        
        # Check if there's already a goal for the same shop and date range
        from datetime import datetime
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Check for overlapping goals for ANY user (not just current user) that are not deleted
            existing_goals = Goal.objects.filter(  # type: ignore
                shop=shop,
                deleted_by__isnull=True
            ).exclude(
                start_date__gt=end_date_obj
            ).exclude(
                end_date__lt=start_date_obj
            )
            
            if existing_goals.exists():
                messages.error(request, f'{start_date} - {end_date} tarihleri arasında zaten bu mağaza için hedef var.')
                return redirect('goals')
        except ValueError:
            messages.error(request, 'Geçersiz tarih formatı.')
            return redirect('goals')
        
        # Create new goal
        goal = Goal.objects.create(  # type: ignore
            user=user,
            shop=shop,
            target_entries_per_day=target_entries,
            start_date=start_date,
            end_date=end_date
        )
        
        # Generate daily entries for the goal period
        from datetime import timedelta
        current_date = start_date_obj
        while current_date <= end_date_obj:
            # For future dates, set actual entries to 0
            from django.utils import timezone
            if current_date > timezone.now().date():
                actual_entries = 0
            else:
                # Count actual entries for this date from EntryExitRecord
                actual_entries = EntryExitRecord.objects.filter(  # type: ignore
                    shop=shop,
                    created_at__date=current_date,
                    is_entry=True
                ).count()
            
            # Create daily entry record
            DailyEntry.objects.create(  # type: ignore
                goal=goal,
                date=current_date,
                actual_entries=actual_entries
            )
            
            current_date += timedelta(days=1)
        
        messages.success(request, 'Yeni hedef başarıyla oluşturuldu.')
        return redirect('goals')



from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import EntryExitRecord


@login_required
@require_http_methods(["POST"])
def delete_all_records(request):
    try:
        if request.user.is_superuser:
            # Süper kullanıcı tüm kayıtları silebilir
            deleted_count = EntryExitRecord.objects.all().delete()[0]  # type: ignore
        else:
            # Normal kullanıcı sadece kendi customer_id'sine ait kayıtları silebilir
            if request.user.customer_id:
                deleted_count = EntryExitRecord.objects.filter(  # type: ignore
                    shop__customer_id=request.user.customer_id
                ).delete()[0]
            else:
                messages.error(request, 'Kayıtları silmek için yetkiniz bulunmuyor.')
                return redirect('profile')

        messages.success(
            request, 
            f'{deleted_count} giriş/çıkış kaydı başarıyla silindi.'
        )
    except Exception as e:
        messages.error(
            request, 
            f'Kayıtlar silinirken bir hata oluştu: {str(e)}'
        )
    
    return redirect('profile')

class MonthlyDataView(APIView):
    def get(self, request, user_id):
        try:
            # Get user
            user = User.objects.get(id=user_id)  # type: ignore
            
            # Get shop_id from query parameters
            shop_id = request.query_params.get("shop_id")
            if not shop_id:
                return Response(
                    {"error": "Hangi mağazanın verisi istendiği belirtilmedi (shop_id eksik)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Convert shop_id to integer
            try:
                shop_id = int(shop_id)
            except ValueError:
                return Response(
                    {"error": "Geçersiz shop_id formatı."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if user can access this shop
            user_shops = get_user_shops(user)
            try:
                shop = user_shops.get(id=shop_id)
            except Shop.DoesNotExist:  # type: ignore
                return Response(
                    {"error": "Belirtilen mağaza bulunamadı veya bu kullanıcıya ait değil."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Get the current date and calculate the date 12 months ago
            today = timezone.now().date()
            
            # Initialize monthly data dictionary
            monthly_data = {}
            
            # Calculate data for each month in the last 12 months (including current month)
            for i in range(12):
                # Calculate the target month and year (going backwards from current month)
                target_date = today.replace(day=1)  # Start with first day of current month
                
                # Subtract months
                if target_date.month <= i:
                    target_month = 12 - (i - target_date.month + 1)
                    target_year = target_date.year - 1
                else:
                    target_month = target_date.month - i
                    target_year = target_date.year
                
                # Create start and end dates for the month
                start_date = timezone.make_aware(datetime(target_year, target_month, 1))
                
                # Calculate end date (first day of next month)
                if target_month == 12:
                    end_date = timezone.make_aware(datetime(target_year + 1, 1, 1))
                else:
                    end_date = timezone.make_aware(datetime(target_year, target_month + 1, 1))
                
                # Get records for this month
                records = EntryExitRecord.objects.filter(  # type: ignore
                    shop=shop,
                    created_at__gte=start_date,
                    created_at__lt=end_date
                )
                
                # Count entries and exits
                entry_count = records.filter(is_entry=True).count()
                exit_count = records.filter(is_entry=False).count()
                
                # Format month name (e.g., "2024-01")
                month_key = f"{target_year}-{target_month:02d}"
                
                monthly_data[month_key] = {
                    'entry_count': entry_count,
                    'exit_count': exit_count
                }
            
            # Prepare response data
            months = list(monthly_data.keys())
            # Sort months in ascending order (oldest to newest)
            months.sort()
            entry_counts = [monthly_data[month]['entry_count'] for month in months]
            exit_counts = [monthly_data[month]['exit_count'] for month in months]
            
            return Response({
                'months': months,
                'entry_counts': entry_counts,
                'exit_counts': exit_counts
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:  # type: ignore
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HourlyDataView(APIView):
    def get(self, request, user_id, start_hour, end_hour):
        try:
            # Kullanıcıyı getir
            user = User.objects.get(id=user_id)
            
            # Saat aralığını kontrol et
            if start_hour < 0 or start_hour > 23 or end_hour < 0 or end_hour > 23 or start_hour >= end_hour:
                return Response(
                    {"error": "Geçersiz saat aralığı. Saatler 0-23 arasında olmalı ve başlangıç saati bitiş saatinden küçük olmalı."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Shop ID'sini al
            shop_id = request.query_params.get("shop_id")
            if not shop_id:
                return Response(
                    {"error": "shop_id parametresi gereklidir."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Kullanıcının erişim yetkisi olan mağazayı kontrol et
            user_shops = get_user_shops(user)
            try:
                shop = user_shops.get(id=shop_id)
            except Shop.DoesNotExist:  # type: ignore
                return Response(
                    {"error": "Belirtilen mağaza bulunamadı veya bu kullanıcıya ait değil."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Bugünün tarihini al
            local_tz = timezone.get_default_timezone()

            start_datetime = local_tz.localize(datetime.combine(today, time(start_hour, 0)))
            end_datetime = local_tz.localize(datetime.combine(today, time(end_hour, 0)))

            
            # Belirtilen saat aralığındaki kayıtları al
            records = EntryExitRecord.objects.filter(  # type: ignore
                shop=shop,
                created_at__gte=start_datetime,
                created_at__lt=end_datetime
            ).order_by('created_at')
            
            # Saatlik verileri hazırla
            hourly_data = {}
            for record in records:
                # Kaydın saatini al
                record_hour = record.created_at.hour
                
                # Saat için veri yapısını oluştur
                if record_hour not in hourly_data:
                    hourly_data[record_hour] = {
                        'entry_count': 0,
                        'exit_count': 0,
                        'records': []
                    }
                
                # Giriş/çıkış sayısını güncelle
                if record.is_entry:
                    hourly_data[record_hour]['entry_count'] += 1
                else:
                    hourly_data[record_hour]['exit_count'] += 1
                
                aware_dt = timezone.make_aware(record.created_at) if timezone.is_naive(record.created_at) else record.created_at
                local_dt = timezone.localtime(aware_dt)

                hourly_data[record_hour]['records'].append({
                    'id': record.id,
                    'device_id': record.device.id if record.device else None,
                    'device_name': record.device.name if record.device else None,
                    'date': local_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_entry': record.is_entry
                })
            
            # Yanıtı hazırla
            response_data = {
                'shop_id': shop.id,
                'shop_name': shop.name,
                'date': today.strftime('%Y-%m-%d'),
                'start_hour': start_hour,
                'end_hour': end_hour,
                'hourly_data': hourly_data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:  # type: ignore
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HourlyHeatmapView(APIView):
    def get(self, request, user_id):
        try:
            # Kullanıcıyı getir
            user = User.objects.get(id=user_id)  # type: ignore
            
            # Shop ID'sini al
            shop_id = request.query_params.get("shop_id")
            if not shop_id:
                return Response(
                    {"error": "Hangi mağazanın verisi istendiği belirtilmedi (shop_id eksik)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Convert shop_id to integer
            try:
                shop_id = int(shop_id)
            except ValueError:
                return Response(
                    {"error": "Geçersiz shop_id formatı."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if user can access this shop
            user_shops = get_user_shops(user)
            try:
                shop = user_shops.get(id=shop_id)
            except Shop.DoesNotExist:  # type: ignore
                return Response(
                    {"error": "Belirtilen mağaza bulunamadı veya bu kullanıcıya ait değil."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Get the current date
            today = timezone.now().date()
            
            # Initialize hourly data dictionary for 24 hours
            hourly_data = {}
            
            # Calculate data for each hour in the day (0-23)
            for hour in range(24):
                # Create start and end times for the hour
                start_time = timezone.make_aware(datetime.combine(today, time(hour, 0)))
                end_time = timezone.make_aware(datetime.combine(today, time(hour, 59, 59)))
                
                # Get records for this hour
                records = EntryExitRecord.objects.filter(  # type: ignore
                    shop=shop,
                    created_at__gte=start_time,
                    created_at__lte=end_time
                )
                
                # Count entries (people entering the store)
                entry_count = records.filter(is_entry=True).count()
                
                hourly_data[hour] = entry_count
            
            # Prepare response data
            hours = list(range(24))
            counts = [hourly_data[hour] for hour in hours]
            
            return Response({
                'hours': hours,
                'counts': counts
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:  # type: ignore
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class YearlyDataView(APIView):
    def get(self, request, user_id):
        try:
            # Kullanıcıyı getir
            user = User.objects.get(id=user_id)  # type: ignore
            
            # Shop ID'sini al
            shop_id = request.query_params.get("shop_id")
            if not shop_id:
                return Response(
                    {"error": "Hangi mağazanın verisi istendiği belirtilmedi (shop_id eksik)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Convert shop_id to integer
            try:
                shop_id = int(shop_id)
            except ValueError:
                return Response(
                    {"error": "Geçersiz shop_id formatı."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if user can access this shop
            user_shops = get_user_shops(user)
            try:
                shop = user_shops.get(id=shop_id)
            except Shop.DoesNotExist:  # type: ignore
                return Response(
                    {"error": "Belirtilen mağaza bulunamadı veya bu kullanıcıya ait değil."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Get the current date and calculate the date 5 years ago
            today = timezone.now().date()
            five_years_ago = today.replace(year=today.year - 4)  # 5 years including current year
            
            # Initialize yearly data dictionary
            yearly_data = {}
            
            # Calculate data for each year in the last 5 years
            for i in range(5):
                target_year = five_years_ago.year + i
                
                # Create start and end dates for the year
                start_date = timezone.make_aware(datetime(target_year, 1, 1))
                end_date = timezone.make_aware(datetime(target_year + 1, 1, 1))
                
                # Get records for this year
                records = EntryExitRecord.objects.filter(  # type: ignore
                    shop=shop,
                    created_at__gte=start_date,
                    created_at__lt=end_date
                )
                
                # Count entries and exits
                entry_count = records.filter(is_entry=True).count()
                exit_count = records.filter(is_entry=False).count()
                
                # Format year
                year_key = str(target_year)
                
                yearly_data[year_key] = {
                    'entry_count': entry_count,
                    'exit_count': exit_count
                }
            
            # Prepare response data
            years = list(yearly_data.keys())
            entry_counts = [yearly_data[year]['entry_count'] for year in years]
            exit_counts = [yearly_data[year]['exit_count'] for year in years]
            
            return Response({
                'years': years,
                'entry_counts': entry_counts,
                'exit_counts': exit_counts
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:  # type: ignore
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FilteredDataView(APIView):
    def get(self, request, user_id):
        try:
            # Get user
            user = User.objects.get(id=user_id)  # type: ignore
            
            # Get shop_id from query parameters
            shop_id = request.query_params.get("shop_id")
            if not shop_id:
                return Response(
                    {"error": "Hangi mağazanın verisi istendiği belirtilmedi (shop_id eksik)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Convert shop_id to integer
            try:
                shop_id = int(shop_id)
            except ValueError:
                return Response(
                    {"error": "Geçersiz shop_id formatı."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if user can access this shop
            user_shops = get_user_shops(user)
            try:
                shop = user_shops.get(id=shop_id)
            except Shop.DoesNotExist:  # type: ignore
                return Response(
                    {"error": "Belirtilen mağaza bulunamadı veya bu kullanıcıya ait değil."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Get date range from query parameters
            date_range = request.query_params.get("range", "monthly")  # default to monthly
            start_date_str = request.query_params.get("start_date")
            end_date_str = request.query_params.get("end_date")
            
            # Calculate date range based on the selected option
            today = timezone.now().date()
            
            if date_range == "weekly":
                # Last 7 days (including today)
                end_date = timezone.make_aware(datetime.combine(today, time.max))
                start_date = timezone.make_aware(datetime.combine(today - timedelta(days=6), time.min))
                date_format = '%Y-%m-%d'
            elif date_range == "monthly":
                # Last 30 days (including today)
                end_date = timezone.make_aware(datetime.combine(today, time.max))
                start_date = timezone.make_aware(datetime.combine(today - timedelta(days=29), time.min))
                date_format = '%Y-%m-%d'
            elif date_range == "custom" and start_date_str and end_date_str:
                # Custom date range
                try:
                    start_date = timezone.make_aware(datetime.combine(datetime.strptime(start_date_str, '%Y-%m-%d').date(), time.min))
                    end_date = timezone.make_aware(datetime.combine(datetime.strptime(end_date_str, '%Y-%m-%d').date(), time.max))
                    date_format = '%Y-%m-%d'
                except ValueError:
                    return Response(
                        {"error": "Geçersiz tarih formatı. YYYY-MM-DD formatında olmalıdır."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Default to monthly (last 30 days)
                end_date = timezone.make_aware(datetime.combine(today, time.max))
                start_date = timezone.make_aware(datetime.combine(today - timedelta(days=29), time.min))
                date_format = '%Y-%m-%d'
            
            # Get records for the specified date range
            records = EntryExitRecord.objects.filter(  # type: ignore
                shop=shop,
                created_at__gte=start_date,
                created_at__lte=end_date
            ).order_by('created_at')
            
            # Group records by date
            daily_data = {}
            for record in records:
                date_key = record.created_at.strftime(date_format)
                if date_key not in daily_data:
                    daily_data[date_key] = {
                        'entry_count': 0,
                        'exit_count': 0
                    }
                if record.is_entry:
                    daily_data[date_key]['entry_count'] += 1
                else:
                    daily_data[date_key]['exit_count'] += 1
            
            # Prepare response data
            labels = list(daily_data.keys())
            entry_counts = [daily_data[label]['entry_count'] for label in labels]
            exit_counts = [daily_data[label]['exit_count'] for label in labels]
            
            return Response({
                'labels': labels,
                'entry_counts': entry_counts,
                'exit_counts': exit_counts
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:  # type: ignore
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 != password2:
            messages.error(request, 'Şifreler eşleşmiyor!')
            return render(request, 'entryapp/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Bu kullanıcı adı zaten kullanımda!')
            return render(request, 'entryapp/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Bu e-posta zaten kullanımda!')
            return render(request, 'entryapp/register.html')
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1
            )
            messages.success(request, 'Kayıt başarılı! Şimdi giriş yapabilirsiniz.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Kayıt işlemi başarısız oldu: {str(e)}')
            return render(request, 'entryapp/register.html')
    
    return render(request, 'entryapp/register.html')

# Add these imports at the top of the file
from .models import Role, UserRole

@method_decorator(csrf_exempt, name='dispatch')
class RoleListCreateView(APIView):
    """
    API endpoint for listing and creating roles.
    Only accessible by superusers.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, user_id):
        """Get all roles in the system"""
        try:
            # Log the request for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Role list request - user_id from URL: {user_id}, authenticated user: {request.user.id if request.user.is_authenticated else 'None'}")
            
            # Verify requesting user exists and is superuser
            requesting_user = User.objects.get(id=user_id)
            logger.info(f"Requesting user: {requesting_user.username}, is_superuser: {requesting_user.is_superuser}")
            
            if not requesting_user.is_superuser:
                logger.warning(f"User {requesting_user.username} is not a superuser")
                return Response({
                    "error": "Bu işlemi yapmak için yetkiniz yok."
                }, status=status.HTTP_403_FORBIDDEN)
            
            roles = Role.objects.all()
            serializer = RoleSerializer(roles, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:  # type: ignore
            logger.error(f"User with id {user_id} does not exist")
            return Response({
                "error": "Kullanıcı bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in role listing: {str(e)}", exc_info=True)
            return Response({
                "error": f"Rol listeleme sırasında hata oluştu: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, user_id):
        """Create a new role"""
        try:
            # Log the request for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Role creation request - user_id from URL: {user_id}, authenticated user: {request.user.id if request.user.is_authenticated else 'None'}")
            
            # Verify requesting user exists and is superuser
            requesting_user = User.objects.get(id=user_id)
            logger.info(f"Requesting user: {requesting_user.username}, is_superuser: {requesting_user.is_superuser}")
            
            if not requesting_user.is_superuser:
                logger.warning(f"User {requesting_user.username} is not a superuser")
                return Response({
                    "error": "Bu işlemi yapmak için yetkiniz yok."
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = RoleSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                logger.error(f"Role creation failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:  # type: ignore
            logger.error(f"User with id {user_id} does not exist")
            return Response({
                "error": "Kullanıcı bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in role creation: {str(e)}", exc_info=True)
            return Response({
                "error": f"Rol oluşturma sırasında hata oluştu: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class RoleDetailView(APIView):
    """
    API endpoint for retrieving, updating, and deleting a specific role.
    Only accessible by superusers.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, user_id, role_id):
        """Get a specific role"""
        try:
            # Log the request for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Role detail request - user_id from URL: {user_id}, role_id from URL: {role_id}, authenticated user: {request.user.id if request.user.is_authenticated else 'None'}")
            
            # Verify requesting user exists and is superuser
            requesting_user = User.objects.get(id=user_id)
            logger.info(f"Requesting user: {requesting_user.username}, is_superuser: {requesting_user.is_superuser}")
            
            if not requesting_user.is_superuser:
                logger.warning(f"User {requesting_user.username} is not a superuser")
                return Response({
                    "error": "Bu işlemi yapmak için yetkiniz yok."
                }, status=status.HTTP_403_FORBIDDEN)
            
            role = Role.objects.get(id=role_id)
            serializer = RoleSerializer(role)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:  # type: ignore
            logger.error(f"User with id {user_id} does not exist")
            return Response({
                "error": "Kullanıcı bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Role.DoesNotExist:  # type: ignore
            logger.error(f"Role with id {role_id} does not exist")
            return Response({
                "error": "Rol bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in role retrieval: {str(e)}", exc_info=True)
            return Response({
                "error": f"Rol alırken hata oluştu: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, user_id, role_id):
        """Update a specific role"""
        try:
            # Log the request for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Role update request - user_id from URL: {user_id}, role_id from URL: {role_id}, authenticated user: {request.user.id if request.user.is_authenticated else 'None'}")
            
            # Verify requesting user exists and is superuser
            requesting_user = User.objects.get(id=user_id)
            logger.info(f"Requesting user: {requesting_user.username}, is_superuser: {requesting_user.is_superuser}")
            
            if not requesting_user.is_superuser:
                logger.warning(f"User {requesting_user.username} is not a superuser")
                return Response({
                    "error": "Bu işlemi yapmak için yetkiniz yok."
                }, status=status.HTTP_403_FORBIDDEN)
            
            role = Role.objects.get(id=role_id)
            serializer = RoleSerializer(role, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                logger.error(f"Role update failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:  # type: ignore
            logger.error(f"User with id {user_id} does not exist")
            return Response({
                "error": "Kullanıcı bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Role.DoesNotExist:  # type: ignore
            logger.error(f"Role with id {role_id} does not exist")
            return Response({
                "error": "Rol bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in role update: {str(e)}", exc_info=True)
            return Response({
                "error": f"Rol güncelleme sırasında hata oluştu: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, user_id, role_id):
        """Delete a specific role"""
        try:
            # Log the request for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Role deletion request - user_id from URL: {user_id}, role_id from URL: {role_id}, authenticated user: {request.user.id if request.user.is_authenticated else 'None'}")
            
            # Verify requesting user exists and is superuser
            requesting_user = User.objects.get(id=user_id)
            logger.info(f"Requesting user: {requesting_user.username}, is_superuser: {requesting_user.is_superuser}")
            
            if not requesting_user.is_superuser:
                logger.warning(f"User {requesting_user.username} is not a superuser")
                return Response({
                    "error": "Bu işlemi yapmak için yetkiniz yok."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get all roles
            roles = Role.objects.all().order_by('name')  # type: ignore
            role_data = []
            for role in roles:
                role_data.append({
                    "id": role.id,
                    "name": role.name,
                    "description": role.description
                })
            
            return Response(role_data, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:  # type: ignore
            return Response({
                "error": "Kullanıcı bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in role listing: {str(e)}", exc_info=True)
            return Response({
                "error": f"Roller alınırken hata oluştu: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, user_id):
        """Create a new role"""
        try:
            # Log the request for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Role creation request - user_id from URL: {user_id}, authenticated user: {request.user.id if request.user.is_authenticated else 'None'}")
            
            # Verify requesting user exists and is superuser
            requesting_user = User.objects.get(id=user_id)
            logger.info(f"Requesting user: {requesting_user.username}, is_superuser: {requesting_user.is_superuser}")
            
            if not requesting_user.is_superuser:
                logger.warning(f"User {requesting_user.username} is not a superuser")
                return Response({
                    "error": "Bu işlemi yapmak için yetkiniz yok."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Validate input data
            name = request.data.get('name', '').strip()
            description = request.data.get('description', '').strip()
            
            if not name:
                return Response({
                    "error": "Rol adı gereklidir."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if role already exists
            if Role.objects.filter(name__iexact=name).exists():  # type: ignore
                return Response({
                    "error": f"'{name}' adında bir rol zaten mevcut."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create new role
            role = Role.objects.create(  # type: ignore
                name=name,
                description=description
            )
            
            return Response({
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "message": f"'{role.name}' adlı rol başarıyla oluşturuldu."
            }, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:  # type: ignore
            return Response({
                "error": "Kullanıcı bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in role creation: {str(e)}", exc_info=True)
            return Response({
                "error": f"Rol oluşturulurken hata oluştu: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, user_id):
        """Delete a role"""
        try:
            # Log the request for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Role deletion request - user_id from URL: {user_id}, authenticated user: {request.user.id if request.user.is_authenticated else 'None'}")
            
            # Verify requesting user exists and is superuser
            requesting_user = User.objects.get(id=user_id)
            logger.info(f"Requesting user: {requesting_user.username}, is_superuser: {requesting_user.is_superuser}")
            
            if not requesting_user.is_superuser:
                logger.warning(f"User {requesting_user.username} is not a superuser")
                return Response({
                    "error": "Bu işlemi yapmak için yetkiniz yok."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Validate input data
            role_id = request.data.get('role_id')
            
            if not role_id:
                return Response({
                    "error": "Rol ID gereklidir."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Convert to integer
            try:
                role_id = int(role_id)
            except ValueError:
                return Response({
                    "error": "Geçersiz rol ID formatı."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify role exists
            try:
                role = Role.objects.get(id=role_id)  # type: ignore
            except Role.DoesNotExist:  # type: ignore
                return Response({
                    "error": "Belirtilen rol bulunamadı."
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Prevent deletion of roles that are assigned to users
            user_count = UserRole.objects.filter(role=role).count()  # type: ignore
            if user_count > 0:
                return Response({
                    "error": f"Bu rol {user_count} kullanıcıya atanmış durumda. Önce kullanıcı rollerini kaldırın."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Delete the role
            role_name = role.name
            role.delete()
            
            return Response({
                "message": f"'{role_name}' adlı rol başarıyla silindi."
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:  # type: ignore
            return Response({
                "error": "Yetkilendiren kullanıcı bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in role deletion: {str(e)}", exc_info=True)
            return Response({
                "error": f"Rol silinirken hata oluştu: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class UserRoleAssignmentView(APIView):
    """
    API endpoint for assigning roles to users.
    Only accessible by superusers.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, user_id):
        """Assign a role to a user"""
        try:
            # Log the request for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Role assignment request - user_id from URL: {user_id}, authenticated user: {request.user.id if request.user.is_authenticated else 'None'}")
            
            # Verify requesting user exists and is superuser
            requesting_user = User.objects.get(id=user_id)
            logger.info(f"Requesting user: {requesting_user.username}, is_superuser: {requesting_user.is_superuser}")
            
            if not requesting_user.is_superuser:
                logger.warning(f"User {requesting_user.username} is not a superuser")
                return Response({
                    "error": "Bu işlemi yapmak için yetkiniz yok."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Validate input data
            target_user_id = request.data.get('user_id')
            role_id = request.data.get('role_id')
            
            if not target_user_id or not role_id:
                return Response({
                    "error": "Kullanıcı ID ve rol ID gereklidir."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Convert to integers
            try:
                target_user_id = int(target_user_id)
                role_id = int(role_id)
            except ValueError:
                return Response({
                    "error": "Geçersiz kullanıcı ID veya rol ID formatı."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify target user exists
            try:
                target_user = User.objects.get(id=target_user_id)  # type: ignore
            except User.DoesNotExist:  # type: ignore
                return Response({
                    "error": "Belirtilen kullanıcı bulunamadı."
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Verify role exists
            try:
                role = Role.objects.get(id=role_id)  # type: ignore
            except Role.DoesNotExist:  # type: ignore
                return Response({
                    "error": "Belirtilen rol bulunamadı."
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user already has this role
            user_role, created = UserRole.objects.get_or_create(  # type: ignore
                user=target_user,
                role=role,
                defaults={'assigned_by': requesting_user}
            )
            
            if created:
                message = f"'{target_user.username}' kullanıcısına '{role.name}' rolü başarıyla atandı."
                status_code = status.HTTP_201_CREATED
            else:
                message = f"'{target_user.username}' kullanıcısının zaten '{role.name}' rolü var."
                status_code = status.HTTP_200_OK
            
            return Response({
                "message": message,
                "user_role": {
                    "id": user_role.id,
                    "user_id": target_user.id,
                    "username": target_user.username,
                    "role_id": role.id,
                    "role_name": role.name,
                    "assigned_at": user_role.assigned_at.isoformat() if user_role.assigned_at else None
                }
            }, status=status_code)
            
        except User.DoesNotExist:  # type: ignore
            return Response({
                "error": "Yetkilendiren kullanıcı bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in role assignment: {str(e)}", exc_info=True)
            return Response({
                "error": f"Rol ataması yapılırken hata oluştu: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, user_id):
        """Remove a role from a user"""
        try:
            # Log the request for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Role removal request - user_id from URL: {user_id}, authenticated user: {request.user.id if request.user.is_authenticated else 'None'}")
            
            # Verify requesting user exists and is superuser
            requesting_user = User.objects.get(id=user_id)
            logger.info(f"Requesting user: {requesting_user.username}, is_superuser: {requesting_user.is_superuser}")
            
            if not requesting_user.is_superuser:
                logger.warning(f"User {requesting_user.username} is not a superuser")
                return Response({
                    "error": "Bu işlemi yapmak için yetkiniz yok."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Validate input data
            target_user_id = request.data.get('user_id')
            role_id = request.data.get('role_id')
            
            if not target_user_id or not role_id:
                return Response({
                    "error": "Kullanıcı ID ve rol ID gereklidir."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Convert to integers
            try:
                target_user_id = int(target_user_id)
                role_id = int(role_id)
            except ValueError:
                return Response({
                    "error": "Geçersiz kullanıcı ID veya rol ID formatı."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify target user exists
            try:
                target_user = User.objects.get(id=target_user_id)  # type: ignore
            except User.DoesNotExist:  # type: ignore
                return Response({
                    "error": "Belirtilen kullanıcı bulunamadı."
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Verify role exists
            try:
                role = Role.objects.get(id=role_id)  # type: ignore
            except Role.DoesNotExist:  # type: ignore
                return Response({
                    "error": "Belirtilen rol bulunamadı."
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user has this role
            try:
                user_role = UserRole.objects.get(user=target_user, role=role)  # type: ignore
                user_role.delete()
                message = f"'{target_user.username}' kullanıcısından '{role.name}' rolü başarıyla kaldırıldı."
            except UserRole.DoesNotExist:  # type: ignore
                return Response({
                    "error": f"'{target_user.username}' kullanıcısının '{role.name}' rolü zaten yok."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                "message": message
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:  # type: ignore
            return Response({
                "error": "Yetkilendiren kullanıcı bulunamadı."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in role removal: {str(e)}", exc_info=True)
            return Response({
                "error": f"Rol kaldırılırken hata oluştu: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)