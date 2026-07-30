class ThemeManager{

    constructor(events,state,storage){
        this._events=events;
        this._state=state;
        this._storage=storage;
        this._themes=[
            {id:"dark",label:"Escuro",icon:"icon-moon",color:"#0f172a"},
            {id:"light",label:"Claro",icon:"icon-sun",color:"#f8fafc"},
            {id:"high-contrast",label:"Alto Contraste",icon:"icon-eye",color:"#000000"},
            {id:"separator"},
            {id:"corporate-blue",label:"Corporativo Azul",icon:"icon-building",color:"#2563eb"},
            {id:"corporate-green",label:"Corporativo Verde",icon:"icon-building",color:"#16a34a"},
            {id:"corporate-purple",label:"Corporativo Roxo",icon:"icon-building",color:"#7c3aed"},
        ];
    }

    init(){
        const saved=this._storage.get("theme","dark");
        this._apply(saved);
        this._state.observe("theme",({value})=>{
            this._apply(value);
        });
        this._events.on("theme:set",({theme})=>{
            this._state.set("theme",theme);
        });
    }

    _apply(theme){
        document.documentElement.setAttribute("data-theme",theme);
        this._storage.set("theme",theme);
        const iconMap={};
        this._themes.forEach(t=>iconMap[t.id]=t.icon);
        const el=document.getElementById("theme-icon");
        if(el)el.setAttribute("href","#"+iconMap[theme]);
        const picker=document.getElementById("theme-picker");
        if(picker){
            picker.querySelectorAll(".theme-opt").forEach(opt=>{
                opt.classList.toggle("active",opt.dataset.theme===theme);
            });
        }
    }

    list(){
        return this._themes;
    }

    current(){
        return this._state.get("theme")||"dark";
    }

    set(themeId){
        this._state.set("theme",themeId);
    }

    renderPicker(container){
        if(!container)return;
        const current=this.current();
        container.innerHTML=`
            <button class="topbar-icon-btn" id="theme-toggle-btn" title="Tema: clique para trocar">
                <svg class="icon"><use href="#icon-palette"/></svg>
            </button>
            <div class="theme-dropdown" id="theme-picker">
                ${this._themes.map(t=>{
                    if(t.id==="separator") return '<div class="theme-separator"><span>Corporativo</span></div>';
                    return `
                    <div class="theme-opt ${t.id===current?'active':''}" data-theme="${t.id}" onclick="themeManager.set('${t.id}')">
                        <span class="theme-swatch" style="background:${t.color}"></span>
                        <span class="theme-label">${t.label}</span>
                        <svg class="icon icon-check"><use href="#icon-check"/></svg>
                    </div>`;
                }).join("")}
                <div class="theme-separator"><span>Personalizar</span></div>
                <div class="theme-opt" onclick="window.themeManager._openCustomizer()">
                    <span class="theme-swatch theme-swatch-custom"><svg class="icon icon-12"><use href="#icon-edit"/></svg></span>
                    <span class="theme-label">Cor personalizada...</span>
                </div>
            </div>
        `;
        const btn=container.querySelector("#theme-toggle-btn");
        const dropdown=container.querySelector("#theme-picker");
        btn.addEventListener("click",e=>{
            e.stopPropagation();
            dropdown.classList.toggle("open");
        });
        document.addEventListener("click",()=>dropdown.classList.remove("open"),{once:false});
    }

    _openCustomizer(){
        const current=this.current();
        const picker=document.getElementById("theme-picker");
        if(picker)picker.classList.remove("open");
        const colorInput=document.createElement("input");
        colorInput.type="color";
        colorInput.value=current==="dark"?"#14b8a6":"#0f766e";
        colorInput.style.position="fixed";
        colorInput.style.opacity="0";
        colorInput.style.pointerEvents="none";
        document.body.appendChild(colorInput);
        colorInput.addEventListener("input",()=>this._applyCustom(colorInput.value));
        colorInput.addEventListener("change",()=>{
            const val=colorInput.value;
            this._storage.set("custom_color",val);
            colorInput.remove();
            FiscalUI.toast?.success("Cor personalizada salva!");
        });
        setTimeout(()=>colorInput.click(),50);
    }

    _applyCustom(hex){
        document.documentElement.style.setProperty("--color-primary",hex);
        const hover=this._darken(hex,12);
        document.documentElement.style.setProperty("--color-primary-hover",hover);
        const active=this._darken(hex,20);
        document.documentElement.style.setProperty("--color-primary-active",active);
        this._storage.set("custom_color",hex);
        this._state.set("theme","dark");
        const picker=document.getElementById("theme-picker");
        if(picker){
            picker.querySelectorAll(".theme-opt").forEach(o=>o.classList.toggle("active",false));
        }
        const icon=document.getElementById("theme-icon");
        if(icon)icon.setAttribute("href","#icon-palette");
    }

    _darken(hex,pct){
        const num=parseInt(hex.slice(1),16);
        const r=Math.max(0,(num>>16)-Math.round((num>>16)*pct/100));
        const g=Math.max(0,((num>>8)&255)-Math.round(((num>>8)&255)*pct/100));
        const b=Math.max(0,(num&255)-Math.round((num&255)*pct/100));
        return "#"+(r*65536+g*256+b).toString(16).padStart(6,"0");
    }
}

window.ThemeManager=ThemeManager;
