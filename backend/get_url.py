import subprocess
import re
import time
import threading
from flask import Flask, render_template

# === CONFIGURACIÓN DEL SERVIDOR FLASK === #
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

def run_flask():
    """Ejecuta Flask en un hilo separado"""
    app.run(host='0.0.0.0', port=5001, debug=False)

# === CONFIGURACIÓN DE TÚNELES === #
OUTPUT_FILE = "public_url.txt"
serveo_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.serveo\.net")
cloudflare_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")

def write_url(url: str):
    with open(OUTPUT_FILE, "w") as f:
        f.write(url + "\n")
    print(f"✅ URL pública guardada en {OUTPUT_FILE}: {url}")

def start_serveo():
    """Intenta iniciar Serveo"""
    print("🚀 Intentando conectar con Serveo...")
    command = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:5001", "serveo.net"]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    start_time = time.time()

    for line in process.stdout:
        print(line.strip())

        match = serveo_pattern.search(line)
        if match:
            url = match.group(0)
            write_url(url)
            return process

        if time.time() - start_time > 15:
            print("⚠️ Serveo no respondió a tiempo. Probando Cloudflare Tunnel...")
            process.terminate()
            break

    return None

def start_cloudflare():
    """Inicia túnel con Cloudflare si Serveo falla"""
    print("🌩️ Iniciando túnel con Cloudflare...")
    command = ["cloudflared", "tunnel", "--url", "http://localhost:5001"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    for line in process.stdout:
        print(line.strip())

        match = cloudflare_pattern.search(line)
        if match:
            url = match.group(0)
            write_url(url)
            return process

    return None

def main():
    # Ejecutar Flask en un hilo separado
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Esperar un poco para asegurar que Flask ya inició
    time.sleep(3)

    serveo_process = start_serveo()

    if serveo_process is None:
        cloudflare_process = start_cloudflare()
        if cloudflare_process is None:
            print("❌ No se pudo establecer conexión con Serveo ni Cloudflare.")
        else:
            print("✅ Conexión establecida con Cloudflare.")
            cloudflare_process.wait()
    else:
        print("✅ Conexión establecida con Serveo.")
        serveo_process.wait()

if __name__ == "__main__":
    main()