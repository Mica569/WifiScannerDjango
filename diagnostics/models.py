from django.db import models

class SpeedTest(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    download_mbps = models.FloatField(default=0)
    upload_mbps = models.FloatField(default=0)
    ping_ms = models.FloatField(default=0)

class Device(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.CharField(max_length=64)
    mac = models.CharField(max_length=64, blank=True, default="")
    hostname = models.CharField(max_length=128, blank=True, default="")

class WiFiNetwork(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    ssid = models.CharField(max_length=128)
    bssid = models.CharField(max_length=64, blank=True, default="")
    signal = models.IntegerField(default=0)
    channel = models.IntegerField(default=0)
    security = models.CharField(max_length=128, blank=True, default="")

class TrafficSample(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.CharField(max_length=64)
    download_mbps = models.FloatField(default=0)
    upload_mbps = models.FloatField(default=0)
