import subprocess
import platform
import re
from typing import List, Dict

class NetworkScanner:
    """Clase para escanear dispositivos en la red"""
    
    def __init__(self):
        self.os_type = platform.system()
    
    def get_connected_devices(self) -> List[Dict]:
        """Obtiene la lista de dispositivos conectados a la red"""
        devices = []
        
        try:
            if self.os_type == "Windows":
                devices = self._scan_windows()
            elif self.os_type == "Linux":
                devices = self._scan_linux()
            elif self.os_type == "Darwin":  # macOS
                devices = self._scan_macos()
        except Exception as e:
            print(f"Error scanning devices: {e}")
        
        return devices
    
    def _scan_windows(self) -> List[Dict]:
        """Escaneo para sistemas Windows"""
        devices = []
        try:
            # Ejecutar arp -a para obtener la tabla ARP
            result = subprocess.check_output(["arp", "-a"], text=True)
            
            # Expresión regular para encontrar direcciones IP y MAC
            pattern = r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-]+)\s+(\w+)"
            
            for match in re.finditer(pattern, result):
                ip, mac, _ = match.groups()
                devices.append({
                    "ip": ip,
                    "mac": mac,
                    "hostname": self._get_hostname(ip)
                })
        except Exception as e:
            print(f"Windows scan error: {e}")
        
        return devices
    
    def _scan_linux(self) -> List[Dict]:
        """Escaneo para sistemas Linux"""
        devices = []
        try:
            # Usar nmap si está disponible
            try:
                result = subprocess.check_output(["nmap", "-sn", "192.168.1.0/24"], text=True)
                pattern = r"Nmap scan report for (.*?)\n.*?Host is up.*?\n.*?MAC Address: (.*?) \(.*?\)"
                
                for match in re.finditer(pattern, result, re.DOTALL):
                    hostname, mac = match.groups()
                    devices.append({
                        "ip": hostname.split()[-1] if ' ' in hostname else hostname,
                        "mac": mac.strip(),
                        "hostname": hostname if '(' not in hostname else ""
                    })
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to arp scan
                result = subprocess.check_output(["arp", "-a"], text=True)
                pattern = r"(\S+) \((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-fA-F:]+) .*"
                
                for match in re.finditer(pattern, result):
                    hostname, ip, mac = match.groups()
                    devices.append({
                        "ip": ip,
                        "mac": mac,
                        "hostname": hostname
                    })
        except Exception as e:
            print(f"Linux scan error: {e}")
        
        return devices
    
    def _scan_macos(self) -> List[Dict]:
        """Escaneo para sistemas macOS"""
        devices = []
        try:
            result = subprocess.check_output(["arp", "-a"], text=True)
            pattern = r"(\S+) \((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-fA-F:]+) .*"
            
            for match in re.finditer(pattern, result):
                hostname, ip, mac = match.groups()
                devices.append({
                    "ip": ip,
                    "mac": mac,
                    "hostname": hostname
                })
        except Exception as e:
            print(f"macOS scan error: {e}")
        
        return devices
    
    def _get_hostname(self, ip: str) -> str:
        """Intenta obtener el nombre de host de una IP"""
        try:
            result = subprocess.check_output(["nslookup", ip], text=True, timeout=2)
            if "name" in result:
                pattern = r"name = (.*?)\n"
                match = re.search(pattern, result)
                if match:
                    return match.group(1)
        except:
            pass
        return "Unknown"