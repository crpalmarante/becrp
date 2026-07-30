class Accordion{

    constructor(container){
        this._container=container;
        this._items=[];
    }

    add(id, title, content, open=false){
        this._items.push({id,title,content,open});
        return this;
    }

    render(){
        if(!this._container)return;
        this._container.innerHTML=this._items.map((item,i)=>
            `<div class="accordion-item ${item.open?'expanded':''}">
                <div class="accordion-header" onclick="accordion.toggle(${i})">
                    <span class="accordion-title">${item.title}</span>
                    <svg class="icon icon-16 accordion-arrow"><use href="#icon-chevron-down"/></svg>
                </div>
                <div class="accordion-body" style="${item.open?'max-height:500px':'max-height:0'}">
                    <div class="accordion-content">${item.content}</div>
                </div>
            </div>`
        ).join("");
    }

    toggle(index){
        const items=this._container.querySelectorAll(".accordion-item");
        const item=items[index];
        if(!item)return;
        const isOpen=item.classList.contains("expanded");
        item.classList.toggle("expanded");
        const body=item.querySelector(".accordion-body");
        body.style.maxHeight=isOpen?"0":"500px";
        FiscalUI.emit("accordion:toggle",{index,id:this._items[index]?.id,open:!isOpen});
    }
}

window.Accordion=Accordion;
