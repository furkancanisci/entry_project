from django.urls import path, include
from .views import (
    AddDeviceView, ShopListView, UserDetailView, UserListView, RegisterUserView, DeleteUserView, FilteredUserListView,
    AddEntryExitRecordView, login_view, shops_view, statistics_view, home_view, devices_view,
    users_view, profile_view, ShopViewSet, DeviceViewSet, EntryExitRecordViewSet,
    HourlyDataView, DailyRecordView, add_shop, update_shop, delete_shop,
    add_device, update_device, delete_device, support_view, permissions_view, update_permissions,
    IndexView, RecentRecordsView, StatisticsView, RegisterView, logout_view, records_view,
    DeviceEntryExitAPIView, APILoginView
)
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import delete_all_records

router = DefaultRouter()
router.register(r'shops', ShopViewSet, basename='shop')
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'entry-exit-records', EntryExitRecordViewSet, basename='entryexitrecord')

urlpatterns = [
    # Web arayüzü URL'leri
    path('', IndexView.as_view(), name='index'),
    path('login/', login_view, name='login'),
    path('register/', RegisterView.as_view(), name='register'),  # RegisterView sınıfını kullanıyoruz
    path('logout/', logout_view, name='logout'),
    path('delete-all-records/', delete_all_records, name='delete_all_records'),

    # Ana sayfalar
    path('home/', IndexView.as_view(), name='home'),
    path('shops/', shops_view, name='shops'),
    path('devices/', devices_view, name='devices'),
    path('statistics/', statistics_view, name='statistics'),
    path('users/', users_view, name='users'),
    path('profile/', profile_view, name='profile'),
    path('support/', support_view, name='support'),
    path('permissions/', permissions_view, name='permissions'),
    path('records/', records_view, name='records'),
    
    # Yönetim işlemleri
    path('permissions/update/<int:user_id>/', update_permissions, name='update_permissions'),
    path('shops/add/', add_shop, name='add_shop'),
    path('shops/<int:shop_id>/update/', update_shop, name='update_shop'),
    path('shops/<int:shop_id>/delete/', delete_shop, name='delete_shop'),
    path('devices/add/', add_device, name='add_device'),
    path('devices/<int:device_id>/update/', update_device, name='update_device'),
    path('devices/<int:device_id>/delete/', delete_device, name='delete_device'),
    path('api/shops/<int:user_id>/daily-data/', DailyRecordView.as_view(), name='daily_data'),
    path('api/users/<int:user_id>/shops/', ShopListView.as_view(), name='shop_list'),
    path('api/shops/<int:user_id>/recent-records/', RecentRecordsView.as_view(), name='recent_records'),
    path('api/shops/<int:user_id>/statistics/', StatisticsView.as_view(), name='statistics'),
    path('api/showusers/<int:user_id>/', UserListView.as_view(), name='user_list'),
    path('api/users/register/', RegisterUserView.as_view(), name='user_register'),
    path('api/users/<int:user_id>/', DeleteUserView.as_view(), name='user_delete'),
    path('api/usersdetail/<int:id>/', UserDetailView.as_view(), name='user_detail'),
    path('api/users/filtered/<int:user_id>/', FilteredUserListView.as_view(), name='filtered_user_list'),
    path('api/devices/add/', AddDeviceView.as_view(), name='add_device'),
    path('api/records/add/', AddEntryExitRecordView.as_view(), name='add_record'),
    path('api/entry-exit-record/', DeviceEntryExitAPIView.as_view(), name='device-records'),
]

urlpatterns += router.urls
