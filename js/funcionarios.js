/* funcionarios.js - Lógica da página de Funcionários (dual-view pattern) */

const DAYS = ['seg','ter','qua','qui','sex','sab','dom'];
let filiais = [];
let empresas = [];
let empresaLabels = [];
let todosFuncionarios = [];

// ── View toggling ──
function show(view) {
    document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + view));
    if (view === 'list') carregarFuncionarios();
}

// ── Tabs ──
function bindTabs() {
    document.querySelectorAll('.pf-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.pf-tab').forEach(t => t.classList.toggle('active', t === tab));
            document.querySelectorAll('.pf-pane').forEach(p => p.classList.toggle('active', p.id === 'tab-' + tab.dataset.tab));
            // Load sub-entity data when switching tabs
            if (tab.dataset.tab === 'dependentes') carregarDependentes();
            if (tab.dataset.tab === 'filiais') { carregarFiliaisTabela(); carregarEmpresas(); }
            if (tab.dataset.tab === 'historico') { carregarSalarios(); carregarMovimentacoes(); }
        });
    });
}

function resetTabs() {
    document.querySelectorAll('.pf-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === 'pessoal'));
    document.querySelectorAll('.pf-pane').forEach(p => p.classList.toggle('active', p.id === 'tab-pessoal'));
}

// ── Toast ──
function mostrarToast(msg, tipo) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast ' + tipo;
    t.style.display = 'block';
    setTimeout(() => t.style.display = 'none', 3000);
}

// ── Weekend schedule ──
function toggleFimDeSemana() {
    const trabSab = document.getElementById('f-trab-sab').checked;
    const trabDom = document.getElementById('f-trab-dom').checked;
    ['f-sab-ent','f-sab-sai'].forEach(id => document.getElementById(id).disabled = !trabSab);
    ['f-dom-ent','f-dom-sai'].forEach(id => document.getElementById(id).disabled = !trabDom);
}

function getTime(id) { return document.getElementById(id).value || ''; }

// ── Pension mask ──
function togglePensaoMask() {
    const tipo = document.getElementById('f-pensao-tipo').value;
    const el = document.getElementById('f-pensao-valor');
    if (tipo === 'V') {
        el.type = 'text';
        el.setAttribute('data-mask', 'moeda');
        el.value = (el.value && Number(el.value) > 0) ? Mascaras.fmtMoeda(String(Math.round(Number(el.value) * 100))) : 'R$ 0,00';
        Mascaras.aplicar('f-pensao-valor');
    } else {
        el.removeAttribute('data-mask');
        el.type = 'number';
        el.value = (el.value && Mascaras.limparMoeda(el.value)) ? Mascaras.limparMoeda(el.value) : '0';
    }
}

// ── Uploads ──
async function uploadFoto(input) {
    const file = input.files[0];
    if (!file) return;
    const ext = file.name.split('.').pop() || 'jpg';
    const reader = new FileReader();
    reader.onload = async function(e) {
        const base64 = e.target.result.split(',')[1];
        try {
            const r = await fetch('/api/funcionario/upload', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({type:'foto',data:base64,ext:ext})
            });
            const data = await r.json();
            if (data.status === 'ok') {
                document.getElementById('f-foto').value = data.filename;
                document.getElementById('foto-preview').src = data.url;
            } else mostrarToast(data.mensagem||'Erro upload', 'error');
        } catch(e) { mostrarToast('Erro ao enviar foto', 'error'); }
    };
    reader.readAsDataURL(file);
}

async function uploadCurriculo(input) {
    const file = input.files[0];
    if (!file) return;
    const ext = file.name.split('.').pop() || 'pdf';
    const reader = new FileReader();
    reader.onload = async function(e) {
        const base64 = e.target.result.split(',')[1];
        try {
            const r = await fetch('/api/funcionario/upload', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({type:'curriculo',data:base64,ext:ext})
            });
            const data = await r.json();
            if (data.status === 'ok') {
                document.getElementById('f-curriculo').value = data.filename;
                document.getElementById('curriculo-nome').textContent = file.name;
            } else mostrarToast(data.mensagem||'Erro upload', 'error');
        } catch(e) { mostrarToast('Erro ao enviar curriculo', 'error'); }
    };
    reader.readAsDataURL(file);
}

// ── Clear form ──
function limparForm() {
    ['f-id','f-nome','f-cpf','f-rg','f-data-nasc','f-celular','f-tel-comercial','f-email','f-email-particular',
    'f-endereco','f-data-adm','f-data-dem','f-salario','f-foto','f-contato-emerg-nome','f-contato-emerg-tel','f-curriculo','f-tipo-sanguineo','f-banco','f-agencia','f-conta','f-conta-digito','f-conta-tipo','f-pix','f-pis','f-ctps','f-ctps-serie','f-ctps-uf','f-cbo','f-grau-instrucao','f-tipo-contrato','f-motivo-deslig','f-vt-desconto','f-vt-dias','f-vr','f-plano-saude','f-plano-saude-valor','f-rg-orgao','f-rg-uf','f-titulo-eleitor','f-sexo','f-estado-civil','f-nacionalidade','f-cep','f-cidade','f-uf','f-situacao-vinculo','f-departamento','f-data-posse-cargo','f-exame-adm-venc','f-forma-pagamento','f-meio-pagamento','f-carga-horaria','f-pensao-tipo','f-pensao-valor','f-observacoes','f-vt-optante'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    document.getElementById('foto-preview').src = '/img/sem-foto.png';
    document.getElementById('curriculo-nome').textContent = '';
    document.getElementById('f-empresa-id').value = '';
    document.getElementById('f-filial-id').value = '0';
    document.getElementById('f-supervisor-id').value = '';
    document.getElementById('f-trab-sab').checked = false;
    document.getElementById('f-trab-dom').checked = false;
    ['f-seg-ent','f-seg-alm','f-seg-sai','f-ter-ent','f-ter-alm','f-ter-sai',
    'f-qua-ent','f-qua-alm','f-qua-sai','f-qui-ent','f-qui-alm','f-qui-sai',
    'f-sex-ent','f-sex-alm','f-sex-sai'].forEach(id => document.getElementById(id).value = '08:00');
    ['f-sab-ent','f-dom-ent'].forEach(id => document.getElementById(id).value = '08:00');
    ['f-sab-sai','f-dom-sai'].forEach(id => document.getElementById(id).value = '12:00');
    document.getElementById('form-titulo').textContent = 'Novo Funcionário';
    resetTabs();
    toggleFimDeSemana();
    togglePensaoMask();
}

// ── Load entities ──
async function carregarFiliais() {
    try {
        const r = await fetch('/api/filiais');
        const data = await r.json();
        filiais = data.filiais || [];
        const sel = document.getElementById('f-filial-id');
        sel.innerHTML = '<option value="0">Matriz</option>' + filiais.map(f =>
            '<option value="' + f.id + '">' + f.nome + '</option>'
        ).join('');
    } catch(e) {}
}

async function carregarSupervisores() {
    try {
        const r = await fetch('/api/funcionarios');
        const data = await r.json();
        const funcs = data.funcionarios || [];
        const sel = document.getElementById('f-supervisor-id');
        const atual = sel.value;
        sel.innerHTML = '<option value="">Nenhum</option>' + funcs
            .filter(f => !(f.situacao_vinculo || '').toLowerCase().includes('desligado'))
            .map(f => '<option value="' + f.id + '">' + (f.nome || 'Func. ' + f.id) + '</option>').join('');
        if (atual) sel.value = atual;
    } catch(e) {}
}

async function carregarEmpresas() {
    try {
        const token = localStorage.getItem('auth_token') || '';
        const r = await fetch('/api/auth/minhas-empresas', { headers: { 'X-Auth-Token': token } });
        const data = await r.json();
        empresas = data.empresas || [];
        empresaLabels = empresas.map(e => e.nome_fantasia || e.nome_razao || e.nome || e.id || '');
        const selFilial = document.getElementById('fl-empresa-id');
        if (selFilial) {
            const atualFilial = selFilial.value;
            selFilial.innerHTML = '<option value="">Selecionar...</option>' + empresas.map((e, i) =>
                '<option value="' + (i + 1) + '">' + empresaLabels[i] + '</option>').join('');
            if (atualFilial) selFilial.value = atualFilial;
        }
        const selFunc = document.getElementById('f-empresa-id');
        if (selFunc) {
            const atualFunc = selFunc.value;
            selFunc.innerHTML = '<option value="">Selecionar...</option>' + empresas.map((e, i) =>
                '<option value="' + (i + 1) + '">' + empresaLabels[i] + '</option>').join('');
            if (atualFunc) selFunc.value = atualFunc;
        }
    } catch(e) {}
}

function empresaLabel(empresaId) {
    if (!empresaId) return 'Matriz';
    const i = parseInt(empresaId, 10) - 1;
    return empresaLabels[i] || ('Empresa #' + empresaId);
}

// ── Filiais table ──
async function carregarFiliaisTabela() {
    try {
        const r = await fetch('/api/filiais');
        const data = await r.json();
        filiais = data.filiais || [];
        const tbody = document.getElementById('tabela-filiais');
        if (filiais.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:20px;">Nenhuma filial</td></tr>';
        } else {
            tbody.innerHTML = filiais.map(f =>
                '<tr><td>' + f.id + '</td><td>' + (f.nome || '') + '</td><td>' + (f.endereco || '') + '</td><td>' + (f.responsavel || '') + '</td><td>' + empresaLabel(f.empresa_id) + '</td>' +
                '<td style="white-space:nowrap;">' +
                '<button class="so-btn" onclick="editarFilial(' + f.id + ')">Editar</button> ' +
                '<button class="so-btn danger" onclick="excluirFilial(' + f.id + ')">Excluir</button>' +
                '</td></tr>').join('');
        }
    } catch(e) { mostrarToast('Erro ao carregar filiais', 'error'); }
}

function limparFormFilial() {
    document.getElementById('fl-id').value = '';
    document.getElementById('fl-nome').value = '';
    document.getElementById('fl-endereco').value = '';
    document.getElementById('fl-responsavel').value = '';
    document.getElementById('fl-empresa-id').value = '';
}

async function salvarFilial() {
    const id = document.getElementById('fl-id').value;
    const isEdit = id !== '';
    const nome = document.getElementById('fl-nome').value.trim();
    if (!nome) { mostrarToast('Nome da filial obrigatório', 'error'); return; }
    const params = new URLSearchParams();
    params.set('nome', nome);
    params.set('endereco', document.getElementById('fl-endereco').value.trim());
    params.set('responsavel', document.getElementById('fl-responsavel').value.trim());
    params.set('empresa_id', document.getElementById('fl-empresa-id').value);
    if (isEdit) params.set('id', id);
    const endpoint = isEdit ? '/api/filial/alterar' : '/api/filial/incluir';
    try {
        const r = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params });
        const data = await r.json();
        if (data.status === 'ok' || data.id) { mostrarToast('Filial salva!', 'success'); limparFormFilial(); carregarFiliaisTabela(); carregarFiliais(); }
        else mostrarToast(data.message || data.mensagem || 'Erro', 'error');
    } catch(e) { mostrarToast('Erro ao salvar filial', 'error'); }
}

function editarFilial(id) {
    const f = filiais.find(x => String(x.id) === String(id));
    if (!f) { mostrarToast('Filial não encontrada', 'error'); return; }
    document.getElementById('fl-id').value = f.id;
    document.getElementById('fl-nome').value = f.nome || '';
    document.getElementById('fl-endereco').value = f.endereco || '';
    document.getElementById('fl-responsavel').value = f.responsavel || '';
    document.getElementById('fl-empresa-id').value = f.empresa_id || '';
}

async function excluirFilial(id) {
    if (!confirm('Excluir filial #' + id + '?')) return;
    const params = new URLSearchParams(); params.set('id', id);
    try {
        const r = await fetch('/api/filial/excluir', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params });
        const data = await r.json();
        if (data.status === 'ok') { mostrarToast('Filial excluída!', 'success'); carregarFiliaisTabela(); carregarFiliais(); }
        else mostrarToast(data.message || data.mensagem || 'Erro', 'error');
    } catch(e) { mostrarToast('Erro ao excluir filial', 'error'); }
}

// ── Format schedule ──
function formatHorario(func) {
    if (!func) return '-';
    const dias = [];
    DAYS.forEach(d => {
        const ent = func[d + '_ent'];
        const sai = func[d + '_sai'];
        if (ent || sai) {
            const label = {seg:'2',ter:'3',qua:'4',qui:'5',sex:'6',sab:'S',dom:'D'}[d];
            dias.push(label + ' ' + (ent || '--') + '-' + (sai || '--'));
        }
    });
    if (dias.length === 0) return '2-6 08:00-18:00';
    return dias.join(' ');
}

// ── Load employees ──
async function carregarFuncionarios() {
    try {
        const r = await fetch('/api/funcionarios');
        const data = await r.json();
        todosFuncionarios = data.funcionarios || [];
        renderizarTabela(todosFuncionarios);
    } catch(e) { mostrarToast('Erro ao carregar funcionários', 'error'); }
}

function renderizarTabela(funcs) {
    const tbody = document.getElementById('tabela-funcionarios');
    if (funcs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="17" style="text-align:center;color:var(--text-muted);padding:30px;">Nenhum funcionário cadastrado</td></tr>';
        return;
    }
    tbody.innerHTML = funcs.map(f => {
        const cargo = f.cargo_nome || '---';
        const salario = f.salario ? 'R$ ' + parseFloat(f.salario).toFixed(2) : '-';
        const horario = formatHorario(f);
        const fotoUrl = f.foto ? '/uploads/funcionarios/' + f.foto : '/img/sem-foto.png';
        const tipoS = f.tipo_sanguineo || '-';
        const bancoLabel = f.banco ? f.banco.substr(0,10) : '-';
        const pixLabel = f.pix ? (f.pix.length > 12 ? f.pix.substr(0,10)+'...' : f.pix) : '-';
        const desligado = (f.situacao_vinculo || '').trim() === 'desligado';
        const usuarioLabel = f.usuario_vinculado ? '<span class="badge badge-info" title="'+f.usuario_nome+'">'+f.usuario_vinculado+'</span>' : '<span style="color:var(--text-muted)">-</span>';
        return '<tr>' +
            '<td>' + f.id + '</td>' +
            '<td><img src="' + fotoUrl + '" class="photo-mini"></td>' +
            '<td>' + (f.nome || '') + (desligado ? ' <span class="badge badge-danger" style="font-size:.6rem">DESLIGADO</span>' : '') + '</td>' +
            '<td>' + cargo + '</td>' +
            '<td>' + (f.celular || '') + '</td>' +
            '<td>' + (f.email || '') + '</td>' +
            '<td>' + tipoS + '</td>' +
            '<td>' + (f.data_adm || '') + '</td>' +
            '<td>' + (desligado ? '<span style="color:#fca5a5;font-weight:600">Desligado</span><div style="font-size:.7rem;color:var(--text-muted)">' + (f.data_dem || '') + '</div>' : '<span style="color:#6ee7b7">Ativo</span>') + '</td>' +
            '<td>' + salario + '</td>' +
            '<td style="font-size:.75rem;">' + bancoLabel + '</td>' +
            '<td style="font-size:.75rem;">' + pixLabel + '</td>' +
            '<td style="font-size:.75rem;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + horario + '">' + horario + '</td>' +
            '<td>' + (f.empresa_nome || (f.empresa_id ? 'Empresa #' + f.empresa_id : 'Matriz')) + '</td>' +
            '<td>' + (f.supervisor_nome || '') + '</td>' +
            '<td>' + usuarioLabel + '</td>' +
            '<td style="white-space:nowrap;">' +
            '<button class="so-btn" onclick="editarFuncionario(' + f.id + ')">Editar</button> ' +
            (desligado
                ? '<button class="so-btn primary" onclick="reativarFuncionario(' + f.id + ')">Reativar</button>'
                : '<button class="so-btn warning" onclick="abrirModalDesligar(' + f.id + ',\'' + (f.nome || '').replace(/'/g,'') + '\')">Desligar</button>') + ' ' +
            '<button class="so-btn danger" onclick="excluirFuncionario(' + f.id + ')">Excluir</button>' +
            '</td></tr>';
    }).join('');
}

// ── Search ──
function filtrarFuncionarios() {
    const q = document.getElementById('busca-func').value.toLowerCase().trim();
    if (!q) { renderizarTabela(todosFuncionarios); return; }
    const filtrados = todosFuncionarios.filter(f =>
        (f.nome || '').toLowerCase().includes(q) ||
        (f.cpf || '').includes(q) ||
        (f.celular || '').includes(q) ||
        (f.email || '').toLowerCase().includes(q) ||
        (f.cargo_nome || '').toLowerCase().includes(q) ||
        String(f.id).includes(q)
    );
    renderizarTabela(filtrados);
}

// ── Save employee ──
async function salvarFuncionario() {
    const id = document.getElementById('f-id').value;
    const isEdit = id !== '';
    const nome = document.getElementById('f-nome').value.trim();

    if (!nome) { mostrarToast('Nome obrigatório', 'error'); return; }
    const cpfVal = document.getElementById('f-cpf').value.trim();
    if (cpfVal) {
        const cpfOk = Mascaras.validarCPF(cpfVal);
        if (cpfOk === false) { mostrarToast('CPF inválido', 'error'); return; }
    }
    const obrigatorios = {
        'f-data-nasc': 'Data de nascimento', 'f-sexo': 'Sexo', 'f-nacionalidade': 'Nacionalidade',
        'f-endereco': 'Endereço', 'f-cep': 'CEP', 'f-cidade': 'Cidade', 'f-uf': 'UF',
        'f-ctps': 'Número CTPS', 'f-data-adm': 'Data de admissão',
        'f-departamento-id': 'Departamento', 'f-cargo-id': 'Cargo',
        'f-forma-pagamento': 'Forma de pagamento', 'f-salario': 'Salário'
    };
    for (const [id, label] of Object.entries(obrigatorios)) {
        const el = document.getElementById(id);
        if (!el || !el.value) { mostrarToast(label + ' é obrigatório', 'error'); return; }
    }

    const params = new URLSearchParams();
    params.set('nome', nome);
    params.set('cpf', document.getElementById('f-cpf').value.trim());
    params.set('rg', document.getElementById('f-rg').value.trim());
    params.set('data_nasc', document.getElementById('f-data-nasc').value);
    params.set('celular', document.getElementById('f-celular').value.trim());
    params.set('email_particular', document.getElementById('f-email-particular').value.trim());
    params.set('tel_comercial', document.getElementById('f-tel-comercial').value.trim());
    params.set('email', document.getElementById('f-email').value.trim());
    params.set('endereco', document.getElementById('f-endereco').value.trim());
    params.set('data_adm', document.getElementById('f-data-adm').value);
    params.set('data_dem', document.getElementById('f-data-dem').value);
    params.set('salario', Mascaras.limparMoeda(document.getElementById('f-salario').value) || '0');
    params.set('empresa_id', document.getElementById('f-empresa-id').value);
    params.set('filial_id', document.getElementById('f-filial-id').value);
    params.set('supervisor_id', document.getElementById('f-supervisor-id').value);
    params.set('trab_sab', document.getElementById('f-trab-sab').checked ? 'S' : 'N');
    params.set('trab_dom', document.getElementById('f-trab-dom').checked ? 'S' : 'N');
    params.set('foto', document.getElementById('f-foto').value);
    params.set('contato_emerg_nome', document.getElementById('f-contato-emerg-nome').value.trim());
    params.set('contato_emerg_tel', document.getElementById('f-contato-emerg-tel').value.trim());
    params.set('curriculo', document.getElementById('f-curriculo').value);
    params.set('tipo_sanguineo', document.getElementById('f-tipo-sanguineo').value);
    params.set('banco', document.getElementById('f-banco').value.trim());
    params.set('agencia', document.getElementById('f-agencia').value.trim());
    params.set('conta', document.getElementById('f-conta').value.trim());
    params.set('conta_digito', document.getElementById('f-conta-digito').value.trim());
    params.set('conta_tipo', document.getElementById('f-conta-tipo').value);
    params.set('pix', document.getElementById('f-pix').value.trim());
    params.set('pis', document.getElementById('f-pis').value.trim());
    params.set('ctps', document.getElementById('f-ctps').value.trim());
    params.set('ctps_serie', document.getElementById('f-ctps-serie').value.trim());
    params.set('ctps_uf', document.getElementById('f-ctps-uf').value.trim());
    params.set('cbo', document.getElementById('f-cbo').value.trim());
    params.set('grau_instrucao', document.getElementById('f-grau-instrucao').value);
    params.set('tipo_contrato', document.getElementById('f-tipo-contrato').value);
    params.set('motivo_deslig', document.getElementById('f-motivo-deslig').value);
    params.set('vt_desconto', Mascaras.limparMoeda(document.getElementById('f-vt-desconto').value));
    params.set('vt_dias', document.getElementById('f-vt-dias').value || '0');
    params.set('vr', Mascaras.limparMoeda(document.getElementById('f-vr').value) || '0');
    params.set('plano_saude', document.getElementById('f-plano-saude').value.trim());
    params.set('plano_saude_valor', Mascaras.limparMoeda(document.getElementById('f-plano-saude-valor').value) || '0');
    params.set('sexo', document.getElementById('f-sexo').value);
    params.set('estado_civil', document.getElementById('f-estado-civil').value);
    params.set('nacionalidade', document.getElementById('f-nacionalidade').value.trim());
    params.set('rg_orgao', document.getElementById('f-rg-orgao').value.trim());
    params.set('rg_uf', document.getElementById('f-rg-uf').value.trim());
    params.set('titulo_eleitor', document.getElementById('f-titulo-eleitor').value.trim());
    params.set('cep', document.getElementById('f-cep').value.trim());
    params.set('cidade', document.getElementById('f-cidade').value.trim());
    params.set('uf', document.getElementById('f-uf').value.trim());
    params.set('situacao_vinculo', document.getElementById('f-situacao-vinculo').value);
    params.set('departamento_id', document.getElementById('f-departamento-id').value);
    params.set('cargo_id', document.getElementById('f-cargo-id').value);
    params.set('data_posse_cargo', document.getElementById('f-data-posse-cargo').value);
    params.set('forma_pagamento', document.getElementById('f-forma-pagamento').value);
    params.set('meio_pagamento', document.getElementById('f-meio-pagamento').value);
    params.set('carga_horaria', document.getElementById('f-carga-horaria').value || '0');
    params.set('exame_adm_venc', document.getElementById('f-exame-adm-venc').value);
    params.set('observacoes', document.getElementById('f-observacoes').value.trim());
    params.set('pensao_tipo', document.getElementById('f-pensao-tipo').value);
    const pvEl = document.getElementById('f-pensao-valor');
    params.set('pensao_valor', pvEl.getAttribute('data-mask') === 'moeda' ? Mascaras.limparMoeda(pvEl.value) : (pvEl.value || '0'));
    params.set('vt_optante', document.getElementById('f-vt-optante').value);
    ['seg','ter','qua','qui','sex'].forEach(d => {
        params.set(d + '_ent', getTime('f-' + d + '-ent'));
        params.set(d + '_alm', getTime('f-' + d + '-alm'));
        params.set(d + '_sai', getTime('f-' + d + '-sai'));
    });
    params.set('sab_ent', getTime('f-sab-ent'));
    params.set('sab_sai', getTime('f-sab-sai'));
    params.set('dom_ent', getTime('f-dom-ent'));
    params.set('dom_sai', getTime('f-dom-sai'));

    const endpoint = isEdit ? '/api/funcionario/alterar' : '/api/funcionario/incluir';
    if (isEdit) params.set('id', id);

    try {
        const r = await fetch(endpoint, {
            method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params
        });
        const data = await r.json();
        if (data.status === 'ok' || data.id) {
            mostrarToast(isEdit ? 'Funcionário atualizado!' : 'Funcionário cadastrado!', 'success');
            limparForm();
            show('list');
        } else {
            mostrarToast(data.mensagem || 'Erro', 'error');
        }
    } catch(e) { mostrarToast('Erro de conexão', 'error'); }
}

// ── Edit employee ──
async function editarFuncionario(id) {
    try {
        const r = await fetch('/api/funcionarios');
        const data = await r.json();
        const func = (data.funcionarios || []).find(f => f.id === id);
        if (!func) { mostrarToast('Funcionário não encontrado', 'error'); return; }

        document.getElementById('f-id').value = id;
        document.getElementById('f-nome').value = func.nome || '';
        document.getElementById('f-cpf').value = func.cpf || '';
        document.getElementById('f-rg').value = func.rg || '';
        document.getElementById('f-data-nasc').value = func.data_nasc || '';
        document.getElementById('f-celular').value = func.celular || '';
        document.getElementById('f-email-particular').value = func.email_particular || '';
        document.getElementById('f-tel-comercial').value = func.tel_comercial || '';
        document.getElementById('f-email').value = func.email || '';
        document.getElementById('f-endereco').value = func.endereco || '';
        document.getElementById('f-empresa-id').value = func.empresa_id || '';
        document.getElementById('f-filial-id').value = func.filial_id || '0';
        document.getElementById('f-supervisor-id').value = func.supervisor_id || '';
        document.getElementById('f-data-adm').value = func.data_adm || '';
        document.getElementById('f-data-dem').value = func.data_dem || '';
        document.getElementById('f-salario').value = func.salario ? Mascaras.fmtMoeda(String(Math.round(Number(func.salario) * 100))) : '';
        document.getElementById('f-foto').value = func.foto || '';
        document.getElementById('f-contato-emerg-nome').value = func.contato_emerg_nome || '';
        document.getElementById('f-contato-emerg-tel').value = func.contato_emerg_tel || '';
        document.getElementById('f-curriculo').value = func.curriculo || '';
        document.getElementById('f-tipo-sanguineo').value = func.tipo_sanguineo || '';
        document.getElementById('f-banco').value = func.banco || '';
        document.getElementById('f-agencia').value = func.agencia || '';
        document.getElementById('f-conta').value = func.conta || '';
        document.getElementById('f-conta-digito').value = func.conta_digito || '';
        document.getElementById('f-conta-tipo').value = func.conta_tipo || '';
        document.getElementById('f-pix').value = func.pix || '';
        document.getElementById('f-pis').value = func.pis || '';
        document.getElementById('f-ctps').value = func.ctps || '';
        document.getElementById('f-ctps-serie').value = func.ctps_serie || '';
        document.getElementById('f-ctps-uf').value = func.ctps_uf || '';
        document.getElementById('f-cbo').value = func.cbo || '';
        document.getElementById('f-grau-instrucao').value = func.grau_instrucao || '';
        document.getElementById('f-tipo-contrato').value = func.tipo_contrato || '';
        document.getElementById('f-motivo-deslig').value = func.motivo_deslig || '';
        document.getElementById('f-vt-desconto').value = func.vt_desconto ? Mascaras.fmtMoeda(String(Math.round(Number(func.vt_desconto) * 100))) : 'R$ 0,00';
        document.getElementById('f-vt-dias').value = func.vt_dias || '22';
        document.getElementById('f-vt-optante').value = func.vt_optante || '';
        document.getElementById('f-vr').value = func.vr ? Mascaras.fmtMoeda(String(Math.round(Number(func.vr) * 100))) : 'R$ 0,00';
        document.getElementById('f-plano-saude').value = func.plano_saude || '';
        document.getElementById('f-plano-saude-valor').value = func.plano_saude_valor ? Mascaras.fmtMoeda(String(Math.round(Number(func.plano_saude_valor) * 100))) : 'R$ 0,00';
        document.getElementById('f-rg-orgao').value = func.rg_orgao || '';
        document.getElementById('f-rg-uf').value = func.rg_uf || '';
        document.getElementById('f-titulo-eleitor').value = func.titulo_eleitor || '';
        document.getElementById('f-sexo').value = func.sexo || '';
        document.getElementById('f-estado-civil').value = func.estado_civil || '';
        document.getElementById('f-nacionalidade').value = func.nacionalidade || '';
        document.getElementById('f-cep').value = func.cep || '';
        document.getElementById('f-cidade').value = func.cidade || '';
        document.getElementById('f-uf').value = func.uf || '';
        document.getElementById('f-situacao-vinculo').value = func.situacao_vinculo || '';
        document.getElementById('f-departamento-id').value = func.departamento_id || '';
        document.getElementById('f-cargo-id').value = func.cargo_id || '';
        document.getElementById('f-data-posse-cargo').value = func.data_posse_cargo || '';
        document.getElementById('f-forma-pagamento').value = func.forma_pagamento || '';
        document.getElementById('f-meio-pagamento').value = func.meio_pagamento || '';
        document.getElementById('f-carga-horaria').value = func.carga_horaria || '';
        document.getElementById('f-exame-adm-venc').value = func.exame_adm_venc || '';
        document.getElementById('f-observacoes').value = func.observacoes || '';
        document.getElementById('f-pensao-tipo').value = func.pensao_tipo || '';
        document.getElementById('f-pensao-valor').value = func.pensao_valor || '0';
        togglePensaoMask();
        document.getElementById('foto-preview').src = func.foto ? '/uploads/funcionarios/' + func.foto : '/img/sem-foto.png';
        document.getElementById('curriculo-nome').textContent = func.curriculo ? 'Currículo anexado' : '';
        document.getElementById('f-trab-sab').checked = func.trab_sab === 'S';
        document.getElementById('f-trab-dom').checked = func.trab_dom === 'S';
        ['seg','ter','qua','qui','sex'].forEach(d => {
            document.getElementById('f-' + d + '-ent').value = func[d + '_ent'] || '08:00';
            document.getElementById('f-' + d + '-alm').value = func[d + '_alm'] || '12:00';
            document.getElementById('f-' + d + '-sai').value = func[d + '_sai'] || '18:00';
        });
        document.getElementById('f-sab-ent').value = func.sab_ent || '08:00';
        document.getElementById('f-sab-sai').value = func.sab_sai || '12:00';
        document.getElementById('f-dom-ent').value = func.dom_ent || '08:00';
        document.getElementById('f-dom-sai').value = func.dom_sai || '12:00';
        document.getElementById('form-titulo').textContent = 'Editar Funcionário #' + id;
        resetTabs();
        toggleFimDeSemana();
        show('form');
    } catch(e) { mostrarToast('Erro ao carregar dados', 'error'); }
}

// ── Delete employee ──
async function excluirFuncionario(id) {
    if (!confirm('Excluir funcionário #' + id + '?')) return;
    const params = new URLSearchParams();
    params.set('id', String(id));
    try {
        const r = await fetch('/api/funcionario/excluir', {
            method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: params
        });
        const data = await r.json();
        if (data.status === 'ok') { mostrarToast('Funcionário excluído!', 'success'); carregarFuncionarios(); }
        else { mostrarToast(data.mensagem || 'Erro', 'error'); }
    } catch(e) { mostrarToast('Erro de conexão', 'error'); }
}

// ── Access control ──
function verificarAcesso() {
    try {
        const saved = localStorage.getItem('pos_usuario');
        if (saved) {
            const user = JSON.parse(saved);
            if (user.tipo === 'usuario') return;
            const userData = localStorage.getItem('user_data');
            if (userData) {
                const u = JSON.parse(userData);
                const role = u.role || '';
                if (role !== 'admin' && role !== 'gerente' && role !== 'supervisor') {
                    document.querySelector('.workspace-title').textContent = 'Acesso restrito';
                    document.getElementById('tabela-funcionarios').innerHTML = '<tr><td colspan="17" style="text-align:center;color:var(--text-muted);padding:40px;">Apenas gerentes podem gerenciar funcionários</td></tr>';
                    document.querySelector('.toolbar').style.display = 'none';
                }
            }
        }
    } catch(e) {}
}

// ── Dependentes ──
async function carregarDependentes() {
    const id = document.getElementById('f-id').value;
    if (!id) { document.getElementById('tabela-dependentes').innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:20px;">Salve o funcionário primeiro</td></tr>'; return; }
    try {
        const r = await fetch('/api/dependentes?funcionario_id=' + id);
        const data = await r.json();
        const deps = data.dependentes || [];
        const tbody = document.getElementById('tabela-dependentes');
        if (deps.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:20px;">Nenhum dependente</td></tr>';
        } else {
            tbody.innerHTML = deps.map(d =>
                '<tr><td>' + d.id + '</td><td>' + (d.nome || '') + '</td><td>' + (d.cpf || '') + '</td><td>' + (d.data_nasc || '') + '</td>' +
                '<td>' + (d.grau_parentesco || d.tipo || '') + '</td>' +
                '<td>' + (d.irrf === 'S' ? '✅' : '') + '</td>' +
                '<td>' + (d.sal_familia === 'S' ? '✅' : '') + '</td>' +
                '<td><button class="so-btn" onclick="editarDependente(' + d.id + ')">Editar</button> ' +
                '<button class="so-btn danger" onclick="excluirDependente(' + d.id + ')">Excluir</button></td></tr>'
            ).join('');
        }
    } catch(e) {}
}

function editarDependente(id) {
    const funcId = document.getElementById('f-id').value;
    fetch('/api/dependentes?funcionario_id=' + funcId).then(r=>r.json()).then(data => {
        const d = (data.dependentes||[]).find(x => x.id == id);
        if (!d) return;
        document.getElementById('dp-id').value = d.id;
        document.getElementById('dp-nome').value = d.nome || '';
        document.getElementById('dp-cpf').value = d.cpf || '';
        document.getElementById('dp-data-nasc').value = d.data_nasc || '';
        document.getElementById('dp-tipo').value = d.grau_parentesco || d.tipo || '';
        document.getElementById('dp-irrf').checked = d.irrf === 'S';
        document.getElementById('dp-sal-familia').checked = d.sal_familia === 'S';
    });
}

async function salvarDependente() {
    const funcId = document.getElementById('f-id').value;
    if (!funcId) { mostrarToast('Salve o funcionário primeiro', 'error'); return; }
    const id = document.getElementById('dp-id').value;
    const isEdit = id !== '';
    const params = new URLSearchParams();
    params.set('funcionario_id', funcId);
    params.set('nome', document.getElementById('dp-nome').value.trim());
    params.set('cpf', document.getElementById('dp-cpf').value.trim());
    params.set('data_nasc', document.getElementById('dp-data-nasc').value);
    params.set('grau_parentesco', document.getElementById('dp-tipo').value);
    params.set('irrf', document.getElementById('dp-irrf').checked ? 'S' : 'N');
    params.set('sal_familia', document.getElementById('dp-sal-familia').checked ? 'S' : 'N');
    if (isEdit) params.set('id', id);
    const endpoint = isEdit ? '/api/dependente/alterar' : '/api/dependente/incluir';
    try {
        const r = await fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:params});
        const data = await r.json();
        if (data.status === 'ok' || data.id) {
            mostrarToast('Dependente salvo!', 'success');
            ['dp-id','dp-nome','dp-cpf','dp-data-nasc','dp-tipo'].forEach(x => document.getElementById(x).value = '');
            document.getElementById('dp-irrf').checked = false;
            document.getElementById('dp-sal-familia').checked = false;
            carregarDependentes();
        } else mostrarToast(data.mensagem||'Erro','error');
    } catch(e) { mostrarToast('Erro','error'); }
}

async function excluirDependente(id) {
    if (!confirm('Excluir dependente #' + id + '?')) return;
    const params = new URLSearchParams(); params.set('id', id);
    try {
        const r = await fetch('/api/dependente/excluir', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:params});
        const data = await r.json();
        if (data.status === 'ok') { mostrarToast('Dependente excluído!','success'); carregarDependentes(); }
        else mostrarToast(data.mensagem||'Erro','error');
    } catch(e) { mostrarToast('Erro','error'); }
}

// ── Departamentos / Cargos ──
async function carregarDepartamentos() {
    try {
        const r = await fetch('/api/departamentos?ativos=1');
        const data = await r.json();
        const sel = document.getElementById('f-departamento-id');
        if (!sel) return;
        sel.innerHTML = '<option value="">Selecionar...</option>' + (data.departamentos||[]).map(d => '<option value="'+d.id+'">'+d.descricao+'</option>').join('');
    } catch(e) {}
}

async function carregarCargos() {
    try {
        const r = await fetch('/api/cargos?ativos=1');
        const data = await r.json();
        const sel = document.getElementById('f-cargo-id');
        if (!sel) return;
        sel.innerHTML = '<option value="">Selecionar...</option>' + (data.cargos||[]).map(c => '<option value="'+c.id+'">'+c.descricao+'</option>').join('');
    } catch(e) {}
}

// ── Desligar modal ──
let desligarId = null;
function abrirModalDesligar(id, nome){
    desligarId = id;
    document.getElementById('desligar-nome').textContent = nome + ' (#' + id + ')';
    document.getElementById('desligar-data').value = new Date().toISOString().slice(0,10);
    document.getElementById('desligar-motivo').value = '';
    document.getElementById('modal-desligar').style.display = 'flex';
}
function fecharModalDesligar(){
    document.getElementById('modal-desligar').style.display = 'none';
    desligarId = null;
}
async function confirmarDesligar(){
    if(!desligarId) return;
    const motivo = document.getElementById('desligar-motivo').value;
    const dataDem = document.getElementById('desligar-data').value;
    if(!motivo){ mostrarToast('Selecione o motivo','error'); return; }
    try{
        const params = new URLSearchParams();
        params.set('id', desligarId);
        params.set('motivo', motivo);
        params.set('data_dem', dataDem);
        const r = await fetch('/api/funcionarios/desligar', { method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:params });
        const data = await r.json();
        if(data.status==='ok'){ mostrarToast(data.message||'Funcionário desligado!','success'); fecharModalDesligar(); carregarFuncionarios(); }
        else mostrarToast(data.message||'Erro','error');
    }catch(e){ mostrarToast('Erro','error'); }
}
async function reativarFuncionario(id){
    if(!confirm('Reativar funcionário #'+id+'?')) return;
    try{
        const params = new URLSearchParams(); params.set('id', id);
        const r = await fetch('/api/funcionarios/reativar', { method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:params });
        const data = await r.json();
        if(data.status==='ok'){ mostrarToast(data.message||'Reativado!','success'); carregarFuncionarios(); }
        else mostrarToast(data.message||'Erro','error');
    }catch(e){ mostrarToast('Erro','error'); }
}

// ── Histórico Salarial ──
function fmtSalarioValor(v) {
    if (typeof Mascaras !== 'undefined' && Mascaras.fmtMoeda) {
        return Mascaras.fmtMoeda(String(Math.round(Number(v) * 100)));
    }
    return Number(v).toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
}

async function carregarSalarios() {
    const funcId = document.getElementById('f-id').value;
    if (!funcId) { document.getElementById('tabela-salarios').innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">Salve o funcionário primeiro</td></tr>'; return; }
    try {
        const r = await fetch('/api/funcionario/salario/listar?funcionario_id=' + funcId);
        const data = await r.json();
        const itens = data.salarios || [];
        const tbody = document.getElementById('tabela-salarios');
        if (itens.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px;">Nenhum registro salarial</td></tr>';
        } else {
            tbody.innerHTML = itens.map(s =>
                '<tr><td>' + s.id + '</td><td>' + fmtSalarioValor(s.salario) + '</td><td>' + (s.data_inicio || '') + '</td>' +
                '<td>' + (s.data_fim || '-') + '</td><td>' + (s.status || '') + '</td></tr>'
            ).join('');
        }
    } catch(e) {}
}

async function salvarSalario() {
    const funcId = document.getElementById('f-id').value;
    if (!funcId) { mostrarToast('Salve o funcionário primeiro','error'); return; }
    const sal = document.getElementById('sl-salario').value;
    const dataInicio = document.getElementById('sl-data-inicio').value;
    if (!sal || !dataInicio) { mostrarToast('Informe salário e data de início','error'); return; }
    const valor = (typeof Mascaras !== 'undefined' && Mascaras.limparMoeda) ? Mascaras.limparMoeda(sal) : sal.replace(/[^\d.]/g, '');
    const params = new URLSearchParams();
    params.set('funcionario_id', funcId);
    params.set('salario', valor);
    params.set('data_inicio', dataInicio);
    try {
        const r = await fetch('/api/funcionario/salario/incluir', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:params});
        const data = await r.json();
        if (data.status === 'ok' || data.id) { mostrarToast('Salário registrado!','success'); document.getElementById('sl-salario').value=''; document.getElementById('sl-data-inicio').value=''; carregarSalarios(); }
        else mostrarToast(data.mensagem||data.message||'Erro','error');
    } catch(e) { mostrarToast('Erro','error'); }
}

// ── Movimentações Contratuais ──
async function carregarMovimentacoes() {
    const funcId = document.getElementById('f-id').value;
    if (!funcId) { document.getElementById('tabela-movimentacoes').innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Salve o funcionário primeiro</td></tr>'; return; }
    const tipo = document.getElementById('mv-tipo').value;
    try {
        const r = await fetch('/api/funcionario/movimentacao/listar?funcionario_id=' + funcId + '&tipo=' + tipo);
        const data = await r.json();
        const itens = data.movimentacoes || [];
        const tbody = document.getElementById('tabela-movimentacoes');
        if (itens.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:20px;">Nenhuma movimentação deste tipo</td></tr>';
        } else {
            tbody.innerHTML = itens.map(m =>
                '<tr><td>' + m.id + '</td><td>' + (m.tipo || '') + '</td><td>' + (m.valor_referencia || '') + '</td>' +
                '<td>' + (m.data_inicio || '') + '</td><td>' + (m.data_fim || '-') + '</td><td>' + (m.status || '') + '</td></tr>'
            ).join('');
        }
    } catch(e) {}
}

async function salvarMovimentacao() {
    const funcId = document.getElementById('f-id').value;
    if (!funcId) { mostrarToast('Salve o funcionário primeiro','error'); return; }
    const tipo = document.getElementById('mv-tipo').value;
    const valor = document.getElementById('mv-valor-referencia').value;
    const dataInicio = document.getElementById('mv-data-inicio').value;
    if (!valor || !dataInicio) { mostrarToast('Informe ID do cargo/departamento e data de início','error'); return; }
    const params = new URLSearchParams();
    params.set('funcionario_id', funcId);
    params.set('tipo', tipo);
    params.set('valor_referencia', valor);
    params.set('data_inicio', dataInicio);
    try {
        const r = await fetch('/api/funcionario/movimentacao/incluir', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:params});
        const data = await r.json();
        if (data.status === 'ok' || data.id) { mostrarToast('Movimentação registrada!','success'); document.getElementById('mv-valor-referencia').value=''; document.getElementById('mv-data-inicio').value=''; carregarMovimentacoes(); }
        else mostrarToast(data.mensagem||data.message||'Erro','error');
    } catch(e) { mostrarToast('Erro','error'); }
}

// ── Init ──
document.addEventListener('DOMContentLoaded', function() {
    bindTabs();
    toggleFimDeSemana();
    carregarEmpresas();
    carregarFiliais();
    carregarSupervisores();
    verificarAcesso();
    carregarFuncionarios();
    carregarDepartamentos();
    carregarCargos();

    // Search handler
    const buscaInput = document.getElementById('busca-func');
    if (buscaInput) buscaInput.addEventListener('input', filtrarFuncionarios);

    // Load user name
    const stored = localStorage.getItem("user_data");
    if (stored) {
        try {
            const u = JSON.parse(stored);
            document.getElementById("user-name-display").textContent = u.nome || "Administrador";
            document.getElementById("status-user-info").textContent = "Usuário: " + (u.nome || "Administrador");
        } catch (e) { }
    }
});
