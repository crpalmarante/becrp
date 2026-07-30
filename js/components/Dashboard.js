class Dashboard{

    constructor(){
        this.widgets=new WidgetManager();
        this._kpiData=[
            {id:"kpi-receita",label:"Faturamento Hoje",value:0,prefix:"R$",format:"money",icon:"icon-dollar",color:"primary"},
            {id:"kpi-pedidos",label:"Pedidos Pendentes",value:0,format:"number",icon:"icon-file-text",color:"warning"},
            {id:"kpi-notas",label:"Notas Emitidas",value:0,format:"number",icon:"icon-printer",color:"info"},
            {id:"kpi-clientes",label:"Clientes Ativos",value:0,format:"number",icon:"icon-users",color:"success"}
        ];
    }

    init(){
        this._defineWidgets();
    }

    _defineWidgets(){
        this.widgets.define("kpi-receita",{
            title:"Faturamento Hoje",
            icon:"icon-dollar",
            category:"kpi",
            size:"sm",
            load:()=>this._loadKPI("receita"),
            render:(data)=>this._renderKPI({...this._kpiData[0],...data})
        });
        this.widgets.define("kpi-pedidos",{
            title:"Pedidos Pendentes",
            icon:"icon-file-text",
            category:"kpi",
            size:"sm",
            load:()=>this._loadKPI("pedidos"),
            render:(data)=>this._renderKPI({...this._kpiData[1],...data})
        });
        this.widgets.define("kpi-notas",{
            title:"Notas Emitidas",
            icon:"icon-printer",
            category:"kpi",
            size:"sm",
            load:()=>this._loadKPI("notas"),
            render:(data)=>this._renderKPI({...this._kpiData[2],...data})
        });
        this.widgets.define("kpi-clientes",{
            title:"Clientes Ativos",
            icon:"icon-users",
            category:"kpi",
            size:"sm",
            load:()=>this._loadKPI("clientes"),
            render:(data)=>this._renderKPI({...this._kpiData[3],...data})
        });

        this.widgets.define("quick-actions",{
            title:"Ações Rápidas",
            icon:"icon-plus",
            category:"acoes",
            size:"md",
            load:()=>Promise.resolve({}),
            render:()=>this._renderQuickActions()
        });

        this.widgets.define("recent-activity",{
            title:"Atividade Recente",
            icon:"icon-clock",
            category:"info",
            size:"md",
            load:()=>this._loadActivity(),
            render:(data)=>this._renderActivity(data)
        });

        this.widgets.define("chart-vendas",{
            title:"Vendas (30 dias)",
            icon:"icon-file-text",
            category:"chart",
            size:"lg",
            load:()=>this._loadChart(),
            render:(data)=>this._renderChart(data)
        });
    }

    async renderDashboard(container){
        if(!container)return;
        container.innerHTML=`
            <div class="dashboard-kpis" id="dashboard-kpis"></div>
            <div class="dashboard-widgets" id="dashboard-widgets"></div>
        `;

        const kpis=container.querySelector("#dashboard-kpis");
        const widgets=container.querySelector("#dashboard-widgets");

        for(const id of["kpi-receita","kpi-pedidos","kpi-notas","kpi-clientes"]){
            await this.widgets.create(id, kpis);
        }
        await this.widgets.renderAll();

        for(const id of["quick-actions","recent-activity","chart-vendas"]){
            await this.widgets.create(id, widgets);
        }
        await this.widgets.renderAll();

        this.widgets.startAll();
    }

    async _loadKPI(type){
        const mockData={
            receita:{value:45890.00,change:12.5},
            pedidos:{value:23,change:-3},
            notas:{value:156,change:8.2},
            clientes:{value:89,change:2.1}
        };
        return mockData[type]||{value:0,change:0};
    }

    _renderKPI(data){
        const colorClass=data.color||"primary";
        const value=this._formatValue(data.value, data.format||"number");
        const signal=data.change>=0?"+":"";
        const changeClass=data.change>=0?"kpi-change-up":"kpi-change-down";
        return `
            <div class="kpi-card kpi-${colorClass}">
                <div class="kpi-header">
                    <span class="kpi-icon">
                        <svg class="icon icon-lg"><use href="#${data.icon}"/></svg>
                    </span>
                    <span class="kpi-change ${changeClass}">${signal}${data.change}%</span>
                </div>
                <div class="kpi-value" data-target="${data.value}">${value}</div>
                <div class="kpi-label">${data.label}</div>
            </div>
        `;
    }

    _renderQuickActions(){
        const actions=[
            {label:"Nova NF-e",icon:"icon-plus",href:"?mod=nfe"},
            {label:"Novo Pedido",icon:"icon-file-text",href:"?mod=pedidos-venda"},
            {label:"Nova NFC-e",icon:"icon-printer",href:"?mod=nfce"},
            {label:"Rel. Vendas",icon:"icon-file-text",href:"?mod=rel-vendas"}
        ];
        return `
            <div class="widget-header">
                <svg class="icon icon-md"><use href="#icon-plus"/></svg>
                <span class="widget-title">Ações Rápidas</span>
            </div>
            <div class="quick-actions-grid">
                ${actions.map(a=>`
                    <a class="quick-action-btn" href="${a.href}">
                        <svg class="icon"><use href="#${a.icon}"/></svg>
                        <span>${a.label}</span>
                    </a>
                `).join("")}
            </div>
        `;
    }

    async _loadActivity(){
        return {
            items:[
                {text:"NF-e 000001 autorizada",time:"2 min atrás",type:"success"},
                {text:"Pedido #1234 criado",time:"15 min atrás",type:"info"},
                {text:"NFC-e 000056 cancelada",time:"1 h atrás",type:"warning"},
                {text:"Cliente ACME Ltda cadastrado",time:"2 h atrás",type:"info"},
                {text:"Boleto #789 vence hoje",time:"3 h atrás",type:"danger"}
            ]
        };
    }

    _renderActivity(data){
        const items=data.items||[];
        return `
            <div class="widget-header">
                <svg class="icon icon-md"><use href="#icon-clock"/></svg>
                <span class="widget-title">Atividade Recente</span>
            </div>
            <div class="activity-list">
                ${items.map(i=>`
                    <div class="activity-item">
                        <span class="activity-dot activity-${i.type}"></span>
                        <div class="activity-content">
                            <span class="activity-text">${i.text}</span>
                            <span class="activity-time">${i.time}</span>
                        </div>
                    </div>
                `).join("")}
            </div>
        `;
    }

    async _loadChart(){
        return {
            labels:["Sem 1","Sem 2","Sem 3","Sem 4"],
            values:[28500,34200,29800,45890]
        };
    }

    _renderChart(data){
        const labels=data.labels||[];
        const values=data.values||[];
        const max=Math.max(...values,1);
        return `
            <div class="widget-header">
                <svg class="icon icon-md"><use href="#icon-file-text"/></svg>
                <span class="widget-title">Vendas (30 dias)</span>
            </div>
            <div class="chart-bars">
                ${labels.map((l,i)=>`
                    <div class="chart-bar-col">
                        <div class="chart-bar" style="height:${(values[i]/max)*100}%">
                            <span class="chart-bar-value">R$ ${(values[i]/1000).toFixed(1)}k</span>
                        </div>
                        <span class="chart-bar-label">${l}</span>
                    </div>
                `).join("")}
            </div>
        `;
    }

    _formatValue(value, format){
        if(format==="money"){
            return "R$ "+value.toLocaleString("pt-BR",{minimumFractionDigits:2});
        }
        return value.toLocaleString("pt-BR");
    }
}

window.Dashboard=Dashboard;
