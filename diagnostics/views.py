from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .models import SpeedTest, Device, WiFiNetwork, TrafficSample

# Importar servicios (logica original)
from .services.network_scanner import NetworkScanner
from .services.speed_test import SpeedTester
from .services.wifi_analyzer import WiFiAnalyzer
from .services.traffic_monitor import sample_bandwidth, as_mbps


def dashboard(request):
    last_speed = SpeedTest.objects.order_by('-created_at').first()
    devices_count = Device.objects.filter(created_at__date=timezone.now().date()).count()
    wifi_count = WiFiNetwork.objects.filter(created_at__date=timezone.now().date()).count()
    # Valores seguros para JS (números, sin filtros en template)
    speed_dl = float(getattr(last_speed, 'download_mbps', 0) or 0)
    speed_ul = float(getattr(last_speed, 'upload_mbps', 0) or 0)
    speed_ping = float(getattr(last_speed, 'ping_ms', 0) or 0)
    return render(request, 'diagnostics/dashboard.html', {
        'last_speed': last_speed,
        'devices_count': devices_count,
        'wifi_count': wifi_count,
        'speed_dl': speed_dl,
        'speed_ul': speed_ul,
        'speed_ping': speed_ping,
    })


def speedtest_view(request):
    # Ejecutar prueba con tolerancia a entornos sin red (evitar 500/403)
    try:
        tester = SpeedTester()
        tester.run_test()
        obj = SpeedTest.objects.create(
            download_mbps=getattr(tester, 'download_speed', 0) or 0,
            upload_mbps=getattr(tester, 'upload_speed', 0) or 0,
            ping_ms=getattr(tester, 'ping', 0) or 0,
        )
        ctx = {'speed': obj}
    except Exception as e:
        obj = SpeedTest.objects.create(download_mbps=0, upload_mbps=0, ping_ms=0)
        ctx = {'speed': obj, 'error': str(e)}
    return render(request, 'diagnostics/speedtest.html', ctx)


def devices_view(request):
    scanner = NetworkScanner()
    devices = scanner.get_connected_devices()
    # Limpiar capturas de hoy para no acumular
    Device.objects.filter(created_at__date=timezone.now().date()).delete()
    Device.objects.bulk_create([
        Device(ip=d.get('ip', ''), mac=d.get('mac', ''), hostname=d.get('hostname', ''))
        for d in devices
    ])
    return render(request, 'diagnostics/devices.html', {'devices': devices})


def wifi_view(request):
    analyzer = WiFiAnalyzer()
    nets = analyzer.get_available_networks()
    # Limpiar capturas de hoy para no acumular
    WiFiNetwork.objects.filter(created_at__date=timezone.now().date()).delete()
    WiFiNetwork.objects.bulk_create([
        WiFiNetwork(
            ssid=n.get('ssid', ''), bssid=n.get('bssid', ''),
            signal=int(n.get('signal', 0)), channel=int(n.get('channel', 0)),
            security=n.get('security', ''),
        ) for n in nets
    ])
    return render(request, 'diagnostics/wifi.html', {'networks': nets})


def traffic_view(request):
    # Tomar una muestra corta (2s)
    raw = sample_bandwidth(duration_sec=2.0)
    samples_list = as_mbps(raw)
    # Guardar top 10 si hay datos
    if samples_list:
        # Limpiar capturas de hoy para no acumular
        TrafficSample.objects.filter(created_at__date=timezone.now().date()).delete()
        objs = [
            TrafficSample(
                ip=s.get('ip', ''),
                download_mbps=float(s.get('download_mbps', 0.0)),
                upload_mbps=float(s.get('upload_mbps', 0.0)),
            ) for s in samples_list[:10]
        ]
        if objs:
            TrafficSample.objects.bulk_create(objs)
    return render(request, 'diagnostics/traffic.html', {'samples': samples_list})


def report_view(request):
    last_tests = SpeedTest.objects.order_by('-created_at')[:10]
    last_traffic = TrafficSample.objects.order_by('-created_at')[:10]
    return render(request, 'diagnostics/report.html', {
        'last_tests': last_tests,
        'last_traffic': last_traffic,
    })


def report_csv(request):
    import csv
    from io import StringIO
    buff = StringIO()
    writer = csv.writer(buff)
    writer.writerow(['created_at', 'type', 'metric1', 'metric2', 'metric3'])
    for s in SpeedTest.objects.order_by('-created_at')[:50]:
        writer.writerow([s.created_at.isoformat(), 'speedtest', s.download_mbps, s.upload_mbps, s.ping_ms])
    for t in TrafficSample.objects.order_by('-created_at')[:50]:
        writer.writerow([t.created_at.isoformat(), 'traffic', t.ip, t.download_mbps, t.upload_mbps])
    resp = HttpResponse(buff.getvalue(), content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="reporte.csv"'
    return resp
