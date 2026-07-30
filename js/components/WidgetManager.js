class WidgetManager{

    constructor(){
        this._registry=new Map();
        this._instances=new Map();
    }

    define(id, config){
        this._registry.set(id, {
            id,
            title:config.title||id,
            icon:config.icon||"icon-file-text",
            category:config.category||"geral",
            size:config.size||"md",
            render:config.render||(()=>""),
            async load:config.load||(()=>Promise.resolve()),
            refresh:config.refresh||null,
            interval:config.interval||0
        });
    }

    async create(id, container){
        const def=this._registry.get(id);
        if(!def){console.warn("Widget not found:",id);return;}

        const el=document.createElement("div");
        el.className=`dashboard-widget widget-${def.size}`;
        el.dataset.widgetId=id;
        container.appendChild(el);

        const instance={
            id,def,el,
            _timer:null,
            data:null
        };

        this._instances.set(id, instance);
        return instance;
    }

    async render(id){
        const inst=this._instances.get(id);
        if(!inst)return;
        const def=inst.def;

        try{
            inst.data=await def.load();
        }catch(e){
            console.warn("Widget load error:",id,e);
        }

        inst.el.innerHTML=def.render(inst.data||{});
    }

    async renderAll(){
        for(const id of this._instances.keys()){
            await this.render(id);
        }
    }

    startRefresh(id){
        const inst=this._instances.get(id);
        if(!inst||!inst.def.refresh||!inst.def.interval)return;
        inst._timer=setInterval(()=>{
            this.render(id);
        },inst.def.interval);
    }

    startAll(){
        for(const id of this._instances.keys()){
            this.startRefresh(id);
        }
    }

    stopAll(){
        for(const inst of this._instances.values()){
            if(inst._timer)clearInterval(inst._timer);
        }
    }

    destroy(id){
        const inst=this._instances.get(id);
        if(!inst)return;
        if(inst._timer)clearInterval(inst._timer);
        inst.el.remove();
        this._instances.delete(id);
    }
}

window.WidgetManager=WidgetManager;
