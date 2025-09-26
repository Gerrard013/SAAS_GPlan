# auth_routes.py
import jwt
from flask import Blueprint, request, jsonify
from models import db, AdminUser, BarbeariaCliente
from werkzeug.security import check_password_hash
import datetime
from config import Config

auth_routes = Blueprint('auth_routes', __name__)

def gerar_token_admin(admin):
    """Gera token JWT para admin"""
    return jwt.encode({
        'user_id': admin.id,
        'username': admin.username,
        'tipo': 'admin',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, Config.SECRET_KEY, algorithm='HS256')

def gerar_token_barbearia(barbearia):
    """Gera token JWT para barbearia"""
    return jwt.encode({
        'barbearia_id': barbearia.id,
        'dominio': barbearia.dominio,
        'tipo': 'barbearia',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, Config.SECRET_KEY, algorithm='HS256')

@auth_routes.route('/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"erro": "Username e senha são obrigatórios"}), 400

        admin = AdminUser.query.filter_by(username=username).first()
        if not admin:
            return jsonify({"erro": "Credenciais inválidas"}), 401

        # Verificar senha
        if not admin.check_password(password):
            return jsonify({"erro": "Credenciais inválidas"}), 401

        token = gerar_token_admin(admin)

        return jsonify({
            "msg": "Login realizado com sucesso",
            "token": token,
            "user": {
                "id": admin.id,
                "username": admin.username,
                "email": admin.email,
                "is_superadmin": admin.is_superadmin
            }
        }), 200

    except Exception as e:
        return jsonify({"erro": "Erro interno do servidor"}), 500

@auth_routes.route('/barbearia/login', methods=['POST'])
def barbearia_login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        dominio = data.get('dominio')

        if not email and not dominio:
            return jsonify({"erro": "Email ou domínio são obrigatórios"}), 400

        # Buscar barbearia
        barbearia = None
        if email:
            barbearia = BarbeariaCliente.query.filter_by(email=email).first()
        elif dominio:
            barbearia = BarbeariaCliente.query.filter_by(dominio=dominio).first()

        if not barbearia:
            return jsonify({"erro": "Barbearia não encontrada"}), 404

        if not barbearia.ativo:
            return jsonify({"erro": "Barbearia inativa. Entre em contato com o suporte."}), 400

        # Verificar se a assinatura está expirada
        if barbearia.data_expiracao and barbearia.data_expiracao < datetime.datetime.utcnow():
            return jsonify({"erro": "Assinatura expirada. Renove para continuar usando."}), 400

        token = gerar_token_barbearia(barbearia)

        return jsonify({
            "msg": "Login realizado com sucesso",
            "token": token,
            "barbearia": {
                "id": barbearia.id,
                "nome": barbearia.nome,
                "dominio": barbearia.dominio,
                "email": barbearia.email,
                "plano": barbearia.plano.nome if barbearia.plano else "Free",
                "ativo": barbearia.ativo
            }
        }), 200

    except Exception as e:
        return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500

@auth_routes.route('/barbearia/registrar', methods=['POST'])
def barbearia_registrar():
    """Registro de nova barbearia (onboarding)"""
    try:
        data = request.json
        nome = data.get('nome')
        email = data.get('email')
        telefone = data.get('telefone')
        plano_id = data.get('plano_id', 1)

        if not all([nome, email, telefone]):
            return jsonify({"erro": "Nome, email e telefone são obrigatórios"}), 400

        # Verificar se email já existe
        if BarbeariaCliente.query.filter_by(email=email).first():
            return jsonify({"erro": "Email já cadastrado"}), 400

        # Gerar domínio único
        from utils import gerar_dominio_unico
        dominio = gerar_dominio_unico(nome)

        nova_barbearia = BarbeariaCliente(
            nome=nome,
            email=email,
            telefone=telefone,
            dominio=dominio,
            plano_id=plano_id,
            ativo=True,
            data_expiracao=datetime.datetime.utcnow() + datetime.timedelta(days=7)  # Trial
        )

        db.session.add(nova_barbearia)
        db.session.commit()

        token = gerar_token_barbearia(nova_barbearia)

        return jsonify({
            "msg": "Barbearia criada com sucesso!",
            "token": token,
            "barbearia": {
                "id": nova_barbearia.id,
                "nome": nova_barbearia.nome,
                "dominio": nova_barbearia.dominio,
                "trial_ate": nova_barbearia.data_expiracao.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao criar barbearia: {str(e)}"}), 500

@auth_routes.route('/verificar-token', methods=['POST'])
def verificar_token():
    """Verifica se um token JWT é válido"""
    try:
        token = request.json.get('token')
        if not token:
            return jsonify({"valido": False, "erro": "Token não fornecido"}), 400

        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        return jsonify({"valido": True, "payload": payload}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"valido": False, "erro": "Token expirado"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"valido": False, "erro": "Token inválido"}), 401