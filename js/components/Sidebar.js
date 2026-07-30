class Sidebar{

    constructor(){
        this._el=document.getElementById("sidebar");
    }

    renderModules(modules){
        let html="";
        for(const mod of modules){
            const hasApps=mod.apps&&mod.apps.length>0;
            const href=mod.href||"#";
            if(hasApps){
                html+=`<div class="menu-item has-children" data-id="${mod.id}" title="${mod.label}" onclick="sidebar.toggleSubmenu('${mod.id}')">
                    <svg class="icon"><use href="#${mod.icon}"/></svg>
                    <span class="menu-label">${mod.label}</span>
                    <svg class="icon icon-16 menu-arrow"><use href="#icon-chevron-down"/></svg>
                </div>`;
                html+=`<div class="menu-submenu" id="sub-${mod.id}">`;
                html+=this.renderApps(mod.apps);
                html+=`</div>`;
            }else{
                html+=`<a class="menu-item" href="${href}" data-id="${mod.id}" title="${mod.label}">
                    <svg class="icon"><use href="#${mod.icon}"/></svg>
                    <span class="menu-label">${mod.label}</span>
                </a>`;
            }
        }
        return html;
    }

    renderApps(apps){
        let html="";
        for(const app of apps){
            if(app.section){
                html+=`<div class="menu-section">${app.section}</div>`;
                continue;
            }
            html+=`<a class="menu-item" href="${app.href}" data-id="${app.id}" title="${app.label}">
                <svg class="icon"><use href="#${app.icon}"/></svg>
                <span class="menu-label">${app.label}</span>
            </a>`;
        }
        return html;
    }

    renderLaunchpad(modules, userData){
        const sidebar=this._el;
        if(!sidebar)return;
        sidebar.innerHTML=`
            <div class="sidebar-brand">
                <svg class="icon"><use href="#icon-building"/></svg>
                <span class="brand-text">FiscalBrasil</span>
            </div>
            <div class="sidebar-collapse" onclick="sidebar.toggle()">
                <svg class="icon"><use href="#icon-chevron-left"/></svg>
            </div>
            <nav class="sidebar-nav">
                ${this.renderModules(modules)}
            </nav>
            <div class="sidebar-recentes">
                <div class="recentes-title">Recentes</div>
                <a class="recente-item" href="#">
                    <svg class="icon icon-16"><use href="#icon-clock"/></svg>
                    <span class="menu-label">Nenhum acesso recente</span>
                </a>
            </div>
            ${this._userSection(userData)}
        `;
        this.highlightActive();
    }

    renderWorkspaceSidebar(mod, userData){
        const sidebar=this._el;
        if(!sidebar)return;
        let sidebarHtml=`
            <div class="sidebar-brand" onclick="goToLaunchpad()" style="cursor:pointer">
                <svg class="icon"><use href="#icon-chevron-left"/></svg>
                <span class="brand-text">Voltar</span>
            </div>
            <div class="sidebar-collapse" onclick="sidebar.toggle()">
                <svg class="icon"><use href="#icon-chevron-left"/></svg>
            </div>
        `;
        if(mod&&mod.apps&&mod.apps.length>0){
            sidebarHtml+=`<div class="sidebar-context-title">${mod.label}</div>`;
            sidebarHtml+=`<nav class="sidebar-nav">${this.renderApps(mod.apps)}</nav>`;
        }else{
            sidebarHtml+=`<nav class="sidebar-nav">
                <a class="menu-item active" href="#">
                    <svg class="icon"><use href="#icon-file-text"/></svg>
                    <span class="menu-label">${mod?mod.label:"Módulo"}</span>
                </a>
            </nav>`;
        }
        sidebarHtml+=`<div class="sidebar-recentes">
            <div class="recentes-title">Recentes</div>
            <a class="recente-item" href="#">
                <svg class="icon icon-16"><use href="#icon-clock"/></svg>
                <span class="menu-label">Último acesso</span>
            </a>
        </div>`;
        sidebarHtml+=this._userSection(userData);
        sidebar.innerHTML=sidebarHtml;
    }

    toggle(){
        const sidebar=this._el;
        sidebar.classList.toggle("collapsed");
        const collapsed=sidebar.classList.contains("collapsed");
        localStorage.setItem("sidebar_collapsed",collapsed);
        if(window.FiscalUI) FiscalUI.state.set("sidebarCollapsed",collapsed);
    }

    toggleSubmenu(id){
        const el=document.getElementById("sub-"+id);
        if(!el)return;
        el.classList.toggle("open");
        const arrow=el.previousElementSibling?.querySelector(".menu-arrow");
        if(arrow)arrow.classList.toggle("rotated");
    }

    highlightActive(){
        const current=window.location.search||window.location.pathname.split("/").pop()||"";
        document.querySelectorAll(".menu-item").forEach(el=>{
            const href=el.getAttribute("href")||"";
            if(href===current||href===window.location.pathname.split("/").pop()){
                el.classList.add("active");
                let parent=el.closest(".menu-submenu");
                while(parent){
                    parent.classList.add("open");
                    const prev=parent.previousElementSibling;
                    if(prev&&prev.classList.contains("has-children")){
                        const arrow=prev.querySelector(".menu-arrow");
                        if(arrow)arrow.classList.add("rotated");
                    }
                    parent=parent.parentElement?.closest(".menu-submenu");
                }
            }
        });
    }

    toggleMobile(){
        const sidebar=this._el;
        sidebar.classList.toggle("mobile-open");
        let overlay=document.querySelector(".sidebar-overlay");
        if(!overlay){
            overlay=document.createElement("div");
            overlay.className="sidebar-overlay";
            overlay.onclick=()=>{
                sidebar.classList.remove("mobile-open");
                overlay.classList.remove("open");
            };
            document.body.appendChild(overlay);
        }
        overlay.classList.toggle("open",sidebar.classList.contains("mobile-open"));
    }

    _userSection(userData){
        const nome=userData.nome||userData.usuario;
        const tipo=userData.tipo==="usuario"?"Administrador":"Funcionário";
        return `
            <div class="sidebar-user">
                <div class="user-avatar">${nome.charAt(0).toUpperCase()}</div>
                <div class="user-info">
                    <div class="user-name">${nome}</div>
                    <div class="user-role">${tipo}</div>
                </div>
                <button class="user-logout" onclick="logout()" title="Sair">
                    <svg class="icon"><use href="#icon-logout"/></svg>
                </button>
            </div>
        `;
    }
}

window.Sidebar=Sidebar;
