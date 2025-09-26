# utils.py
import random
import string
from datetime import datetime, timedelta
from models import db, BarbeariaCliente

def gerar_dominio_unico(nome_barbearia):
    """Gera um domínio único baseado no nome da barbearia"""
    base = nome_barbearia.lower().replace(' ', '-')
    base = ''.join(c for c in base if c.isalnum() or c == '-')
    base = base[:30]  # Limitar tamanho
    
    dominio = base
    tentativas = 0
    
    while BarbeariaCliente.query.filter_by(dominio=dominio).first() and tentativas < 10:
        sufixo = ''.join(random.choices(string.digits, k=3))
        dominio = f"{base}-{sufixo}"
        tentativas += 1
    
    if tentativas == 10:
        # Fallback: usar timestamp
        dominio = f"{base}-{int(datetime.now().timestamp())}"
    
    return dominio

def validar_horario_funcionamento(horario, config_barbearia):
    """Valida se um horário está dentro do funcionamento da barbearia"""
    if not config_barbearia:
        return True
    
    hora_agendamento = horario.time()
    return (config_barbearia.horario_abertura <= hora_agendamento <= 
            config_barbearia.horario_fechamento)

def calcular_proximo_horario_disponivel(barbeiro_id, barbearia_id, duracao_minutos=30):
    """Calcula o próximo horário disponível para um barbeiro"""
    from models import Agendamento, ConfiguracaoBarbearia
    
    agora = datetime.now()
    config = ConfiguracaoBarbearia.query.filter_by(barbearia_id=barbearia_id).first()
    
    if not config:
        return agora.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    
    # Começar no próximo intervalo
    intervalo = config.intervalo_agendamento
    minutos_ate_proximo = intervalo - (agora.minute % intervalo)
    horario_candidato = agora.replace(second=0, microsecond=0) + timedelta(minutes=minutos_ate_proximo)
    
    # Verificar horário de funcionamento
    while not validar_horario_funcionamento(horario_candidato, config):
        horario_candidato += timedelta(minutes=intervalo)
        # Se passar do fechamento, ir para o próximo dia
        if horario_candidato.time() > config.horario_fechamento:
            proximo_dia = horario_candidato.date() + timedelta(days=1)
            horario_candidato = datetime.combine(proximo_dia, config.horario_abertura)
    
    # Verificar conflitos
    while True:
        conflito = Agendamento.query.filter_by(
            barbeiro_id=barbeiro_id,
            horario=horario_candidato
        ).first()
        
        if not conflito:
            break
            
        horario_candidato += timedelta(minutes=intervalo)
        
        # Verificar se ainda está no horário de funcionamento
        if not validar_horario_funcionamento(horario_candidato, config):
            proximo_dia = horario_candidato.date() + timedelta(days=1)
            horario_candidato = datetime.combine(proximo_dia, config.horario_abertura)
    
    return horario_candidato

def formatar_telefone(telefone):
    """Formata número de telefone para exibição"""
    if not telefone:
        return ""
    
    # Remover caracteres não numéricos
    numeros = ''.join(filter(str.isdigit, telefone))
    
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    else:
        return telefone

def gerar_codigo_confirmacao():
    """Gera código de confirmação para agendamentos"""
    return ''.join(random.choices(string.digits, k=6))

def calcular_tempo_restante_trial(barbearia):
    """Calcula dias restantes do trial"""
    if not barbearia.data_expiracao:
        return 0
    
    hoje = datetime.now().date()
    expiracao = barbearia.data_expiracao.date()
    dias_restantes = (expiracao - hoje).days
    
    return max(0, dias_restantes)