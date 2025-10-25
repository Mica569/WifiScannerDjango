from django.contrib import admin
from .models import SpeedTest, Device, WiFiNetwork, TrafficSample

admin.site.register(SpeedTest)
admin.site.register(Device)
admin.site.register(WiFiNetwork)
admin.site.register(TrafficSample)
