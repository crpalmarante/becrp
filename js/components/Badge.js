class Badge{

    static render(label, variant="default", size="sm"){
        return `<span class="badge badge-${variant} badge-${size}">${label}</span>`;
    }

    static tag(label, closable=false, onClose){
        const id="tag-"+Math.random().toString(36).slice(2);
        const closeBtn=closable?`<button class="tag-close" data-id="${id}" onclick="Badge._close(this)">&times;</button>`:"";
        return `<span class="tag" id="${id}">${label}${closeBtn}</span>`;
    }

    static status(label, type="info"){
        return `<span class="badge badge-${type} badge-status">${label}</span>`;
    }

    static _close(btn){
        const tag=btn.closest(".tag");
        if(tag){
            tag.style.opacity="0";
            setTimeout(()=>tag.remove(),200);
        }
    }
}

window.Badge=Badge;
