class ResponsiveLayout{

    constructor(events,state){
        this._events=events;
        this._state=state;
        this._sidebar=document.getElementById("sidebar");
        this._mainArea=document.querySelector(".main-area");
        this._overlay=null;
        this._init();
    }

    _init(){
        this._ensureOverlay();

        this._state.observe("sidebarCollapsed",({value})=>{
            if(this._sidebar)this._sidebar.classList.toggle("collapsed",value);
            if(this._mainArea)this._mainArea.classList.toggle("collapsed",value);
        });

        this._state.observe("isMobile",({value})=>{
            if(!value&&this._sidebar){
                this._sidebar.classList.remove("mobile-open");
                this._hideOverlay();
            }
        });

        this._state.observe("breakpoint",({value,prev})=>{
            if(prev==="xs"||prev==="sm"){
                if(this._sidebar)this._sidebar.classList.remove("mobile-open");
                this._hideOverlay();
                if(this._state)this._state.set("sidebarCollapsed",false);
            }
        });

        document.addEventListener("click",e=>{
            const toggle=e.target.closest("[data-toggle-sidebar]");
            if(toggle){this._toggleSidebar();return;}
        });

        this._initTouch();
    }

    _ensureOverlay(){
        if(document.querySelector(".sidebar-overlay"))return;
        this._overlay=document.createElement("div");
        this._overlay.className="sidebar-overlay";
        this._overlay.addEventListener("click",()=>this._closeMobileSidebar());
        document.body.appendChild(this._overlay);
    }

    _toggleSidebar(){
        const isMobile=this._state.get("isMobile");
        if(isMobile){
            this._sidebar.classList.toggle("mobile-open");
            this._overlay.classList.toggle("open",this._sidebar.classList.contains("mobile-open"));
        }else{
            this._state.set("sidebarCollapsed",!this._state.get("sidebarCollapsed"));
        }
        FiscalUI.emit("sidebar:toggle",{mobile:isMobile,collapsed:!isMobile?this._state.get("sidebarCollapsed"):null});
    }

    _closeMobileSidebar(){
        if(this._sidebar)this._sidebar.classList.remove("mobile-open");
        this._hideOverlay();
    }

    _hideOverlay(){
        if(this._overlay)this._overlay.classList.remove("open");
    }

    _initTouch(){
        let startX=0;
        let startY=0;
        document.addEventListener("touchstart",e=>{
            const touch=e.touches[0];
            startX=touch.clientX;
            startY=touch.clientY;
        },{passive:true});

        document.addEventListener("touchend",e=>{
            const touch=e.changedTouches[0];
            const dx=touch.clientX-startX;
            const dy=touch.clientY-startY;
            if(Math.abs(dx)<30||Math.abs(dy)>Math.abs(dx)*2)return;
            const isMobile=this._state.get("isMobile");
            if(dx>80&&isMobile){
                if(this._sidebar)this._sidebar.classList.add("mobile-open");
                if(this._overlay)this._overlay.classList.add("open");
            }
            if(dx<-80&&this._sidebar&&this._sidebar.classList.contains("mobile-open")){
                this._closeMobileSidebar();
            }
        },{passive:true});
    }

    renderHamburger(container){
        if(!container)return;
        container.innerHTML=`
            <button class="mobile-menu-btn" data-toggle-sidebar title="Menu">
                <svg class="icon"><use href="#icon-menu"/></svg>
            </button>
        `;
    }
}

window.ResponsiveLayout=ResponsiveLayout;
