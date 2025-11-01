import subprocess
import re
import time
import threading
import requests
import os
from flask import Flask, render_template
import signal
import sys

# === CONFIGURACIÓN DEL SERVIDOR FLASK === #
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return 'OK', 200

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

# === CONFIGURACIÓN DE TÚNELES === #
OUTPUT_FILE = "public_url.txt"
RECONNECT_INTERVAL = 300  # 5 minutos después de falla total
HEALTH_CHECK_INTERVAL = 60  # 1 minuto
MAX_ATTEMPTS_PER_SERVICE = 5  # 5 intentos por servicio
ATTEMPT_DELAY = 10  # 10 segundos entre intentos del mismo servicio

serveo_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.serveo\.net")
cloudflare_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
localhost_run_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.lhr\.life")

# Variables globales para control de procesos
current_tunnel_process = None
tunnel_active = False
current_url = None
service_attempts = {}  # Seguimiento de intentos por servicio

def write_url(url: str):
    global current_url
    current_url = url
    with open(OUTPUT_FILE, "w") as f:
        f.write(url + "\n")
    print(f"✅ URL pública guardada en {OUTPUT_FILE}: {url}")

def wait_for_flask_ready(timeout=30):
    print("⏳ Esperando a que Flask esté listo...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get('http://localhost:5000/health', timeout=5)
            if response.status_code == 200:
                print("✅ Flask está listo y respondiendo")
                return True
        except:
            pass
        time.sleep(1)
    print("❌ Flask no respondió en el tiempo esperado")
    return False

def check_tunnel_health(url):
    """Verifica si el túnel está respondiendo"""
    try:
        response = requests.get(f"{url}/health", timeout=10)
        return response.status_code == 200
    except:
        return False

def tunnel_health_monitor():
    """Monitorea la salud del túnel y reconecta si es necesario"""
    global tunnel_active, current_url
    
    while True:
        time.sleep(HEALTH_CHECK_INTERVAL)
        
        if current_url and tunnel_active:
            if not check_tunnel_health(current_url):
                print("❌ El túnel no responde, reconectando...")
                tunnel_active = False
                start_tunnel_services()

def start_serveo():
    """Intenta iniciar Serveo con múltiples intentos"""
    global current_tunnel_process
    print("🚀 Intentando conectar con Serveo...")
    try:
        command = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:5000", "serveo.net"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        start_time = time.time()

        while time.time() - start_time < 15:
            line = process.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue

            print(line.strip())

            match = serveo_pattern.search(line)
            if match:
                url = match.group(0)
                write_url(url)
                
                # Verificar que el túnel funciona
                if check_tunnel_health(url):
                    current_tunnel_process = process
                    return process
                else:
                    print("❌ Serveo conectado pero no responde")
                    process.terminate()
                    return None

        print("⚠️ Serveo no respondió a tiempo")
        process.terminate()
    except Exception as e:
        print(f"❌ Error con Serveo: {e}")
    
    return None

def start_localhost_run():
    """Inicia túnel con localhost.run con múltiples intentos"""
    global current_tunnel_process
    print("🌐 Intentando con localhost.run...")
    try:
        command = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:5000", "nokey@localhost.run"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        start_time = time.time()
        url = None
        
        while time.time() - start_time < 25:
            line = process.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
                
            print(line.strip())
            
            # Buscar patrones de URL de localhost.run
            if "assigned URL" in line or "lhr.life" in line:
                words = line.split()
                for word in words:
                    if word.startswith("https://") and "lhr.life" in word:
                        url = word.strip()
                        url = url.split(',')[0].split('"')[0].split(')')[0]
                        write_url(url)
                        
                        # Verificar que funciona
                        if check_tunnel_health(url):
                            current_tunnel_process = process
                            print("✅ localhost.run conectado exitosamente")
                            return process
                        else:
                            print("❌ localhost.run conectado pero no responde")
                            process.terminate()
                            return None
        
        if not url:
            print("❌ No se pudo obtener URL de localhost.run")
            process.terminate()
            
    except Exception as e:
        print(f"❌ Error con localhost.run: {e}")
    
    return None

def start_cloudflare():
    """Inicia túnel con Cloudflare con múltiples intentos"""
    global current_tunnel_process
    print("🌩️ Intentando conectar con Cloudflare...")
    
    try:
        subprocess.run(["cloudflared", "--version"], capture_output=True, check=True)
    except:
        print("❌ cloudflared no está instalado, saltando Cloudflare...")
        return None

    # Detener instancias previas
    subprocess.run(["pkill", "-f", "cloudflared"], capture_output=True)
    time.sleep(2)
    
    try:
        command = ["cloudflared", "tunnel", "--url", "http://localhost:5000"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        start_time = time.time()
        url = None
        
        while time.time() - start_time < 30:
            line = process.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
                
            print(line.strip())
            
            match = cloudflare_pattern.search(line)
            if match:
                url = match.group(0)
                write_url(url)
                
                # Esperar y verificar que funciona
                for i in range(5):
                    try:
                        print(f"🔍 Verificando intento {i+1}/5...")
                        response = requests.get(f"{url}/", timeout=15)
                        
                        if response.status_code == 200:
                            current_tunnel_process = process
                            print("✅ ¡Túnel de Cloudflare completamente operativo!")
                            return process
                        else:
                            time.sleep(3)
                    except requests.exceptions.RequestException:
                        time.sleep(3)
                
                print("❌ El túnel de Cloudflare no se volvió accesible")
                process.terminate()
                return None
        
        if not url:
            print("❌ No se pudo obtener URL de Cloudflare")
            process.terminate()
            
    except Exception as e:
        print(f"❌ Error con Cloudflare: {e}")
    
    return None

def start_service_with_retries(service_name, service_func):
    """Intenta conectar a un servicio con múltiples reintentos"""
    global service_attempts
    
    if service_name not in service_attempts:
        service_attempts[service_name] = 0
    
    for attempt in range(1, MAX_ATTEMPTS_PER_SERVICE + 1):
        service_attempts[service_name] = attempt
        print(f"\n🔄 {service_name} - Intento {attempt}/{MAX_ATTEMPTS_PER_SERVICE}")
        
        process = service_func()
        if process is not None:
            print(f"✅ {service_name} conectado exitosamente en el intento {attempt}")
            service_attempts[service_name] = 0  # Resetear contador
            return process
        
        if attempt < MAX_ATTEMPTS_PER_SERVICE:
            print(f"⏳ Esperando {ATTEMPT_DELAY} segundos antes del próximo intento...")
            time.sleep(ATTEMPT_DELAY)
    
    print(f"❌ {service_name} falló después de {MAX_ATTEMPTS_PER_SERVICE} intentos")
    return None

def check_templates_exist():
    template_path = os.path.join("templates", "index.html")
    if os.path.exists(template_path):
        print(f"✅ Template encontrado: {template_path}")
        return True
    else:
        print(f"❌ Template no encontrado: {template_path}")
        return False

def cleanup(signum=None, frame=None):
    """Limpia los procesos al cerrar la aplicación"""
    global current_tunnel_process
    print("\n🛑 Cerrando aplicación...")
    if current_tunnel_process:
        current_tunnel_process.terminate()
    sys.exit(0)

def start_tunnel_services():
    """Inicia los servicios de túnel con reintentos por servicio"""
    global tunnel_active, current_tunnel_process, service_attempts
    
    services = [
        ("Serveo", start_serveo),
        ("localhost.run", start_localhost_run),
        ("Cloudflare", start_cloudflare)
    ]

    # Reiniciar contadores de intentos si es la primera vez
    if not service_attempts:
        for service_name, _ in services:
            service_attempts[service_name] = 0

    print(f"\n🎯 Iniciando proceso de conexión con {MAX_ATTEMPTS_PER_SERVICE} intentos por servicio")
    
    for service_name, service_func in services:
        print(f"\n{'='*60}")
        print(f"🔍 Probando {service_name}...")
        
        process = start_service_with_retries(service_name, service_func)
        if process is not None:
            print(f"✅ Conectado exitosamente con {service_name}")
            tunnel_active = True
            current_tunnel_process = process
            return True

    # Si llegamos aquí, todos los servicios fallaron
    print(f"\n💥 TODOS LOS SERVICIOS FALLARON después de {MAX_ATTEMPTS_PER_SERVICE} intentos cada uno")
    print(f"⏳ Reintentando en {RECONNECT_INTERVAL//60} minutos...")
    
    # Mostrar resumen de intentos
    print("\n📊 Resumen de intentos:")
    for service_name, attempts in service_attempts.items():
        status = "❌ Falló" if attempts >= MAX_ATTEMPTS_PER_SERVICE else "⚠️ No probado completamente"
        print(f"   {service_name}: {attempts}/{MAX_ATTEMPTS_PER_SERVICE} intentos - {status}")
    
    return False

def main():
    global tunnel_active
    
    # Configurar manejo de señales para limpieza graceful
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    print("🎯 Iniciando servidor Flask con sistema de reconexión mejorado")
    print("📡 Servicios disponibles: Serveo → localhost.run → Cloudflare")
    print(f"🔄 {MAX_ATTEMPTS_PER_SERVICE} intentos por servicio, {RECONNECT_INTERVAL//60} minutos entre ciclos completos")
    
    if not check_templates_exist():
        return

    # Iniciar Flask en hilo separado
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    if not wait_for_flask_ready():
        print("❌ No se pudo iniciar Flask correctamente")
        return

    # Iniciar monitoreo de salud en hilo separado
    health_thread = threading.Thread(target=tunnel_health_monitor, daemon=True)
    health_thread.start()

    # Bucle principal con reintentos completos cada 5 minutos
    consecutive_failures = 0
    while True:
        success = start_tunnel_services()
        
        if success:
            consecutive_failures = 0
            print("\n✅ Conexión establecida. Monitoreando...")
            
            # Esperar mientras el túnel esté activo
            try:
                while tunnel_active:
                    time.sleep(10)
            except KeyboardInterrupt:
                cleanup()
        else:
            consecutive_failures += 1
            print(f"\n❌ Ciclo de conexión fallido (#{consecutive_failures})")
            print(f"⏳ Esperando {RECONNECT_INTERVAL//60} minutos para el próximo ciclo...")
            
            # Contar regresivamente los 5 minutos
            for remaining in range(RECONNECT_INTERVAL, 0, -30):  # Actualizar cada 30 segundos
                if remaining % 60 == 0:
                    print(f"   Tiempo restante: {remaining//60} minutos")
                else:
                    print(f"   Tiempo restante: {remaining} segundos")
                time.sleep(30)
            
            print("🔄 Reiniciando ciclo de conexión...")

if __name__ == "__main__":
    main()