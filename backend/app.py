from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import os

# === CONFIGURACIÓN PRINCIPAL === #
app = Flask(__name__, instance_relative_config=True)

# Configuración de base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scores.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Asegurar que el directorio instance existe
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Inicialización de la base de datos
db = SQLAlchemy(app)

LIMIT_DATE = datetime(2025, 11, 5, 23, 59, 59, tzinfo=timezone.utc)

# === MODELO === #
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(50))
    score = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# === RUTAS PRINCIPALES === #
@app.route('/')
def home():
    """Página principal del juego"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Endpoint de salud del servidor"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'endpoints': {
            'score': '/score (POST)',
            'scores': '/scores (GET)',
            'home': '/ (GET)'
        }
    }), 200

@app.route('/score', methods=['POST', 'GET'])  # Permitir GET para testing
def add_score():
    """Endpoint para agregar puntuación"""
    if request.method == 'GET':
        return jsonify({'message': 'Use POST para enviar puntuaciones'}), 200
        
    try:
        # Verificar fecha límite
        now = datetime.now(timezone.utc)
        if now > LIMIT_DATE:
            return jsonify({
                'status': 'error',
                'message': 'El evento ha terminado'
            }), 403

        # Obtener y validar datos
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error', 
                'message': 'Datos JSON requeridos'
            }), 400
            
        discord_id = data.get('discord_id')
        score = data.get('score')
        
        if not discord_id or score is None:
            return jsonify({
                'status': 'error',
                'message': 'Datos incompletos: discord_id y score son requeridos'
            }), 400

        # Guardar en base de datos
        new_score = Score(discord_id=discord_id, score=score)
        db.session.add(new_score)
        db.session.commit()
        
        print(f"✅ Puntuación guardada: {discord_id} - {score} puntos")
        return jsonify({
            'status': 'success',
            'message': 'Puntaje guardado correctamente',
            'id': new_score.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error guardando puntuación: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error interno del servidor: {str(e)}'
        }), 500

@app.route('/scores', methods=['GET'])
def get_scores():
    """Endpoint para obtener el ranking de puntuaciones"""
    try:
        # Obtener top 10 puntuaciones (menor score = mejor)
        top_scores = Score.query.order_by(Score.score.asc()).limit(10).all()
        
        # Formatear respuesta
        scores_data = [
            {
                'discord_id': score.discord_id,
                'score': score.score,
                'date': score.date.isoformat() if score.date else None
            }
            for score in top_scores
        ]
        
        print(f"✅ Enviando {len(scores_data)} puntuaciones")
        return jsonify(scores_data)
        
    except Exception as e:
        print(f"❌ Error obteniendo puntuaciones: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error obteniendo puntuaciones: {str(e)}'
        }), 500

# === RUTAS ADICIONALES PARA DEBUGGING === #
@app.route('/debug/routes')
def debug_routes():
    """Mostrar todas las rutas disponibles"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify(routes)

@app.route('/debug/db')
def debug_db():
    """Información de la base de datos"""
    try:
        count = Score.query.count()
        db_path = os.path.join(app.instance_path, 'scores.db')
        return jsonify({
            'database_path': db_path,
            'records_count': count,
            'file_exists': os.path.exists(db_path),
            'file_size': os.path.getsize(db_path) if os.path.exists(db_path) else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === MANEJO DE ERRORES === #
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint no encontrado',
        'available_endpoints': [
            '/', '/health', '/score', '/scores', '/debug/routes', '/debug/db'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error', 
        'message': 'Error interno del servidor'
    }), 500

# === INICIALIZACIÓN === #
def init_db():
    """Inicializar la base de datos"""
    with app.app_context():
        try:
            db.create_all()
            print("✅ Base de datos inicializada correctamente")
            
            # Verificar conteo de registros
            count = Score.query.count()
            print(f"📊 Registros en la base de datos: {count}")
            
            # Mostrar ubicación de la base de datos
            db_path = os.path.join(app.instance_path, 'scores.db')
            print(f"📁 Base de datos ubicada en: {db_path}")
            
        except Exception as e:
            print(f"❌ Error inicializando base de datos: {e}")

# === EJECUCIÓN PRINCIPAL === #
if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask...")
    print("=" * 50)
    
    # Inicializar base de datos
    init_db()
    
    print("\n📋 Endpoints disponibles:")
    print("   GET  /              → Página principal del juego")
    print("   GET  /health        → Estado del servidor")
    print("   POST /score         → Guardar puntuación")
    print("   GET  /scores        → Obtener ranking")
    print("   GET  /debug/routes  → Todas las rutas (debug)")
    print("   GET  /debug/db      → Info base de datos (debug)")
    print("\n🌐 Servidor corriendo en: http://0.0.0.0:5000")
    print("=" * 50)
    
    # Ejecutar servidor
    app.run(host='0.0.0.0', port=5000, debug=True)