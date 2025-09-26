// Constantes globais
let SERVICOS = [];
let BARBEIROS = [];
let AGENDAMENTOS = [];
let BARBEARIA_ID = 1; // Em produção, isso viria do login

// Constantes DOM
const form = document.getElementById('formAgendamento');
const listaHorarios = document.getElementById('listaHorarios');
const horariosContainer = document.getElementById('horariosContainer');
const listaAgendamentos = document.getElementById('listaAgendamentos');
const contador = document.getElementById('contador');

// Função para mostrar toast
function mostrarToast(mensagem, tipo) {
    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    toast.textContent = mensagem;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('mostrar'), 100);
    setTimeout(() => {
        toast.classList.remove('mostrar');
        setTimeout(() => document.body.removeChild(toast), 300);
    }, 3000);
}

// Carregar serviços do backend
async function carregarServicos() {
    try {
        const res = await fetch(`http://localhost:5000/servicos?barbearia_id=${BARBEARIA_ID}`);
        if (!res.ok) throw new Error('Erro ao carregar serviços');
        
        SERVICOS = await res.json();
        const listaServicos = document.getElementById('listaServicos');
        listaServicos.innerHTML = '';
        
        SERVICOS.forEach(servico => {
            const li = document.createElement('li');
            li.className = 'servico';
            li.setAttribute('data-id', servico.id);
            li.innerHTML = `
                <strong>${servico.nome}</strong>
                <span class="servico-preco">R$ ${servico.preco.toFixed(2)}</span>
            `;
            li.addEventListener('click', () => selecionarServico(servico.id));
            listaServicos.appendChild(li);
        });
    } catch (error) {
        console.error("Erro ao carregar serviços:", error);
        mostrarToast("Erro ao carregar serviços.", 'erro');
    }
}

// Carregar barbeiros do backend
async function carregarBarbeiros() {
    try {
        const res = await fetch(`http://localhost:5000/barbeiros?barbearia_id=${BARBEARIA_ID}`);
        if (!res.ok) throw new Error('Erro ao carregar barbeiros');
        
        BARBEIROS = await res.json();
        const selectBarbeiro = document.getElementById('barbeiroSelecionado');
        
        selectBarbeiro.innerHTML = '<option value="" disabled selected>Escolha o seu Barbeiro</option>';
        BARBEIROS.forEach(barbeiro => {
            const option = document.createElement('option');
            option.value = barbeiro.id;
            option.textContent = barbeiro.nome + (barbeiro.especialidade ? ` - ${barbeiro.especialidade}` : '');
            selectBarbeiro.appendChild(option);
        });
        
    } catch (error) {
        console.error("Erro ao carregar barbeiros:", error);
        mostrarToast("Erro ao carregar a lista de profissionais.", 'erro');
    }
}

// Carregar horários disponíveis
async function carregarHorarios() {
    const data = document.getElementById('data').value;
    const barbeiroId = document.getElementById('barbeiroSelecionado').value;
    const servicoId = document.getElementById('servicoSelecionadoId').value;
    
    listaHorarios.innerHTML = '';
    document.getElementById('hora').value = '';

    if (!data || !barbeiroId || !servicoId) {
        horariosContainer.style.display = 'none';
        return;
    }

    try {
        const res = await fetch(
            `http://localhost:5000/horarios-disponiveis?barbearia_id=${BARBEARIA_ID}&barbeiro_id=${barbeiroId}&data=${data}`
        );
        
        if (!res.ok) throw new Error('Erro ao carregar horários');
        
        const dataHorarios = await res.json();
        
        if (dataHorarios.horarios_disponiveis.length === 0) {
            listaHorarios.innerHTML = '<p style="color:#aaa; text-align:center; padding:20px;">Nenhum horário disponível para esta data</p>';
        } else {
            dataHorarios.horarios_disponiveis.forEach(horario => {
                const div = document.createElement('div');
                div.className = 'horario-opcao';
                div.textContent = horario;
                
                div.onclick = () => {
                    document.getElementById('hora').value = `${data}T${horario}:00`;
                    // Remover seleção anterior
                    Array.from(listaHorarios.children).forEach(c => {
                        c.style.background = '';
                        c.style.color = '';
                    });
                    // Destacar seleção atual
                    div.style.background = '#e74c3c';
                    div.style.color = '#fff';
                };
                
                listaHorarios.appendChild(div);
            });
        }
        
        horariosContainer.style.display = 'block';

    } catch (error) {
        console.error("Erro ao carregar horários:", error);
        listaHorarios.innerHTML = '<p style="color:#e74c3c; text-align:center;">Erro ao carregar horários</p>';
    }
}

// Selecionar serviço
function selecionarServico(servicoId) {
    // Remover seleção anterior
    document.querySelectorAll('.servico').forEach(s => s.classList.remove('selecionado'));
    
    // Adicionar seleção atual
    const servicoSelecionado = document.querySelector(`.servico[data-id="${servicoId}"]`);
    servicoSelecionado.classList.add('selecionado');
    
    const servico = SERVICOS.find(s => s.id === servicoId);
    if (servico) {
        document.getElementById('servicoSelecionado').value = servico.nome;
        document.getElementById('servicoSelecionadoId').value = servico.id;
        document.getElementById('precoSelecionado').value = servico.preco;
        
        mostrarToast(`Serviço selecionado: ${servico.nome} - R$ ${servico.preco.toFixed(2)}`, 'sucesso');
        
        // Carregar horários se já tiver barbeiro selecionado
        const barbeiroId = document.getElementById('barbeiroSelecionado').value;
        if (barbeiroId) {
            carregarHorarios();
        }
    }
}

// Enviar agendamento
form.addEventListener('submit', async e => {
    e.preventDefault();
    
    const nome = document.getElementById('nomeCliente').value;
    const email = document.getElementById('email').value;
    const telefone = document.getElementById('telefone').value;
    const servicoId = document.getElementById('servicoSelecionadoId').value;
    const horario = document.getElementById('hora').value;
    const barbeiroId = document.getElementById('barbeiroSelecionado').value;

    // Validações
    if (!nome || !telefone || !servicoId || !horario || !barbeiroId) {
        mostrarToast("Preencha todos os campos obrigatórios!", 'erro');
        return;
    }

    try {
        const res = await fetch('http://localhost:5000/agendar', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Barbearia-ID': BARBEARIA_ID.toString()
            },
            body: JSON.stringify({ 
                nome, 
                email, 
                telefone, 
                servico_id: servicoId, // ✅ CORRIGIDO: servico_id em vez de servico
                horario, 
                barbeiro_id: barbeiroId 
            })
        });
        
        const data = await res.json();
        
        if (!res.ok) {
            throw new Error(data.erro || 'Erro ao agendar');
        }
        
        mostrarToast(data.msg, 'sucesso');
        
        // Limpar formulário
        form.reset();
        document.getElementById('servicoSelecionado').value = '';
        document.getElementById('servicoSelecionadoId').value = '';
        document.getElementById('precoSelecionado').value = '';
        document.getElementById('hora').value = '';
        document.querySelectorAll('.servico').forEach(s => s.classList.remove('selecionado'));
        horariosContainer.style.display = 'none';
        
        // Recarregar lista de agendamentos
        await atualizarListaAgendamentos();
        
    } catch (error) {
        console.error('Erro no agendamento:', error);
        mostrarToast(error.message, 'erro');
    }
});

// Atualizar lista de agendamentos
async function atualizarListaAgendamentos() {
    try {
        const res = await fetch(`http://localhost:5000/agendamentos?barbearia_id=${BARBEARIA_ID}`);
        if (!res.ok) throw new Error('Erro ao carregar agendamentos');
        
        AGENDAMENTOS = await res.json();
        filtrarAgendamentos('todos');
    } catch (error) {
        console.error('Erro ao carregar agendamentos:', error);
        mostrarToast('Erro ao carregar agendamentos', 'erro');
    }
}

// Filtrar agendamentos
function filtrarAgendamentos(status, event = null) {
    // Atualizar botões de filtro se event foi passado
    if (event) {
        document.querySelectorAll('.filtro-btn').forEach(btn => btn.classList.remove('ativo'));
        event.target.classList.add('ativo');
    }

    const agendamentosFiltrados = status === 'todos' 
        ? AGENDAMENTOS 
        : AGENDAMENTOS.filter(a => a.status === status);
    
    listaAgendamentos.innerHTML = '';

    if (agendamentosFiltrados.length === 0) {
        listaAgendamentos.innerHTML = '<p style="text-align:center; color:#aaa; padding:20px;">Nenhum agendamento encontrado</p>';
    } else {
        agendamentosFiltrados.forEach(agendamento => {
            const div = document.createElement('div');
            div.className = 'agendamento-item';
            
            const statusDisplay = agendamento.status.charAt(0).toUpperCase() + agendamento.status.slice(1);
            const isCancelado = agendamento.status === 'cancelado';
            const dataHora = new Date(agendamento.horario);
            
            div.innerHTML = `
                <div style="flex: 1;">
                    <strong>${agendamento.cliente}</strong>
                    <br>📞 ${agendamento.telefone}
                    ${agendamento.email ? `<br>📧 ${agendamento.email}` : ''}
                    <br>✂️ ${agendamento.servico} com ${agendamento.barbeiro}
                    <br>📅 ${dataHora.toLocaleDateString('pt-BR')} às ${dataHora.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}
                    ${agendamento.observacoes ? `<br>💬 ${agendamento.observacoes}` : ''}
                </div>
                <div style="display: flex; flex-direction: column; align-items: center; gap: 10px;">
                    <span style="color: ${isCancelado ? '#e74c3c' : '#2ecc71'}; font-weight: bold;">
                        ${statusDisplay}
                    </span>
                    ${!isCancelado ? 
                        `<button class="cancelar-btn" onclick="cancelarAgendamento(${agendamento.id})">Cancelar</button>` : 
                        ''
                    }
                </div>
            `;
            listaAgendamentos.appendChild(div);
        });
    }
    
    contador.textContent = `Total: ${agendamentosFiltrados.length} agendamento(s)`;
}

// Cancelar agendamento
async function cancelarAgendamento(agendamentoId) {
    if (!confirm('Tem certeza que deseja cancelar este agendamento?')) return;
    
    try {
        const res = await fetch(`http://localhost:5000/agendamento/${agendamentoId}/cancelar`, { 
            method: 'POST',
            headers: {
                'X-Barbearia-ID': BARBEARIA_ID.toString()
            }
        });
        
        if (!res.ok) throw new Error('Erro ao cancelar agendamento');
        
        const data = await res.json();
        mostrarToast(data.msg, 'sucesso');
        await atualizarListaAgendamentos();
    } catch (error) {
        console.error('Erro ao cancelar:', error);
        mostrarToast(error.message, 'erro');
    }
}

// Exportar lista para CSV
async function exportarLista() {
    try {
        if (AGENDAMENTOS.length === 0) {
            mostrarToast('Nenhum agendamento para exportar', 'erro');
            return;
        }
        
        let csv = 'Cliente,Telefone,Email,Serviço,Barbeiro,Data,Hora,Status\n';
        AGENDAMENTOS.forEach(agendamento => {
            const dataHora = new Date(agendamento.horario);
            csv += `"${agendamento.cliente}","${agendamento.telefone}","${agendamento.email || ''}","${agendamento.servico}","${agendamento.barbeiro}","${dataHora.toLocaleDateString('pt-BR')}","${dataHora.toLocaleTimeString('pt-BR')}","${agendamento.status}"\n`;
        });
        
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `agendamentos_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        mostrarToast('Lista exportada com sucesso!', 'sucesso');
    } catch (error) {
        console.error('Erro ao exportar:', error);
        mostrarToast('Erro ao exportar lista', 'erro');
    }
}

// Limpar filtros (não agendamentos)
function limparFiltros() {
    document.querySelectorAll('.filtro-btn').forEach(btn => btn.classList.remove('ativo'));
    document.querySelector('.filtro-btn').classList.add('ativo'); // Ativar "Todos"
    filtrarAgendamentos('todos');
}

// Atualizar dados
async function atualizarDados() {
    await Promise.all([
        carregarServicos(),
        carregarBarbeiros(),
        atualizarListaAgendamentos()
    ]);
    mostrarToast('Dados atualizados!', 'sucesso');
}

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    // Configurar data mínima como hoje
    const today = new Date();
    const todayISO = today.toISOString().split('T')[0];
    const dataInput = document.getElementById('data');
    
    dataInput.setAttribute('min', todayISO);
    dataInput.value = todayISO;
    
    // Adicionar evento de change para data e barbeiro
    dataInput.addEventListener('change', carregarHorarios);
    document.getElementById('barbeiroSelecionado').addEventListener('change', carregarHorarios);
    
    // Criar campo hidden para servico_id se não existir
    if (!document.getElementById('servicoSelecionadoId')) {
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.id = 'servicoSelecionadoId';
        form.appendChild(hiddenInput);
    }
    
    // Carregar dados iniciais
    atualizarDados();
    
    // Atualizar a cada 30 segundos
    setInterval(atualizarListaAgendamentos, 30000);
});