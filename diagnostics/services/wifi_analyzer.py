import subprocess
import re
import platform
from typing import List, Dict

class WiFiAnalyzer:
    """Clase para analizar redes WiFi disponibles"""
    
    def __init__(self):
        self.os_type = platform.system()
    
    def get_available_networks(self) -> List[Dict]:
        """Obtiene la lista de redes WiFi disponibles"""
        networks = []
        
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
    
    def _scan_windows_wifi(self) -> List[Dict]:
        """Escaneo de redes WiFi para Windows"""
        networks = []
        try:
            # Ejecutar comando netsh para listar redes WiFi
            result = subprocess.check_output(["netsh", "wlan", "show", "networks", "mode=bssid"], text=True)
            
            # Parsear resultado
            current_ssid = None
            current_bssid = None
            current_channel = None
            current_signal = None
            
            for line in result.split('\n'):
                line = line.strip()
                
                if line.startswith("SSID"):
                    if current_ssid and current_bssid and current_channel and current_signal:
                        networks.append({
                            "ssid": current_ssid,
                            "bssid": current_bssid,
                            "channel": current_channel,
                            "signal": current_signal
                        })
                    
                    current_ssid = line.split(':', 1)[1].strip()
                    current_bssid = None
                    current_channel = None
                    current_signal = None
                
                elif line.startswith("BSSID"):
                    if current_bssid and current_channel and current_signal:
                        networks.append({
                            "ssid": current_ssid,
                            "bssid": current_bssid,
                            "channel": current_channel,
                            "signal": current_signal
                        })
                    
                    current_bssid = line.split(':', 1)[1].strip()
                
                elif line.startswith("Channel"):
                    current_channel = int(line.split(':', 1)[1].strip())
                
                elif line.startswith("Signal"):
                    current_signal = int(line.split(':', 1)[1].strip().replace('%', ''))
            
            # Añadir la última red
            if current_ssid and current_bssid and current_channel and current_signal:
                networks.append({
                    "ssid": current_ssid,
                    "bssid": current_bssid,
                    "channel": current_channel,
                    "signal": current_signal
                })
                
        except Exception as e:
            print(f"Windows WiFi scan error: {e}")
        
        return networks
    
    def _scan_linux_wifi(self) -> List[Dict]:
        """Escaneo de redes WiFi para Linux"""
        networks = []
        try:
            # Usar iwlist si está disponible
            result = subprocess.check_output(["iwlist", "scan"], text=True)
            
            current_cell = {}
            for line in result.split('\n'):
                line = line.strip()
                
                if "Cell" in line and "Address" in line:
                    if current_cell:
                        networks.append(current_cell)
                    current_cell = {"bssid": line.split('Address: ')[1]}
                
                elif "ESSID" in line:
                    current_cell["ssid"] = line.split(':"')[1].replace('"', '')
                
                elif "Channel:" in line:
                    current_cell["channel"] = int(line.split('Channel:')[1])
                
                elif "Quality=" in line and "Signal level=" in line:
                    signal_str = line.split('Signal level=')[1].split(' ')[0]
                    current_cell["signal"] = int(signal_str)
            
            if current_cell:
                networks.append(current_cell)
                
        except Exception as e:
            print(f"Linux WiFi scan error: {e}")
        
        return networks
    
    def _scan_macos_wifi(self) -> List[Dict]:
        """Escaneo de redes WiFi para macOS"""
        networks = []
        try:
            # Usar airport utility
            result = subprocess.check_output(["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"], text=True)
            
            # Saltar la línea de encabezado
            lines = result.split('\n')[1:]
            
            for line in lines:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 4:
                    networks.append({
                        "ssid": parts[0],
                        "bssid": parts[1],
                        "channel": int(parts[3].replace(',', '')),
                        "signal": int(parts[2])
                    })
                    
        except Exception as e:
            print(f"macOS WiFi scan error: {e}")
        
        return networks
    
    def get_channel_analysis(self) -> Dict[int, List[Dict]]:
        """Analiza la congestión de canales WiFi"""
        networks = self.get_available_networks()
        channel_usage = {}
        
        for network in networks:
            channel = network.get("channel", 0)
            if channel not in channel_usage:
                channel_usage[channel] = []
            channel_usage[channel].append(network)
        
        return channel_usage