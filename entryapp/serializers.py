from rest_framework import serializers
from .models import Shop, Device, EntryExitRecord, User, InvitationCode
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class DeviceSerializer(serializers.ModelSerializer):
    shop_name = serializers.ReadOnlyField()
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Device
        fields = ['id', 'name', 'device_id', 'shop', 'shop_name', 'is_active', 'last_heartbeat', 'created_at', 'updated_at']

from rest_framework import serializers
from .models import InvitationCode, Shop



from rest_framework import serializers
from .models import Shop, Device

class ShopSerializer(serializers.ModelSerializer):
    device_count = serializers.ReadOnlyField()
    active_device_count = serializers.ReadOnlyField()

    class Meta:
        model = Shop
        fields = ['id', 'name', 'address', 'phone', 'email', 'device_count', 'active_device_count', 'created_at', 'updated_at']


class InvitationCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvitationCode
        fields = ['code', 'shop', 'is_used', 'created_at']

from rest_framework import serializers
from .models import EntryExitRecord

class EntryExitRecordSerializer(serializers.ModelSerializer):
    shop_name = serializers.ReadOnlyField()
    device_name = serializers.ReadOnlyField()

    class Meta:
        model = EntryExitRecord
        fields = ['id', 'shop', 'device', 'shop_name', 'device_name', 'is_entry', 'created_at']


from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()
# Eğer User modelinizde customer_id doğrudan alan olarak tanımlı değilse,
# bir SerializerMethodField kullanarak customer_id'yi hesaplayıp eklemeniz gerekebilir.
# customer_id'nin User modelinizde doğrudan bir alan olduğunu varsayıyoruz.

class UserSerializer(serializers.ModelSerializer):
    # customer_id alanını fields listesine ekliyoruz
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'email', 'is_author', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'customer_id'] # <-- customer_id EKLENDİ ve diğer faydalı alanlar da eklendi (frontend'de kullanılanlar)
        extra_kwargs = {'password': {'write_only': True}}

    # create metodu yeni kullanıcı oluşturmak için (register endpoint'inde kullanılabilir)
    def create(self, validated_data):
        # Eğer customer_id create sırasında validated_data'da geliyorsa, onu ayrıca alıp kullanıcıya atamanız gerekebilir.
        # create_user genellikle password gibi alanları işler. Customer_id özel bir alan olabilir.
        # Eğer RegisterUserView customer_id'yi validated_data'ya koyuyorsa ve User modeliniz create_user ile set ediyorsa sorun olmaz.
        # Ancak emin olmak için customer_id'nin nasıl işlendiğini RegisterUserView'de kontrol edebilirsiniz.
        
        # Eğer create_user customer_id'yi doğrudan almıyorsa, custom bir create metodu gerekebilir:
        # customer_id = validated_data.pop('customer_id', None) # validated_data'dan customer_id'yi çıkar
        # user = User.objects.create_user(**validated_data) # Kullanıcıyı diğer alanlarla oluştur
        # if customer_id is not None:
        #     user.customer_id = customer_id # customer_id'yi kullanıcıya ata
        #     user.save() # Kullanıcıyı kaydet
        # return user
        
        # Varsayılan create_user'ın customer_id'yi işleyebildiğini varsayarak:
        user = User.objects.create_user(**validated_data)
        return user

    # Eğer custom_id User modelinde doğrudan alan değilse, bu metodu ekleyin:
    # customer_id = serializers.SerializerMethodField()
    #
    # def get_customer_id(self, obj):
    #     # obj, serialize edilen User instance'ıdır
    #     # obj.customer veya başka bir ilişki üzerinden customer_id'ye erişme mantığı buraya gelecek
    #     # Örneğin: return obj.customer.id if obj.customer else None
    #     # Eğer customer_id doğrudan alan ise buna gerek yok
    #     return obj.customer_id # customer_id'nin doğrudan alan olduğunu varsayıyoruz

from django.db import connection
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Ek Bilgiler: Token içine dahil
        token['user_id'] = user.id
        token['username'] = user.username
        token['email'] = user.email
        token['joined_date'] = user.date_joined.strftime('%Y-%m-%d')  # Kullanıcının sisteme katılım tarihi
        token['shop_name'] = cls.get_shop_name(user.id)  # Mağaza adı sorgudan

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Yanıt İçine Ek Bilgiler
        data['user_id'] = self.user.id
        data['username'] = self.user.username
        data['email'] = self.user.email
        data['joined_date'] = self.user.date_joined.strftime('%Y-%m-%d')
        data['shop_name'] = self.get_shop_name(self.user.id)

        return data

    @staticmethod
    def get_shop_name(user_id):
        """SQL Sorgusuyla Mağaza Adını Getir"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT es."name"
                FROM entryapp_user eu
                LEFT JOIN entryapp_shop es ON es.id = eu.shop_id
                WHERE eu.id = %s
            """, [user_id])

            result = cursor.fetchone()
            return result[0] if result else None


from rest_framework import serializers
from django.contrib.auth.models import User

class RegisterSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def validate(self, data):
        # Şifre eşleşmesini kontrol et
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({"password": "Şifreler eşleşmiyor."})

        return data

    def create(self, validated_data):
        # Şifreleri temizle
        password = validated_data.pop('password1')
        validated_data.pop('password2')

        # Yeni kullanıcı oluştur
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email']
        )
        user.set_password(password)
        user.save()
        return user

