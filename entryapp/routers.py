from rest_framework.routers import DefaultRouter
from django.urls import path
from rest_framework.routers import DefaultRouter
from entryapp.views import (
    DeviceViewSet, ShopViewSet, EntryExitRecordViewSet,
    APILoginView, RegisterView, AddEntryExitRecordView,
    HourlyDataView, DailyRecordView, UserListView,
    FilteredUserListView, DeleteUserView
)

router = DefaultRouter()
router.register('devices', DeviceViewSet)
router.register('shops', ShopViewSet)
router.register('records', EntryExitRecordViewSet)

urlpatterns = [
    # API kimlik doğrulama
    path('login/', APILoginView.as_view(), name='api_login'),
    path('register/', RegisterView.as_view(), name='api_register'),
    
    # API veri işlemleri
    path('entry-exit-record/', AddEntryExitRecordView.as_view(), name='add-entry-exit-record'),
    path('shops/<int:user_id>/hourly-data/<int:start_hour>/<int:end_hour>/', HourlyDataView.as_view(), name='hourly_data'),
    path('daily-records/', DailyRecordView.as_view(), name='daily_records'),
    
    # API kullanıcı yönetimi
    path('users/<int:user_id>/', UserListView.as_view(), name='user_list'),
    path('users/filtered/<int:user_id>/', FilteredUserListView.as_view(), name='filtered_user_list'),
    path('users/<int:user_id>/delete/', DeleteUserView.as_view(), name='user_delete'),
] + router.urls
