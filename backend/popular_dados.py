# popular_dados.py
from app import app, db
from models import BarbeariaCliente, Cliente, Barbeiro, Servico, Agendamento
from datetime import datetime, timedelta

def popular_dados_teste():
    with app.app_context():
        # Criar barbearia de teste
        barbearia = BarbeariaCliente.query.filter_by(nome="Barbearia do Zé").first()
        if not barbearia:
            barbearia = BarbeariaCliente(
                nome="Barbearia do Zé",
                email="ze@barbearia.com",
                telefone="11999999999",
                dominio="ze-barbearia",
                plano_id=2,
                ativo=True
            )
            db.session.add(barbearia)
            db.session.commit()
            print("✅ Barbearia de teste criada")

        # Criar barbeiros
        barbeiros = [
            Barbeiro(nome="João Silva", especialidade="Cortes modernos", barbearia_id=barbearia.id),
            Barbeiro(nome="Pedro Santos", especialidade="Barba e bigode", barbearia_id=barbearia.id),
        ]
        
        for barbeiro in barbeiros:
            if not Barbeiro.query.filter_by(nome=barbeiro.nome, barbearia_id=barbearia.id).first():
                db.session.add(barbeiro)
        
        db.session.commit()
        print("✅ Barbeiros criados")

        # Criar serviços
        servicos = [
            Servico(nome="Corte Social", preco=30.0, duracao_minutos=30, barbearia_id=barbearia.id),
            Servico(nome="Barba Completa", preco=25.0, duracao_minutos=30, barbearia_id=barbearia.id),
            Servico(nome="Corte + Barba", preco=50.0, duracao_minutos=60, barbearia_id=barbearia.id),
        ]
        
        for servico in servicos:
            if not Servico.query.filter_by(nome=servico.nome, barbearia_id=barbearia.id).first():
                db.session.add(servico)
        
        db.session.commit()
        print("✅ Serviços criados")

        # Criar clientes
        clientes = [
            Cliente(nome="Carlos Silva", telefone="11988887777", barbearia_id=barbearia.id),
            Cliente(nome="Maria Santos", telefone="11977776666", barbearia_id=barbearia.id),
            Cliente(nome="João Pereira", telefone="11966665555", barbearia_id=barbearia.id),
        ]
        
        for cliente in clientes:
            if not Cliente.query.filter_by(telefone=cliente.telefone, barbearia_id=barbearia.id).first():
                db.session.add(cliente)
        
        db.session.commit()
        print("✅ Clientes criados")

        # Criar agendamentos (alguns para hoje)
        hoje = datetime.now().date()
        barbeiro = Barbeiro.query.filter_by(barbearia_id=barbearia.id).first()
        servico = Servico.query.filter_by(barbearia_id=barbearia.id).first()
        cliente = Cliente.query.filter_by(barbearia_id=barbearia.id).first()

        if barbeiro and servico and cliente:
            # Agendamentos para hoje
            agendamentos_hoje = [
                Agendamento(
                    barbearia_id=barbearia.id,
                    cliente_id=cliente.id,
                    barbeiro_id=barbeiro.id,
                    servico_id=servico.id,
                    horario=datetime.combine(hoje, datetime.strptime("10:00", "%H:%M").time()),
                    status="confirmado"
                ),
                Agendamento(
                    barbearia_id=barbearia.id,
                    cliente_id=cliente.id,
                    barbeiro_id=barbeiro.id,
                    servico_id=servico.id,
                    horario=datetime.combine(hoje, datetime.strptime("14:00", "%H:%M").time()),
                    status="confirmado"
                ),
            ]
            
            # Agendamentos para outros dias (faturamento)
            for i in range(15):
                agendamento = Agendamento(
                    barbearia_id=barbearia.id,
                    cliente_id=cliente.id,
                    barbeiro_id=barbeiro.id,
                    servico_id=servico.id,
                    horario=datetime.now() - timedelta(days=i),
                    status="realizado"
                )
                db.session.add(agendamento)
            
            db.session.commit()
            print("✅ Agendamentos criados")

        print("🎉 Dados de teste criados com sucesso!")
        print(f"📊 Agora o dashboard mostrará dados reais!")

if __name__ == "__main__":
    popular_dados_teste()