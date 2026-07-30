/*=========================================================
    FiscalBrasil ERP
    File    : app.js — Refactored (Sprint 02)
=========================================================*/

/*=========================================================
  STATE
=========================================================*/

let menuData=[];
let userEmpresas=[];
let currentEmpresaId=localStorage.getItem("current_empresa_id");
let currentMod=null;
let currentModule=null;

/*=========================================================
  COMPONENTS
=========================================================*/

const sidebar=new window.Sidebar();
const header=new window.Header();
const toolbar=new window.Toolbar();
const dashboard=new window.Dashboard();

/*=========================================================
  AUTH
=========================================================*/

const storedUser=localStorage.getItem("user_data");
let userData=null;
if(storedUser){
    try{userData=JSON.parse(storedUser);}catch(e){}
}

const token=localStorage.getItem("auth_token");
if(!token||!userData) window.location.href="index.html";

/*=========================================================
  API
=========================================================*/

async function apiFetch(path,options={}){
    const headers={"X-Auth-Token":token,...options.headers};
    try{
        const res=await fetch(path,{...options,headers});
        if(!res.ok){
            const text=await res.text().catch(()=>"");
            throw new Error("HTTP "+res.status+": "+(text||res.statusText));
        }
        return res.json();
    }catch(e){
        if(window.FiscalUI&&FiscalUI.errors){
            FiscalUI.errors.capture(e,{level:"error",api:path});
        }
        return{status:"error",message:e.message};
    }
}

/*=========================================================
  VALIDAR TOKEN
=========================================================*/

const authData=await apiFetch("/api/auth/me");
if(authData.status!=="ok"){
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");
    window.location.href="index.html";
}
userData=authData.conta;
localStorage.setItem("user_data",JSON.stringify(userData));
header.setUser(userData);

/*=========================================================
  EMPRESAS (multi-empresa)
=========================================================*/

try{
    const res=await fetch("/api/auth/minhas-empresas",{headers:{"X-Auth-Token":token}});
    const data=await res.json();
    if(data.status==="ok") userEmpresas=data.empresas||[];
}catch(e){
    console.warn("minhas-empresas not loaded",e);
}

if(userEmpresas.length>0){
    if(!currentEmpresaId||!userEmpresas.find(e=>e.id===currentEmpresaId)){
        currentEmpresaId=userEmpresas[0].id;
    }
    localStorage.setItem("current_empresa_id",currentEmpresaId);
    const sel=document.getElementById("empresa-select");
    const container=document.getElementById("topbar-empresa");
    if(sel&&container){
        container.style.display="block";
        sel.innerHTML=userEmpresas.map(e=>
            `<option value="${e.id}" ${e.id===currentEmpresaId?"selected":""}>${e.nome}</option>`
        ).join("");
        sel.addEventListener("change",function(){
            currentEmpresaId=this.value;
            localStorage.setItem("current_empresa_id",currentEmpresaId);
            window.filteredMenu=filterMenu(menuData);
            renderLaunchpad();
        });
    }
    const statusCompany=document.getElementById("status-company");
    if(statusCompany){
        const ce=userEmpresas.find(e=>e.id===currentEmpresaId);
        if(ce) statusCompany.textContent=ce.nome;
    }
}

/*=========================================================
  MENU
=========================================================*/

try{
    const res=await fetch("assets/data/menu.json");
    menuData=await res.json();
}catch(e){
    if(window.FiscalUI&&FiscalUI.errors){
        FiscalUI.errors.warn("menu.json not loaded");
    }else{
        console.error("menu.json not loaded",e);
    }
}

/*=========================================================
  PERMISSIONS
=========================================================*/

function getCurrentCompanyRole(){
    if(!currentEmpresaId||userData.role==="admin") return userData.role;
    const empresa=userEmpresas.find(e=>e.id===currentEmpresaId);
    return empresa?empresa.role:userData.role;
}

const ROLE_MODULES={
    admin:"*",
    supervisor:["dashboard","nfe","nfce","clientes","produtos","relatorios","folha","contabilidade"],
    operador:["dashboard","nfe","nfce"]
};

function hasPermission(id){
    const role=getCurrentCompanyRole();
    if(role==="admin") return true;
    const perms=ROLE_MODULES[role]||[];
    return perms.includes(id);
}

function filterMenu(items){
    const result=[];
    for(const item of items){
        if(item.section){
            result.push(item);
            continue;
        }
        if(item.id==="configuracoes"||item.id==="admin"){
            if(userData.role==="admin"){
                result.push(item);
            }
            continue;
        }
        if(item.apps){
            const filtered=item.apps.filter(a=>hasPermission(a.id));
            if(filtered.length>0){
                result.push({...item,apps:filtered});
            }
        }else{
            if(hasPermission(item.id)){
                result.push(item);
            }
        }
    }
    return result;
}

window.filteredMenu=filterMenu(menuData);

/*=========================================================
  HELPERS
=========================================================*/

function findModuleByAppId(appId){
    for(const mod of filteredMenu){
        if(mod.apps){
            const app=mod.apps.find(a=>a.id===appId);
            if(app) return {module:mod,app};
        }
        if(mod.id===appId) return {module:mod,app:mod};
    }
    return null;
}

function getModFromUrl(){
    const params=new URLSearchParams(window.location.search);
    return params.get("mod");
}

/*=========================================================
  MODULE CONTENT
=========================================================*/

const moduleTables={
    nfe:{title:"NF-e",cols:["Número","Cliente","Valor","Status","Data"]},
    nfce:{title:"NFC-e",cols:["Número","Cliente","Valor","Status","Data"]},
    "notas-fiscais":{title:"Notas Fiscais",cols:["Número","Cliente","Valor","Status","Data"]},
    produtos:{title:"Produtos",cols:["Código","Produto","NCM","Estoque","Valor"]},
    clientes:{title:"Clientes",cols:["Código","Nome","CPF/CNPJ","Telefone","E-mail"]},
    estoque:{title:"Estoque",cols:["Produto","Quantidade","Unidade","Local","Valor"]},
    faturas:{title:"Faturas",cols:["Número","Cliente","Valor","Vencimento","Status"]},
    boletos:{title:"Boletos",cols:["Número","Cliente","Valor","Vencimento","Status"]},
    "config-empresas":{title:"Empresas",cols:["CNPJ","Razão Social","Fantasia","Regime","Status"]}
};

function showcaseHTML(){
    return `<!-- Tabs -->
<div class="glass-panel" style="margin-bottom:var(--space-6)">
    <h3 style="margin-bottom:var(--space-4)">Tabs</h3>
    <div id="showcase-tabs"></div>
</div>

<!-- Accordion -->
<div class="glass-panel" style="margin-bottom:var(--space-6)">
    <h3 style="margin-bottom:var(--space-4)">Accordion</h3>
    <div id="showcase-accordion"></div>
</div>

<!-- Badges & Tags -->
<div class="glass-panel" style="margin-bottom:var(--space-6)">
    <h3 style="margin-bottom:var(--space-4)">Badges & Tags</h3>
    <div style="display:flex;flex-wrap:wrap;gap:var(--space-3);align-items:center">
        ${Badge.render("Default")}
        ${Badge.render("Primary","primary")}
        ${Badge.render("Success","success")}
        ${Badge.render("Warning","warning")}
        ${Badge.render("Danger","danger")}
        ${Badge.render("Info","info")}
        ${Badge.tag("Tag fixa")}
        ${Badge.tag("Tag removível",true)}
        ${Badge.status("Ativo","success")}
        ${Badge.status("Pendente","warning")}
        ${Badge.status("Cancelado","danger")}
    </div>
</div>

<!-- Skeleton (exemplo estático) -->
<div class="glass-panel" style="margin-bottom:var(--space-6)">
    <h3 style="margin-bottom:var(--space-4)">Skeleton Loading</h3>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:var(--space-4)">
        ${Skeleton.kpi()}
        ${Skeleton.card(3)}
        ${Skeleton.widget()}
    </div>
</div>

<!-- Form System (Sprint 06) -->
<div class="glass-panel" style="margin-bottom:var(--space-6)">
    <h3 style="margin-bottom:var(--space-4)">Form System</h3>
    <div class="form-field">
        <label class="form-label">DatePicker</label>
        <input class="form-input" id="demo-datepicker" placeholder="DD/MM/AAAA">
    </div>
    <div class="form-field" style="margin-top:var(--space-3)">
        <label class="form-label">Autocomplete (cliente)</label>
        <input class="form-input" id="demo-autocomplete" placeholder="Digite 'mar' ou 'silva'...">
    </div>
    <div class="form-field" style="margin-top:var(--space-3)">
        <label class="form-label">Upload de arquivos</label>
        <div id="demo-upload"></div>
    </div>
</div>

<script>
    (function(){
        var dpInput=document.getElementById("demo-datepicker");
        if(dpInput&&window.DatePicker) new DatePicker(dpInput);

        var acInput=document.getElementById("demo-autocomplete");
        if(acInput&&window.Autocomplete){
            var clientes=["Maria Souza","Marcio Lima","Ana Silva","Pedro Santos","Marina Oliveira","Carlos Silva"];
            new Autocomplete(acInput,{source:clientes,minChars:1});
        }

        var upContainer=document.getElementById("demo-upload");
        if(upContainer&&window.FileUpload) new FileUpload(upContainer,{accept:"image/*,.pdf"});
    })();
</script>

<!-- DataGrid (Sprint 07) -->
<div class="glass-panel" style="margin-bottom:var(--space-6)">
    <h3 style="margin-bottom:var(--space-4)">DataGrid</h3>
    <div id="demo-datagrid"></div>
</div>

<script>
    (function(){
        var dgContainer=document.getElementById("demo-datagrid");
        if(dgContainer&&window.DataGrid){
            var demoData=[
                {id:1,nome:"Nota Fiscal Eletrônica",modulo:"NF-e",valor:15230.5,status:"ativo",data:"2026-07-01"},
                {id:2,nome:"Nota Fiscal ao Consumidor",modulo:"NFC-e",valor:892.9,status:"ativo",data:"2026-07-02"},
                {id:3,nome:"Conhecimento de Transporte",modulo:"CT-e",valor:4500,status:"pendente",data:"2026-07-03"},
                {id:4,nome:"Nota Fiscal de Serviço",modulo:"NFS-e",valor:3200.75,status:"cancelado",data:"2026-06-28"},
                {id:5,nome:"Manifesto de Documentos",modulo:"MDF-e",valor:12800,status:"ativo",data:"2026-07-04"},
                {id:6,nome:"Nota Fiscal Eletrônica",modulo:"NF-e",valor:7650.2,status:"pendente",data:"2026-07-05"},
                {id:7,nome:"NF-e Complementar",modulo:"NF-e",valor:980.3,status:"ativo",data:"2026-07-06"},
                {id:8,nome:"Cupom Fiscal",modulo:"NFC-e",valor:45.9,status:"cancelado",data:"2026-06-30"},
            ];
            new DataGrid(dgContainer,{
                columns:[
                    {field:"id",label:"Código",width:70,sortable:true},
                    {field:"nome",label:"Documento",width:250,sortable:true,filterable:true},
                    {field:"modulo",label:"Módulo",width:100,sortable:true},
                    {field:"valor",label:"Valor",width:120,sortable:true,formatter:"currency",align:"right"},
                    {field:"data",label:"Data",width:110,formatter:"date"},
                    {field:"status",label:"Status",width:110,formatter:"status"},
                ],
                data:demoData,
                pageSize:5,
                selectable:true,
                sortable:true,
                filterable:true,
                striped:true,
            });
        }
    })();
</script>

<!-- Dialog (demo buttons) -->
<div class="glass-panel" style="margin-bottom:var(--space-6)">
    <h3 style="margin-bottom:var(--space-4)">Dialog</h3>
    <div style="display:flex;flex-wrap:wrap;gap:var(--space-3)">
        <button class="btn btn-primary" data-dialog="alert" data-title="Aviso" data-message="Esta é uma mensagem de alerta!">Alert</button>
        <button class="btn btn-primary" data-dialog="confirm" data-title="Confirmação" data-message="Deseja confirmar esta ação?">Confirm</button>
        <button class="btn btn-primary" data-dialog="prompt" data-title="Entrada" data-message="Digite seu nome:">Prompt</button>
    </div>
</div>

<script>
    (function(){
        const tabContainer=document.getElementById("showcase-tabs");
        if(tabContainer&&window.Tabs){
            const tabs=new Tabs(tabContainer);
            tabs.define("html","HTML","<p>Conteúdo da aba <strong>HTML</strong></p>")
                .define("css","CSS","<p>Conteúdo da aba <strong>CSS</strong></p>")
                .define("js","JavaScript","<p>Conteúdo da aba <strong>JavaScript</strong></p>")
                .render("html");
        }
        const accContainer=document.getElementById("showcase-accordion");
        if(accContainer&&window.Accordion){
            window.accordion=new Accordion(accContainer);
            accordion.add("faq1","O que é o FiscalUI?","Framework visual corporativo zero dependências.")
                .add("faq2","Como funciona o tema?","CSS Variables + data-theme no HTML.")
                .add("faq3","Quantos componentes existem?","60+ componentes planejados.",true)
                .render();
        }
    })();
</script>`;
}

function moduleContent(appId){
    if(appId==="dashboard"){
        return `<div id="dashboard-container"></div>`;
    }
    if(appId==="showcase"){
        return showcaseHTML();
    }
    const cfg=moduleTables[appId];
    if(!cfg)return `<div class="glass-panel"><p class="workspace-placeholder">Módulo em desenvolvimento.</p></div>`;
    let rows="";
    for(let i=0;i<5;i++){
        rows+=`<tr>${cfg.cols.map(()=>"<td>—</td>").join("")}</tr>`;
    }
    return `
        <div class="glass-panel">
            <h3 style="margin-bottom:var(--space-4);font-size:var(--font-lg);font-weight:var(--font-semibold)">${cfg.title}</h3>
            <table>
                <thead><tr>${cfg.cols.map(c=>`<th>${c}</th>`).join("")}</tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

/*=========================================================
  CLOCK
=========================================================*/

let _clockInterval=null;

function startClock(){
    if(_clockInterval)clearInterval(_clockInterval);
    function tick(){
        const el=document.getElementById("status-clock");
        if(el)el.textContent=new Date().toLocaleString("pt-BR");
    }
    tick();
    _clockInterval=setInterval(tick,1000);
}

/*=========================================================
  RENDER LAUNCHPAD
=========================================================*/

function pageTransition(showLaunchpad, callback){
    const lp=document.getElementById("launchpad");
    const wv=document.getElementById("workspace-view");
    const target=showLaunchpad?lp:wv;
    const hide=showLaunchpad?wv:lp;
    if(!target)return callback();
    target.style.opacity="0";
    hide.style.opacity="0";
    setTimeout(()=>{
        callback();
        target.classList.remove("page-enter");
        void target.offsetWidth;
        target.classList.add("page-enter");
        target.style.opacity="1";
    },120);
}

function renderLaunchpad(){
    pageTransition(true,()=>{
    document.getElementById("launchpad").style.display="";
    document.getElementById("workspace-view").style.display="none";

    sidebar.renderLaunchpad(filteredMenu, userData);
    header.renderModules(filteredMenu, null);
    header.setTitle("FiscalBrasil");
    header.setBreadcrumb("");

    const nome=userData.nome||userData.usuario;
    const greetingEl=document.getElementById("welcome-greeting");
    if(greetingEl){
        const h=new Date().getHours();
        let g="Olá";
        if(h<12) g="Bom dia";
        else if(h<18) g="Boa tarde";
        else g="Boa noite";
        greetingEl.textContent=g+", "+nome;
    }

    const grid=document.getElementById("quick-grid");
    if(grid){
        grid.innerHTML=filteredMenu.filter(m=>!m.section).map(m=>`
            <a class="quick-card" href="${m.href||'#'}">
                <span class="quick-icon">
                    <svg class="icon icon-xl"><use href="#${m.icon}"/></svg>
                </span>
                <span class="quick-label">${m.label}</span>
            </a>
        `).join("");
    }

    document.getElementById("status-user").textContent="";
    const ce=userEmpresas.find(e=>e.id===currentEmpresaId);
    if(ce){
        const sc=document.getElementById("status-company");
        if(sc) sc.textContent=ce.nome;
    }
    startClock();
    });
}

/*=========================================================
  RENDER WORKSPACE
=========================================================*/

function renderWorkspace(appId){
    pageTransition(false,()=>{
    document.getElementById("launchpad").style.display="none";
    document.getElementById("workspace-view").style.display="flex";

    const found=findModuleByAppId(appId);
    const mod=found?found.module:null;
    const app=found?found.app:null;
    const title=app?app.label:(mod?mod.label:appId.toUpperCase());

    currentModule=mod;

    header.setBreadcrumb("FiscalBrasil / "+(mod?mod.label+"/":"")+title);
    header.setTitle(title);
    header.renderApps(mod?mod.apps:null, appId);

    const defaultActions=["+ Novo","Pesquisar"];
    toolbar.render(defaultActions);
    document.getElementById("workspace-content").innerHTML=moduleContent(appId);

    if(appId==="dashboard"){
        dashboard.init();
        const container=document.getElementById("dashboard-container");
        if(container)dashboard.renderDashboard(container);
    }

    const nome=userData.nome||userData.usuario;
    document.getElementById("status-user").textContent="Usuário: "+nome;
    startClock();

    sidebar.renderWorkspaceSidebar(mod, userData);
    sidebar.highlightActive();

    FiscalUI.emit("workspace:loaded",{modId:appId,title,module:mod});
    });
}

/*=========================================================
  NAVIGATION
=========================================================*/

window.goToLaunchpad=function(){
    history.pushState(null,"","/");
    renderLaunchpad();
};

/*=========================================================
  LOGOUT
=========================================================*/

window.logout=function(){
    apiFetch("/api/auth/logout",{method:"POST"}).catch(()=>{});
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");
    localStorage.removeItem("current_empresa_id");
    window.location.href="index.html";
};

/*=========================================================
  THEME — delegado ao ThemeManager (/js/services/ThemeManager.js)
=========================================================*/

/*=========================================================
  FILTERS
=========================================================*/

window.toggleFilters=function(){
    toolbar.toggleFilters();
};

window.clearFilters=function(){
    document.querySelectorAll(".filter-input").forEach(i=>i.value="");
    document.querySelectorAll(".filter-select").forEach(s=>s.selectedIndex=0);
};

/*=========================================================
  BOOT
=========================================================*/

(function boot(){
    const mod=getModFromUrl();
    if(mod&&findModuleByAppId(mod)){
        currentMod=mod;
        renderWorkspace(mod);
    }else{
        renderLaunchpad();
    }
    console.log("FiscalBrasil ERP loaded —",userData?.nome);
})();

/*=========================================================
  ROUTER SETUP
=========================================================*/

function setupFiscalUI(){
    function goMod(mod){
        if(mod&&findModuleByAppId(mod)){
            currentMod=mod;
            renderWorkspace(mod);
        }else{
            renderLaunchpad();
        }
    }

    FiscalUI.router
        .add("/",()=>renderLaunchpad())
        .add("/nfe",()=>goMod("nfe"))
        .add("/nfce",()=>goMod("nfce"))
        .add("/produtos",()=>goMod("produtos"))
        .add("/clientes",()=>goMod("clientes"))
        .add("/dashboard",()=>goMod("dashboard"))
        .add("/showcase",()=>renderWorkspace("showcase"));

    const curPath=window.location.pathname+window.location.search;
    FiscalUI.router.resolve(curPath);
    FiscalUI.state.set("currentPath",curPath);

    FiscalUI.plugins.register("shortcuts",ShortcutsPlugin);
    FiscalUI.plugins.enable("shortcuts");

    const sp=FiscalUI.plugins.get("shortcuts")._instance;
    sp.add(["Ctrl","N"],"Novo",()=>console.log("Novo"));
    sp.add(["Ctrl","F"],"Pesquisar",()=>document.querySelector(".filter-input")?.focus());
    sp.add(["Escape"],"Fechar modal",()=>{
        if(FiscalUI.state.get("modalOpen"))FiscalUI.modal.close();
    });

    const pickerContainer=document.getElementById("theme-picker-container");
    if(pickerContainer&&window.themeManager){
        themeManager.renderPicker(pickerContainer);
    }

    if(window.FiscalUI&&FiscalUI.responsiveLayout){
        const hamburgerContainer=document.getElementById("hamburger-container");
        if(hamburgerContainer)FiscalUI.responsiveLayout.renderHamburger(hamburgerContainer);
    }
}

if(window.FiscalUI&&FiscalUI.state&&FiscalUI.state.get("theme")){
    setupFiscalUI();
}else{
    FiscalUI.on("fiscalui:ready",setupFiscalUI);
}

window.goToLaunchpad=function(){
    if(FiscalUI.router) FiscalUI.router.navigate("/");
};
