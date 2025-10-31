import subprocess
import re

# Comando SSH para crear el túnel a localhost:5000 (puedes cambiar el puerto)
command = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:5000", "serveo.net"]

# Ejecuta el comando y captura la salida en tiempo real
process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

# Expresión regular para detectar la URL
url_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.serveo\.net")

# Archivo donde se guardará la URL pública
output_file = "public_url.txt"

with open(output_file, "w") as f:
    for line in process.stdout:
        print(line.strip())  # Muestra la salida en consola
        match = url_pattern.search(line)
        if match:
            url = match.group(0)
            f.write(url + "\n")
            f.flush()
            print(f"✅ URL pública guardada en {output_file}: {url}")
            break

print("⏳ Esperando mantener el túnel activo...")
process.wait()