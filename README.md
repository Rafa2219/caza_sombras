# 🎃 La Caza de Sombras

Minijuego web de Halloween para tu servidor de Discord.
Rompecabezas divertido con emojis de Halloween, ranking en tiempo real y puntuaciones asociadas al Discord ID de cada jugador.

**Duración del evento:** hasta el 5 de noviembre 2025.

---
> Esto está hecho con IA por cierto.

## 🗂 Estructura de archivos

```
caza_sombras/
│
├─ frontend/
│   └─ index.html       <-- Juego web con animaciones y ranking
│
├─ backend/
│   └─ app.py           <-- API Flask para guardar puntuaciones
│   └─ scores.db        <-- Base de datos SQLite (se genera automáticamente)
│   └─ templates/
│      └─ index.html
└─ README.md            <-- Este archivo
```

---

## 💻 Requisitos

- Python 3.8+
- Flask
- Flask SQLAlchemy
- Navegador moderno (Chrome, Edge, Firefox)
- Discord bot (opcional) para integración de ranking

---

## 🚀 Instalación

1. **Clonar o descargar el repositorio**

```bash
git clone <URL_DEL_REPOSITORIO>
cd ./caza_sombras/backend
```

2. **Crear entorno virtual y activar**

```bash
python3 -m venv venv
source venv/bin/activate  # Linux / Mac
venv\Scripts\activate     # Windows
```

3. **Instalar dependencias**

```bash
pip install flask flask_sqlalchemy
```

4. **Ejecutar backend**

```bash
python app.py
```

> El backend correrá en `http://localhost:5000/` y creará automáticamente la base de datos `scores.db`.

5. **Abrir frontend**

- Desde tu navegador, abre:  
`http://localhost:5000/index.html`

---

## 🎮 Cómo jugar

1. Ingresa tu **Discord ID** cuando se te solicite.
2. Resuelve el **rompecabezas** arrastrando o seleccionando las piezas en el orden correcto.
3. El **temporizador** cuenta 60 segundos.
4. Al completar el puzzle o agotarse el tiempo, tu **puntaje se envía automáticamente al backend**.
5. Visualiza el **ranking Top 5** en la web o Top 10 en Discord.

---

## 🤖 Integración con Discord (opcional)

- Comando `/caza_sombras` para enviar el enlace del juego a un usuario.

- Comando `/ranking_halloween` para mostrar el ranking Top 10.

---

## 📅 Fecha límite

- Solo se aceptarán puntuaciones hasta **5 de noviembre 2025, 23:59:59 UTC**.

---

## ✨ Características

- Puzzle interactivo y fácil de completar  
- Emojis de Halloween: 🎃 👻 🦇 🕸️ 🍬 🧙‍♀️ 🕷️ 🦉 💀  
- Partículas y animaciones al mover piezas  
- Ranking Top 5 en la web y Top 10 vía Discord  
- Temporizador con límite de 60 segundos  
- Guardado de puntuaciones por Discord ID  

¡Disfruta el evento y que la Caza de Sombras comience! 🎃👻
