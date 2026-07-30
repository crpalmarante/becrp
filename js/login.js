/*=========================================================
    FiscalBrasil ERP
    File    : login.js
=========================================================*/

/*=========================================================
  DOM
=========================================================*/

const loginForm=document.getElementById("login-form");
const loginPanel=document.getElementById("login-form-panel");
const setupPanel=document.getElementById("setup-form-panel");
const loginUser=document.getElementById("login-user");
const loginPass=document.getElementById("login-pass");
const loginError=document.getElementById("login-error");
const loginBtn=document.getElementById("login-btn");
const loginLoading=document.getElementById("login-loading");
const setupForm=document.getElementById("setup-form");
const setupName=document.getElementById("setup-name");
const setupUser=document.getElementById("setup-user");
const setupEmail=document.getElementById("setup-email");
const setupPass=document.getElementById("setup-pass");
const setupPass2=document.getElementById("setup-pass2");
const setupError=document.getElementById("setup-error");
const setupBtn=document.getElementById("setup-btn");
const setupLoading=document.getElementById("setup-loading");
const subtitle=document.getElementById("login-subtitle");

/*=========================================================
  CHECK SETUP
=========================================================*/

async function checkSetup(){
    try{
        const res=await fetch("/api/auth/check-setup");
        const data=await res.json();
        if(data.status==="ok"&&data.setup){
            setupPanel.style.display="block";
            loginPanel.style.display="none";
            subtitle.textContent="Configuração inicial do sistema";
        }
    }catch(e){}
}

checkSetup();

/*=========================================================
  LOGIN
=========================================================*/

loginForm.addEventListener("submit",async function(e){
    e.preventDefault();
    const usuario=loginUser.value.trim();
    const senha=loginPass.value.trim();
    if(!usuario||!senha){
        loginError.textContent="Preencha usuário e senha";
        loginError.classList.add("visible");
        return;
    }
    loginError.classList.remove("visible");
    loginBtn.disabled=true;
    loginLoading.classList.add("visible");
    try{
        const res=await fetch("/api/auth/login",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({usuario,senha})
        });
        const data=await res.json();
        if(data.status!=="ok"){
            loginError.textContent=data.message||"Usuário ou senha incorretos";
            loginError.classList.add("visible");
            loginBtn.disabled=false;
            loginLoading.classList.remove("visible");
            return;
        }
        localStorage.setItem("auth_token",data.token);
        localStorage.setItem("user_data",JSON.stringify(data));
        window.location.href="index4.html";
    }catch(err){
        loginError.textContent="Erro de conexão com o servidor";
        loginError.classList.add("visible");
        loginBtn.disabled=false;
        loginLoading.classList.remove("visible");
    }
});

/*=========================================================
  SETUP (cria admin master)
=========================================================*/

setupForm.addEventListener("submit",async function(e){
    e.preventDefault();
    const nome=setupName.value.trim();
    const usuario=setupUser.value.trim();
    const email=setupEmail.value.trim();
    const senha=setupPass.value.trim();
    const senha2=setupPass2.value.trim();
    if(!nome||!usuario||!senha){
        setupError.textContent="Preencha nome, usuário e senha";
        setupError.classList.add("visible");
        return;
    }
    if(senha!==senha2){
        setupError.textContent="Senhas não conferem";
        setupError.classList.add("visible");
        return;
    }
    setupError.classList.remove("visible");
    setupBtn.disabled=true;
    setupLoading.classList.add("visible");
    try{
        const res=await fetch("/api/auth/setup",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({nome,usuario,senha,email})
        });
        const data=await res.json();
        if(data.status!=="ok"){
            setupError.textContent=data.message||"Erro ao configurar";
            setupError.classList.add("visible");
            setupBtn.disabled=false;
            setupLoading.classList.remove("visible");
            return;
        }
        localStorage.setItem("auth_token",data.token);
        localStorage.setItem("user_data",JSON.stringify(data));
        window.location.href="index4.html";
    }catch(err){
        setupError.textContent="Erro de conexão com o servidor";
        setupError.classList.add("visible");
        setupBtn.disabled=false;
        setupLoading.classList.remove("visible");
    }
});
