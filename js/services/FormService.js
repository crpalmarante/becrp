class FormService{

    constructor(events){

        this._events=events;

        this._maskHandlers=new Map();

        this._customValidators=new Map();

        this._autoInitDone=false;

    }

    init(){

        this._autoMasks();

        if(!this._autoInitDone){
            this._autoInitDone=true;
            this._autoValidate();
        }

    }

    validator(name,fn){
        if(fn){
            this._customValidators.set(name,fn);
            return this;
        }
        return this._customValidators.get(name);
    }

    _autoValidate(){
        document.addEventListener("blur",e=>{
            const el=e.target;
            if(el.closest&&!el.closest(".form-field"))return;
            if(el.tagName!=="INPUT"&&el.tagName!=="SELECT"&&el.tagName!=="TEXTAREA")return;
            const field=el.closest(".form-field");
            if(!field)return;
            const err=this._validateField(el);
            if(err){
                field.classList.add("has-error");
                field.classList.remove("has-success");
                const msg=field.querySelector(".form-error");
                if(msg)msg.textContent=err;
            }else if(el.value){
                field.classList.remove("has-error");
                field.classList.add("has-success");
                const msg=field.querySelector(".form-error");
                if(msg)msg.textContent="";
            }else{
                field.classList.remove("has-error","has-success");
            }
        },true);
    }

    _validateField(el){
        const field=el.closest(".form-field");
        const label=field?field.querySelector(".form-label")?.textContent.replace("*","").trim():el.name;
        if(el.hasAttribute("required")&&(!el.value||el.value.trim()==="")){
            return (label||"Campo")+" é obrigatório.";
        }
        const maskType=el.getAttribute("data-mask");
        if(maskType==="email"&&el.value&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(el.value)){
            return "E-mail inválido.";
        }
        if(maskType==="cpf"&&el.value&&!this._validCPF(el.value)) return "CPF inválido.";
        if(maskType==="cnpj"&&el.value&&!this._validCNPJ(el.value)) return "CNPJ inválido.";
        const customRule=el.getAttribute("data-validate");
        if(customRule){
            const fn=this._customValidators.get(customRule);
            if(fn){
                const msg=fn(el.value,el);
                if(msg)return msg;
            }
        }
        return null;
    }

    serialize(formEl){

        if(!formEl)return{};

        const data={};

        const elements=formEl.querySelectorAll("[name]");

        elements.forEach(el=>{

            const name=el.name;

            if(!name)return;

            if(el.type==="checkbox"){

                if(!data[name])data[name]=[];

                if(el.checked)data[name].push(el.value);

            }else if(el.type==="radio"){

                if(el.checked)data[name]=el.value;

            }else{

                data[name]=el.value;

            }

        });

        return data;

    }

    populate(formEl,data){

        if(!formEl||!data)return;

        Object.keys(data).forEach(name=>{

            const el=formEl.querySelector("[name='"+name+"']");

            if(!el)return;

            if(el.type==="checkbox"){

                el.checked=(Array.isArray(data[name])&&data[name].includes(el.value))||data[name]===true;

            }else if(el.type==="radio"){

                el.checked=el.value===data[name];

            }else{

                el.value=data[name]||"";

            }

        });

    }

    validate(formEl){

        const errors=[];

        const elements=formEl.querySelectorAll("[required]");

        elements.forEach(el=>{

            const label=formEl.querySelector("[for='"+el.id+"']")||el.closest(".form-field")?.querySelector(".form-label");

            const fieldName=label?label.textContent.trim().replace("*",""):el.name||"Campo";

            if(!el.value||el.value.trim()===""){

                errors.push({field:el,name:fieldName,message:fieldName+" é obrigatório.",type:"required"});

            }

        });

        elements.forEach(el=>{

            if(!el.value)return;

            const type=el.getAttribute("data-mask")||el.type;

            if(type==="email"&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(el.value)){

                errors.push({field:el,name:el.name,message:"E-mail inválido.",type:"format"});

            }

            if(type==="cpf"&&!this._validCPF(el.value)){

                errors.push({field:el,name:el.name,message:"CPF inválido.",type:"format"});

            }

            if(type==="cnpj"&&!this._validCNPJ(el.value)){

                errors.push({field:el,name:el.name,message:"CNPJ inválido.",type:"format"});

            }

        });

        return errors;

    }

    showErrors(formEl,errors){

        formEl.querySelectorAll(".form-field.has-error").forEach(el=>el.classList.remove("has-error"));

        errors.forEach(err=>{

            const field=err.field.closest?.(".form-field")||formEl.querySelector(".form-field:has(#"+err.field.id+")");

            if(field){

                field.classList.add("has-error");

                const msg=field.querySelector(".form-error");

                if(msg)msg.textContent=err.message;

            }

        });

    }

    clearErrors(formEl){

        formEl.querySelectorAll(".form-field.has-error").forEach(el=>el.classList.remove("has-error"));

    }

    mask(el,maskType){

        if(!el)return;

        el.setAttribute("data-mask",maskType);

        if(!this._maskHandlers.has(maskType)){

            const handler=this._createMaskHandler(maskType);

            if(handler)this._maskHandlers.set(maskType,handler);

        }

    }

    _autoMasks(){

        document.addEventListener("input",e=>{

            const el=e.target;

            if(el.tagName!=="INPUT"&&el.tagName!=="TEXTAREA")return;

            const type=el.getAttribute("data-mask");

            if(!type)return;

            const handler=this._maskHandlers.get(type);

            if(handler)handler(el);

        },true);

    }

    _createMaskHandler(type){

        const masks={

            cpf(el){

                let v=el.value.replace(/\D/g,"").slice(0,11);

                if(v.length<=3)el.value=v;

                else if(v.length<=6)el.value=v.replace(/(\d{3})(\d+)/,"$1.$2");

                else if(v.length<=9)el.value=v.replace(/(\d{3})(\d{3})(\d+)/,"$1.$2.$3");

                else el.value=v.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/,"$1.$2.$3-$4");

            },

            cnpj(el){

                let v=el.value.replace(/\D/g,"").slice(0,14);

                if(v.length<=2)el.value=v;

                else if(v.length<=5)el.value=v.replace(/(\d{2})(\d+)/,"$1.$2");

                else if(v.length<=8)el.value=v.replace(/(\d{2})(\d{3})(\d+)/,"$1.$2.$3");

                else if(v.length<=12)el.value=v.replace(/(\d{2})(\d{3})(\d{3})(\d+)/,"$1.$2.$3/$4");

                else el.value=v.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/,"$1.$2.$3/$4-$5");

            },

            cep(el){

                let v=el.value.replace(/\D/g,"").slice(0,8);

                if(v.length<=5)el.value=v;

                else el.value=v.replace(/(\d{5})(\d{3})/,"$1-$2");

            },

            phone(el){

                let v=el.value.replace(/\D/g,"").slice(0,11);

                if(v.length<=2)el.value="("+v;

                else if(v.length<=7)el.value=v.replace(/(\d{2})(\d+)/,"($1) $2");

                else if(v.length<=11)el.value=v.replace(/(\d{2})(\d{5})(\d+)/,"($1) $2-$3");

            },

            money(el){

                let v=el.value.replace(/\D/g,"");

                let num=parseInt(v,10)/100;

                if(isNaN(num))num=0;

                el.value=num.toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2});

            },

            percent(el){

                let v=el.value.replace(/\D/g,"");

                let num=parseInt(v,10)/100;

                if(isNaN(num))num=0;

                el.value=num.toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2});

            }

        };

        return masks[type]||null;

    }

    _validCPF(cpf){

        const v=cpf.replace(/\D/g,"");

        if(v.length!==11||/^(\d)\1{10}$/.test(v))return false;

        let sum=0;

        for(let i=0;i<9;i++)sum+=parseInt(v[i],10)*(10-i);

        let r=(sum*10)%11;

        if(r===10)r=0;

        if(r!==parseInt(v[9],10))return false;

        sum=0;

        for(let i=0;i<10;i++)sum+=parseInt(v[i],10)*(11-i);

        r=(sum*10)%11;

        if(r===10)r=0;

        return r===parseInt(v[10],10);

    }

    _validCNPJ(cnpj){

        const v=cnpj.replace(/\D/g,"");

        if(v.length!==14||/^(\d)\1{13}$/.test(v))return false;

        const calc=(digitos,pesos)=>{

            let sum=0;

            for(let i=0;i<digitos.length;i++)sum+=parseInt(digitos[i],10)*pesos[i];

            const r=sum%11;

            return r<2?0:11-r;

        };

        const w1=[5,4,3,2,9,8,7,6,5,4,3,2];

        const w2=[6,5,4,3,2,9,8,7,6,5,4,3,2];

        const d1=calc(v.slice(0,12),w1);

        if(d1!==parseInt(v[12],10))return false;

        const d2=calc(v.slice(0,13),w2);

        return d2===parseInt(v[13],10);

    }

}

window.FormService=FormService;
