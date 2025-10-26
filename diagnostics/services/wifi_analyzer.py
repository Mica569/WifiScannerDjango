import subprocess
import platform
import shutil
import unicodedata
from typing import List, Dict


def _normalize_text(s: str) -> str:
    try:
        s = unicodedata.normalize('NFKD', s)
        s = ''.join(c for c in s if not unicodedata.combining(c))
    except Exception:
        pass
    return s.lower()


class WiFiAnalyzer:
    """Analiza redes WiFi disponibles con soporte para Windows/Linux/macOS.
    Maneja salidas en distintos idiomas y utilidades alternativas.
    """

    def __init__(self):
        self.os_type = platform.system()

    def get_available_networks(self) -> List[Dict]:
        networks: List[Dict] = []
        try:
            if self.os_type == "Windows":
                networks = self._scan_windows_wifi()
            elif self.os_type == "Linux":
                networks = self._scan_linux_wifi()
            elif self.os_type == "Darwin":  # macOS
                networks = self._scan_macos_wifi()
        except Exception as e:
            print(f"WiFi scan error: {e}")
        return networks

    # --- Windows ---------------------------------------------------------
    def _scan_windows_wifi(self) -> List[Dict]:
        networks: List[Dict] = []
        try:
            result = subprocess.check_output(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                text=True, encoding="utf-8", errors="ignore"
            )

            current_ssid = None
            current_bssid = None
            current_channel = None
            current_signal = None

            for raw in result.split('\n'):
                line = raw.strip()
                low = _normalize_text(line)

                if low.startswith("ssid"):
                    if current_ssid and current_bssid and current_channel is not None and current_signal is not None:
                        networks.append({
                            "ssid": current_ssid,
                            "bssid": current_bssid,
                            "channel": current_channel,
                            "signal": current_signal,
                        })
                    current_ssid = line.split(':', 1)[-1].strip()
                    current_bssid = None
                    current_channel = None
                    current_signal = None

                elif low.startswith("bssid"):
                    if current_bssid and current_channel is not None and current_signal is not None:
                        networks.append({
                            "ssid": current_ssid,
                            "bssid": current_bssid,
                            "channel": current_channel,
                            "signal": current_signal,
                        })
                    current_bssid = line.split(':', 1)[-1].strip()

                elif low.startswith("channel") or low.startswith("canal"):
                    try:
                        current_channel = int(line.split(':', 1)[-1].strip())
                    except Exception:
                        current_channel = None

                elif low.startswith("signal") or low.startswith("senal"):
                    try:
                        val = line.split(':', 1)[-1].strip().replace('%', '')
                        current_signal = int(val)
                    except Exception:
                        current_signal = None

            if current_ssid and current_bssid and current_channel is not None and current_signal is not None:
                networks.append({
                    "ssid": current_ssid,
                    "bssid": current_bssid,
                    "channel": current_channel,
                    "signal": current_signal,
                })

        except Exception as e:
            print(f"Windows WiFi scan error: {e}")
        return networks

    # --- Linux -----------------------------------------------------------
    def _scan_linux_wifi(self) -> List[Dict]:
        networks: List[Dict] = []

        # Try nmcli (no suele requerir root y es estable)
        if shutil.which("nmcli"):
            try:
                out = subprocess.check_output(
                    ["nmcli", "-t", "-f", "SSID,BSSID,CHAN,SIGNAL", "device", "wifi", "list"],
                    text=True, encoding="utf-8", errors="ignore"
                )
                for row in out.split('\n'):
                    if not row.strip():
                        continue
                    parts = row.split(':')
                    if len(parts) >= 4:
                        ssid, bssid, chan, signal = parts[:4]
                        try:
                            networks.append({
                                "ssid": ssid,
                                "bssid": bssid,
                                "channel": int(chan or 0),
                                "signal": int(signal or 0),
                            })
                        except Exception:
                            pass
                if networks:
                    return networks
            except Exception:
                pass

        # Fallback a iwlist (puede requerir privilegios)
        def parse_iwlist(txt: str) -> List[Dict]:
            nets: List[Dict] = []
            cur: Dict = {}
            for ln in txt.split('\n'):
                ln = ln.strip()
                if "Cell" in ln and "Address" in ln:
                    if cur:
                        nets.append(cur)
                    cur = {"bssid": ln.split('Address:')[-1].strip()}
                elif "ESSID:" in ln:
                    cur["ssid"] = ln.split('ESSID:')[-1].strip().strip('"')
                elif "Channel:" in ln:
                    try:
                        cur["channel"] = int(ln.split('Channel:')[-1].strip())
                    except Exception:
                        pass
                elif "Signal level=" in ln:
                    try:
                        sig = ln.split('Signal level=')[-1].split(' ')[0]
                        cur["signal"] = int(sig)
                    except Exception:
                        pass
            if cur:
                nets.append(cur)
            return nets

        try:
            txt = subprocess.check_output(["iwlist", "scan"], text=True, encoding="utf-8", errors="ignore")
            networks = parse_iwlist(txt)
            if networks:
                return networks
        except Exception:
            pass

        # Detectar interfaz y reintentar: `iw dev` -> Interface <name>
        try:
            iwdev = subprocess.check_output(["iw", "dev"], text=True, encoding="utf-8", errors="ignore")
            iface = None
            for ln in iwdev.split('\n'):
                ln = ln.strip()
                if ln.startswith("Interface "):
                    iface = ln.split("Interface ", 1)[1].strip()
                    break
            if iface:
                txt = subprocess.check_output(["iwlist", iface, "scan"], text=True, encoding="utf-8", errors="ignore")
                networks = parse_iwlist(txt)
        except Exception as e:
            print(f"Linux WiFi scan error: {e}")

        return networks

    # --- macOS -----------------------------------------------------------
    def _scan_macos_wifi(self) -> List[Dict]:
        networks: List[Dict] = []
        airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        try:
            out = subprocess.check_output([airport, "-s"], text=True, encoding="utf-8", errors="ignore")
            lines = out.split('\n')[1:]  # saltar encabezado
            for ln in lines:
                if not ln.strip():
                    continue
                parts = ln.split()
                if len(parts) >= 4:
                    ssid = parts[0]
                    bssid = parts[1]
                    try:
                        channel = int(str(parts[3]).split(',')[0])
                    except Exception:
                        channel = 0
                    try:
                        signal = int(parts[2])
                    except Exception:
                        signal = 0
                    networks.append({
                        "ssid": ssid,
                        "bssid": bssid,
                        "channel": channel,
                        "signal": signal,
                    })
        except Exception as e:
            print(f"macOS WiFi scan error: {e}")
        return networks

    # --- Utilidades ------------------------------------------------------
    def get_channel_analysis(self) -> Dict[int, List[Dict]]:
        channel_usage: Dict[int, List[Dict]] = {}
        for net in self.get_available_networks():
            ch = int(net.get("channel", 0) or 0)
            channel_usage.setdefault(ch, []).append(net)
        return channel_usage
