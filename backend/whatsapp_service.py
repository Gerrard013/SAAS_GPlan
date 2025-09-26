# whatsapp_service.py
import requests
import logging
from flask import current_app
from models import db, Agendamento, BarbeariaCliente

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.base_url = current_app.config.get('WHATSAPP_BUSINESS_API_URL')
        self.phone_number_id = current_app.config.get('WHATSAPP_BUSINESS_PHONE_NUMBER_ID')
        self.access_token = current_app.config.get('WHATSAPP_BUSINESS_ACCESS_TOKEN')
    
    def enviar_mensagem(self, numero_destino, mensagem):
        """Envia mensagem via WhatsApp Business API"""
        try:
            if not all([self.base_url, self.phone_number_id, self.access_token]):
                logger.warning("WhatsApp Business não configurado")
                return False

            url = f"{self.base_url}/{self.phone_number_id}/messages"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": numero_destino,
                "type": "text",
                "text": {
                    "body": mensagem
                }
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Mensagem enviada para {numero_destino}")
                return True
            else:
                logger.error(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro no WhatsAppService: {str(e)}")
            return False

    def enviar_confirmacao_agendamento(self, agendamento):
        """Envia confirmação de agendamento"""
        try:
            cliente = agendamento.cliente_info
            servico = agendamento.servico_info
            barbeiro = agendamento.barbeiro_info
            barbearia = agendamento.barbearia
            
            mensagem = f"""
✅ *Agendamento Confirmado!*

Olá {cliente.nome}, seu agendamento foi confirmado!

📅 *Data:* {agendamento.horario.strftime('%d/%m/%Y')}
⏰ *Horário:* {agendamento.horario.strftime('%H:%M')}
💈 *Serviço:* {servico.nome}
💇 *Barbeiro:* {barbeiro.nome}
🏪 *Barbearia:* {barbearia.nome}

*Valor:* R$ {servico.preco:.2f}

📍 *Endereço:* [Endereço da barbearia]
📞 *Telefone:* {barbearia.telefone}

⚠️ *Lembretes importantes:*
- Chegue 5 minutos antes do horário
- Cancelamentos com até 2h de antecedência
- Atendimento por ordem de chegada

Obrigado pela preferência! 👏
            """
            
            return self.enviar_mensagem(cliente.telefone, mensagem.strip())
            
        except Exception as e:
            logger.error(f"Erro ao enviar confirmação: {str(e)}")
            return False

    def enviar_lembrete_agendamento(self, agendamento, horas_antes=24):
        """Envia lembrete de agendamento"""
        try:
            cliente = agendamento.cliente_info
            servico = agendamento.servico_info
            
            mensagem = f"""
🔔 *Lembrete de Agendamento*

Olá {cliente.nome}, lembrete do seu agendamento!

💈 *Serviço:* {servico.nome}
📅 *Amanhã às {agendamento.horario.strftime('%H:%M')}*

Não se esqueça do seu horário! 😊

*Barbearia {agendamento.barbearia.nome}*
            """
            
            return self.enviar_mensagem(cliente.telefone, mensagem.strip())
            
        except Exception as e:
            logger.error(f"Erro ao enviar lembrete: {str(e)}")
            return False

    def enviar_confirmacao_assinatura(self, barbearia, plano):
        """Envia confirmação de assinatura/renovação"""
        try:
            mensagem = f"""
🎉 *Assinatura Ativada!*

Olá {barbearia.nome}, 

Sua assinatura do plano *{plano.nome}* foi ativada com sucesso!

📊 *Benefícios do seu plano:*
- {plano.limite_barbeiros} barbeiros
- {plano.limite_agendamentos or 'ilimitados'} agendamentos/mês
- WhatsApp Business integrado

💎 *Valor:* R$ {plano.preco_mensal:.2f}/mês
📅 *Próxima cobrança:* {barbearia.data_expiracao.strftime('%d/%m/%Y')}

Acesse seu dashboard: https://{barbearia.dominio}.gplan.com.br

Obrigado por escolher o GPlan! 💈
            """
            
            return self.enviar_mensagem(barbearia.telefone, mensagem.strip())
            
        except Exception as e:
            logger.error(f"Erro ao enviar confirmação de assinatura: {str(e)}")
            return False

    def enviar_alerta_expiracao(self, barbearia, dias_restantes):
        """Envia alerta de expiração da assinatura"""
        try:
            mensagem = f"""
⚠️ *Assinatura Expirando!*

Olá {barbearia.nome},

Sua assinatura expira em *{dias_restantes} dias*!

Para continuar usando todos os recursos do GPlan, renove sua assinatura.

Acesse: https://gplan.com.br/renovacao

Não perca seus agendamentos e clientes! 🚨
            """
            
            return self.enviar_mensagem(barbearia.telefone, mensagem.strip())
            
        except Exception as e:
            logger.error(f"Erro ao enviar alerta: {str(e)}")
            return False

# Instância global do serviço
whatsapp_service = WhatsAppService()