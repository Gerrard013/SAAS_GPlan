# admin_routes.py
from flask import Blueprint, request, jsonify
from models import db, BarbeariaCliente, Agendamento, PlanoAssinatura, Pagamento, AdminUser
from sqlalchemy import func
from datetime import datetime, timedelta
import jwt
from config import Config

admin_routes = Blueprint('admin_routes', __name__)

def verificar_token_admin():
    """Middleware para verificar token JWT"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@admin_routes.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    auth = verificar_token_admin()
    if not auth:
        return jsonify({"erro": "Token inválido ou expirado"}), 401

    try:
        # Estatísticas gerais
        total_barbearias = BarbeariaCliente.query.count()
        barbearias_ativas = BarbeariaCliente.query.filter_by(ativo=True).count()
        total_agendamentos = Agendamento.query.count()
        
        # Agendamentos últimos 7 dias
        sete_dias_atras = datetime.utcnow() - timedelta(days=7)
        agendamentos_recentes = Agendamento.query.filter(
            Agendamento.data_criacao >= sete_dias_atras
        ).count()

        # Faturamento
        faturamento_mensal = Pagamento.query.filter(
            Pagamento.status == 'pago',
            Pagamento.data_pagamento >= datetime.utcnow().replace(day=1)
        ).with_entities(func.sum(Pagamento.valor)).scalar() or 0

        return jsonify({
            "estatisticas": {
                "total_barbearias": total_barbearias,
                "barbearias_ativas": barbearias_ativas,
                "total_agendamentos": total_agendamentos,
                "agendamentos_7_dias": agendamentos_recentes,
                "faturamento_mensal": float(faturamento_mensal)
            },
            "barbearias_recentes": [
                {
                    "id": b.id,
                    "nome": b.nome,
                    "email": b.email,
                    "data_criacao": b.data_criacao.isoformat(),
                    "plano": b.plano.nome if b.plano else "Free"
                }
                for b in BarbeariaCliente.query.order_by(BarbeariaCliente.data_criacao.desc()).limit(5).all()
            ]
        }), 200

    except Exception as e:
        return jsonify({"erro": "Erro interno do servidor"}), 500

@admin_routes.route('/admin/barbearias', methods=['GET'])
def listar_barbearias():
    auth = verificar_token_admin()
    if not auth:
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20

        barbearias = BarbeariaCliente.query.order_by(
            BarbeariaCliente.data_criacao.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        resultado = {
            "barbearias": [
                {
                    "id": b.id,
                    "nome": b.nome,
                    "email": b.email,
                    "telefone": b.telefone,
                    "dominio": b.dominio,
                    "plano": b.plano.nome if b.plano else "Free",
                    "ativo": b.ativo,
                    "data_criacao": b.data_criacao.isoformat(),
                    "data_expiracao": b.data_expiracao.isoformat() if b.data_expiracao else None,
                    "total_agendamentos": Agendamento.query.filter_by(barbearia_id=b.id).count()
                }
                for b in barbearias.items
            ],
            "total": barbearias.total,
            "paginas": barbearias.pages,
            "pagina_atual": page
        }

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({"erro": "Erro interno do servidor"}), 500

@admin_routes.route('/admin/barbearias/<int:barbearia_id>/ativar', methods=['POST'])
def ativar_barbearia(barbearia_id):
    auth = verificar_token_admin()
    if not auth:
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        barbearia = BarbeariaCliente.query.get(barbearia_id)
        if not barbearia:
            return jsonify({"erro": "Barbearia não encontrada"}), 404

        barbearia.ativo = True
        db.session.commit()

        return jsonify({"msg": "Barbearia ativada com sucesso"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": "Erro interno do servidor"}), 500

@admin_routes.route('/admin/barbearias/<int:barbearia_id>/desativar', methods=['POST'])
def desativar_barbearia(barbearia_id):
    auth = verificar_token_admin()
    if not auth:
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        barbearia = BarbeariaCliente.query.get(barbearia_id)
        if not barbearia:
            return jsonify({"erro": "Barbearia não encontrada"}), 404

        barbearia.ativo = False
        db.session.commit()

        return jsonify({"msg": "Barbearia desativada com sucesso"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": "Erro interno do servidor"}), 500