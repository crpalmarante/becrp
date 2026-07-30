class Header{

    constructor(){
        this._nav=document.getElementById("topbar-nav");
        this._userName=document.getElementById("topbar-user-name");
        this._title=document.querySelector(".topbar-title");
    }

    renderModules(modules, activeModId){
        if(!this._nav)return;
        this._nav.innerHTML=modules.map(m=>{
            const href=m.href||"#";
            const active=m.id===activeModId?"active":"";
            return `<a href="${href}" data-id="${m.id}" class="${active}">${m.label}</a>`;
        }).join("");
    }

    renderApps(apps, activeAppId){
        if(!this._nav)return;
        if(!apps||apps.length===0){
            this._nav.innerHTML="";
            return;
        }
        this._nav.innerHTML=apps.map(a=>{
            const active=a.id===activeAppId?"active":"";
            return `<a href="${a.href}" data-id="${a.id}" class="${active}">${a.label}</a>`;
        }).join("");
    }

    setUser(userData){
        if(!this._userName)return;
        this._userName.textContent=userData.nome||userData.usuario;
    }

    setTitle(title){
        if(this._title)this._title.textContent=title;
    }

    setBreadcrumb(path){
        const el=document.getElementById("workspace-breadcrumb");
        if(el)el.textContent=path;
    }
}

window.Header=Header;
