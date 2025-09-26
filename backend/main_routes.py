# routes.py
from flask import Blueprint, request, jsonify, g
from models import db, BarbeariaCliente, Agendamento, Barbeiro, Servico, Cliente, ConfiguracaoBarbearia
from datetime import datetime, timedelta
import json

routes = Blueprint('routes', __name__)

def verificar_barbearia():
    """Middleware para verificar se a barbearia existe e está ativa"""
    barbearia_id = request.headers.get('X-Barbearia-ID')
    if not barbearia_id:
        return None
    
    barbearia = BarbeariaCliente.query.get(barbearia_id)
    if not barbearia or not barbearia.ativo:
        return None
    
    return barbearia

# -------------------- ROTAS PÚBLICAS --------------------

@routes.route('/api/barbearias/<dominio>', methods=['GET'])
def info_barbearia(dominio):
    """Informações públicas da barbearia para agendamento"""
    try:
        barbearia = BarbeariaCliente.query.filter_by(dominio=dominio, ativo=True).first()
        if not barbearia:
            return jsonify({"erro": "Barbearia não encontrada"}), 404

        # Verificar se a assinatura está ativa
        if barbearia.data_expiracao and barbearia.data_expiracao < datetime.utcnow():
            return jsonify({"erro": "Barbearia inativa"}), 400

        barbeiros = Barbeiro.query.filter_by(barbearia_id=barbearia.id, ativo=True).all()
        servicos = Servico.query.filter_by(barbearia_id=barbearia.id, ativo=True).all()
        config = ConfiguracaoBarbearia.query.filter_by(barbearia_id=barbearia.id).first()

        return jsonify({
            "barbearia": {
                "id": barbearia.id,
                "nome": barbearia.nome,
                "telefone": barbearia.telefone,
                "dominio": barbearia.dominio
            },
            "configuracao": {
                "horario_abertura": config.horario_abertura.strftime('%H:%M') if config else '08:00',
                "horario_fechamento": config.horario_fechamento.strftime('%H:%M') if config else '18:00',
                "intervalo_agendamento": config.intervalo_agendamento if config else 30
            },
            "barbeiros": [
                {
                    "id": b.id,
                    "nome": b.nome,
                    "especialidade": b.especialidade,
                    "foto_url": b.foto_url
                }
                for b in barbeiros
            ],
            "servicos": [
                {
                    "id": s.id,
                    "nome": s.nome,
                    "duracao": s.duracao_minutos,
                    "preco": s.preco,
                    "descricao": s.descricao
                }
                for s in servicos
            ]
        }), 200

    except Exception as e:
        return jsonify({"erro": "Erro interno do servidor"}), 500

@routes.route('/api/agendamentos', methods=['POST'])
def criar_agendamento():
    """Criar novo agendamento (público)"""
    try:
        data = request.json
        barbearia_id = data.get('barbearia_id')
        cliente_nome = data.get('cliente_nome')
        cliente_telefone = data.get('cliente_telefone')
        barbeiro_id = data.get('barbeiro_id')
        servico_id = data.get('servico_id')
        horario = data.get('horario')

        if not all([barbearia_id, cliente_nome, cliente_telefone, barbeiro_id, servico_id, horario]):
            return jsonify({"erro": "Dados incompletos"}), 400

        # Verificar barbearia
        barbearia = BarbeariaCliente.query.get(barbearia_id)
        if not barbearia or not barbearia.ativo:
            return jsonify({"erro": "Barbearia não encontrada"}), 404

        # Verificar se a assinatura está ativa
        if barbearia.data_expiracao and barbearia.data_expiracao < datetime.utcnow():
            return jsonify({"erro": "Barbearia inativa"}), 400

        # Verificar barbeiro e serviço
        barbeiro = Barbeiro.query.filter_by(id=barbeiro_id, barbearia_id=barbearia_id).first()
        servico = Servico.query.filter_by(id=servico_id, barbearia_id=barbearia_id).first()
        
        if not barbeiro or not servico:
            return jsonify({"erro": "Barbeiro ou serviço inválido"}), 400

        # Converter horário
        horario_dt = datetime.fromisoformat(horario.replace('Z', '+00:00'))

        # Verificar conflito de horário
        conflito = Agendamento.query.filter_by(
            barbearia_id=barbearia_id,
            barbeiro_id=barbeiro_id,
            horario=horario_dt
        ).first()

        if conflito:
            return jsonify({"erro": "Horário indisponível"}), 400

        # Buscar ou criar cliente
        cliente = Cliente.query.filter_by(
            barbearia_id=barbearia_id,
            telefone=cliente_telefone
        ).first()

        if not cliente:
            cliente = Cliente(
                barbearia_id=barbearia_id,
                nome=cliente_nome,
                telefone=cliente_telefone
            )
            db.session.add(cliente)
            db.session.flush()

        # Criar agendamento
        agendamento = Agendamento(
            barbearia_id=barbearia_id,
            cliente_id=cliente.id,
            barbeiro_id=barbeiro_id,
            servico_id=servico_id,
            horario=horario_dt,
            status='confirmado'
        )

        db.session.add(agendamento)
        db.session.commit()

        # Enviar confirmação por WhatsApp (se configurado)
        try:
            from whatsapp_service import whatsapp_service
            whatsapp_service.enviar_confirmacao_agendamento(agendamento)
        except Exception as e:
            print(f"Erro ao enviar WhatsApp: {e}")

        return jsonify({
            "msg": "Agendamento criado com sucesso",
            "agendamento_id": agendamento.id,
            "codigo": f"#{agendamento.id:06d}"
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao criar agendamento: {str(e)}"}), 500

@routes.route('/api/barbearias/<dominio>/horarios-disponiveis', methods=['GET'])
def horarios_disponiveis(dominio):
    """Buscar horários disponíveis para agendamento"""
    try:
        data_str = request.args.get('data')
        barbeiro_id = request.args.get('barbeiro_id')
        
        if not data_str:
            return jsonify({"erro": "Data é obrigatória"}), 400

        data = datetime.strptime(data_str, '%Y-%m-%d').date()
        
        barbearia = BarbeariaCliente.query.filter_by(dominio=dominio, ativo=True).first()
        if not barbearia:
            return jsonify({"erro": "Barbearia não encontrada"}), 404

        config = ConfiguracaoBarbearia.query.filter_by(barbearia_id=barbearia.id).first()
        if not config:
            return jsonify({"erro": "Configuração não encontrada"}), 404

        # Gerar horários do dia
        horarios = []
        hora_atual = datetime.combine(data, config.horario_abertura)
        fechamento = datetime.combine(data, config.horario_fechamento)

        while hora_atual < fechamento:
            # Verificar se horário está disponível
            conflito = Agendamento.query.filter_by(
                barbearia_id=barbearia.id,
                barbeiro_id=barbeiro_id,
                horario=hora_atual
            ).first()

            if not conflito and hora_atual > datetime.utcnow():
                horarios.append(hora_atual.strftime('%H:%M'))

            hora_atual += timedelta(minutes=config.intervalo_agendamento)

        return jsonify({"horarios": horarios}), 200

    except Exception as e:
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

# -------------------- ROTAS PRIVADAS (DASHBOARD) --------------------

@routes.route('/api/dashboard/<int:barbearia_id>/estatisticas', methods=['GET'])
def dashboard_estatisticas(barbearia_id):
    """Estatísticas do dashboard da barbearia"""
    barbearia = verificar_barbearia()
    if not barbearia or barbearia.id != barbearia_id:
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        hoje = datetime.utcnow().date()
        inicio_mes = hoje.replace(day=1)
        
        # Agendamentos do dia
        agendamentos_hoje = Agendamento.query.filter(
            Agendamento.barbearia_id == barbearia_id,
            db.func.date(Agendamento.horario) == hoje
        ).count()

        # Faturamento do mês
        faturamento_mes = db.session.query(db.func.sum(Servico.preco)).join(
            Agendamento, Agendamento.servico_id == Servico.id
        ).filter(
            Agendamento.barbearia_id == barbearia_id,
            Agendamento.horario >= inicio_mes,
            Agendamento.status == 'confirmado'
        ).scalar() or 0

        # Clientes novos este mês
        clientes_novos = Cliente.query.filter(
            Cliente.barbearia_id == barbearia_id,
            Cliente.data_cadastro >= inicio_mes
        ).count()

        return jsonify({
            "agendamentos_hoje": agendamentos_hoje,
            "faturamento_mes": float(faturamento_mes),
            "clientes_novos": clientes_novos,
            "barbeiros_ativos": Barbeiro.query.filter_by(
                barbearia_id=barbearia_id, ativo=True
            ).count()
        }), 200

    except Exception as e:
        return jsonify({"erro": "Erro interno"}), 500

@routes.route('/api/barbearias/<int:barbearia_id>/agendamentos', methods=['GET'])
def listar_agendamentos(barbearia_id):
    """Listar agendamentos da barbearia"""
    barbearia = verificar_barbearia()
    if not barbearia or barbearia.id != barbearia_id:
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        data = request.args.get('data')
        query = Agendamento.query.filter_by(barbearia_id=barbearia_id)
        
        if data:
            data_obj = datetime.strptime(data, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Agendamento.horario) == data_obj)

        agendamentos = query.order_by(Agendamento.horario.asc()).all()

        return jsonify({
            "agendamentos": [
                {
                    "id": a.id,
                    "cliente": a.cliente_info.nome,
                    "barbeiro": a.barbeiro_info.nome,
                    "servico": a.servico_info.nome,
                    "horario": a.horario.isoformat(),
                    "status": a.status,
                    "telefone": a.cliente_info.telefone
                }
                for a in agendamentos
            ]
        }), 200

    except Exception as e:
        return jsonify({"erro": "Erro interno"}), 500

@routes.route('/api/barbearias/<int:barbearia_id>/agendamentos/<int:agendamento_id>', methods=['PUT'])
def atualizar_agendamento(barbearia_id, agendamento_id):
    """Atualizar status do agendamento"""
    barbearia = verificar_barbearia()
    if not barbearia or barbearia.id != barbearia_id:
        return jsonify({"erro": "Não autorizado"}), 401

    try:
        data = request.json
        agendamento = Agendamento.query.filter_by(
            id=agendamento_id, barbearia_id=barbearia_id
        ).first()

        if not agendamento:
            return jsonify({"erro": "Agendamento não encontrado"}), 404

        if 'status' in data:
            agendamento.status = data['status']

        db.session.commit()

        return jsonify({"msg": "Agendamento atualizado"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": "Erro interno"}), 500