import subprocess
import re
import time
import threading
import requests
import os
from flask import Flask, render_template

# === CONFIGURACIÓN DEL SERVIDOR FLASK === #
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return 'OK', 200

def run_flask():
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)

# === CONFIGURACIÓN DE TÚNELES === #
OUTPUT_FILE = "public_url.txt"
serveo_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.serveo\.net")
cloudflare_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
localhost_run_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.lhr\.life")

def write_url(url: str):
    with open(OUTPUT_FILE, "w") as f:
        f.write(url + "\n")
    print(f"✅ URL pública guardada en {OUTPUT_FILE}: {url}")

def wait_for_flask_ready(timeout=30):
    print("⏳ Esperando a que Flask esté listo...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get('http://localhost:5001/health', timeout=5)
            if response.status_code == 200:
                print("✅ Flask está listo y respondiendo")
                return True
        except:
            pass
        time.sleep(1)
    print("❌ Flask no respondió en el tiempo esperado")
    return False

def start_serveo():
    """Intenta iniciar Serveo"""
    print("🚀 Intentando conectar con Serveo...")
    try:
        command = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:5001", "serveo.net"]
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
                return process

        print("⚠️ Serveo no respondió a tiempo")
        process.terminate()
    except Exception as e:
        print(f"❌ Error con Serveo: {e}")
    
    return None

def start_localhost_run():
    """Intenta con localhost.run (¡sabemos que funciona!)"""
    print("🌐 Intentando con localhost.run...")
    try:
        command = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:5001", "nokey@localhost.run"]
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
                # Intentar extraer la URL manualmente
                words = line.split()
                for word in words:
                    if word.startswith("https://") and "lhr.life" in word:
                        url = word.strip()
                        # Limpiar la URL si tiene caracteres extraños
                        url = url.split(',')[0].split('"')[0].split(')')[0]
                        write_url(url)
                        print("✅ localhost.run conectado exitosamente")
                        
                        # Verificar que funciona inmediatamente
                        try:
                            print("🔍 Verificando que el túnel esté operativo...")
                            response = requests.get(f"{url}/", timeout=10)
                            if response.status_code == 200:
                                print("✅ ¡Túnel de localhost.run completamente operativo!")
                                return process
                            else:
                                print(f"⚠️ localhost.run responde con estado {response.status_code}")
                        except Exception as e:
                            print(f"⚠️ Error verificando localhost.run: {e}")
                        
                        return process  # Devolver el proceso aunque la verificación falle
        
        if not url:
            print("❌ No se pudo obtener URL de localhost.run")
            process.terminate()
            
    except Exception as e:
        print(f"❌ Error con localhost.run: {e}")
    
    return None

def start_cloudflare():
    """Inicia túnel con Cloudflare (como respaldo)"""
    print("🌩️ Intentando conectar con Cloudflare...")
    
    # Verificar si cloudflared está instalado
    try:
        subprocess.run(["cloudflared", "--version"], capture_output=True, check=True)
    except:
        print("❌ cloudflared no está instalado, saltando Cloudflare...")
        return None

    # Detener instancias previas
    subprocess.run(["pkill", "-f", "cloudflared"], capture_output=True)
    time.sleep(2)
    
    try:
        command = ["cloudflared", "tunnel", "--url", "http://localhost:5001"]
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
                print("⏳ Esperando a que el túnel de Cloudflare se estabilice...")
                
                # Verificar que funciona
                for i in range(5):
                    try:
                        print(f"🔍 Verificando intento {i+1}/5...")
                        response = requests.get(f"{url}/", timeout=15)
                        print(f"📊 Estado HTTP: {response.status_code}")
                        
                        if response.status_code == 200:
                            print("✅ ¡Túnel de Cloudflare completamente operativo!")
                            return process
                        else:
                            print(f"⏱️ Túnel aún no listo, estado: {response.status_code}. Esperando...")
                            time.sleep(3)
                    except requests.exceptions.RequestException as e:
                        print(f"⏱️ Túnel no accesible aún: {e}. Esperando...")
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

def check_templates_exist():
    template_path = os.path.join("templates", "index.html")
    if os.path.exists(template_path):
        print(f"✅ Template encontrado: {template_path}")
        return True
    else:
        print(f"❌ Template no encontrado: {template_path}")
        return False

def main():
    print("🎯 Iniciando servidor Flask y buscando túnel público...")
    print("📡 Servicios disponibles: localhost.run → Serveo → Cloudflare")
    
    if not check_templates_exist():
        return

    # Iniciar Flask en hilo separado
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    if not wait_for_flask_ready():
        print("❌ No se pudo iniciar Flask correctamente")
        return

    # Probar servicios en orden - localhost.run PRIMERO (porque sabemos que funciona)
    services = [
        ("localhost.run", start_localhost_run),
        ("Serveo", start_serveo),
        ("Cloudflare", start_cloudflare)
    ]

    process = None
    for service_name, service_func in services:
        print(f"\n{'='*50}")
        print(f"🔍 Probando {service_name}...")
        process = service_func()
        if process is not None:
            print(f"✅ Conectado exitosamente con {service_name}")
            break
        else:
            print(f"❌ {service_name} falló")

    if process is None:
        print("\n💥 Todos los servicios fallaron.")
        print("\n💡 Soluciones:")
        print("1. Verifica tu conexión a Internet")
        print("2. localhost.run debería funcionar - prueba manualmente:")
        print("   ssh -o StrictHostKeyChecking=no -R 80:localhost:5001 nokey@localhost.run")
    else:
        print(f"\n🎉 ¡Túnel público activo! Revisa el archivo: {OUTPUT_FILE}")
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo servicios...")
            process.terminate()

if __name__ == "__main__":
    main()