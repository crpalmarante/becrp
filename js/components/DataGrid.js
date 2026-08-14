class DataGrid{

    constructor(container, options={}){
        this._container=container;
        this._columns=options.columns||[];
        this._data=options.data||[];
        this._pageSize=options.pageSize||10;
        this._pageSizeOptions=options.pageSizeOptions||[5,10,25,50];
        this._sortable=options.sortable!==false;
        this._filterable=options.filterable!==false;
        this._selectable=!!options.selectable;
        this._resizable=!!options.resizable;
        this._striped=options.striped!==false;
        this._loading=!!options.loading;
        this._page=1;
        this._sortField=null;
        this._sortDir="asc";
        this._filterText="";
        this._selected=new Set();
        this._events={};
        this._colWidths={};
        this._allData=this._data.slice();
        this._resizeStart=null;
        this._highlight=null;
        this._render();
    }

    on(event, fn){
        if(!this._events[event])this._events[event]=[];
        this._events[event].push(fn);
        return this;
    }

    _emit(event, data){
        (this._events[event]||[]).forEach(fn=>fn(data));
    }

    setData(data){
        this._allData=data.slice();
        this._data=this._allData.slice();
        this._page=1;
        this._selected.clear();
        this._apply();
    }

    setLoading(v){
        this._loading=v;
        this._apply();
    }

    setPage(n){
        const total=this._getFiltered().length;
        const pages=Math.ceil(total/this._pageSize)||1;
        this._page=Math.min(Math.max(1, Number(n)||1), pages);
        this._apply();
    }

    /** Destaca visualmente a linha cujo campo `field` === `value`.
        `variant` define a cor: "new" (verde), "edit" (azul) ou "del" (vermelho). */
    highlight(field, value, variant){
        this._highlight={field, value:String(value), variant:variant||"new"};
        this._apply();
    }

    clearHighlight(){
        this._highlight=null;
        this._apply();
    }

    /** Rola a lista ate a linha cujo campo `field` === `value`, centralizando-a no .dg-scroll. */
    scrollTo(field, value){
        const idx=this._allData.findIndex(row=>String(this._rawValue(row,{field}))===String(value));
        if(idx<0)return;
        const rowEl=this._container.querySelector(`[data-idx="${idx}"]`);
        if(!rowEl)return;
        const scrollEl=this._container.querySelector(".dg-scroll");
        if(scrollEl){
            const cur=scrollEl.getBoundingClientRect();
            const row=rowEl.getBoundingClientRect();
            const target=scrollEl.scrollTop+(row.top-cur.top)-(cur.height-row.height)/2;
            scrollEl.scrollTo({top:Math.max(0,target), behavior:"smooth"});
        }
        // garante que paginas pai (workspace) tambem rolem se a linha estiver fora da tela
        rowEl.scrollIntoView({behavior:"smooth", block:"nearest"});
    }

    data(){
        return this._data;
    }

    selected(){
        return this._data.filter((_,i)=>this._selected.has(i));
    }

    _render(){
        if(!this._container)return;
        this._container.innerHTML=`
            <div class="dg-wrapper">
                ${this._filterable?`
                <div class="dg-toolbar">
                    <input class="dg-filter-input" placeholder="Pesquisar...">
                </div>`:""}
                <div class="dg-scroll">
                    <table class="dg-table">
                        <thead><tr class="dg-header">${this._renderHeaders()}</tr></thead>
                        <tbody class="dg-body">${this._loading?"":this._renderRows()}</tbody>
                    </table>
                    ${this._loading?this._renderSkeleton():""}
                    ${!this._loading&&this._getFiltered().length===0?'<div class="dg-empty">Nenhum registro encontrado.</div>':""}
                </div>
                <div class="dg-footer">${this._renderPagination()}</div>
            </div>
        `;
        this._bindEvents();
    }

    _renderHeaders(){
        return this._columns.map((col,i)=>{
            const w=this._colWidths[col.field]||col.width||"";
            const sort=this._sortField===col.field;
            return `<th class="dg-th ${this._sortable&&col.sortable!==false?"dg-sortable":""}" data-field="${col.field}" style="${w?"width:"+w+"px":""}">
                <div class="dg-th-content">
                    <span>${col.label||col.field}</span>
                    ${this._sortable&&col.sortable!==false?`
                    <span class="dg-sort-icon ${sort?this._sortDir:""}">
                        ${sort?'<svg class="icon icon-12"><use href="#icon-chevron-'+this._sortDir+'"/></svg>':""}
                    </span>`:""}
                </div>
                ${this._resizable?'<div class="dg-resize-handle" data-col="'+i+'"></div>':""}
            </th>`;
        }).join("");
    }

    _renderRows(){
        const filtered=this._getFiltered();
        const sorted=this._sortData(filtered);
        const paged=this._paginate(sorted);
        const isMobile=window.FiscalUI&&FiscalUI.state&&FiscalUI.state.get("isMobile");
        if(isMobile){
            return this._renderCards(paged);
        }
        return paged.map((row,ri)=>{
            const idx=this._allData.indexOf(row);
            const sel=this._selected.has(idx);
            const hl=this._highlight&&String(this._rawValue(row,{field:this._highlight.field}))===this._highlight.value;
            const hlCls=hl?("dg-row-"+(this._highlight.variant||"new")):"";
            return `<tr class="dg-row ${sel?"dg-row-sel":""} ${this._striped&&ri%2?"dg-row-alt":""} ${hlCls}" data-idx="${idx}">
                ${this._selectable?`<td class="dg-cell dg-cell-select" data-idx="${idx}">
                    <input type="checkbox" ${sel?"checked":""}>
                </td>`:""}
                ${this._columns.map(col=>{
                    const val=this._cellValue(row,col);
                    return `<td class="dg-cell dg-cell-${col.align||"left"}" data-field="${col.field}" data-idx="${idx}">${val}</td>`;
                }).join("")}
            </tr>`;
        }).join("");
    }

    _renderCards(paged){
        return paged.map((row,ri)=>{
            const idx=this._allData.indexOf(row);
            const sel=this._selected.has(idx);
            const hl=this._highlight&&String(this._rawValue(row,{field:this._highlight.field}))===this._highlight.value;
            const hlCls=hl?("dg-row-"+(this._highlight.variant||"new")):"";
            return `<div class="dg-card ${sel?"dg-card-sel":""} ${hlCls}" data-idx="${idx}">
                ${this._selectable?`<div class="dg-card-select"><input type="checkbox" ${sel?"checked":""}></div>`:""}
                ${this._columns.map(col=>{
                    const val=this._cellValue(row,col);
                    return `<div class="dg-card-row" data-field="${col.field}">
                        <span class="dg-card-label">${col.label||col.field}</span>
                        <span class="dg-card-value">${val}</span>
                    </div>`;
                }).join("")}
            </div>`;
        }).join("");
    }

    _renderSkeleton(){
        const rows=Math.min(this._pageSize,5);
        return `<table class="dg-table dg-skeleton">
            <tbody>${Array.from({length:rows},()=>`
                <tr class="dg-row">${this._columns.map(()=>`
                    <td class="dg-cell"><div class="dg-skel-line"></div></td>
                `).join("")}</tr>
            `).join("")}</tbody>
        </table>`;
    }

    _renderPagination(){
        const total=this._getFiltered().length;
        const pages=Math.ceil(total/this._pageSize)||1;
        if(total===0)return"";
        const start=(this._page-1)*this._pageSize+1;
        const end=Math.min(this._page*this._pageSize,total);
        let btns="";
        for(let i=1;i<=pages;i++){
            if(i===1||i===pages||Math.abs(i-this._page)<=1){
                btns+=`<button class="dg-page ${i===this._page?"dg-page-active":""}" data-page="${i}">${i}</button>`;
            }else if(btns[btns.length-1]!=="…"){
                btns+="<span class=\"dg-page-dots\">…</span>";
            }
        }
        const prevDisabled = this._page<=1;
        const nextDisabled = this._page>=pages;
        return `
            <div class="dg-pagination">
                <div class="dg-page-info">${start}–${end} de ${total} (pág ${this._page}/${pages})</div>
                <div class="dg-page-btns">
                    <button class="dg-page-nav" data-page="first" ${prevDisabled?"disabled":""}>&laquo;</button>
                    <button class="dg-page-nav" data-page="prev" ${prevDisabled?"disabled":""}>&lsaquo;</button>
                    ${btns}
                    <button class="dg-page-nav" data-page="next" ${nextDisabled?"disabled":""}>&rsaquo;</button>
                    <button class="dg-page-nav" data-page="last" ${nextDisabled?"disabled":""}>&raquo;</button>
                </div>
                <select class="dg-page-size">
                    ${this._pageSizeOptions.map(s=>`<option value="${s}" ${s===this._pageSize?"selected":""}>${s}/pág</option>`).join("")}
                </select>
            </div>
        `;
    }

    _getFiltered(){
        if(!this._filterText)return this._allData;
        const q=this._filterText.toLowerCase();
        return this._allData.filter(row=>{
            return this._columns.some(col=>{
                const v=this._rawValue(row,col);
                return v!=null&&String(v).toLowerCase().includes(q);
            });
        });
    }

    _sortData(data){
        if(!this._sortField)return data;
        return data.slice().sort((a,b)=>{
            const va=this._rawValue(a,{field:this._sortField});
            const vb=this._rawValue(b,{field:this._sortField});
            if(va==null)return 1;
            if(vb==null)return -1;
            if(typeof va==="number"&&typeof vb==="number")return this._sortDir==="asc"?va-vb:vb-va;
            return this._sortDir==="asc"?String(va).localeCompare(String(vb)):String(vb).localeCompare(String(va));
        });
    }

    _paginate(data){
        const start=(this._page-1)*this._pageSize;
        return data.slice(start,start+this._pageSize);
    }

    _rawValue(row,col){
        if(col.value)return col.value(row);
        const v=row[col.field];
        return v!=null?v:"";
    }

    _cellValue(row,col){
        const raw=this._rawValue(row,col);
        if(col.formatter==="currency"){
            const n=parseFloat(raw);
            return isNaN(n)?"—":"R$ "+n.toFixed(2).replace(".",",");
        }
        if(col.formatter==="date"){
            if(!raw)return"—";
            const d=new Date(raw);
            if(isNaN(d.getTime()))return raw;
            return String(d.getDate()).padStart(2,"0")+"/"+String(d.getMonth()+1).padStart(2,"0")+"/"+d.getFullYear();
        }
        if(col.formatter==="status"){
            if(raw==="ativo"||raw==="active"||raw==="success") return Badge.status(raw,"success");
            if(raw==="pendente"||raw==="pending"||raw==="warning") return Badge.status(raw,"warning");
            if(raw==="cancelado"||raw==="cancelled"||raw==="danger") return Badge.status(raw,"danger");
            return Badge.render(raw,"info");
        }
        if(col.formatter)return col.formatter(raw,row);
        return raw;
    }

    _bindEvents(){
        const wrap=this._container.querySelector(".dg-wrapper");
        if(!wrap)return;

        if(this._filterable){
            const input=wrap.querySelector(".dg-filter-input");
            if(input){
                let timer;
                input.addEventListener("input",()=>{
                    clearTimeout(timer);
                    timer=setTimeout(()=>{
                        this._filterText=input.value;
                        this._page=1;
                        this._apply();
                        this._emit("filter",{value:this._filterText});
                    },250);
                });
            }
        }

        wrap.addEventListener("click",e=>{
            const th=e.target.closest(".dg-sortable");
            if(th){
                const field=th.dataset.field;
                this._sortField===field?this._sortDir=this._sortDir==="asc"?"desc":"asc":this._sortDir="asc";
                this._sortField=field;
                this._page=1;
                this._apply();
                this._emit("sort",{field,dir:this._sortDir});
                return;
            }

            const pageBtn=e.target.closest("[data-page]");
            if(pageBtn){
                const p=pageBtn.dataset.page;
                const pages = Math.ceil(this._getFiltered().length/this._pageSize)||1;
                if(p==="prev"){ if(this._page>1) this._page--; }
                else if(p==="next"){ if(this._page<pages) this._page++; }
                else if(p==="first"){ this._page = 1; }
                else if(p==="last"){ this._page = pages; }
                else { this._page = parseInt(p); }
                this._apply();
                this._emit("page",{page:this._page,pageSize:this._pageSize});
                return;
            }

            const cell=e.target.closest(".dg-cell");
            if(cell&&cell.dataset.idx!=null){
                const idx=parseInt(cell.dataset.idx);
                const row=this._allData[idx];
                const field=cell.dataset.field;
                const val=field!=null?this._rawValue(row,{field}):null;
                this._emit("cellClick",{row,idx,field,value:val});
            }
        });

        wrap.addEventListener("change",e=>{
            const cb=e.target.closest(".dg-cell-select input");
            if(cb){
                const idx=parseInt(cb.closest(".dg-cell-select").dataset.idx);
                if(cb.checked)this._selected.add(idx);
                else this._selected.delete(idx);
                this._emit("select",{rows:this.selected()});
                cb.closest("tr").classList.toggle("dg-row-sel",cb.checked);
                return;
            }
            const sizeSelect=e.target.closest(".dg-page-size");
            if(sizeSelect){
                this._pageSize=parseInt(sizeSelect.value);
                this._page=1;
                this._apply();
                this._emit("page",{page:this._page,pageSize:this._pageSize});
                return;
            }
        });

        if(this._resizable){
            wrap.querySelectorAll(".dg-resize-handle").forEach(handle=>{
                handle.addEventListener("mousedown",e=>{
                    e.preventDefault();
                    const colIdx=parseInt(handle.dataset.col);
                    const th=handle.closest("th");
                    this._resizeStart={colIdx,th,startX:e.clientX,startW:th.offsetWidth};
                    const onMove=me=>{
                        if(!this._resizeStart)return;
                        const dx=me.clientX-this._resizeStart.startX;
                        const nw=Math.max(50,this._resizeStart.startW+dx);
                        this._colWidths[this._columns[this._resizeStart.colIdx].field]=nw;
                        this._resizeStart.th.style.width=nw+"px";
                    };
                    const onUp=()=>{
                        this._resizeStart=null;
                        document.removeEventListener("mousemove",onMove);
                        document.removeEventListener("mouseup",onUp);
                    };
                    document.addEventListener("mousemove",onMove);
                    document.addEventListener("mouseup",onUp);
                });
            });
        }
    }

    _apply(){
        const scrollTop=this._container.querySelector(".dg-scroll")?.scrollTop||0;
        this._render();
        const scrollEl=this._container.querySelector(".dg-scroll");
        if(scrollEl)scrollEl.scrollTop=scrollTop;
    }

    refresh(){
        this._apply();
    }
}

window.DataGrid=DataGrid;
