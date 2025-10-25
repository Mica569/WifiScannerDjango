import threading
import time
import speedtest
import ping3
from typing import Dict, Tuple, Optional

class SpeedTester:
    """Clase para realizar pruebas de velocidad y latencia"""
    
    def __init__(self):
        # Crear instancia perezosa para evitar fallar en entornos sin red
        self.st: Optional[speedtest.Speedtest] = None
        self.download_speed = 0
        self.upload_speed = 0
        self.ping = 0
        self.is_testing = False
    
    def run_test(self, callback=None) -> Dict[str, float]:
        """Ejecuta la prueba de velocidad completa"""
        self.is_testing = True
        
        try:
            # Medir ping
            self.ping = self._measure_ping()
            
            # Medir velocidad de descarga
            self.download_speed = self._measure_download()
            
            # Medir velocidad de subida
            self.upload_speed = self._measure_upload()
            
            result = {
                "download": self.download_speed,
                "upload": self.upload_speed,
                "ping": self.ping
            }
            
            if callback:
                callback(result)
                
            return result
        except Exception as e:
            print(f"Speed test error: {e}")
            return {"download": 0, "upload": 0, "ping": 0}
        finally:
            self.is_testing = False
    
    def _measure_ping(self) -> float:
        """Mide la latencia de la conexión"""
        try:
            # Medir ping a Google DNS
            latency = ping3.ping('8.8.8.8', timeout=2)
            return round(latency * 1000, 2) if latency else 0
        except:
            return 0
    
    def _measure_download(self) -> float:
        """Mide la velocidad de descarga"""
        try:
            if self.st is None:
                self.st = speedtest.Speedtest()
            self.st.get_best_server()
            return round(self.st.download() / 1_000_000, 2)  # Convertir a Mbps
        except Exception:
            return 0
    
    def _measure_upload(self) -> float:
        """Mide la velocidad de subida"""
        try:
            if self.st is None:
                self.st = speedtest.Speedtest()
            return round(self.st.upload() / 1_000_000, 2)  # Convertir a Mbps
        except Exception:
            return 0
    
    def run_test_async(self, callback=None):
        """Ejecuta la prueba de velocidad en un hilo separado"""
        thread = threading.Thread(target=self.run_test, args=(callback,))
        thread.daemon = True
        thread.start()
