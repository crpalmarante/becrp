class Autocomplete{

    constructor(input,options={}){
        this._input=input;
        this._source=options.source||[];
        this._async=typeof this._source==="function";
        this._minChars=options.minChars||2;
        this._debounceMs=options.debounce||250;
        this._onSelect=null;
        this._dropdown=null;
        this._selectedIndex=-1;
        this._loading=false;
        this._items=[];
        this._abort=null;
        this._init();
    }

    _init(){
        this._input.setAttribute("autocomplete","off");
        this._input.addEventListener("input",()=>this._onInput());
        this._input.addEventListener("focus",()=>{
            if(this._items.length>0)this._show();
        });
        this._input.addEventListener("keydown",e=>this._onKeydown(e));
        document.addEventListener("click",e=>{
            if(this._dropdown&&!this._dropdown.contains(e.target)&&e.target!==this._input){
                this._hide();
            }
        });
    }

    _onInput(){
        const val=this._input.value.trim();
        if(val.length<this._minChars){
            this._items=[];
            this._hide();
            return;
        }
        if(this._debounceTimer)clearTimeout(this._debounceTimer);
        this._debounceTimer=setTimeout(()=>this._search(val),this._debounceMs);
    }

    async _search(val){
        if(this._abort)this._abort.abort();
        if(this._async){
            this._loading=true;
            this._abort=new AbortController();
            try{
                const result=await this._source(val,this._abort.signal);
                this._items=result||[];
            }catch(e){
                if(e.name!=="AbortError")this._items=[];
            }
            this._loading=false;
        }else{
            const q=val.toLowerCase();
            this._items=this._source.filter(item=>{
                const label=typeof item==="string"?item:item.label||item.name||"";
                return label.toLowerCase().includes(q);
            });
        }
        this._selectedIndex=-1;
        this._items.length>0?this._show():this._hide();
    }

    _show(){
        this._hide();
        if(this._items.length===0)return;
        this._dropdown=document.createElement("div");
        this._dropdown.className="autocomplete-dropdown show";
        this._dropdown.innerHTML=this._items.map((item,i)=>{
            const label=typeof item==="string"?item:item.label||item.name||"";
            return `<div class="autocomplete-item" data-index="${i}">${this._highlight(label)}</div>`;
        }).join("");
        document.body.appendChild(this._dropdown);
        const rect=this._input.getBoundingClientRect();
        this._dropdown.style.top=(rect.bottom+4)+"px";
        this._dropdown.style.left=rect.left+"px";
        this._dropdown.style.minWidth=Math.max(rect.width,200)+"px";
        this._dropdown.querySelectorAll(".autocomplete-item").forEach(el=>{
            el.addEventListener("mousedown",e=>{
                e.preventDefault();
                const idx=parseInt(el.dataset.index);
                this._select(idx);
            });
        });
    }

    _hide(){
        if(this._dropdown){
            this._dropdown.remove();
            this._dropdown=null;
            this._selectedIndex=-1;
        }
    }

    _highlight(text){
        const q=this._input.value.trim();
        if(!q)return text;
        const idx=text.toLowerCase().indexOf(q.toLowerCase());
        if(idx===-1)return text;
        return text.slice(0,idx)+"<strong>"+text.slice(idx,idx+q.length)+"</strong>"+text.slice(idx+q.length);
    }

    _onKeydown(e){
        if(!this._dropdown)return;
        const items=this._dropdown.querySelectorAll(".autocomplete-item");
        if(e.key==="ArrowDown"){
            e.preventDefault();
            this._selectedIndex=Math.min(this._selectedIndex+1,items.length-1);
            this._scrollTo(items);
        }else if(e.key==="ArrowUp"){
            e.preventDefault();
            this._selectedIndex=Math.max(this._selectedIndex-1,0);
            this._scrollTo(items);
        }else if(e.key==="Enter"){
            e.preventDefault();
            if(this._selectedIndex>=0)this._select(this._selectedIndex);
        }else if(e.key==="Escape"){
            this._hide();
        }
        items.forEach((el,i)=>el.classList.toggle("active",i===this._selectedIndex));
    }

    _scrollTo(items){
        if(items[this._selectedIndex]){
            items[this._selectedIndex].scrollIntoView({block:"nearest"});
        }
    }

    _select(index){
        const item=this._items[index];
        const label=typeof item==="string"?item:item.label||item.name||"";
        this._input.value=label;
        if(this._onSelect)this._onSelect(item);
        FiscalUI.emit("autocomplete:select",{input:this._input,item});
        this._hide();
    }

    onSelect(callback){
        this._onSelect=callback;
        return this;
    }
}

window.Autocomplete=Autocomplete;
