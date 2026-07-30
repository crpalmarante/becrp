(function(){
    window.dialog=new Dialog();
    window.Badge=Badge;
    window.Skeleton=Skeleton;
    window.Accordion=Accordion;
    window.Tabs=Tabs;
    window.DatePicker=DatePicker;
    window.Autocomplete=Autocomplete;
    window.FileUpload=FileUpload;
    window.DataGrid=DataGrid;

    FiscalUI.dialog=dialog;

    document.addEventListener("click",function(e){
        const btn=e.target.closest("[data-dialog]");
        if(!btn)return;
        const action=btn.dataset.dialog;
        const msg=btn.dataset.message||"";
        const title=btn.dataset.title||"";

        if(action==="alert") dialog.alert(msg,title);
        else if(action==="confirm"){
            dialog.confirm(msg,title).then(r=>{
                if(r) FiscalUI.toast?.success("Confirmado!");
            });
        }
        else if(action==="prompt"){
            dialog.prompt(msg,"",title).then(r=>{
                if(r!==null) FiscalUI.toast?.info("Você digitou: "+r);
            });
        }
    });

    console.log("FiscalUI Components ready");
})();
