class Toolbar{

    constructor(){
        this._el=document.getElementById("workspace-toolbar");
        this._filters=document.getElementById("workspace-filters");
        this._currentView="list";
    }

    render(actions){
        if(!this._el)return;
        const allActions=actions.slice();
        allActions.push("Filtros");
        this._el.innerHTML=`
            <div class="toolbar-actions">
                ${allActions.map(a=>{
                    if(a==="Filtros") return `<button class="toolbar-btn filter-toggle" onclick="toolbar.toggleFilters()">${a}</button>`;
                    return `<button class="toolbar-btn${a.startsWith('+')?' primary':''}">${a}</button>`;
                }).join("")}
            </div>
            <div class="toolbar-view-switcher">
                <button class="view-btn active" data-view="list" onclick="toolbar.setView('list')" title="Lista">
                    <svg class="icon icon-16"><use href="#icon-list"/></svg>
                </button>
                <button class="view-btn" data-view="grid" onclick="toolbar.setView('grid')" title="Grid">
                    <svg class="icon icon-16"><use href="#icon-grid"/></svg>
                </button>
            </div>
        `;
    }

    toggleFilters(){
        if(!this._filters)return;
        const visible=this._filters.style.display!=="none";
        this._filters.style.display=visible?"none":"";
    }

    setView(view){
        this._currentView=view;
        document.querySelectorAll(".view-btn").forEach(btn=>{
            btn.classList.toggle("active",btn.dataset.view===view);
        });
        FiscalUI.emit("toolbar:viewChange",{view});
    }

    getCurrentView(){
        return this._currentView;
    }
}

window.Toolbar=Toolbar;
