class Tabs{

    constructor(container){
        this._container=container;
        this._tabs=[];
        this._activeTab=null;
    }

    define(id, label, content){
        this._tabs.push({id,label,content});
        return this;
    }

    render(activeId){
        if(!this._container)return;
        const active=activeId||(this._tabs.length>0?this._tabs[0].id:null);
        this._activeTab=active;

        this._container.innerHTML=`
            <div class="tabs-header" role="tablist">
                ${this._tabs.map(t=>`
                    <button class="tab-btn ${t.id===active?'active':''}"
                        role="tab"
                        aria-selected="${t.id===active}"
                        onclick="tabs.switch('${t.id}')">
                        ${t.label}
                    </button>
                `).join("")}
            </div>
            <div class="tabs-body">
                ${this._tabs.map(t=>`
                    <div class="tab-panel ${t.id===active?'active':''}"
                        role="tabpanel"
                        id="tabpanel-${t.id}">
                        ${t.content}
                    </div>
                `).join("")}
            </div>
        `;
    }

    switch(id){
        this._activeTab=id;
        this._container.querySelectorAll(".tab-btn").forEach(btn=>{
            btn.classList.toggle("active",btn.textContent.trim()===this._tabs.find(t=>t.id===id)?.label);
        });
        this._container.querySelectorAll(".tab-panel").forEach(panel=>{
            panel.classList.toggle("active",panel.id==="tabpanel-"+id);
        });
        FiscalUI.emit("tabs:switch",{tabsId:this._container.id,tabs:this,tabId:id});
    }

    active(){
        return this._activeTab;
    }
}

window.Tabs=Tabs;
