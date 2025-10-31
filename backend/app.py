from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import logging
import os
from threading import Lock
import time

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scores.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

# Inicialización de la base de datos
db = SQLAlchemy(app)

# Lock para operaciones concurrentes en la base de datos
db_lock = Lock()

LIMIT_DATE = datetime(2025, 11, 5, 23, 59, 59)  # Fecha límite evento

# --- Modelo de puntuación ---
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(50), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'discord_id': self.discord_id,
            'score': self.score,
            'date': self.date.isoformat() if self.date else None
        }

# --- Manejo de errores ---
@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'Endpoint no encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'status': 'error', 'message': 'Error interno del servidor'}), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'status': 'error', 'message': 'Solicitud mal formada'}), 400

# --- Middleware para logging ---
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        logger.info(f"{request.method} {request.path} - {response.status_code} - {duration:.3f}s")
    return response

# --- Endpoints ---
@app.route('/')
def home():
    """Endpoint principal que sirve la página web"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        return jsonify({'status': 'error', 'message': 'Error al cargar la página'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar el estado del servicio"""
    try:
        # Verificar que la base de datos esté accesible
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'disconnected'
        }), 503

@app.route('/score', methods=['POST'])
def add_score():
    """Endpoint para agregar una nueva puntuación"""
    now = datetime.utcnow()
    
    # Verificar fecha límite
    if now > LIMIT_DATE:
        return jsonify({
            'status': 'error',
            'message': 'El evento ha terminado'
        }), 403

    # Validar contenido JSON
    if not request.is_json:
        return jsonify({
            'status': 'error',
            'message': 'Content-Type debe ser application/json'
        }), 400

    try:
        data = request.get_json()
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        return jsonify({
            'status': 'error',
            'message': 'JSON mal formado'
        }), 400

    # Validar datos requeridos
    discord_id = data.get('discord_id')
    score = data.get('score')
    
    if not discord_id or not isinstance(discord_id, str):
        return jsonify({
            'status': 'error',
            'message': 'discord_id es requerido y debe ser una cadena'
        }), 400
        
    if score is None or not isinstance(score, int) or score < 0:
        return jsonify({
            'status': 'error',
            'message': 'score es requerido y debe ser un entero no negativo'
        }), 400

    # Guardar en base de datos con manejo de concurrencia
    with db_lock:
        try:
            new_score = Score(discord_id=discord_id, score=score)
            db.session.add(new_score)
            db.session.commit()
            
            logger.info(f"Score added: {discord_id} - {score}")
            
            return jsonify({
                'status': 'success',
                'message': 'Puntaje guardado correctamente',
                'id': new_score.id
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error while adding score: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Error al guardar en la base de datos'
            }), 500

@app.route('/scores', methods=['GET'])
def get_scores():
    """Endpoint para obtener las mejores puntuaciones"""
    try:
        # Parámetros opcionales para paginación
        limit = min(int(request.args.get('limit', 10)), 50)  # Máximo 50 resultados
        offset = int(request.args.get('offset', 0))
        
        with db_lock:
            top_scores = (Score.query
                         .filter(Score.date <= LIMIT_DATE)
                         .order_by(Score.score.desc())
                         .offset(offset)
                         .limit(limit)
                         .all())
            
            return jsonify({
                'status': 'success',
                'scores': [score.to_dict() for score in top_scores],
                'count': len(top_scores),
                'limit': limit,
                'offset': offset
            })
            
    except Exception as e:
        logger.error(f"Error retrieving scores: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Error al recuperar las puntuaciones'
        }), 500

@app.route('/scores/<discord_id>', methods=['GET'])
def get_user_scores(discord_id):
    """Endpoint para obtener las puntuaciones de un usuario específico"""
    try:
        limit = min(int(request.args.get('limit', 5)), 20)
        
        with db_lock:
            user_scores = (Score.query
                          .filter(Score.discord_id == discord_id, Score.date <= LIMIT_DATE)
                          .order_by(Score.score.desc())
                          .limit(limit)
                          .all())
            
            return jsonify({
                'status': 'success',
                'discord_id': discord_id,
                'scores': [score.to_dict() for score in user_scores],
                'count': len(user_scores)
            })
            
    except Exception as e:
        logger.error(f"Error retrieving user scores for {discord_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Error al recuperar las puntuaciones del usuario'
        }), 500

# --- Función para inicializar la base de datos ---
def init_db():
    """Inicializa la base de datos y crea las tablas si no existen"""
    with app.app_context():
        try:
            db.create_all()
            logger.info("✅ Base de datos inicializada correctamente")
            
            # Verificar que el directorio de templates existe
            templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
            if not os.path.exists(templates_dir):
                logger.warning(f"⚠️ Directorio de templates no encontrado: {templates_dir}")
                os.makedirs(templates_dir, exist_ok=True)
                
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
            raise

# --- Configuración del servidor ---
if __name__ == '__main__':
    # Inicializar la base de datos
    init_db()
    
    # Configuración del servidor Flask para producción
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"🚀 Iniciando servidor en {host}:{port}")
    
    # Ejecutar la aplicación
    app.run(
        host=host,
        port=port,
        debug=False,  # Desactivar debug en producción
        threaded=True  # Manejar múltiples solicitudes concurrentes
    )