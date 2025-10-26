from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .models import SpeedTest, Device, WiFiNetwork, TrafficSample
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from io import BytesIO
import math

# Renderizado de grÃ¡ficos en servidor (PNG)
try:
    import matplotlib
    matplotlib.use('Agg')  # backend sin GUI
    import matplotlib.pyplot as plt
except Exception:
    matplotlib = None
    plt = None

# Importar servicios (logica original)
from .services.network_scanner import NetworkScanner
from .services.speed_test import SpeedTester
from .services.wifi_analyzer import WiFiAnalyzer
from .services.traffic_monitor import sample_bandwidth, as_mbps


def dashboard(request):
    last_speed = SpeedTest.objects.order_by('-created_at').first()
    # Contar por fecha del último escaneo disponible para evitar ceros por huso horario
    last_device = Device.objects.order_by('-created_at').first()
    last_wifi = WiFiNetwork.objects.order_by('-created_at').first()
    if last_device:
        devices_count = Device.objects.filter(created_at__date=last_device.created_at.date()).count()
    else:
        devices_count = 0
    if last_wifi:
        wifi_count = WiFiNetwork.objects.filter(created_at__date=last_wifi.created_at.date()).count()
    else:
        wifi_count = 0
    # Valores seguros para JS (nÃºmeros, sin filtros en template)
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


def signup(request):
    if request.user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registro exitoso. Ahora puedes iniciar sesiÃ³n.')
            return redirect('/accounts/login/?next=/')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def diagnostics_info(request):
    """Página de diagnóstico: muestra salida cruda de comandos usados para escaneos."""
    import platform, subprocess, shutil
    os_name = platform.system()
    info = []

    def run(cmd):
        try:
            out = subprocess.check_output(cmd, text=True, encoding='utf-8', errors='ignore', timeout=8)
            return out.strip()
        except Exception as e:
            return f"<error> {e}"

    if os_name == 'Windows':
        info.append(('arp -a', run(['arp', '-a'])))
        info.append(('netsh wlan show networks mode=bssid', run(['netsh', 'wlan', 'show', 'networks', 'mode=bssid'])))
        info.append(('ipconfig', run(['ipconfig'])))
    elif os_name == 'Linux':
        if shutil.which('nmcli'):
            info.append(('nmcli device wifi list', run(['nmcli', '-t', '-f', 'SSID,BSSID,CHAN,SIGNAL', 'device', 'wifi', 'list'])))
        info.append(('iw dev', run(['iw', 'dev'])))
        info.append(('iwlist scan', run(['iwlist', 'scan'])))
        info.append(('ip addr', run(['ip', 'addr'])))
    elif os_name == 'Darwin':
        info.append(('airport -s', run(['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-s'])))
        info.append(('ifconfig', run(['ifconfig'])))

    return render(request, 'diagnostics/diagnostics.html', {
        'os_name': os_name,
        'info': info,
    })



def speed_chart_image(request):
    """PNG con evolución (últimos 20) + resumen de promedios/medianas.
    Si matplotlib no está disponible, devuelve un PNG mínimo.
    """
    last_tests = list(SpeedTest.objects.order_by("-created_at")[:20])
    last_tests.reverse()

    if not last_tests:
        if not plt:
            pixel = BytesIO()
            pixel.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT\x08\x99c```\xf8\xff\x9f\x01\x00\x06\x05\x02\x15\x9d\x82\x8b\x0d\x00\x00\x00\x00IEND\xaeB`\x82")
            return HttpResponse(pixel.getvalue(), content_type="image/png")
        buf = BytesIO()
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", fontsize=12)
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        buf.seek(0)
        return HttpResponse(buf.getvalue(), content_type="image/png")

    xs = list(range(1, len(last_tests) + 1))
    dls = [float(getattr(s, "download_mbps", 0) or 0) for s in last_tests]
    uls = [float(getattr(s, "upload_mbps", 0) or 0) for s in last_tests]
    pings = [float(getattr(s, "ping_ms", 0) or 0) for s in last_tests]

    if not plt:
        pixel = BytesIO()
        pixel.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT\x08\x99c```\xf8\xff\x9f\x01\x00\x06\x05\x02\x15\x9d\x82\x8b\x0d\x00\x00\x00\x00IEND\xaeB`\x82")
        return HttpResponse(pixel.getvalue(), content_type="image/png")

    import statistics as stats
    def smean(v):
        try:
            return stats.mean(v)
        except Exception:
            return 0.0
    def smedian(v):
        try:
            return stats.median(v)
        except Exception:
            return 0.0

    dl_mean, dl_med = smean(dls), smedian(dls)
    ul_mean, ul_med = smean(uls), smedian(uls)
    pg_mean, pg_med = smean(pings), smedian(pings)

    from matplotlib.gridspec import GridSpec
    buf = BytesIO()
    fig = plt.figure(figsize=(9, 4))
    gs = GridSpec(1, 2, width_ratios=[3, 2])
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(xs, dls, "-o", color="#0d6efd", label="Descarga (Mbps)")
    ax.plot(xs, uls, "-o", color="#198754", label="Subida (Mbps)")
    ax.set_xlabel("Muestras recientes")
    ax.set_ylabel("Mbps")
    ax.set_title(f"Evolución últimos {len(xs)} Speed Tests")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower right")

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axis("off")
    start = last_tests[0].created_at
    end = last_tests[-1].created_at
    lines = [
        f"Rango: {start:%d/%m %H:%M} → {end:%d/%m %H:%M}",
        f"N = {len(xs)}",
        f"Bajada: media {dl_mean:.2f} | mediana {dl_med:.2f}",
        f"Subida: media {ul_mean:.2f} | mediana {ul_med:.2f}",
        f"Ping:   media {pg_mean:.2f} | mediana {pg_med:.2f}",
    ]
    ax2.text(0.02, 0.98, "\n".join(lines), va="top", ha="left", fontsize=11)

    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")
