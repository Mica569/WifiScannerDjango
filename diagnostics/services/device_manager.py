import psutil
from typing import List, Dict

class DeviceManager:
    """Clase para gestionar y monitorear dispositivos"""
    
    def __init__(self):
        pass
    
    def get_network_usage(self) -> Dict[str, float]:
        """Obtiene el uso actual de la red"""
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
    
    def get_processes_network_usage(self) -> List[Dict]:
        """Obtiene el uso de red por proceso"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                io_counters = proc.io_counters()
                if io_counters:
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "read_bytes": io_counters.read_bytes,
                        "write_bytes": io_counters.write_bytes
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return sorted(processes, key=lambda x: x['read_bytes'] + x['write_bytes'], reverse=True)[:10]