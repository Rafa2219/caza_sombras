from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import logging
import os
from threading import Lock
import time

# === CONFIGURACIÓN PRINCIPAL === #
app = Flask(__name__)

# OBTENER LA RUTA ABSOLUTA DEL DIRECTORIO ACTUAL
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, 'scores.db')

# USAR RUTA ABSOLUTA PARA LA BASE DE DATOS
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print(f"📁 Base de datos en: {db_path}")  # Para verificar la ruta

# El resto de tu código permanece igual...
db = SQLAlchemy(app)
db_lock = Lock()

LIMIT_DATE = datetime(2025, 11, 5, 23, 59, 59)

# === MODELO === #
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(50))
    score = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# === RUTAS === #
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return 'OK', 200

@app.route('/score', methods=['POST'])
def add_score():
    now = datetime.utcnow()
    if now > LIMIT_DATE:
        return jsonify({'status':'error','message':'El evento ha terminado'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'status':'error','message':'Datos JSON requeridos'}), 400
        
    discord_id = data.get('discord_id')
    score = data.get('score')
    
    if not discord_id or score is None:
        return jsonify({'status':'error','message':'Datos incompletos'}), 400

    try:
        new_score = Score(discord_id=discord_id, score=score)
        db.session.add(new_score)
        db.session.commit()
        return jsonify({'status':'success','message':'Puntaje guardado correctamente'})
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error en base de datos: {e}")
        return jsonify({'status':'error','message':'Error en la base de datos'}), 500

@app.route('/scores', methods=['GET'])
def get_scores():
    try:
        top_scores = Score.query.filter(Score.date <= LIMIT_DATE).order_by(Score.score.asc()).limit(10).all()
        return jsonify([
            {'discord_id': s.discord_id, 'score': s.score, 'date': s.date.isoformat()}
            for s in top_scores
        ])
    except Exception as e:
        print(f"❌ Error recuperando scores: {e}")
        return jsonify({'status':'error','message':'Error recuperando puntuaciones'}), 500

# === INICIALIZACIÓN === #
def init_db():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Base de datos inicializada correctamente")
            
            # Verificar que tenemos la tabla y algunos datos de prueba
            count = Score.query.count()
            print(f"✅ Registros en la base de datos: {count}")
            
        except Exception as e:
            print(f"❌ Error inicializando base de datos: {e}")

# === EJECUCIÓN === #
if __name__ == '__main__':
    init_db()
    print("🚀 Servidor Flask iniciando...")
    print("📊 Endpoints disponibles:")
    print("   GET  /          -> Página principal")
    print("   GET  /health    -> Health check")
    print("   POST /score     -> Guardar puntuación")
    print("   GET  /scores    -> Obtener ranking")
    
    app.run(host='0.0.0.0', port=5000, debug=True)