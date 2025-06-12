from django.http import Http404
from django.shortcuts import redirect, render, get_object_or_404, reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Shop, EntryExitRecord, User, Device
from .serializers import DeviceSerializer, ShopSerializer, EntryExitRecordSerializer, RegisterSerializer
from datetime import datetime, time, timedelta
from rest_framework.generics import CreateAPIView
from .serializers import UserSerializer
from rest_framework.viewsets import ModelViewSet
from .forms import CustomUserCreationForm
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, permissions
from django.views.generic import TemplateView, CreateView
from django.views.decorators.http import require_http_methods
from django.urls import reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.views import View
from django.http import JsonResponse
from .forms import CustomUserCreationForm

import json
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class DeleteUserView(APIView):
    """
    Belirli bir kullanıcıyı silmek için
    """
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return Response({"message": "Kullanıcı başarıyla silindi."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Shop

@csrf_exempt
def shop_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            shop = Shop(
                shop_id=data['shop_id'],
                entry_count=data['entry_count'],
                exit_count=data['exit_count']
            )
            shop.save()
            return JsonResponse({"message": "Data saved successfully"}, status=201)
        except KeyError:
            return JsonResponse({"error": "Invalid data format"}, status=400)
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)



# views.py dosyanızda

from rest_framework import generics
from .serializers import UserSerializer # Kullanıcı modelinizi serialize etmek için serializer'ınız olmalı
from django.contrib.auth import get_user_model
User = get_user_model()

# api/users/<int:user_id>/ URL'si için view
# Eğer DeleteUserView'i kullanacaksanız, bu view'e bir get metodu ekleyin.
# DRF Generic View kullanmak daha standarttır:
class UserDetailView(generics.RetrieveAPIView): # Sadece detay getirme (GET) için
    queryset = User.objects.all() # Tüm kullanıcılar arasında arama yapar
    serializer_class = UserSerializer # Kullanıcı detaylarını JSON'a çevirir
    lookup_field = 'id' # URL'deki <int:user_id>'yi user modelinin 'id' alanı ile eşler

    
    
# Eğer hem get hem delete aynı View'de olacaksa (url'de name='user_delete' kaldığı için mantıklı olabilir):
# class UserRetrieveDestroyView(generics.RetrieveDestroyAPIView):
#     queryset = User.objects.all()
#     serializer_class = UserSerializer
#     lookup_field = 'id'
#     # delete metodu RetrieveDestroyAPIView içinde zaten tanımlıdır

# views.py dosyanızda kullandığınız UserSerializer'ın customer_id alanını içerdiğinden emin olun:
# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'customer_id'] # customer_id burada OLMALI

from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# User modelinizi doğru şekilde import ettiğinizden emin olun
# from django.contrib.auth import get_user_model
# User = get_user_model() # veya kendi özel User modeliniz nasıl import ediliyorsa öyle yapın

from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# User modelinizi doğru şekilde import ettiğinizden emin olun
from django.contrib.auth import get_user_model
User = get_user_model() # veya kendi özel User modeliniz nasıl import ediliyorsa öyle yapın

class UserListView(APIView):
    """
    Eğer istek yapan kullanıcı (user_id) süper kullanıcı ise tüm kullanıcıları,
    değilse kendi customer_id'sine ait kullanıcıları listelemek için.
    """
    # get metodu URL'den gelen user_id parametresini kabul ediyor
    def get(self, request, user_id):
        try:
            # 1. URL'den gelen user_id'ye sahip istek yapan kullanıcıyı bul
            try:
                requesting_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                # user_id ile eşleşen kullanıcı bulunamazsa 404 Not Found döndür
                return Response({"error": "Belirtilen kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

            # 2. İstek yapan kullanıcının süper kullanıcı olup olmadığını kontrol et
            if requesting_user.is_superuser:
                # Eğer süper kullanıcı ise, veritabanındaki TÜM kullanıcıları listele
                # Frontend'in beklediği alanları .values() içinde belirtin
                users = User.objects.all().values(
                    "id", "username", "email", "first_name", "last_name", "is_staff", "is_superuser" # Gerekli tüm alanlar
                )
                print(f"User {user_id} is superuser. Listing all users.") # Debug çıktısı

            else:
                # Eğer süper kullanıcı değilse, sadece kendi customer_id'sine ait kullanıcıları filtrele
                customer_id = requesting_user.customer_id

                # Kullanıcının ilişkili bir customer_id'si yoksa hata döndür
                if customer_id is None: # customer_id alanı User modelinizde None olabilir
                     print(f"User {user_id} is not superuser and has no customer_id.") # Debug
                     return Response(
                        {"error": "Belirtilen kullanıcının ilişkili bir customer_id bilgisi bulunamadı."},
                        status=status.HTTP_400_BAD_REQUEST, # veya 404 duruma göre
                    )

                # Aynı customer_id'ye sahip tüm kullanıcıları filtrele
                # Kendi kullanıcısını listede görmek istemiyorsanız .exclude(id=user_id) ekleyebilirsiniz.
                # Frontend'in beklediği alanları .values() içinde belirtin (Süper kullanıcı dalı ile aynı olmalı)
                users = User.objects.filter(customer_id=customer_id).values(
                    "id", "username", "email", "first_name", "last_name", "is_staff", "is_superuser" # Gerekli tüm alanlar
                )
                print(f"User {user_id} is not superuser. Listing users for customer_id: {customer_id}") # Debug çıktısı


            # 3. Elde edilen kullanıcı listesini döndür
            # QuerySet'i listeye çevirerek Response içine koy
            return Response(list(users), status=status.HTTP_200_OK)

        except Exception as e:
            # Beklenmedik diğer hatalar için 500 Internal Server Error döndür
            # Hata detayını debug için ekleyebilirsiniz
            print(f"An unexpected error occurred in UserListView for user {user_id}: {e}") # Debug çıktısı
            return Response({"error": f"Bir hata oluştu: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Shop  # Shop modeli kullanılıyor

User = get_user_model()

class FilteredUserListView(APIView):
    """
    Kullanıcının rolüne göre kullanıcıları filtreleyerek listeleme.
    """
    def get(self, request, user_id):
        try:
            requesting_user = User.objects.get(id=user_id)

            if requesting_user.is_superuser:
                users = User.objects.all().values("id", "username", "email", "first_name", "last_name", "shop_id")
                return Response(list(users), status=status.HTTP_200_OK)

            elif requesting_user.is_author:
                users = User.objects.filter(shop_id=requesting_user.shop_id).values(
                    "id", "username", "email", "first_name", "last_name", "shop_id"
                )
                return Response(list(users), status=status.HTTP_200_OK)

            else:
                return Response({"error": "Bu kullanıcı listesine erişim izniniz yok."}, status=status.HTTP_403_FORBIDDEN)

        except User.DoesNotExist:
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RegisterUserView(APIView):
    """
    Yeni bir kullanıcı eklemek için
    """
    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not email or not password:
            return Response({"error": "Tüm alanlar zorunludur."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Bu kullanıcı adı zaten mevcut."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, email=email, password=password)
        return Response({"message": "Kullanıcı başarıyla oluşturuldu.", "id": user.id}, status=status.HTTP_201_CREATED)

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from entryapp.models import User

class RegisterView(View):
    def get(self, request):
        form = CustomUserCreationForm()
        return render(request, 'register.html', {'form': form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
        return render(request, 'register.html', {'form': form})


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import InvitationCode, Shop
from .serializers import InvitationCodeSerializer
import random
import string

class CreateInvitationCodeView(APIView):
    def post(self, request):
        user = request.user

        # Kullanıcının süper kullanıcı olup olmadığını kontrol edin
        if not user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        shop_id = request.data.get('shop_id')
        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        # Rastgele bir davet kodu oluştur
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        invitation = InvitationCode.objects.create(code=code, shop=shop)
        serializer = InvitationCodeSerializer(invitation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from .models import InvitationCode

class RegisterWithInvitationCodeView(APIView):
    def post(self, request):
        # Kullanıcı bilgilerinin alınması
        username = request.data.get('username')
        email = request.data.get('email')
        password1 = request.data.get('password1')
        password2 = request.data.get('password2')
        code = request.data.get('code')

        # Şifre eşleşmesini kontrol et
        if password1 != password2:
            return Response({"error": "Passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

        # Davet kodunun doğrulanması
        try:
            invitation = InvitationCode.objects.get(code=code, is_used=False)
        except InvitationCode.DoesNotExist:
            return Response({"error": "Invalid or already used invitation code"}, status=status.HTTP_400_BAD_REQUEST)

        # Kullanıcı oluşturma işlemi
        try:
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.save()

            # SQL sorgusuyla kullanıcıya mağaza atanması
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE entryapp_user
                        SET shop_id = (
                            SELECT ei.shop_id 
                            FROM entryapp_invitationcode ei 
                            LEFT JOIN entryapp_shop es ON es.id = ei.shop_id 
                            WHERE ei.code = %s
                        )
                        WHERE id = %s
                    """, [code, user.id])
            except Exception as sql_error:
                return Response({"error": f"An error occurred while assigning shop: {str(sql_error)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Davet kodunun kullanılmış olarak işaretlenmesi
            invitation.is_used = True
            invitation.save()

            return Response({"message": "Registration successful"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"An error occurred during user creation: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('home')  # Kayıt olduktan sonra home sayfasına yönlendir
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Device.objects.all().order_by('-created_at')

class UserRegisterView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


from datetime import datetime, time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import EntryExitRecord
from .serializers import EntryExitRecordSerializer


from datetime import datetime, time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import EntryExitRecord
from .serializers import EntryExitRecordSerializer

from datetime import datetime, time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import EntryExitRecord
from .serializers import EntryExitRecordSerializer

from datetime import datetime, time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import EntryExitRecord
from .serializers import EntryExitRecordSerializer
from datetime import datetime, time
from django.utils import timezone

# Başlangıç ve bitiş zamanlarını timezone-aware hale getirin

from datetime import datetime, time
from django.utils.timezone import make_aware
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import EntryExitRecord
from .serializers import EntryExitRecordSerializer

# from .models import User, Shop, EntryExitRecord # Importlarınızı kontrol edin
# from datetime import datetime, time, timedelta # Importlarınızı kontrol edin
# from django.utils import timezone # Importlarınızı kontrol edin
# from django.utils.timezone import make_aware # Importlarınızı kontrol edin
# from rest_framework.views import APIView # Importlarınızı kontrol edin
# from rest_framework.response import Response # Importlarınızı kontrol edin
# from rest_framework import status # Importlarınızı kontrol edin

class HourlyDataView(APIView):
    def get(self, request, user_id, start_hour, end_hour):
        try:
            # Kullanıcıyı ve customer_id'sini getir
            user = User.objects.get(id=user_id)
            customer_id = user.customer_id
            if not customer_id:
                return Response(
                    {"error": "Kullanıcının customer_id bilgisi mevcut değil."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # SwiftUI'den gelen shop_id sorgu parametresini al
            shop_id = request.query_params.get("shop_id")
            if not shop_id:
                 return Response(
                    {"error": "Hangi mağazanın verisi istendiği belirtilmedi (shop_id eksik)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # shop_id query parameter'dan string gelebilir, integer'a çevirelim ve hata kontrolü yapalım
            try:
                shop_id = int(shop_id)
            except ValueError:
                 return Response(
                    {"error": "Geçersiz shop_id formatı."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Kullanıcının müşterisine ait ve ID'si eşleşen mağazayı bul
            # Bu kontrol, kullanıcının rastgele bir shop_id gönderip başka bir müşterinin mağaza verisini çekmesini engeller.
            try:
                shop = Shop.objects.get(id=shop_id, customer_id=customer_id) # <-- Burası düzeltildi! customer_id kullanılıyor.
            except Shop.DoesNotExist:
                 return Response(
                    {"error": "Belirtilen mağaza bulunamadı veya bu kullanıcıya ait değil."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Bugünün tarihini al
            today = timezone.now().date()
            
            # Saat aralığını kontrol et
            if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
                return Response({"error": "Geçersiz saat aralığı."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Saat aralığını düzenle (başlangıç saati bitiş saatinden büyükse yer değiştir)
            if start_hour > end_hour:
                start_hour, end_hour = end_hour, start_hour
            
            # Saatlik verileri al
            hourly_data = {}
            for hour in range(start_hour, end_hour + 1):
                start_time = make_aware(datetime.combine(today, time(hour=hour)))
                end_time = make_aware(datetime.combine(today, time(hour=hour, minute=59, second=59)))
                
                records = EntryExitRecord.objects.filter(
                    shop=shop, # Belirtilen mağazaya göre filtrele
                    created_at__range=[start_time, end_time]
                )
                
                entry_count = records.filter(is_entry=True).count()
                exit_count = records.filter(is_entry=False).count()
                
                hourly_data[hour] = {
                    'entry_count': entry_count,
                    'exit_count': exit_count
                }
            
            # Saatleri ve sayıları ayrı listelere ayır
            hours = list(range(start_hour, end_hour + 1))
            entry_counts = [hourly_data[hour]['entry_count'] for hour in hours]
            exit_counts = [hourly_data[hour]['exit_count'] for hour in hours]
            
            # Response'u döndür
            return Response({
                'hours': hours,
                'entry_counts': entry_counts,
                'exit_counts': exit_counts
            }, status=status.HTTP_200_OK) # Başarılı yanıt kodu ekledik
            
        except User.DoesNotExist:
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        # Shop.DoesNotExist hatası artık yukarıdaki try/except içinde ele alınıyor
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@login_required
def home(request):
    return render(request, 'entryapp/home.html')
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import connection

class ShopDevicesView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            shop = Shop.objects.get(id=user.shop_id)
            
            # Mağazanın cihazlarını al
            devices = Device.objects.filter(shop=shop)
            
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
            
        except User.DoesNotExist:
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Shop.DoesNotExist:
            return Response({"error": "Mağaza bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User, Shop, EntryExitRecord

class DailyRecordView(APIView):
    def get(self, request, user_id):
        try:
            # Kullanıcıyı getir, artık user.shop_id yerine customer_id kullanıyoruz.
            user = User.objects.get(id=user_id)
            customer_id = user.customer_id
            if not customer_id:
                return Response(
                    {"error": "Kullanıcının customer_id bilgisi mevcut değil."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Kullanıcının bağlı olduğu customer_id'ye ait tüm mağazaları getir.
            shops = Shop.objects.filter(customer_id=customer_id)
            if not shops.exists():
                return Response(
                    {"error": "Kullanıcının bağlı olduğu mağaza bulunamadı."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # SwiftUI select box'tan gönderilen shop_id varsa seçimi uygula, yoksa varsayılan olarak ilkini al.
            shop_id = request.query_params.get("shop_id")
            if shop_id:
                shop = shops.filter(id=shop_id).first()
                if not shop:
                    return Response(
                        {"error": "Belirtilen mağaza bulunamadı."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                shop = shops.first()
            
            # Son 7 günün kayıtlarını almak için tarih aralığını belirle
            end_date = timezone.now()
            start_date = end_date - timedelta(days=7)
            
            records = EntryExitRecord.objects.filter(
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
            
            # Gruplanmış tarih bilgilerini ayrı listelere aktar ve tarihler en yeni olandan eskiye doğru sıralansın
            dates = []
            entry_counts = []
            exit_counts = []
            all_records = []
            
            for date_str, data in sorted(daily_data.items(), key=lambda x: x[0], reverse=True):
                dates.append(date_str)
                entry_counts.append(data['entry_count'])
                exit_counts.append(data['exit_count'])
                all_records.extend(data['records'])
            
            return Response({
                'dates': dates,
                'entry_counts': entry_counts,
                'exit_counts': exit_counts,
                'records': all_records
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
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

            # Süper kullanıcı kontrolü
            if user.is_superuser:
                # Süper kullanıcı ise tüm mağazaları listele
                shops = Shop.objects.all().values('id', 'name')
            else:
                # Süper kullanıcı değilse customer_id kontrolü yap
                customer_id = user.customer_id
                if not customer_id:
                    return Response(
                        {"error": "Kullanıcının customer_id bilgisi mevcut değil."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                shops = Shop.objects.filter(customer_id=customer_id).values('id', 'name')

            if not shops.exists():
                return Response([], status=status.HTTP_200_OK)

            return Response(list(shops), status=status.HTTP_200_OK)

        except User.DoesNotExist:
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
            shop = Shop.objects.get(id=request.data['shop_id'])
            
            # Cihazı oluştur
            device = Device.objects.create(
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
            
        except Shop.DoesNotExist:
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
                    shop = Shop.objects.get(id=record_data['shop_id'])
                except Shop.DoesNotExist:
                    return Response({"error": f"Mağaza bulunamadı: ID {record_data['shop_id']}"},
                                    status=status.HTTP_404_NOT_FOUND)

                try:
                    device = Device.objects.get(id=record_data['device_id'])
                except Device.DoesNotExist:
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
                record = EntryExitRecord.objects.create(
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
            if next_url and is_safe_url(next_url, allowed_hosts=settings.ALLOWED_HOSTS):
                return redirect(next_url)
            # Aksi takdirde varsayılan yönlendirme
            return redirect('home')
        else:
            messages.error(request, 'Geçersiz kullanıcı adı veya şifre.')
    
    return render(request, 'entryapp/login.html')


@login_required
def shops_view(request):
    user = request.user
    if user.is_superuser:
        shops = Shop.objects.all().order_by('-created_at')
    else:
        shops = Shop.objects.filter(customer_id=user.customer_id).order_by('-created_at')
    return render(request, 'entryapp/shops.html', {'shops': shops})

@login_required
def statistics_view(request):
    return render(request, 'entryapp/statistics.html')

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
            return Response({
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "joined_date": user.date_joined.strftime("%Y-%m-%d"),
                "shop_name": user.shop.name if user.shop else None,
                "is_superuser": user.is_superuser,
                "is_staff": user.is_staff
            })
        else:
            return Response(
                {"error": "Geçersiz kullanıcı adı veya şifre."},
                status=status.HTTP_401_UNAUTHORIZED
            )

@login_required
def devices_view(request):
    devices = Device.objects.all()
    shops = Shop.objects.all()
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
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Shop.objects.all().order_by('-created_at')
        elif user.is_author:
            return Shop.objects.filter(id=user.shop_id).order_by('-created_at')
        else:
            return Shop.objects.filter(id=user.shop_id).order_by('-created_at')

class EntryExitRecordViewSet(viewsets.ModelViewSet):
    queryset = EntryExitRecord.objects.all()
    serializer_class = EntryExitRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EntryExitRecord.objects.all().order_by('-created_at')

class HomeView(TemplateView):
    template_name = 'entryapp/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shops'] = Shop.objects.all().values('id', 'name')
        context['devices'] = Device.objects.all().values('id', 'name', 'device_id', 'shop_id')
        records = EntryExitRecord.objects.all().order_by('-created_at')[:10]
        
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
        context['shops'] = Shop.objects.all().order_by('-created_at')
        return context

class DevicesView(TemplateView):
    template_name = 'entryapp/devices.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['devices'] = Device.objects.all().order_by('-created_at')
        context['shops'] = Shop.objects.all()
        return context

class StatisticsView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            # Toplam cihaz sayısı
            total_devices = Device.objects.count()
            
            # Toplam kullanıcı sayısı
            total_users = User.objects.count()
            
            # Toplam mağaza sayısı
            total_shops = Shop.objects.count()
            
            # Günlük giriş-çıkış sayısı
            today = timezone.now().date()
            daily_entries = EntryExitRecord.objects.filter(
                created_at__date=today
            ).count()
            
            return Response({
                'total_devices': total_devices,
                'total_users': total_users,
                'total_shops': total_shops,
                'daily_entries': daily_entries
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'error': 'Kullanıcı bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@login_required
@require_http_methods(["POST"])
def add_shop(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        
        try:
            shop = Shop.objects.create(
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
            shop = Shop.objects.get(id=shop_id)
            Device.objects.create(
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
            device = Device.objects.get(id=device_id)
            shop_id = request.POST.get('shop')
            mac_address = request.POST.get('mac_address')
            is_active = request.POST.get('is_active') == 'on'
            
            shop = Shop.objects.get(id=shop_id)
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
            device = Device.objects.get(id=device_id)
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
    
    users = User.objects.all().exclude(id=request.user.id)
    return render(request, 'entryapp/permissions.html', {'users': users})

@login_required
@require_http_methods(["POST"])
def update_permissions(request, user_id):
    # Sadece admin kullanıcılar erişebilir
    if not request.user.is_staff:
        messages.error(request, 'Bu işlem için yetkiniz yok.')
        return redirect('home')
    
    try:
        user = User.objects.get(id=user_id)
        permission, created = UserPermission.objects.get_or_create(user=user)
        
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
    # Son 24 saatteki kayıtları al
    last_24_hours = datetime.now() - timedelta(hours=24)
    records = EntryExitRecord.objects.filter(created_at__gte=last_24_hours).order_by('-created_at')
    
    # Mağaza ve cihaz sayılarını al
    shops = Shop.objects.all()
    devices = Device.objects.all()
    users = User.objects.all()
    
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

class RecentRecordsView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if not user.customer_id:
                return Response({'records': []}, status=status.HTTP_200_OK)
                
            shop = Shop.objects.get(customer_id=user.customer_id)           
            if user.is_superuser:
                records = EntryExitRecord.objects.all().order_by('-created_at')[:10]
            else:
                records = EntryExitRecord.objects.filter(shop__customer_id=user.customer_id).order_by('-created_at')[:10]
            
            records_data = []
            for record in records:
                records_data.append({
                    'date': record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'shop_name': record.shop.name,
                    'device_name': record.device.name if record.device else None,
                    'is_entry': record.is_entry
                })
            
            return Response({'records': records_data}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'Kullanıcı bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)
        except Shop.DoesNotExist:
            return Response({'error': 'Mağaza bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def logout_view(request):
    logout(request)
    messages.success(request, 'Başarıyla çıkış yaptınız.')
    return redirect('login')

@login_required
def records_view(request):
    records = EntryExitRecord.objects.all().order_by('-created_at')
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
                try:
                    shop = Shop.objects.get(id=record['shopid'])
                    device = Device.objects.get(id=record['deviceid'])
                    
               
                    
                    entry_record = EntryExitRecord.objects.create(
                        shop=shop,
                        device=device,
                        is_entry=record.get('isentry', False),
                        is_exit=record.get('isexit', False),
                        created_at=record.get('created_at')
                    )
                    created_records.append(entry_record)
                except Shop.DoesNotExist:
                    return Response(
                        {"error": f"Shop with id {record['shopid']} does not exist"},
                        status=status.HTTP_404_NOT_FOUND
                    )
              

            serializer = EntryExitRecordSerializer(created_records, many=True)
            return Response({
                "message": f"{len(created_records)} kayıt başarıyla eklendi.",
                "records": serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Shop  # Shop modelini import et

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

            shop_name = None
            if hasattr(user, 'shop') and user.shop:
                shop_name = user.shop.name

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