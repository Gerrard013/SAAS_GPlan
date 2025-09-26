# routes.py
from flask import Blueprint, request, jsonify, g
from models import db, Cliente, Agendamento, Barbeiro, Servico, BarbeariaCliente, PlanoAssinatura, ConfiguracaoBarbearia
from utils import validar_telefone, validar_horario, formatar_telefone
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import logging
from whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)
routes = Blueprint('routes', __name__)

def get_barbearia_id():
    """Helper para obter ID da barbearia do contexto"""
    return getattr(g, 'barbearia_id', 1)

def verificar_limites_plano(barbearia_id):
    """Verifica se a barbearia está dentro dos limites do plano"""
    barbearia = BarbeariaCliente.query.get(barbearia_id)
    if not barbearia or not barbearia.plano:
        return False, "Plano não encontrado"
    
    plano = barbearia.plano
    
    # Verificar limite de barbeiros
    total_barbeiros = Barbeiro.query.filter_by(barbearia_id=barbearia_id, ativo=True).count()
    if total_barbeiros >= plano.limite_barbeiros:
        return False, f"Limite de {plano.limite_barbeiros} barbeiros atingido"
    
    # Verificar limite de agendamentos (mensal)
    if plano.limite_agendamentos:
        inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        agendamentos_mes = Agendamento.query.filter(
            Agendamento.barbearia_id == barbearia_id,
            Agendamento.data_criacao >= inicio_mes
        ).count()
        
        if agendamentos_mes >= plano.limite_agendamentos:
            return False, f"Limite de {plano.limite_agendamentos} agendamentos/mês atingido"
    
    return True, "Dentro dos limites"

# ROTA PARA CRIAR NOVA BARBEARIA
@routes.route('/barbearias/nova', methods=['POST'])
def criar_barbearia():
    try:
        data = request.json
        nome = data.get('nome')
        email = data.get('email')
        telefone = data.get('telefone')
        plano_id = data.get('plano_id', 1)

        if not all([nome, email, telefone]):
            return jsonify({"erro": "Nome, email e telefone são obrigatórios"}), 400

        if not validar_telefone(telefone):
            return jsonify({"erro": "Número de telefone inválido"}), 400

        # Verificar se email já existe
        if BarbeariaCliente.query.filter_by(email=email).first():
            return jsonify({"erro": "Email já cadastrado"}), 400

        # Gerar domínio único
        base_dominio = nome.lower().replace(' ', '-').replace('.', '')
        dominio = base_dominio
        counter = 1
        while BarbeariaCliente.query.filter_by(dominio=dominio).first():
            dominio = f"{base_dominio}-{counter}"
            counter += 1

        nova_barbearia = BarbeariaCliente(
            nome=nome,
            email=email,
            telefone=telefone,
            dominio=dominio,
            plano_id=plano_id,
            data_expiracao=datetime.utcnow() + timedelta(days=7)
        )

        db.session.add(nova_barbearia)
        db.session.flush()

        # Criar serviços padrão
        servicos_padrao = [
            Servico(barbearia_id=nova_barbearia.id, nome="Corte Social", duracao_minutos=30, preco=25.0),
            Servico(barbearia_id=nova_barbearia.id, nome="Barba", duracao_minutos=30, preco=20.0),
            Servico(barbearia_id=nova_barbearia.id, nome="Corte + Barba", duracao_minutos=60, preco=40.0),
        ]
        db.session.add_all(servicos_padrao)

        # Criar barbeiro padrão
        barbeiro_padrao = Barbeiro(
            barbearia_id=nova_barbearia.id,
            nome="Meu Barbeiro",
            especialidade="Cortes e Barbas"
        )
        db.session.add(barbeiro_padrao)

        # Criar configuração padrão
        config_padrao = ConfiguracaoBarbearia(barbearia_id=nova_barbearia.id)
        db.session.add(config_padrao)

        db.session.commit()

        return jsonify({
            "msg": "Barbearia criada com sucesso!",
            "barbearia_id": nova_barbearia.id,
            "dominio": nova_barbearia.dominio,
            "trial_ate": nova_barbearia.data_expiracao.isoformat()
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"erro": "Email ou domínio já existe"}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar barbearia: {str(e)}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# ROTA PARA LISTAR PLANOS
@routes.route('/planos', methods=['GET'])
def listar_planos():
    try:
        planos = PlanoAssinatura.query.all()
        resultado = [{
            "id": p.id,
            "nome": p.nome,
            "preco_mensal": p.preco_mensal,
            "limite_barbeiros": p.limite_barbeiros,
            "limite_agendamentos": p.limite_agendamentos
        } for p in planos]
        
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Erro ao listar planos: {str(e)}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# ROTA PARA LISTAR BARBEIROS
@routes.route('/barbeiros', methods=['GET'])
def listar_barbeiros():
    try:
        barbearia_id = get_barbearia_id()
        barbeiros = Barbeiro.query.filter_by(barbearia_id=barbearia_id, ativo=True).all()
        
        resultado = [{
            "id": b.id, 
            "nome": b.nome, 
            "especialidade": b.especialidade
        } for b in barbeiros]
        
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Erro ao listar barbeiros: {str(e)}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# ROTA PARA LISTAR SERVIÇOS
@routes.route('/servicos', methods=['GET'])
def listar_servicos():
    try:
        barbearia_id = get_barbearia_id()
        servicos = Servico.query.filter_by(barbearia_id=barbearia_id, ativo=True).all()
        
        resultado = [{
            "id": s.id, 
            "nome": s.nome, 
            "duracao_minutos": s.duracao_minutos,
            "preco": s.preco
        } for s in servicos]
        
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Erro ao listar serviços: {str(e)}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# ROTA PARA HORÁRIOS DISPONÍVEIS
@routes.route('/horarios-disponiveis', methods=['GET'])
def horarios_disponiveis():
    try:
        barbearia_id = get_barbearia_id()
        barbeiro_id = request.args.get('barbeiro_id')
        data_str = request.args.get('data')
        
        if not barbeiro_id or not data_str:
            return jsonify({"erro": "Barbeiro ID e data são obrigatórios"}), 400

        # Converter data
        data = datetime.strptime(data_str, '%Y-%m-%d').date()
        
        # Buscar configurações da barbearia
        config = ConfiguracaoBarbearia.query.filter_by(barbearia_id=barbearia_id).first()
        if not config:
            return jsonify({"erro": "Configuração não encontrada"}), 400

        # Buscar agendamentos existentes
        agendamentos = Agendamento.query.filter(
            func.date(Agendamento.horario) == data,
            Agendamento.barbeiro_id == barbeiro_id,
            Agendamento.status == 'confirmado'
        ).all()

        horarios_ocupados = [ag.horario.time() for ag in agendamentos]
        horarios_disponiveis = []

        # Gerar horários baseado na configuração
        hora_atual = datetime.combine(data, config.horario_abertura)
        hora_fim = datetime.combine(data, config.horario_fechamento)
        
        while hora_atual < hora_fim:
            if hora_atual.time() not in horarios_ocupados and hora_atual > datetime.utcnow():
                horarios_disponiveis.append(hora_atual.strftime("%H:%M"))
            hora_atual += timedelta(minutes=config.intervalo_agendamento)

        return jsonify({
            "horarios_disponiveis": horarios_disponiveis
        })

    except ValueError:
        return jsonify({"erro": "Formato de data inválido. Use YYYY-MM-DD"}), 400
    except Exception as e:
        logger.error(f"Erro ao buscar horários: {str(e)}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# ROTA PRINCIPAL DE AGENDAMENTO
@routes.route('/agendar', methods=['POST'])
def agendar():
    try:
        barbearia_id = get_barbearia_id()
        data = request.json
        
        # Verificar se barbearia está ativa
        barbearia = BarbeariaCliente.query.get(barbearia_id)
        if not barbearia or not barbearia.ativo:
            return jsonify({"erro": "Barbearia não está ativa"}), 400
            
        if barbearia.data_expiracao and barbearia.data_expiracao < datetime.utcnow():
            return jsonify({"erro": "Assinatura expirada. Renove para continuar usando."}), 400

        # Verificar limites do plano
        limite_ok, msg_erro = verificar_limites_plano(barbearia_id)
        if not limite_ok:
            return jsonify({"erro": msg_erro}), 400

        nome = data.get('nome')
        telefone = data.get('telefone')
        servico_id = data.get('servico_id')
        horario_str = data.get('horario')
        barbeiro_id = data.get('barbeiro_id')

        if not all([nome, telefone, servico_id, horario_str, barbeiro_id]):
            return jsonify({"erro": "Todos os campos são obrigatórios"}), 400

        if not validar_telefone(telefone):
            return jsonify({"erro": "Número de telefone inválido"}), 400

        horario = validar_horario(horario_str)
        if not horario:
            return jsonify({"erro": "Formato de horário inválido"}), 400

        if horario < datetime.utcnow():
            return jsonify({"erro": "Não é possível agendar para horários no passado"}), 400

        # Verificar conflito de horário
        ag_existente = Agendamento.query.filter_by(
            horario=horario, 
            barbeiro_id=barbeiro_id, 
            status='confirmado'
        ).first()
        
        if ag_existente:
            hora_formatada = horario.strftime("%H:%M")
            return jsonify({"erro": f"Horário {hora_formatada} já agendado"}), 400

        # Criar ou encontrar cliente
        cliente = Cliente.query.filter_by(telefone=telefone, barbearia_id=barbearia_id).first()
        if not cliente:
            cliente = Cliente(
                barbearia_id=barbearia_id,
                nome=nome, 
                telefone=telefone,
                email=data.get('email')
            )
            db.session.add(cliente)
            db.session.flush()

        # Verificar se serviços/barbeiros pertencem à barbearia
        servico = Servico.query.filter_by(id=servico_id, barbearia_id=barbearia_id).first()
        barbeiro = Barbeiro.query.filter_by(id=barbeiro_id, barbearia_id=barbearia_id).first()
        
        if not servico or not barbeiro:
            return jsonify({"erro": "Serviço ou barbeiro inválido"}), 400

        # Criar agendamento
        agendamento = Agendamento(
            barbearia_id=barbearia_id,
            cliente_id=cliente.id,
            barbeiro_id=barbeiro_id,
            servico_id=servico_id,
            horario=horario,
            status='confirmado',
            observacoes=data.get('observacoes')
        )
        
        db.session.add(agendamento)
        db.session.commit()

        # ✅ INTEGRAÇÃO WHATSAPP
        whatsapp_enviado = False
        try:
            config = ConfiguracaoBarbearia.query.filter_by(barbearia_id=barbearia_id).first()
            
            if config and config.whatsapp_ativo and config.confirmacao_automatica:
                whatsapp_enviado = whatsapp_service.enviar_confirmacao_agendamento(
                    agendamento, cliente, barbearia
                )
                logger.info(f"📱 WhatsApp enviado: {whatsapp_enviado}")
        except Exception as e:
            logger.error(f"❌ Erro ao enviar WhatsApp: {str(e)}")

        return jsonify({
            "msg": "Agendamento realizado com sucesso!",
            "id": agendamento.id,
            "codigo": f"AG{agendamento.id:06d}",
            "cliente": cliente.nome,
            "servico": servico.nome,
            "barbeiro": barbeiro.nome,
            "horario": horario.isoformat(),
            "whatsapp_enviado": whatsapp_enviado
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro no agendamento: {str(e)}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# ROTA PARA LISTAR AGENDAMENTOS
@routes.route('/agendamentos', methods=['GET'])
def listar_agendamentos():
    try:
        barbearia_id = get_barbearia_id()
        
        # Filtros
        data = request.args.get('data')
        status = request.args.get('status')
        
        query = Agendamento.query.filter_by(barbearia_id=barbearia_id)
        
        if data:
            data_obj = datetime.strptime(data, '%Y-%m-%d').date()
            query = query.filter(func.date(Agendamento.horario) == data_obj)
        
        if status:
            query = query.filter_by(status=status)
        
        agendamentos = query.order_by(Agendamento.horario.asc()).all()
        
        resultado = []
        for ag in agendamentos:
            resultado.append({
                "id": ag.id,
                "cliente": ag.cliente_info.nome,
                "telefone": formatar_telefone(ag.cliente_info.telefone),
                "email": ag.cliente_info.email,
                "servico": ag.servico_info.nome,
                "barbeiro": ag.barbeiro_info.nome,
                "horario": ag.horario.isoformat(),
                "status": ag.status,
                "observacoes": ag.observacoes
            })
        
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Erro ao listar agendamentos: {str(e)}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# ROTA PARA CANCELAR AGENDAMENTO
@routes.route('/agendamento/<int:agendamento_id>/cancelar', methods=['POST'])
def cancelar_agendamento(agendamento_id):
    try:
        barbearia_id = get_barbearia_id()
        
        agendamento = Agendamento.query.filter_by(
            id=agendamento_id, 
            barbearia_id=barbearia_id
        ).first()
        
        if not agendamento:
            return jsonify({"erro": "Agendamento não encontrado"}), 404
        
        if agendamento.status == 'cancelado':
            return jsonify({"erro": "Agendamento já está cancelado"}), 400
        
        agendamento.status = 'cancelado'
        db.session.commit()
        
        # ✅ WHATSAPP CANCELAMENTO
        try:
            config = ConfiguracaoBarbearia.query.filter_by(barbearia_id=barbearia_id).first()
            barbearia = BarbeariaCliente.query.get(barbearia_id)
            
            if config and config.whatsapp_ativo:
                whatsapp_service.enviar_cancelamento(
                    agendamento, agendamento.cliente_info, barbearia
                )
        except Exception as e:
            logger.error(f"Erro WhatsApp cancelamento: {str(e)}")
        
        return jsonify({
            "msg": "Agendamento cancelado com sucesso",
            "agendamento_id": agendamento_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao cancelar agendamento: {str(e)}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# ROTA PARA ESTATÍSTICAS
@routes.route('/estatisticas', methods=['GET'])
def estatisticas():
    try:
        barbearia_id = get_barbearia_id()
        
        # Agendamentos do mês
        inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        agendamentos_mes = Agendamento.query.filter(
            Agendamento.barbearia_id == barbearia_id,
            Agendamento.data_criacao >= inicio_mes
        ).count()
        
        # Clientes cadastrados
        total_clientes = Cliente.query.filter_by(barbearia_id=barbearia_id).count()
        
        # Agendamentos de hoje
        hoje = datetime.utcnow().date()
        agendamentos_hoje = Agendamento.query.filter(
            Agendamento.barbearia_id == barbearia_id,
            func.date(Agendamento.horario) == hoje,
            Agendamento.status == 'confirmado'
        ).count()
        
        return jsonify({
            "agendamentos_mes": agendamentos_mes,
            "total_clientes": total_clientes,
            "agendamentos_hoje": agendamentos_hoje,
            "barbeiros_ativos": Barbeiro.query.filter_by(barbearia_id=barbearia_id, ativo=True).count()
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {str(e)}")
        return jsonify({"erro": "Erro interno do servidor"}), 500

# ROTA PARA DASHBOARD
@routes.route('/api/dashboard-data', methods=['GET'])
def dashboard_data():
    try:
        barbearia_id = get_barbearia_id()
        
        # Faturamento do mês (simulado)
        agendamentos_mes = Agendamento.query.filter(
            Agendamento.barbearia_id == barbearia_id,
            Agendamento.data_criacao >= datetime.utcnow().replace(day=1)
        ).all()
        
        faturamento_mes = sum(ag.servico_info.preco for ag in agendamentos_mes if ag.status == 'confirmado')
        
        # Agendamentos de hoje
        hoje = datetime.utcnow().date()
        agendamentos_hoje = Agendamento.query.filter(
            Agendamento.barbearia_id == barbearia_id,
            func.date(Agendamento.horario) == hoje,
            Agendamento.status == 'confirmado'
        ).all()
        
        agendamentos_hoje_lista = []
        for ag in agendamentos_hoje:
            agendamentos_hoje_lista.append({
                "horario": ag.horario.strftime("%H:%M"),
                "cliente": ag.cliente_info.nome,
                "servico": ag.servico_info.nome,
                "barbeiro": ag.barbeiro_info.nome
            })
        
        return jsonify({
            "faturamento_mes": faturamento_mes,
            "agendamentos_hoje": len(agendamentos_hoje),
            "total_clientes": Cliente.query.filter_by(barbearia_id=barbearia_id).count(),
            "agendamentos_hoje_lista": agendamentos_hoje_lista
        })
        
    except Exception as e:
        logger.error(f"Erro no dashboard: {str(e)}")
        return jsonify({"erro": "Erro interno"}), 500