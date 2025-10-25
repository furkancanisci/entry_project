from django.urls import path, include
from .views import (
    AddDeviceView, ShopListView, login_view, shops_view, statistics_view, home_view, devices_view,
    users_view, profile_view, add_shop, update_shop, delete_shop,
    add_device, update_device, delete_device, support_view, permissions_view, update_permissions,
    IndexView, RecentRecordsView, StatisticsView, logout_view, records_view, privacy_policy_view,
    DeviceEntryExitAPIView, APILoginView, delete_all_records, MonthlyDataView, YearlyDataView, register_view, DailyRecordView, analysis_view, heatmap_view, HourlyHeatmapView, users_roles_view,
    RoleListCreateView, UserRoleAssignmentView, GoalsView, GoalsAPIView
)
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # Web arayüzü URL'leri
    path('', IndexView.as_view(), name='index'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('delete-all-records/', delete_all_records, name='delete_all_records'),

    # Ana sayfalar
    path('home/', IndexView.as_view(), name='home'),
    path('privacy-policy/', privacy_policy_view, name='home'),
    path('shops/', shops_view, name='shops'),
    path('devices/', devices_view, name='devices'),
    path('statistics/', statistics_view, name='statistics'),
    path('analysis/', analysis_view, name='analysis'),
    path('heatmap/', heatmap_view, name='heatmap'),
    path('goals/', GoalsView.as_view(), name='goals'),
    path('users-roles/', users_roles_view, name='users_roles'),
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
    path('api/shops/<int:user_id>/monthly-data/', MonthlyDataView.as_view(), name='monthly_data'),
    path('api/shops/<int:user_id>/yearly-data/', YearlyDataView.as_view(), name='yearly_data'),
    path('api/shops/<int:user_id>/hourly-heatmap/', HourlyHeatmapView.as_view(), name='hourly_heatmap'),
    path('api/users/<int:user_id>/shops/', ShopListView.as_view(), name='shop_list'),
    path('api/users/<int:user_id>/recent-records/', RecentRecordsView.as_view(), name='recent_records'),
    path('api/users/<int:user_id>/statistics/', StatisticsView.as_view(), name='statistics'),
    path('api/devices/add/', AddDeviceView.as_view(), name='add_device'),
    path('api/records/add/', DeviceEntryExitAPIView.as_view(), name='add_record'),
    path('api/entry-exit-record/', DeviceEntryExitAPIView.as_view(), name='device-records'),
    
    # Role management API endpoints
    path('api/users/<int:user_id>/roles/', RoleListCreateView.as_view(), name='role_list_create'),
    path('api/users/<int:user_id>/assign-role/', UserRoleAssignmentView.as_view(), name='assign_role'),
    
    # Goals API endpoint - now requires shop_id as a query parameter
    path('api/users/<int:user_id>/goals/', GoalsAPIView.as_view(), name='api_goals'),
]