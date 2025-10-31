import subprocess
import re
import time
import os

# Archivo donde se guardará la URL pública
OUTPUT_FILE = "public_url.txt"

# Expresiones regulares para detectar URLs
serveo_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.serveo\.net")
cloudflare_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")

def write_url(url: str):
    """Guarda la URL en el archivo"""
    with open(OUTPUT_FILE, "w") as f:
        f.write(url + "\n")
    print(f"✅ URL pública guardada en {OUTPUT_FILE}: {url}")

def start_serveo():
    """Intenta iniciar Serveo"""
    print("🚀 Intentando conectar con Serveo...")
    command = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:5000", "serveo.net"]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    start_time = time.time()
    for line in process.stdout:
        print(line.strip())

        # Intentar detectar URL de Serveo
        match = serveo_pattern.search(line)
        if match:
            url = match.group(0)
            write_url(url)
            return process  # Devuelve el proceso activo si funciona

        # Si pasan más de 15 segundos sin éxito, cancelar e intentar Cloudflare
        if time.time() - start_time > 15:
            print("⚠️ Serveo no respondió a tiempo. Probando Cloudflare Tunnel...")
            process.terminate()
            break

    return None


def start_cloudflare():
    """Inicia túnel con Cloudflare si Serveo falla"""
    print("🌩️ Iniciando túnel con Cloudflare...")
    command = ["cloudflared", "tunnel", "--url", "http://localhost:5000"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    for line in process.stdout:
        print(line.strip())

        # Detectar URL de Cloudflare (trycloudflare.com)
        match = cloudflare_pattern.search(line)
        if match:
            url = match.group(0)
            write_url(url)
            return process

    return None


def main():
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