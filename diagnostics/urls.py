from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('speedtest/', views.speedtest_view, name='speedtest'),
    path('devices/', views.devices_view, name='devices'),
    path('wifi/', views.wifi_view, name='wifi'),
    path('traffic/', views.traffic_view, name='traffic'),
    path('report/', views.report_view, name='report'),
    path('report.csv', views.report_csv, name='report_csv'),
    path('signup/', views.signup, name='signup'),
    path('chart/speed.png', views.speed_chart_image, name='speed_chart_image'),
    path('diagnostics/', views.diagnostics_info, name='diagnostics_info'),
]
