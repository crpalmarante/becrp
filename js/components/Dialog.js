class Dialog{

    constructor(){
        this._modal=null;
    }

    _getModal(){
        if(!this._modal){
            this._modal=document.createElement("div");
            this._modal.className="dialog-overlay";
            this._modal.innerHTML=`
                <div class="dialog-box">
                    <div class="dialog-header">
                        <h3 class="dialog-title"></h3>
                        <button class="dialog-close">&times;</button>
                    </div>
                    <div class="dialog-body"></div>
                    <div class="dialog-footer"></div>
                </div>
            `;
            this._modal.querySelector(".dialog-close").onclick=()=>this.close();
            this._modal.addEventListener("click",e=>{if(e.target===this._modal)this.close()});
            document.body.appendChild(this._modal);
        }
        return this._modal;
    }

    open(config){
        const m=this._getModal();
        m.querySelector(".dialog-title").textContent=config.title||"";
        m.querySelector(".dialog-body").innerHTML=typeof config.body==="string"?config.body:"";
        if(config.content instanceof HTMLElement){
            m.querySelector(".dialog-body").appendChild(config.content);
        }
        const footer=m.querySelector(".dialog-footer");
        footer.innerHTML="";
        if(config.buttons){
            config.buttons.forEach(btn=>{
                const el=document.createElement("button");
                el.textContent=btn.label||"";
                el.className="dialog-btn dialog-btn-"+((btn.variant||"primary").toLowerCase());
                el.onclick=()=>{
                    if(btn.action)btn.action();
                    if(btn.close!==false)this.close();
                };
                footer.appendChild(el);
            });
        }
        m.classList.add("dialog-open");
        FiscalUI.emit("dialog:open",config);
        return this;
    }

    close(){
        const m=this._getModal();
        m.classList.remove("dialog-open");
        FiscalUI.emit("dialog:close",{});
    }

    alert(message,title="Aviso"){
        return new Promise(resolve=>{
            this.open({title,body:"<p>"+message+"</p>",buttons:[{label:"OK",variant:"primary",action:()=>resolve(true)}]});
        });
    }

    confirm(message,title="Confirmação"){
        return new Promise(resolve=>{
            this.open({title,body:"<p>"+message+"</p>",buttons:[
                {label:"Cancelar",variant:"secondary",action:()=>resolve(false)},
                {label:"Confirmar",variant:"primary",action:()=>resolve(true)}
            ]});
        });
    }

    prompt(message,value="",title="Entrada"){
        return new Promise(resolve=>{
            const input=document.createElement("input");
            input.className="form-input dialog-input";
            input.value=value;
            input.placeholder=message;
            const body=document.createElement("div");
            body.style.cssText="display:flex;flex-direction:column;gap:12px";
            body.innerHTML="<p>"+message+"</p>";
            body.appendChild(input);
            this.open({title,content:body,buttons:[
                {label:"Cancelar",variant:"secondary",action:()=>resolve(null)},
                {label:"OK",variant:"primary",action:()=>resolve(input.value)}
            ]});
            setTimeout(()=>input.focus(),100);
        });
    }
}

window.Dialog=Dialog;
