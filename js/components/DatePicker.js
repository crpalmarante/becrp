class DatePicker{

    constructor(input){
        this._input=input;
        this._picker=null;
        this._date=new Date();
        this._year=this._date.getFullYear();
        this._month=this._date.getMonth();
        this._onSelect=null;
        this._init();
    }

    _init(){
        this._input.setAttribute("readonly",true);
        this._input.style.cursor="pointer";
        this._input.addEventListener("focus",()=>this._open());
        this._input.addEventListener("click",()=>this._open());
        document.addEventListener("click",e=>{
            if(this._picker&&!this._picker.contains(e.target)&&e.target!==this._input){
                this._close();
            }
        });
    }

    _open(){
        this._close();
        this._picker=document.createElement("div");
        this._picker.className="datepicker-popup";
        this._render();
        document.body.appendChild(this._picker);
        const rect=this._input.getBoundingClientRect();
        this._picker.style.top=(rect.bottom+4)+"px";
        this._picker.style.left=rect.left+"px";
        this._picker.style.minWidth=rect.width+"px";
    }

    _close(){
        if(this._picker){
            this._picker.remove();
            this._picker=null;
        }
    }

    _render(){
        if(!this._picker)return;
        const months=["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
        const days=["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"];
        const firstDay=new Date(this._year,this._month,1).getDay();
        const daysInMonth=new Date(this._year,this._month+1,0).getDate();
        const today=new Date();

        this._picker.innerHTML=`
            <div class="datepicker-header">
                <button class="datepicker-nav" data-action="prev">&lsaquo;</button>
                <span class="datepicker-title">${months[this._month]} ${this._year}</span>
                <button class="datepicker-nav" data-action="next">&rsaquo;</button>
            </div>
            <div class="datepicker-days">
                ${days.map(d=>`<span class="datepicker-day-header">${d}</span>`).join("")}
                ${Array.from({length:firstDay},()=>`<span></span>`).join("")}
                ${Array.from({length:daysInMonth},(_,i)=>{
                    const day=i+1;
                    const dateStr=this._formatDate(this._year,this._month,day);
                    const isToday=this._year===today.getFullYear()&&this._month===today.getMonth()&&day===today.getDate();
                    const isSelected=this._input.value===dateStr;
                    return `<span class="datepicker-day${isToday?" today":""}${isSelected?" selected":""}" data-date="${dateStr}">${day}</span>`;
                }).join("")}
            </div>
        `;

        this._picker.querySelectorAll(".datepicker-nav").forEach(btn=>{
            btn.addEventListener("click",e=>{
                e.stopPropagation();
                const action=btn.dataset.action;
                if(action==="prev"){
                    this._month--;
                    if(this._month<0){this._month=11;this._year--;}
                }else{
                    this._month++;
                    if(this._month>11){this._month=0;this._year++;}
                }
                this._render();
            });
        });

        this._picker.querySelectorAll(".datepicker-day").forEach(el=>{
            el.addEventListener("click",()=>{
                const val=el.dataset.date;
                this._input.value=val;
                if(this._onSelect)this._onSelect(val);
                FiscalUI.emit("datepicker:select",{input:this._input,value:val});
                this._close();
            });
        });
    }

    _formatDate(year,month,day){
        return String(day).padStart(2,"0")+"/"+String(month+1).padStart(2,"0")+"/"+year;
    }

    val(){
        return this._input.value;
    }

    set(val){
        this._input.value=val;
    }

    onSelect(callback){
        this._onSelect=callback;
        return this;
    }
}

window.DatePicker=DatePicker;
