class FileUpload{

    constructor(container,options={}){
        this._container=container;
        this._accept=options.accept||"*/*";
        this._maxSize=options.maxSize||5*1024*1024;
        this._multiple=options.multiple||false;
        this._onUpload=options.onUpload||null;
        this._files=[];
        this._init();
    }

    _init(){
        this._container.innerHTML=`
            <div class="upload-zone" id="upload-${this._container.id||Math.random().toString(36).slice(2)}">
                <div class="upload-placeholder">
                    <svg class="icon icon-upload"><use href="#icon-upload"/></svg>
                    <p class="upload-text">Arraste arquivos aqui ou clique para selecionar</p>
                    <span class="upload-hint">${this._accept} — máx ${(this._maxSize/1024/1024).toFixed(1)}MB</span>
                </div>
                <input type="file" class="upload-input" accept="${this._accept}" ${this._multiple?"multiple":""}>
                <div class="upload-preview"></div>
            </div>
        `;
        this._zone=this._container.querySelector(".upload-zone");
        this._input=this._container.querySelector(".upload-input");
        this._preview=this._container.querySelector(".upload-preview");

        this._input.addEventListener("change",()=>this._handleFiles(this._input.files));

        this._zone.addEventListener("dragover",e=>{
            e.preventDefault();
            this._zone.classList.add("upload-dragover");
        });
        this._zone.addEventListener("dragleave",()=>{
            this._zone.classList.remove("upload-dragover");
        });
        this._zone.addEventListener("drop",e=>{
            e.preventDefault();
            this._zone.classList.remove("upload-dragover");
            this._handleFiles(e.dataTransfer.files);
        });
        this._zone.addEventListener("click",()=>this._input.click());

        this._zone.querySelector(".upload-placeholder").style.pointerEvents="none";
    }

    _handleFiles(fileList){
        Array.from(fileList).forEach(file=>{
            if(file.size>this._maxSize){
                FiscalUI.toast?.error("Arquivo muito grande: "+file.name);
                return;
            }
            if(!this._multiple)this._files=[];
            this._files.push(file);
            this._renderPreview(file);
        });
        this._input.value="";
        FiscalUI.emit("upload:files",{files:this._files});
    }

    _renderPreview(file){
        const card=document.createElement("div");
        card.className="upload-card";
        const isImage=file.type.startsWith("image/");
        const size=(file.size/1024).toFixed(1)+" KB";
        const reader=new FileReader();
        reader.onload=e=>{
            card.innerHTML=`
                ${isImage?`<img class="upload-thumb" src="${e.target.result}" alt="${file.name}">`:`<div class="upload-thumb upload-thumb-file"><svg class="icon"><use href="#icon-file"/></svg></div>`}
                <div class="upload-card-info">
                    <span class="upload-card-name">${file.name}</span>
                    <span class="upload-card-size">${size}</span>
                </div>
                <button class="upload-card-remove" title="Remover">&times;</button>
                <div class="upload-progress"><div class="upload-progress-bar" style="width:0%"></div></div>
            `;
            card.querySelector(".upload-card-remove").addEventListener("click",e=>{
                e.stopPropagation();
                const idx=this._files.indexOf(file);
                if(idx>-1)this._files.splice(idx,1);
                card.remove();
                FiscalUI.emit("upload:remove",{file,files:this._files});
            });
            this._preview.appendChild(card);
            this._simulateProgress(card);
        };
        if(isImage)reader.readAsDataURL(file);
        else reader.onload();
    }

    _simulateProgress(card){
        const bar=card.querySelector(".upload-progress-bar");
        if(!bar)return;
        let p=0;
        const interval=setInterval(()=>{
            p+=Math.random()*15+5;
            if(p>=100){
                p=100;
                clearInterval(interval);
                bar.style.width="100%";
                bar.style.background="var(--color-success)";
                card.classList.add("upload-done");
                FiscalUI.emit("upload:complete",{card});
                if(this._onUpload)this._onUpload(p,card);
                return;
            }
            bar.style.width=p+"%";
            if(this._onUpload)this._onUpload(p,card);
        },200);
    }

    files(){
        return this._files;
    }

    reset(){
        this._files=[];
        this._preview.innerHTML="";
        this._input.value="";
    }
}

window.FileUpload=FileUpload;
