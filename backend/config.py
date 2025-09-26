import os

class Config:
    # -------------------- Banco de Dados --------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///barbearia_saas.db"  # fallback SQLite local
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "chave_secreta_super_segura_2024"
    )

    # -------------------- Mercado Pago --------------------
    MERCADO_PAGO_ACCESS_TOKEN = os.environ.get(
        'MERCADO_PAGO_ACCESS_TOKEN',
        'TEST-XXX'  # token de teste padrão
    )
    MERCADO_PAGO_WEBHOOK_SECRET = os.environ.get(
        'MERCADO_PAGO_WEBHOOK_SECRET',
        ''
    )

    # -------------------- WhatsApp Business API --------------------
    WHATSAPP_BUSINESS_API_URL = os.environ.get(
        'WHATSAPP_BUSINESS_API_URL',
        'https://graph.facebook.com/v17.0'
    )
    WHATSAPP_BUSINESS_PHONE_NUMBER_ID = os.environ.get(
        'WHATSAPP_BUSINESS_PHONE_NUMBER_ID',
        ''  # colocar ID do número do WhatsApp Business
    )
    WHATSAPP_BUSINESS_ACCESS_TOKEN = os.environ.get(
        'WHATSAPP_BUSINESS_ACCESS_TOKEN',
        ''  # colocar token de acesso do WhatsApp Business
    )

    # -------------------- URLs do Sistema --------------------
    SITE_URL = os.environ.get(
        'SITE_URL',
        'http://localhost:5000'  # URL local de desenvolvimento
    )

    # -------------------- Configurações Gerais --------------------
    DEBUG = os.environ.get('DEBUG', 'True').lower() in ['true', '1', 'yes']