# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
from sqlalchemy.orm import validates

db = SQLAlchemy()

class BarbeariaCliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    cnpj = db.Column(db.String(18), unique=True)
    dominio = db.Column(db.String(100), unique=True)
    plano_id = db.Column(db.Integer, db.ForeignKey('plano_assinatura.id'))
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_expiracao = db.Column(db.DateTime)
    
    # Relacionamentos
    barbeiros = db.relationship('Barbeiro', backref='barbearia', lazy=True)
    agendamentos = db.relationship('Agendamento', backref='barbearia', lazy=True)
    clientes = db.relationship('Cliente', backref='barbearia', lazy=True)
    configuracao = db.relationship('ConfiguracaoBarbearia', backref='barbearia', uselist=False)
    pagamentos = db.relationship('Pagamento', backref='barbearia', lazy=True)

    def __repr__(self):
        return f'<Barbearia {self.nome} ({self.dominio})>'
    
    @validates('email')
    def validate_email(self, key, email):
        if not '@' in email:
            raise ValueError("Email inválido")
        return email.lower()
    
    @validates('telefone')
    def validate_telefone(self, key, telefone):
        if len(telefone) < 10:
            raise ValueError("Telefone deve ter pelo menos 10 dígitos")
        return telefone

class PlanoAssinatura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    preco_mensal = db.Column(db.Float, nullable=False)
    limite_barbeiros = db.Column(db.Integer, nullable=False)
    limite_agendamentos = db.Column(db.Integer)
    recursos = db.Column(db.Text)
    
    barbearias = db.relationship('BarbeariaCliente', backref='plano', lazy=True)
    pagamentos = db.relationship('Pagamento', backref='plano', lazy=True)

    def __repr__(self):
        return f'<Plano {self.nome} - R$ {self.preco_mensal}>'
    
    def get_recursos(self):
        return json.loads(self.recursos) if self.recursos else []
    
    @validates('preco_mensal')
    def validate_preco(self, key, preco):
        if preco < 0:
            raise ValueError("Preço não pode ser negativo")
        return preco

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_superadmin = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)

    def __repr__(self):
        return f'<AdminUser {self.username}>'

    def set_password(self, password):
        if len(password) < 6:
            raise ValueError("Senha deve ter pelo menos 6 caracteres")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @validates('email')
    def validate_email(self, key, email):
        if not '@' in email:
            raise ValueError("Email inválido")
        return email.lower()

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barbearia_id = db.Column(db.Integer, db.ForeignKey('barbearia_cliente.id'), nullable=False)
    nome = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    telefone = db.Column(db.String(20), nullable=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    observacoes = db.Column(db.Text)
    
    agendamentos = db.relationship('Agendamento', backref='cliente_info', lazy=True)

    def __repr__(self):
        return f'<Cliente {self.nome} ({self.telefone})>'
    
    @validates('telefone')
    def validate_telefone(self, key, telefone):
        numeros = ''.join(filter(str.isdigit, telefone))
        if len(numeros) < 10:
            raise ValueError("Telefone inválido")
        return telefone

class Barbeiro(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    barbearia_id = db.Column(db.Integer, db.ForeignKey('barbearia_cliente.id'), nullable=False)
    nome = db.Column(db.String(50), nullable=False)
    especialidade = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    foto_url = db.Column(db.String(200))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    comissao_percentual = db.Column(db.Float, default=50.0)
    
    agendamentos = db.relationship('Agendamento', backref='barbeiro_info', lazy=True)

    def __repr__(self):
        return f'<Barbeiro {self.nome}>'

class Servico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barbearia_id = db.Column(db.Integer, db.ForeignKey('barbearia_cliente.id'), nullable=False)
    nome = db.Column(db.String(50), nullable=False)
    duracao_minutos = db.Column(db.Integer, nullable=False, default=30)
    preco = db.Column(db.Float, nullable=False, default=0.0)
    ativo = db.Column(db.Boolean, default=True)
    descricao = db.Column(db.Text)
    
    agendamentos = db.relationship('Agendamento', backref='servico_info', lazy=True)

    def __repr__(self):
        return f'<Servico {self.nome} - R$ {self.preco}>'
    
    @validates('preco')
    def validate_preco(self, key, preco):
        if preco < 0:
            raise ValueError("Preço não pode ser negativo")
        return preco
    
    @validates('duracao_minutos')
    def validate_duracao(self, key, duracao):
        if duracao < 15:
            raise ValueError("Duração mínima de 15 minutos")
        return duracao

class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barbearia_id = db.Column(db.Integer, db.ForeignKey('barbearia_cliente.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    barbeiro_id = db.Column(db.Integer, db.ForeignKey('barbeiro.id'), nullable=False) 
    servico_id = db.Column(db.Integer, db.ForeignKey('servico.id'), nullable=False)
    horario = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='confirmado')
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    observacoes = db.Column(db.Text)

    def __repr__(self):
        return f'<Agendamento #{self.id} - {self.horario.strftime("%d/%m/%Y %H:%M")}>'
    
    @validates('horario')
    def validate_horario(self, key, horario):
        if horario < datetime.utcnow():
            raise ValueError("Não é possível agendar para o passado")
        return horario

class ConfiguracaoBarbearia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barbearia_id = db.Column(db.Integer, db.ForeignKey('barbearia_cliente.id'), nullable=False)
    
    # Configurações WhatsApp
    whatsapp_ativo = db.Column(db.Boolean, default=True)
    whatsapp_token = db.Column(db.String(500))
    whatsapp_numero = db.Column(db.String(20))
    
    # Horários de funcionamento
    horario_abertura = db.Column(db.Time, default=lambda: datetime.strptime('08:00', '%H:%M').time())
    horario_fechamento = db.Column(db.Time, default=lambda: datetime.strptime('18:00', '%H:%M').time())
    intervalo_agendamento = db.Column(db.Integer, default=30)
    
    # Lembretes automáticos
    lembrete_24h = db.Column(db.Boolean, default=True)
    lembrete_1h = db.Column(db.Boolean, default=True)
    confirmacao_automatica = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<ConfiguracaoBarbearia {self.barbearia.nome}>'

class Pagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barbearia_id = db.Column(db.Integer, db.ForeignKey('barbearia_cliente.id'), nullable=False)
    plano_id = db.Column(db.Integer, db.ForeignKey('plano_assinatura.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    metodo = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pendente')
    id_externo = db.Column(db.String(100))  # ID do Mercado Pago
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_pagamento = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Pagamento #{self.id} - R$ {self.valor} - {self.status}>'

class LogSistema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nivel = db.Column(db.String(20), nullable=False)  # info, warning, error
    mensagem = db.Column(db.Text, nullable=False)
    barbearia_id = db.Column(db.Integer, db.ForeignKey('barbearia_cliente.id'), nullable=True)
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Log {self.nivel} - {self.mensagem[:50]}>'