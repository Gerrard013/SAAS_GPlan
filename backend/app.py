from flask import Flask, g, request, render_template, jsonify
from flask_cors import CORS
from models import db, BarbeariaCliente, PlanoAssinatura, AdminUser, ConfiguracaoBarbearia
from routes import routes
from auth_routes import auth_routes
from admin_routes import admin_routes
from main_routes import payment_routes
from config import Config
import logging
import json
from datetime import datetime
from sqlalchemy import text
import os

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializa a aplicação Flask
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(Config)

# Banco de dados
db.init_app(app)

# Libera CORS para acesso mobile
CORS(app)

# Blueprints (rotas separadas)
app.register_blueprint(routes)
app.register_blueprint(auth_routes)
app.register_blueprint(admin_routes)
app.register_blueprint(payment_routes, url_prefix="/payment")

# -------------------- ROTAS PRINCIPAIS --------------------

@app.route('/')
def landing_page():
    return render_template('landing-page.html')

@app.route('/admin/login')
def admin_login_page():
    return render_template('admin-login.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/agendamento')
def agendamento_page():
    return render_template('index.html')

# -------------------- HEALTH CHECK --------------------

@app.route('/health')
def health_check():
    """Endpoint para verificar saúde da aplicação"""
    try:
        with app.app_context():
            db.session.execute(text('SELECT 1'))
        
        return jsonify({
            "status": "healthy",
            "service": "GPlan Barbearia",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "database": "connected",
            "message": "✅ Sistema operacional perfeitamente!"
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "message": "❌ Erro no sistema"
        }), 500

@app.route('/api/info')
def api_info():
    """Informações da API"""
    return jsonify({
        "name": "GPlan API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "landing": "/",
            "admin": "/admin/login",
            "agendamento": "/agendamento",
            "pagamento": "/payment"
        }
    })

# -------------------- MIDDLEWARE --------------------

@app.before_request
def identificar_barbearia():
    barbearia_id = request.headers.get('X-Barbearia-ID') or request.args.get('barbearia_id')
    if barbearia_id:
        try:
            barbearia = BarbeariaCliente.query.get(int(barbearia_id))
            if barbearia:
                g.barbearia = barbearia
                g.barbearia_id = barbearia.id
        except:
            pass

# -------------------- DADOS INICIAIS --------------------

def criar_dados_iniciais():
    with app.app_context():
        db.create_all()
        
        if not PlanoAssinatura.query.first():
            planos = [
                PlanoAssinatura(
                    nome="Start", preco_mensal=150.00, limite_barbeiros=2, limite_agendamentos=100,
                    recursos=json.dumps(["agendamento_24_7", "dashboard_completo", "whatsapp_business"])
                ),
                PlanoAssinatura(
                    nome="Profissional", preco_mensal=297.00, limite_barbeiros=5, limite_agendamentos=300,
                    recursos=json.dumps(["agendamento_24_7", "dashboard_completo", "marketing_automatico"])
                ),
                PlanoAssinatura(
                    nome="Enterprise", preco_mensal=497.00, limite_barbeiros=20, limite_agendamentos=1000,
                    recursos=json.dumps(["todos_recursos", "white_label", "api_exclusiva"])
                )
            ]
            db.session.add_all(planos)
            db.session.commit()
            logger.info("✅ Planos criados com sucesso!")
        
        if not AdminUser.query.first():
            senha_admin = os.getenv("ADMIN_PASSWORD", "admin123")
            admin = AdminUser(username="admin", email="admin@gplan.com.br")
            admin.set_password(senha_admin)
            db.session.add(admin)
            db.session.commit()
            logger.info(f"✅ Admin criado: admin / {senha_admin}")

# -------------------- CONFIGURAÇÃO HOST --------------------

if __name__ == '__main__':
    logger.info("🚀 Iniciando GPlan - Sistema de Gestão para Barbearias")
    
    with app.app_context():
        criar_dados_iniciais()
    
    logger.info("✅ Dados iniciais criados com sucesso!")
    logger.info("🌐 Servidor iniciando em http://0.0.0.0:5000")
    logger.info("🔧 Health Check: http://localhost:5000/health")
    logger.info("📊 API Info: http://localhost:5000/api/info")
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)