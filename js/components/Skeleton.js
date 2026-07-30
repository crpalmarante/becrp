class Skeleton{

    static card(lines=3){
        let html='<div class="skeleton-card">';
        html+='<div class="skeleton-line skeleton-title"></div>';
        for(let i=0;i<lines;i++){
            html+=`<div class="skeleton-line" style="width:${60+Math.random()*30}%"></div>`;
        }
        html+='</div>';
        return html;
    }

    static table(rows=5,cols=4){
        let html='<div class="skeleton-table">';
        html+='<div class="skeleton-row"><div class="skeleton-th"></div></div>';
        for(let i=0;i<rows;i++){
            html+='<div class="skeleton-row">';
            for(let j=0;j<cols;j++){
                html+=`<div class="skeleton-td" style="width:${50+Math.random()*40}%"></div>`;
            }
            html+='</div>';
        }
        html+='</div>';
        return html;
    }

    static kpi(){
        return `
            <div class="skeleton-kpi">
                <div class="skeleton-line" style="width:40%"></div>
                <div class="skeleton-line skeleton-value" style="width:60%"></div>
                <div class="skeleton-line" style="width:30%"></div>
            </div>
        `;
    }

    static widget(){
        return `
            <div class="skeleton-widget">
                <div class="skeleton-line skeleton-title" style="width:50%"></div>
                <div class="skeleton-line" style="width:90%"></div>
                <div class="skeleton-line" style="width:75%"></div>
                <div class="skeleton-line" style="width:60%"></div>
            </div>
        `;
    }

    static apply(container, type="card", options={}){
        if(!container)return;
        container.innerHTML=Skeleton[type](options.rows,options.cols);
    }

    static remove(container){
        if(!container)return;
        container.querySelectorAll(".skeleton-card,.skeleton-table,.skeleton-kpi,.skeleton-widget").forEach(el=>el.remove());
    }
}

window.Skeleton=Skeleton;
