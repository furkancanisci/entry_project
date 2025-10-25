from rest_framework.routers import DefaultRouter
from django.urls import path
from entryapp.views import (
    ShopViewSet, EntryExitRecordViewSet,
    APILoginView, AddEntryExitRecordView,
    DailyRecordView, MonthlyDataView, HourlyDataView, YearlyDataView
)

router = DefaultRouter()
router.register('shops', ShopViewSet)
router.register('records', EntryExitRecordViewSet)

urlpatterns = [
    # API kimlik doğrulama
    path('login/', APILoginView.as_view(), name='api_login'),
    
    # API veri işlemleri
    path('entry-exit-record/', AddEntryExitRecordView.as_view(), name='add-entry-exit-record'),
    path('daily-records/', DailyRecordView.as_view(), name='daily_records'),
    path('shops/<int:user_id>/monthly-data/', MonthlyDataView.as_view(), name='monthly_data'),
    path('shops/<int:user_id>/yearly-data/', YearlyDataView.as_view(), name='yearly_data'),
    path('shops/<int:user_id>/hourly-data/<int:start_hour>/<int:end_hour>/', HourlyDataView.as_view(), name='hourly_data'),
] + router.urls