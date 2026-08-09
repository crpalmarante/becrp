       >>SOURCE FORMAT IS FREE
       *> gerir_funcionarios.cbl - CRUD de funcionarios
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirFuncionarios.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT fn-file ASSIGN TO "dados/funcionarios.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/funcionarios.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT dep-file ASSIGN TO "dados/departamentos.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-ref-status.
           SELECT cr-file ASSIGN TO "dados/cargos.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-ref-status.

       DATA DIVISION.
       FILE SECTION.
       FD dep-file.
       01 dep-reg.
           05 dep-id              PIC 9(3).
           05 dep-codigo          PIC X(10).
           05 dep-descricao       PIC X(50).
           05 dep-centro-custo    PIC X(20).
           05 dep-responsavel     PIC X(40).
           05 dep-status          PIC X(8).

       FD cr-file.
       01 cr-reg.
           05 cr-id               PIC 9(3).
           05 cr-codigo           PIC X(10).
           05 cr-descricao        PIC X(50).
           05 cr-cbo              PIC X(6).
           05 cr-salario-ref      PIC 9(7)V99.
           05 cr-status           PIC X(8).

       FD fn-file.
       01 fn-reg.
           05 fn-id              PIC 9(3).
           05 fn-nome            PIC X(50).
           05 fn-usuario         PIC X(20).
           05 fn-senha           PIC X(30).
           05 fn-permissoes      PIC X(100).
           05 fn-ativo           PIC X.
           05 fn-cpf             PIC X(14).
           05 fn-rg              PIC X(20).
           05 fn-data-nasc       PIC X(10).
           05 fn-celular         PIC X(15).
           05 fn-email           PIC X(50).
           05 fn-endereco        PIC X(80).
           05 fn-data-adm        PIC X(10).
           05 fn-data-dem        PIC X(10).
           05 fn-salario         PIC 9(7)V99.
           05 fn-filial-id       PIC 9(3).
           05 fn-trab-sab       PIC X.
           05 fn-trab-dom       PIC X.
           05 fn-seg-ent        PIC X(5).
           05 fn-seg-alm        PIC X(5).
           05 fn-seg-sai        PIC X(5).
           05 fn-ter-ent        PIC X(5).
           05 fn-ter-alm        PIC X(5).
           05 fn-ter-sai        PIC X(5).
           05 fn-qua-ent        PIC X(5).
           05 fn-qua-alm        PIC X(5).
           05 fn-qua-sai        PIC X(5).
           05 fn-qui-ent        PIC X(5).
           05 fn-qui-alm        PIC X(5).
           05 fn-qui-sai        PIC X(5).
           05 fn-sex-ent        PIC X(5).
           05 fn-sex-alm        PIC X(5).
           05 fn-sex-sai        PIC X(5).
           05 fn-sab-ent        PIC X(5).
           05 fn-sab-sai        PIC X(5).
           05 fn-dom-ent        PIC X(5).
           05 fn-dom-sai        PIC X(5).
           05 fn-foto           PIC X(50).
           05 fn-contato-emerg-nome PIC X(40).
           05 fn-contato-emerg-tel  PIC X(20).
           05 fn-curriculo      PIC X(30).
           05 fn-tipo-sanguineo PIC X(3).
           05 fn-email-particular PIC X(50).
           05 fn-tel-comercial    PIC X(15).
           05 fn-banco            PIC X(30).
           05 fn-agencia          PIC X(10).
           05 fn-conta            PIC X(15).
           05 fn-conta-digito     PIC X(3).
           05 fn-conta-tipo       PIC X(15).
            05 fn-pix              PIC X(50).
            05 fn-pis             PIC X(14).
            05 fn-ctps            PIC X(15).
            05 fn-ctps-serie      PIC X(10).
            05 fn-ctps-uf         PIC X(2).
            05 fn-cbo             PIC X(6).
            05 fn-grau-instrucao  PIC X(25).
            05 fn-tipo-contrato   PIC X(20).
            05 fn-motivo-deslig   PIC X(30).
             05 fn-vt-desconto     PIC 9(3)V99.
             05 fn-vt-dias         PIC 9(2).
             05 fn-vt-optante      PIC X.
             05 fn-vr              PIC 9(5)V99.
            05 fn-plano-saude     PIC X(30).
            05 fn-plano-saude-valor PIC 9(5)V99.
            05 fn-supervisor-id   PIC 9(3).
            05 fn-sexo            PIC X.
            05 fn-estado-civil    PIC X(20).
            05 fn-nacionalidade   PIC X(30).
            05 fn-rg-orgao        PIC X(20).
            05 fn-rg-uf           PIC X(2).
            05 fn-titulo-eleitor  PIC X(15).
            05 fn-cep             PIC X(9).
            05 fn-cidade          PIC X(40).
            05 fn-uf              PIC X(2).
            05 fn-situacao-vinculo PIC X(20).
            05 fn-departamento    PIC X(30).
            05 fn-data-posse-cargo PIC X(10).
            05 fn-forma-pagamento PIC X(15).
            05 fn-meio-pagamento  PIC X(20).
            05 fn-carga-horaria-mensal PIC 9(3).
            05 fn-exame-adm-venc  PIC X(10).
            05 fn-observacoes     PIC X(120).
            05 fn-pensao-tipo     PIC X.
            05 fn-pensao-valor    PIC 9(5)V99.
           05 fn-departamento-id  PIC 9(3).
           05 fn-cargo-id         PIC 9(3).

       FD temp-file.
       01 temp-reg.
           05 tl-id              PIC 9(3).
           05 tl-nome            PIC X(50).
           05 tl-usuario         PIC X(20).
           05 tl-senha           PIC X(30).
           05 tl-permissoes      PIC X(100).
           05 tl-ativo           PIC X.
           05 tl-cpf             PIC X(14).
           05 tl-rg              PIC X(20).
           05 tl-data-nasc       PIC X(10).
           05 tl-celular         PIC X(15).
           05 tl-email           PIC X(50).
           05 tl-endereco        PIC X(80).
           05 tl-data-adm        PIC X(10).
           05 tl-data-dem        PIC X(10).
           05 tl-salario         PIC 9(7)V99.
           05 tl-filial-id       PIC 9(3).
           05 tl-trab-sab       PIC X.
           05 tl-trab-dom       PIC X.
           05 tl-seg-ent        PIC X(5).
           05 tl-seg-alm        PIC X(5).
           05 tl-seg-sai        PIC X(5).
           05 tl-ter-ent        PIC X(5).
           05 tl-ter-alm        PIC X(5).
           05 tl-ter-sai        PIC X(5).
           05 tl-qua-ent        PIC X(5).
           05 tl-qua-alm        PIC X(5).
           05 tl-qua-sai        PIC X(5).
           05 tl-qui-ent        PIC X(5).
           05 tl-qui-alm        PIC X(5).
           05 tl-qui-sai        PIC X(5).
           05 tl-sex-ent        PIC X(5).
           05 tl-sex-alm        PIC X(5).
           05 tl-sex-sai        PIC X(5).
           05 tl-sab-ent        PIC X(5).
           05 tl-sab-sai        PIC X(5).
           05 tl-dom-ent        PIC X(5).
           05 tl-dom-sai        PIC X(5).
           05 tl-foto           PIC X(50).
           05 tl-contato-emerg-nome PIC X(40).
           05 tl-contato-emerg-tel  PIC X(20).
           05 tl-curriculo      PIC X(30).
           05 tl-tipo-sanguineo PIC X(3).
           05 tl-email-particular PIC X(50).
           05 tl-tel-comercial    PIC X(15).
           05 tl-banco            PIC X(30).
           05 tl-agencia          PIC X(10).
           05 tl-conta            PIC X(15).
           05 tl-conta-digito     PIC X(3).
           05 tl-conta-tipo       PIC X(15).
            05 tl-pix              PIC X(50).
            05 tl-pis             PIC X(14).
            05 tl-ctps            PIC X(15).
            05 tl-ctps-serie      PIC X(10).
            05 tl-ctps-uf         PIC X(2).
            05 tl-cbo             PIC X(6).
            05 tl-grau-instrucao  PIC X(25).
            05 tl-tipo-contrato   PIC X(20).
            05 tl-motivo-deslig   PIC X(30).
             05 tl-vt-desconto     PIC 9(3)V99.
             05 tl-vt-dias         PIC 9(2).
             05 tl-vt-optante      PIC X.
             05 tl-vr              PIC 9(5)V99.
             05 tl-plano-saude     PIC X(30).
             05 tl-plano-saude-valor PIC 9(5)V99.
             05 tl-supervisor-id   PIC 9(3).
             05 tl-sexo            PIC X.
             05 tl-estado-civil    PIC X(20).
             05 tl-nacionalidade   PIC X(30).
             05 tl-rg-orgao        PIC X(20).
             05 tl-rg-uf           PIC X(2).
             05 tl-titulo-eleitor  PIC X(15).
             05 tl-cep             PIC X(9).
             05 tl-cidade          PIC X(40).
             05 tl-uf              PIC X(2).
             05 tl-situacao-vinculo PIC X(20).
             05 tl-departamento    PIC X(30).
             05 tl-data-posse-cargo PIC X(10).
             05 tl-forma-pagamento PIC X(15).
             05 tl-meio-pagamento  PIC X(20).
             05 tl-carga-horaria-mensal PIC 9(3).
             05 tl-exame-adm-venc  PIC X(10).
             05 tl-observacoes     PIC X(120).
             05 tl-pensao-tipo     PIC X.
             05 tl-pensao-valor    PIC 9(5)V99.
           05 tl-departamento-id  PIC 9(3).
           05 tl-cargo-id         PIC 9(3).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-file-status     PIC X(2).
       01 ws-encontrou       PIC X(1).
        01 ws-json-linha      PIC X(2400).
        01 ws-id-ed           PIC ZZZ9.
        01 ws-total-ed        PIC ZZZ9.
        01 ws-salario-j       PIC Z(6)9.99.
        01 ws-filial-j        PIC ZZ9.
        01 ws-vt-desc-j       PIC Z(2)9.99.
        01 ws-vt-dias-j       PIC Z9.
        01 ws-vr-j            PIC Z(4)9.99.
        01 ws-plano-val-j     PIC Z(4)9.99.
        01 ws-supervisor-j    PIC ZZZ9.
        01 ws-carga-horaria-j PIC ZZ9.
        01 ws-pensao-valor-j  PIC Z(4)9.99.
       01 ws-id              PIC 9(3).
       01 ws-id-in           PIC X(5).
       01 ws-data-edit       PIC 9(8).
       01 FILLER REDEFINES ws-data-edit.
           05 ws-dt-ano      PIC 9(4).
           05 ws-dt-mes      PIC 9(2).
           05 ws-dt-dia      PIC 9(2).
       01 ws-ref-status      PIC X(2).
       01 ws-achou-ref       PIC X.
       01 ws-nome            PIC X(50).
       01 ws-usuario         PIC X(20).
       01 ws-senha           PIC X(30).
       01 ws-permissoes      PIC X(100).
       01 ws-cpf             PIC X(14).
       01 ws-rg              PIC X(20).
       01 ws-data-nasc       PIC X(10).
       01 ws-celular         PIC X(15).
       01 ws-email           PIC X(50).
       01 ws-endereco        PIC X(80).
       01 ws-data-adm        PIC X(10).
       01 ws-data-dem        PIC X(10).
       01 ws-salario-ed      PIC X(12).
       01 ws-salario         PIC 9(7)V99.
       01 ws-filial-id       PIC X(5).
       01 ws-filial-id-num   PIC 9(3).
       01 ws-trab-sab       PIC X.
       01 ws-trab-dom       PIC X.
       01 ws-seg-ent        PIC X(5).
       01 ws-seg-alm        PIC X(5).
       01 ws-seg-sai        PIC X(5).
       01 ws-ter-ent        PIC X(5).
       01 ws-ter-alm        PIC X(5).
       01 ws-ter-sai        PIC X(5).
       01 ws-qua-ent        PIC X(5).
       01 ws-qua-alm        PIC X(5).
       01 ws-qua-sai        PIC X(5).
       01 ws-qui-ent        PIC X(5).
       01 ws-qui-alm        PIC X(5).
       01 ws-qui-sai        PIC X(5).
       01 ws-sex-ent        PIC X(5).
       01 ws-sex-alm        PIC X(5).
       01 ws-sex-sai        PIC X(5).
       01 ws-sab-ent        PIC X(5).
       01 ws-sab-sai        PIC X(5).
       01 ws-dom-ent        PIC X(5).
        01 ws-dom-sai        PIC X(5).
        01 ws-foto           PIC X(50).
        01 ws-contato-emerg-nome PIC X(40).
        01 ws-contato-emerg-tel  PIC X(20).
        01 ws-curriculo      PIC X(30).
        01 ws-tipo-sanguineo PIC X(3).
        01 ws-email-particular PIC X(50).
        01 ws-tel-comercial    PIC X(15).
        01 ws-banco            PIC X(30).
        01 ws-agencia          PIC X(10).
        01 ws-conta            PIC X(15).
        01 ws-conta-digito     PIC X(3).
        01 ws-conta-tipo       PIC X(15).
         01 ws-pix              PIC X(50).
         01 ws-pis              PIC X(14).
         01 ws-ctps             PIC X(15).
         01 ws-ctps-serie       PIC X(10).
         01 ws-ctps-uf          PIC X(2).
         01 ws-cbo              PIC X(6).
         01 ws-grau-instrucao   PIC X(25).
         01 ws-tipo-contrato    PIC X(20).
         01 ws-motivo-deslig    PIC X(30).
         01 ws-vt-desconto-ed   PIC X(12).
         01 ws-vt-desconto      PIC 9(3)V99.
          01 ws-vt-dias-ed       PIC X(12).
           01 ws-vt-dias          PIC 9(2).
           01 ws-vt-optante       PIC X.
           01 ws-vr-ed            PIC X(12).
          01 ws-vr               PIC 9(5)V99.
          01 ws-plano-saude      PIC X(30).
          01 ws-plano-saude-valor-ed PIC X(12).
          01 ws-plano-saude-valor PIC 9(5)V99.
           01 ws-supervisor-id    PIC X(5).
           01 ws-supervisor-id-num PIC 9(3).
           01 ws-sexo             PIC X.
           01 ws-estado-civil     PIC X(20).
           01 ws-nacionalidade    PIC X(30).
           01 ws-rg-orgao         PIC X(20).
           01 ws-rg-uf            PIC X(2).
           01 ws-titulo-eleitor   PIC X(15).
           01 ws-cep              PIC X(9).
           01 ws-cidade           PIC X(40).
           01 ws-uf               PIC X(2).
           01 ws-situacao-vinculo PIC X(20).
           01 ws-departamento     PIC X(30).
           01 ws-data-posse-cargo PIC X(10).
           01 ws-forma-pagamento  PIC X(15).
           01 ws-meio-pagamento   PIC X(20).
           01 ws-carga-horaria-ed PIC X(5).
           01 ws-carga-horaria    PIC 9(3).
           01 ws-exame-adm-venc   PIC X(10).
           01 ws-observacoes      PIC X(120).
           01 ws-pensao-tipo      PIC X.
           01 ws-pensao-valor-ed  PIC X(12).
           01 ws-pensao-valor     PIC 9(5)V99.
       01 ws-departamento-id  PIC X(5).
       01 ws-departamento-num PIC 9(3).
       01 ws-cargo-id         PIC X(5).
       01 ws-cargo-num        PIC 9(3).
       01 ws-dept-j           PIC ZZ9.
       01 ws-cargo-j          PIC ZZ9.
       01 ws-cpf-limpo        PIC X(11).
       01 ws-cpf-lido-limpo   PIC X(11).
       01 ws-temp-cpf         PIC X(14).
       01 ws-i                PIC 99.
       01 ws-idx              PIC 99.
           01 ws-prox-id         PIC 9(3).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF

           EVALUATE ws-acao
               WHEN "incluir"  PERFORM incluir
               WHEN "alterar"  PERFORM alterar
               WHEN "excluir"  PERFORM excluir
               WHEN "listar"   PERFORM listar
               WHEN "login"    PERFORM login
               WHEN "desligar" PERFORM desligar
               WHEN "reativar" PERFORM reativar
               WHEN OTHER      DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       incluir.
           ACCEPT ws-nome FROM ENVIRONMENT "NOME"
           ACCEPT ws-usuario FROM ENVIRONMENT "USUARIO"
           ACCEPT ws-senha FROM ENVIRONMENT "SENHA"
           ACCEPT ws-permissoes FROM ENVIRONMENT "PERMISSOES"
           ACCEPT ws-cpf FROM ENVIRONMENT "CPF"
           ACCEPT ws-rg FROM ENVIRONMENT "RG"
           ACCEPT ws-data-nasc FROM ENVIRONMENT "DATA_NASC"
           ACCEPT ws-celular FROM ENVIRONMENT "CELULAR"
           ACCEPT ws-email FROM ENVIRONMENT "EMAIL"
           ACCEPT ws-endereco FROM ENVIRONMENT "ENDERECO"
           ACCEPT ws-data-adm FROM ENVIRONMENT "DATA_ADM"
           ACCEPT ws-data-dem FROM ENVIRONMENT "DATA_DEM"
           ACCEPT ws-salario-ed FROM ENVIRONMENT "SALARIO"
           ACCEPT ws-filial-id FROM ENVIRONMENT "FILIAL_ID"
           ACCEPT ws-trab-sab FROM ENVIRONMENT "TRAB_SAB"
           ACCEPT ws-trab-dom FROM ENVIRONMENT "TRAB_DOM"
           ACCEPT ws-seg-ent FROM ENVIRONMENT "SEG_ENT"
           ACCEPT ws-seg-alm FROM ENVIRONMENT "SEG_ALM"
           ACCEPT ws-seg-sai FROM ENVIRONMENT "SEG_SAI"
           ACCEPT ws-ter-ent FROM ENVIRONMENT "TER_ENT"
           ACCEPT ws-ter-alm FROM ENVIRONMENT "TER_ALM"
           ACCEPT ws-ter-sai FROM ENVIRONMENT "TER_SAI"
           ACCEPT ws-qua-ent FROM ENVIRONMENT "QUA_ENT"
           ACCEPT ws-qua-alm FROM ENVIRONMENT "QUA_ALM"
           ACCEPT ws-qua-sai FROM ENVIRONMENT "QUA_SAI"
           ACCEPT ws-qui-ent FROM ENVIRONMENT "QUI_ENT"
           ACCEPT ws-qui-alm FROM ENVIRONMENT "QUI_ALM"
           ACCEPT ws-qui-sai FROM ENVIRONMENT "QUI_SAI"
           ACCEPT ws-sex-ent FROM ENVIRONMENT "SEX_ENT"
           ACCEPT ws-sex-alm FROM ENVIRONMENT "SEX_ALM"
           ACCEPT ws-sex-sai FROM ENVIRONMENT "SEX_SAI"
           ACCEPT ws-sab-ent FROM ENVIRONMENT "SAB_ENT"
           ACCEPT ws-sab-sai FROM ENVIRONMENT "SAB_SAI"
           ACCEPT ws-dom-ent FROM ENVIRONMENT "DOM_ENT"
            ACCEPT ws-dom-sai FROM ENVIRONMENT "DOM_SAI"
            ACCEPT ws-foto FROM ENVIRONMENT "FOTO"
            ACCEPT ws-contato-emerg-nome FROM ENVIRONMENT "CONTATO_EMERG_NOME"
            ACCEPT ws-contato-emerg-tel FROM ENVIRONMENT "CONTATO_EMERG_TEL"
            ACCEPT ws-curriculo FROM ENVIRONMENT "CURRICULO"
            ACCEPT ws-tipo-sanguineo FROM ENVIRONMENT "TIPO_SANGUINEO"
            ACCEPT ws-email-particular FROM ENVIRONMENT "EMAIL_PARTICULAR"
            ACCEPT ws-tel-comercial FROM ENVIRONMENT "TEL_COMERCIAL"
            ACCEPT ws-banco FROM ENVIRONMENT "BANCO"
            ACCEPT ws-agencia FROM ENVIRONMENT "AGENCIA"
            ACCEPT ws-conta FROM ENVIRONMENT "CONTA"
            ACCEPT ws-conta-digito FROM ENVIRONMENT "CONTA_DIGITO"
            ACCEPT ws-conta-tipo FROM ENVIRONMENT "CONTA_TIPO"
            ACCEPT ws-pix FROM ENVIRONMENT "PIX"
            ACCEPT ws-pis FROM ENVIRONMENT "PIS"
            ACCEPT ws-ctps FROM ENVIRONMENT "CTPS"
            ACCEPT ws-ctps-serie FROM ENVIRONMENT "CTPS_SERIE"
            ACCEPT ws-ctps-uf FROM ENVIRONMENT "CTPS_UF"
            ACCEPT ws-cbo FROM ENVIRONMENT "CBO"
            ACCEPT ws-grau-instrucao FROM ENVIRONMENT "GRAU_INSTRUCAO"
            ACCEPT ws-tipo-contrato FROM ENVIRONMENT "TIPO_CONTRATO"
             ACCEPT ws-motivo-deslig FROM ENVIRONMENT "MOTIVO_DESLIG"
             ACCEPT ws-vt-desconto-ed FROM ENVIRONMENT "VT_DESCONTO"
             ACCEPT ws-vt-dias-ed FROM ENVIRONMENT "VT_DIAS"
             ACCEPT ws-vt-optante FROM ENVIRONMENT "VT_OPTANTE"
             ACCEPT ws-vr-ed FROM ENVIRONMENT "VR"
             ACCEPT ws-plano-saude FROM ENVIRONMENT "PLANO_SAUDE"
             ACCEPT ws-plano-saude-valor-ed FROM ENVIRONMENT "PLANO_SAUDE_VALOR"
             ACCEPT ws-supervisor-id FROM ENVIRONMENT "SUPERVISOR_ID"
             ACCEPT ws-sexo FROM ENVIRONMENT "SEXO"
             ACCEPT ws-estado-civil FROM ENVIRONMENT "ESTADO_CIVIL"
             ACCEPT ws-nacionalidade FROM ENVIRONMENT "NACIONALIDADE"
             ACCEPT ws-rg-orgao FROM ENVIRONMENT "RG_ORGAO"
             ACCEPT ws-rg-uf FROM ENVIRONMENT "RG_UF"
             ACCEPT ws-titulo-eleitor FROM ENVIRONMENT "TITULO_ELEITOR"
             ACCEPT ws-cep FROM ENVIRONMENT "CEP"
             ACCEPT ws-cidade FROM ENVIRONMENT "CIDADE"
             ACCEPT ws-uf FROM ENVIRONMENT "UF"
             ACCEPT ws-situacao-vinculo FROM ENVIRONMENT "SITUACAO_VINCULO"
             ACCEPT ws-departamento FROM ENVIRONMENT "DEPARTAMENTO"
             ACCEPT ws-data-posse-cargo FROM ENVIRONMENT "DATA_POSSE_CARGO"
             ACCEPT ws-forma-pagamento FROM ENVIRONMENT "FORMA_PAGAMENTO"
             ACCEPT ws-meio-pagamento FROM ENVIRONMENT "MEIO_PAGAMENTO"
             ACCEPT ws-carga-horaria-ed FROM ENVIRONMENT "CARGA_HORARIA"
             ACCEPT ws-exame-adm-venc FROM ENVIRONMENT "EXAME_ADM_VENC"
             ACCEPT ws-observacoes FROM ENVIRONMENT "OBSERVACOES"
             ACCEPT ws-pensao-tipo FROM ENVIRONMENT "PENSAO_TIPO"
             ACCEPT ws-pensao-valor-ed FROM ENVIRONMENT "PENSAO_VALOR"
             ACCEPT ws-departamento-id FROM ENVIRONMENT "DEPARTAMENTO_ID"
             ACCEPT ws-cargo-id FROM ENVIRONMENT "CARGO_ID"
             IF ws-nome = SPACES THEN
                DISPLAY "ERRO: nome obrigatorio" STOP RUN END-IF
           IF ws-usuario = SPACES THEN
               DISPLAY "ERRO: usuario obrigatorio" STOP RUN END-IF
           IF ws-senha = SPACES THEN
               DISPLAY "ERRO: senha obrigatoria" STOP RUN END-IF
           IF ws-salario-ed NOT = SPACES THEN
               COMPUTE ws-salario = FUNCTION NUMVAL(ws-salario-ed) END-IF
            IF ws-filial-id NOT = SPACES THEN
                COMPUTE ws-filial-id-num = FUNCTION NUMVAL(ws-filial-id) END-IF
            IF ws-vt-desconto-ed NOT = SPACES THEN
                COMPUTE ws-vt-desconto = FUNCTION NUMVAL(ws-vt-desconto-ed) END-IF
            IF ws-vt-dias-ed NOT = SPACES THEN
                COMPUTE ws-vt-dias = FUNCTION NUMVAL(ws-vt-dias-ed) END-IF
            IF ws-vr-ed NOT = SPACES THEN
                COMPUTE ws-vr = FUNCTION NUMVAL(ws-vr-ed) END-IF
            IF ws-plano-saude-valor-ed NOT = SPACES THEN
                COMPUTE ws-plano-saude-valor = FUNCTION NUMVAL(ws-plano-saude-valor-ed) END-IF
             IF ws-supervisor-id NOT = SPACES THEN
                 COMPUTE ws-supervisor-id-num = FUNCTION NUMVAL(ws-supervisor-id) END-IF
             IF ws-carga-horaria-ed NOT = SPACES THEN
                 COMPUTE ws-carga-horaria = FUNCTION NUMVAL(ws-carga-horaria-ed) END-IF
             IF ws-pensao-valor-ed NOT = SPACES THEN
                 COMPUTE ws-pensao-valor = FUNCTION NUMVAL(ws-pensao-valor-ed) END-IF
             IF ws-departamento-id NOT = SPACES THEN
                 COMPUTE ws-departamento-num = FUNCTION NUMVAL(ws-departamento-id)
                 PERFORM validar-departamento END-IF
             IF ws-cargo-id NOT = SPACES THEN
                 COMPUTE ws-cargo-num = FUNCTION NUMVAL(ws-cargo-id)
                 PERFORM validar-cargo END-IF
             PERFORM normaliza-cpf

             MOVE 0 TO ws-prox-id
            OPEN INPUT fn-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT fn-file CLOSE fn-file
               OPEN INPUT fn-file END-IF
           PERFORM UNTIL 1 = 2
               READ fn-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fn-id > ws-prox-id THEN MOVE fn-id TO ws-prox-id END-IF
               IF fn-cpf NOT = SPACES AND ws-cpf-limpo NOT = SPACES THEN
                   PERFORM normaliza-cpf-lido
                   IF ws-cpf-limpo = ws-cpf-lido-limpo THEN
                       DISPLAY "ERRO: CPF ja cadastrado" STOP RUN END-IF
               END-IF
           END-PERFORM
           CLOSE fn-file
           ADD 1 TO ws-prox-id

           OPEN EXTEND fn-file
           MOVE ws-prox-id TO fn-id
           MOVE ws-nome TO fn-nome
           MOVE ws-usuario TO fn-usuario
           MOVE ws-senha TO fn-senha
           MOVE ws-permissoes TO fn-permissoes
           MOVE "S" TO fn-ativo
           MOVE ws-cpf TO fn-cpf
           MOVE ws-rg TO fn-rg
           MOVE ws-data-nasc TO fn-data-nasc
           MOVE ws-celular TO fn-celular
           MOVE ws-email TO fn-email
           MOVE ws-endereco TO fn-endereco
           MOVE ws-data-adm TO fn-data-adm
           MOVE ws-data-dem TO fn-data-dem
           MOVE ws-salario TO fn-salario
            MOVE ws-filial-id-num TO fn-filial-id
            MOVE ws-trab-sab TO fn-trab-sab
            MOVE ws-trab-dom TO fn-trab-dom
            MOVE ws-seg-ent TO fn-seg-ent
            MOVE ws-seg-alm TO fn-seg-alm
            MOVE ws-seg-sai TO fn-seg-sai
            MOVE ws-ter-ent TO fn-ter-ent
            MOVE ws-ter-alm TO fn-ter-alm
            MOVE ws-ter-sai TO fn-ter-sai
            MOVE ws-qua-ent TO fn-qua-ent
            MOVE ws-qua-alm TO fn-qua-alm
            MOVE ws-qua-sai TO fn-qua-sai
            MOVE ws-qui-ent TO fn-qui-ent
            MOVE ws-qui-alm TO fn-qui-alm
            MOVE ws-qui-sai TO fn-qui-sai
            MOVE ws-sex-ent TO fn-sex-ent
            MOVE ws-sex-alm TO fn-sex-alm
            MOVE ws-sex-sai TO fn-sex-sai
            MOVE ws-sab-ent TO fn-sab-ent
            MOVE ws-sab-sai TO fn-sab-sai
            MOVE ws-dom-ent TO fn-dom-ent
            MOVE ws-dom-sai TO fn-dom-sai
            MOVE ws-foto TO fn-foto
            MOVE ws-contato-emerg-nome TO fn-contato-emerg-nome
            MOVE ws-contato-emerg-tel TO fn-contato-emerg-tel
            MOVE ws-curriculo TO fn-curriculo
            MOVE ws-tipo-sanguineo TO fn-tipo-sanguineo
            MOVE ws-email-particular TO fn-email-particular
            MOVE ws-tel-comercial TO fn-tel-comercial
            MOVE ws-banco TO fn-banco
            MOVE ws-agencia TO fn-agencia
            MOVE ws-conta TO fn-conta
            MOVE ws-conta-digito TO fn-conta-digito
            MOVE ws-conta-tipo TO fn-conta-tipo
            MOVE ws-pix TO fn-pix
            MOVE ws-pis TO fn-pis
            MOVE ws-ctps TO fn-ctps
            MOVE ws-ctps-serie TO fn-ctps-serie
            MOVE ws-ctps-uf TO fn-ctps-uf
            MOVE ws-cbo TO fn-cbo
            MOVE ws-grau-instrucao TO fn-grau-instrucao
            MOVE ws-tipo-contrato TO fn-tipo-contrato
            MOVE ws-motivo-deslig TO fn-motivo-deslig
            MOVE ws-vt-desconto TO fn-vt-desconto
            MOVE ws-vt-dias TO fn-vt-dias
            MOVE ws-vt-optante TO fn-vt-optante
            MOVE ws-vr TO fn-vr
            MOVE ws-plano-saude TO fn-plano-saude
            MOVE ws-plano-saude-valor TO fn-plano-saude-valor
            MOVE ws-supervisor-id-num TO fn-supervisor-id
            MOVE ws-sexo TO fn-sexo
            MOVE ws-estado-civil TO fn-estado-civil
            MOVE ws-nacionalidade TO fn-nacionalidade
            MOVE ws-rg-orgao TO fn-rg-orgao
            MOVE ws-rg-uf TO fn-rg-uf
            MOVE ws-titulo-eleitor TO fn-titulo-eleitor
            MOVE ws-cep TO fn-cep
            MOVE ws-cidade TO fn-cidade
            MOVE ws-uf TO fn-uf
            MOVE ws-situacao-vinculo TO fn-situacao-vinculo
            MOVE ws-departamento TO fn-departamento
            MOVE ws-data-posse-cargo TO fn-data-posse-cargo
            MOVE ws-forma-pagamento TO fn-forma-pagamento
            MOVE ws-meio-pagamento TO fn-meio-pagamento
            MOVE ws-carga-horaria TO fn-carga-horaria-mensal
            MOVE ws-exame-adm-venc TO fn-exame-adm-venc
            MOVE ws-observacoes TO fn-observacoes
            MOVE ws-pensao-tipo TO fn-pensao-tipo
            MOVE ws-pensao-valor TO fn-pensao-valor
            MOVE ws-departamento-num TO fn-departamento-id
            MOVE ws-cargo-num TO fn-cargo-id
            WRITE fn-reg
           CLOSE fn-file
           DISPLAY ws-prox-id.

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-nome FROM ENVIRONMENT "NOME"
           ACCEPT ws-usuario FROM ENVIRONMENT "USUARIO"
           ACCEPT ws-senha FROM ENVIRONMENT "SENHA"
           ACCEPT ws-permissoes FROM ENVIRONMENT "PERMISSOES"
           ACCEPT ws-cpf FROM ENVIRONMENT "CPF"
           ACCEPT ws-rg FROM ENVIRONMENT "RG"
           ACCEPT ws-data-nasc FROM ENVIRONMENT "DATA_NASC"
           ACCEPT ws-celular FROM ENVIRONMENT "CELULAR"
           ACCEPT ws-email FROM ENVIRONMENT "EMAIL"
           ACCEPT ws-endereco FROM ENVIRONMENT "ENDERECO"
           ACCEPT ws-data-adm FROM ENVIRONMENT "DATA_ADM"
           ACCEPT ws-data-dem FROM ENVIRONMENT "DATA_DEM"
           ACCEPT ws-salario-ed FROM ENVIRONMENT "SALARIO"
            ACCEPT ws-filial-id FROM ENVIRONMENT "FILIAL_ID"
            ACCEPT ws-trab-sab FROM ENVIRONMENT "TRAB_SAB"
            ACCEPT ws-trab-dom FROM ENVIRONMENT "TRAB_DOM"
            ACCEPT ws-seg-ent FROM ENVIRONMENT "SEG_ENT"
            ACCEPT ws-seg-alm FROM ENVIRONMENT "SEG_ALM"
            ACCEPT ws-seg-sai FROM ENVIRONMENT "SEG_SAI"
            ACCEPT ws-ter-ent FROM ENVIRONMENT "TER_ENT"
            ACCEPT ws-ter-alm FROM ENVIRONMENT "TER_ALM"
            ACCEPT ws-ter-sai FROM ENVIRONMENT "TER_SAI"
            ACCEPT ws-qua-ent FROM ENVIRONMENT "QUA_ENT"
            ACCEPT ws-qua-alm FROM ENVIRONMENT "QUA_ALM"
            ACCEPT ws-qua-sai FROM ENVIRONMENT "QUA_SAI"
            ACCEPT ws-qui-ent FROM ENVIRONMENT "QUI_ENT"
            ACCEPT ws-qui-alm FROM ENVIRONMENT "QUI_ALM"
            ACCEPT ws-qui-sai FROM ENVIRONMENT "QUI_SAI"
            ACCEPT ws-sex-ent FROM ENVIRONMENT "SEX_ENT"
            ACCEPT ws-sex-alm FROM ENVIRONMENT "SEX_ALM"
            ACCEPT ws-sex-sai FROM ENVIRONMENT "SEX_SAI"
            ACCEPT ws-sab-ent FROM ENVIRONMENT "SAB_ENT"
            ACCEPT ws-sab-sai FROM ENVIRONMENT "SAB_SAI"
           ACCEPT ws-dom-ent FROM ENVIRONMENT "DOM_ENT"
            ACCEPT ws-dom-sai FROM ENVIRONMENT "DOM_SAI"
            ACCEPT ws-foto FROM ENVIRONMENT "FOTO"
            ACCEPT ws-contato-emerg-nome FROM ENVIRONMENT "CONTATO_EMERG_NOME"
            ACCEPT ws-contato-emerg-tel FROM ENVIRONMENT "CONTATO_EMERG_TEL"
            ACCEPT ws-curriculo FROM ENVIRONMENT "CURRICULO"
            ACCEPT ws-tipo-sanguineo FROM ENVIRONMENT "TIPO_SANGUINEO"
            ACCEPT ws-email-particular FROM ENVIRONMENT "EMAIL_PARTICULAR"
            ACCEPT ws-tel-comercial FROM ENVIRONMENT "TEL_COMERCIAL"
            ACCEPT ws-banco FROM ENVIRONMENT "BANCO"
            ACCEPT ws-agencia FROM ENVIRONMENT "AGENCIA"
            ACCEPT ws-conta FROM ENVIRONMENT "CONTA"
            ACCEPT ws-conta-digito FROM ENVIRONMENT "CONTA_DIGITO"
            ACCEPT ws-conta-tipo FROM ENVIRONMENT "CONTA_TIPO"
            ACCEPT ws-pix FROM ENVIRONMENT "PIX"
            ACCEPT ws-pis FROM ENVIRONMENT "PIS"
            ACCEPT ws-ctps FROM ENVIRONMENT "CTPS"
            ACCEPT ws-ctps-serie FROM ENVIRONMENT "CTPS_SERIE"
            ACCEPT ws-ctps-uf FROM ENVIRONMENT "CTPS_UF"
            ACCEPT ws-cbo FROM ENVIRONMENT "CBO"
            ACCEPT ws-grau-instrucao FROM ENVIRONMENT "GRAU_INSTRUCAO"
            ACCEPT ws-tipo-contrato FROM ENVIRONMENT "TIPO_CONTRATO"
            ACCEPT ws-motivo-deslig FROM ENVIRONMENT "MOTIVO_DESLIG"
             ACCEPT ws-vt-desconto-ed FROM ENVIRONMENT "VT_DESCONTO"
             ACCEPT ws-vt-dias-ed FROM ENVIRONMENT "VT_DIAS"
             ACCEPT ws-vt-optante FROM ENVIRONMENT "VT_OPTANTE"
             ACCEPT ws-vr-ed FROM ENVIRONMENT "VR"
             ACCEPT ws-plano-saude FROM ENVIRONMENT "PLANO_SAUDE"
             ACCEPT ws-plano-saude-valor-ed FROM ENVIRONMENT "PLANO_SAUDE_VALOR"
             ACCEPT ws-supervisor-id FROM ENVIRONMENT "SUPERVISOR_ID"
             ACCEPT ws-sexo FROM ENVIRONMENT "SEXO"
             ACCEPT ws-estado-civil FROM ENVIRONMENT "ESTADO_CIVIL"
             ACCEPT ws-nacionalidade FROM ENVIRONMENT "NACIONALIDADE"
             ACCEPT ws-rg-orgao FROM ENVIRONMENT "RG_ORGAO"
             ACCEPT ws-rg-uf FROM ENVIRONMENT "RG_UF"
             ACCEPT ws-titulo-eleitor FROM ENVIRONMENT "TITULO_ELEITOR"
             ACCEPT ws-cep FROM ENVIRONMENT "CEP"
             ACCEPT ws-cidade FROM ENVIRONMENT "CIDADE"
             ACCEPT ws-uf FROM ENVIRONMENT "UF"
             ACCEPT ws-situacao-vinculo FROM ENVIRONMENT "SITUACAO_VINCULO"
             ACCEPT ws-departamento FROM ENVIRONMENT "DEPARTAMENTO"
             ACCEPT ws-data-posse-cargo FROM ENVIRONMENT "DATA_POSSE_CARGO"
             ACCEPT ws-forma-pagamento FROM ENVIRONMENT "FORMA_PAGAMENTO"
             ACCEPT ws-meio-pagamento FROM ENVIRONMENT "MEIO_PAGAMENTO"
             ACCEPT ws-carga-horaria-ed FROM ENVIRONMENT "CARGA_HORARIA"
             ACCEPT ws-exame-adm-venc FROM ENVIRONMENT "EXAME_ADM_VENC"
             ACCEPT ws-observacoes FROM ENVIRONMENT "OBSERVACOES"
             ACCEPT ws-pensao-tipo FROM ENVIRONMENT "PENSAO_TIPO"
             ACCEPT ws-pensao-valor-ed FROM ENVIRONMENT "PENSAO_VALOR"
             ACCEPT ws-departamento-id FROM ENVIRONMENT "DEPARTAMENTO_ID"
             ACCEPT ws-cargo-id FROM ENVIRONMENT "CARGO_ID"

             IF ws-pensao-valor-ed NOT = SPACES THEN
                 COMPUTE ws-pensao-valor = FUNCTION NUMVAL(ws-pensao-valor-ed) END-IF
             IF ws-departamento-id NOT = SPACES THEN
                 COMPUTE ws-departamento-num = FUNCTION NUMVAL(ws-departamento-id)
                 PERFORM validar-departamento END-IF
             IF ws-cargo-id NOT = SPACES THEN
                 COMPUTE ws-cargo-num = FUNCTION NUMVAL(ws-cargo-id)
                 PERFORM validar-cargo END-IF
             IF ws-cpf NOT = SPACES THEN PERFORM normaliza-cpf END-IF

             MOVE "N" TO ws-encontrou
           OPEN INPUT fn-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: funcionario nao encontrado" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ fn-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fn-id NOT = ws-id AND fn-cpf NOT = SPACES
                  AND ws-cpf-limpo NOT = SPACES THEN
                   PERFORM normaliza-cpf-lido
                   IF ws-cpf-limpo = ws-cpf-lido-limpo THEN
                       DISPLAY "ERRO: CPF ja cadastrado" STOP RUN END-IF
               END-IF
               IF fn-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-nome NOT = SPACES THEN MOVE ws-nome TO fn-nome END-IF
                   IF ws-usuario NOT = SPACES THEN MOVE ws-usuario TO fn-usuario END-IF
                   IF ws-senha NOT = SPACES THEN MOVE ws-senha TO fn-senha END-IF
                   IF ws-permissoes NOT = SPACES THEN MOVE ws-permissoes TO fn-permissoes END-IF
                   IF ws-cpf NOT = SPACES THEN MOVE ws-cpf TO fn-cpf END-IF
                   IF ws-rg NOT = SPACES THEN MOVE ws-rg TO fn-rg END-IF
                   IF ws-data-nasc NOT = SPACES THEN MOVE ws-data-nasc TO fn-data-nasc END-IF
                   IF ws-celular NOT = SPACES THEN MOVE ws-celular TO fn-celular END-IF
                   IF ws-email NOT = SPACES THEN MOVE ws-email TO fn-email END-IF
                   IF ws-endereco NOT = SPACES THEN MOVE ws-endereco TO fn-endereco END-IF
                   IF ws-data-adm NOT = SPACES THEN MOVE ws-data-adm TO fn-data-adm END-IF
                   IF ws-data-dem NOT = SPACES THEN MOVE ws-data-dem TO fn-data-dem END-IF
                   IF ws-salario-ed NOT = SPACES THEN
                       COMPUTE ws-salario = FUNCTION NUMVAL(ws-salario-ed)
                       MOVE ws-salario TO fn-salario END-IF
                    IF ws-filial-id NOT = SPACES THEN
                        COMPUTE ws-filial-id-num = FUNCTION NUMVAL(ws-filial-id)
                        MOVE ws-filial-id-num TO fn-filial-id END-IF
                    IF ws-trab-sab NOT = SPACES THEN
                        MOVE ws-trab-sab TO fn-trab-sab END-IF
                    IF ws-trab-dom NOT = SPACES THEN
                        MOVE ws-trab-dom TO fn-trab-dom END-IF
                    IF ws-seg-ent NOT = SPACES THEN
                        MOVE ws-seg-ent TO fn-seg-ent END-IF
                    IF ws-seg-alm NOT = SPACES THEN
                        MOVE ws-seg-alm TO fn-seg-alm END-IF
                    IF ws-seg-sai NOT = SPACES THEN
                        MOVE ws-seg-sai TO fn-seg-sai END-IF
                    IF ws-ter-ent NOT = SPACES THEN
                        MOVE ws-ter-ent TO fn-ter-ent END-IF
                    IF ws-ter-alm NOT = SPACES THEN
                        MOVE ws-ter-alm TO fn-ter-alm END-IF
                    IF ws-ter-sai NOT = SPACES THEN
                        MOVE ws-ter-sai TO fn-ter-sai END-IF
                    IF ws-qua-ent NOT = SPACES THEN
                        MOVE ws-qua-ent TO fn-qua-ent END-IF
                    IF ws-qua-alm NOT = SPACES THEN
                        MOVE ws-qua-alm TO fn-qua-alm END-IF
                    IF ws-qua-sai NOT = SPACES THEN
                        MOVE ws-qua-sai TO fn-qua-sai END-IF
                    IF ws-qui-ent NOT = SPACES THEN
                        MOVE ws-qui-ent TO fn-qui-ent END-IF
                    IF ws-qui-alm NOT = SPACES THEN
                        MOVE ws-qui-alm TO fn-qui-alm END-IF
                    IF ws-qui-sai NOT = SPACES THEN
                        MOVE ws-qui-sai TO fn-qui-sai END-IF
                    IF ws-sex-ent NOT = SPACES THEN
                        MOVE ws-sex-ent TO fn-sex-ent END-IF
                    IF ws-sex-alm NOT = SPACES THEN
                        MOVE ws-sex-alm TO fn-sex-alm END-IF
                    IF ws-sex-sai NOT = SPACES THEN
                        MOVE ws-sex-sai TO fn-sex-sai END-IF
                    IF ws-sab-ent NOT = SPACES THEN
                        MOVE ws-sab-ent TO fn-sab-ent END-IF
                    IF ws-sab-sai NOT = SPACES THEN
                        MOVE ws-sab-sai TO fn-sab-sai END-IF
                    IF ws-dom-ent NOT = SPACES THEN
                        MOVE ws-dom-ent TO fn-dom-ent END-IF
                    IF ws-dom-sai NOT = SPACES THEN
                        MOVE ws-dom-sai TO fn-dom-sai END-IF
                    IF ws-foto NOT = SPACES THEN
                        MOVE ws-foto TO fn-foto END-IF
                    IF ws-contato-emerg-nome NOT = SPACES THEN
                        MOVE ws-contato-emerg-nome TO fn-contato-emerg-nome END-IF
                    IF ws-contato-emerg-tel NOT = SPACES THEN
                        MOVE ws-contato-emerg-tel TO fn-contato-emerg-tel END-IF
                    IF ws-curriculo NOT = SPACES THEN
                        MOVE ws-curriculo TO fn-curriculo END-IF
                    IF ws-tipo-sanguineo NOT = SPACES THEN
                        MOVE ws-tipo-sanguineo TO fn-tipo-sanguineo END-IF
                    IF ws-email-particular NOT = SPACES THEN
                        MOVE ws-email-particular TO fn-email-particular END-IF
                    IF ws-tel-comercial NOT = SPACES THEN
                        MOVE ws-tel-comercial TO fn-tel-comercial END-IF
                    IF ws-banco NOT = SPACES THEN
                        MOVE ws-banco TO fn-banco END-IF
                    IF ws-agencia NOT = SPACES THEN
                        MOVE ws-agencia TO fn-agencia END-IF
                    IF ws-conta NOT = SPACES THEN
                        MOVE ws-conta TO fn-conta END-IF
                    IF ws-conta-digito NOT = SPACES THEN
                        MOVE ws-conta-digito TO fn-conta-digito END-IF
                    IF ws-conta-tipo NOT = SPACES THEN
                        MOVE ws-conta-tipo TO fn-conta-tipo END-IF
                    IF ws-pix NOT = SPACES THEN
                         MOVE ws-pix TO fn-pix END-IF
                    IF ws-pis NOT = SPACES THEN
                         MOVE ws-pis TO fn-pis END-IF
                    IF ws-ctps NOT = SPACES THEN
                         MOVE ws-ctps TO fn-ctps END-IF
                    IF ws-ctps-serie NOT = SPACES THEN
                         MOVE ws-ctps-serie TO fn-ctps-serie END-IF
                    IF ws-ctps-uf NOT = SPACES THEN
                         MOVE ws-ctps-uf TO fn-ctps-uf END-IF
                    IF ws-cbo NOT = SPACES THEN
                         MOVE ws-cbo TO fn-cbo END-IF
                    IF ws-grau-instrucao NOT = SPACES THEN
                         MOVE ws-grau-instrucao TO fn-grau-instrucao END-IF
                    IF ws-tipo-contrato NOT = SPACES THEN
                         MOVE ws-tipo-contrato TO fn-tipo-contrato END-IF
                    IF ws-motivo-deslig NOT = SPACES THEN
                         MOVE ws-motivo-deslig TO fn-motivo-deslig END-IF
                    IF ws-vt-desconto-ed NOT = SPACES THEN
                         COMPUTE ws-vt-desconto = FUNCTION NUMVAL(ws-vt-desconto-ed)
                         MOVE ws-vt-desconto TO fn-vt-desconto END-IF
                     IF ws-vt-dias-ed NOT = SPACES THEN
                          COMPUTE ws-vt-dias = FUNCTION NUMVAL(ws-vt-dias-ed)
                          MOVE ws-vt-dias TO fn-vt-dias END-IF
                     IF ws-vt-optante NOT = SPACES THEN
                          MOVE ws-vt-optante TO fn-vt-optante END-IF
                    IF ws-vr-ed NOT = SPACES THEN
                         COMPUTE ws-vr = FUNCTION NUMVAL(ws-vr-ed)
                         MOVE ws-vr TO fn-vr END-IF
                    IF ws-plano-saude NOT = SPACES THEN
                         MOVE ws-plano-saude TO fn-plano-saude END-IF
                    IF ws-plano-saude-valor-ed NOT = SPACES THEN
                         COMPUTE ws-plano-saude-valor = FUNCTION NUMVAL(ws-plano-saude-valor-ed)
                         MOVE ws-plano-saude-valor TO fn-plano-saude-valor END-IF
                     IF ws-supervisor-id NOT = SPACES THEN
                          COMPUTE ws-supervisor-id-num = FUNCTION NUMVAL(ws-supervisor-id)
                          MOVE ws-supervisor-id-num TO fn-supervisor-id END-IF
                     IF ws-sexo NOT = SPACES THEN
                          MOVE ws-sexo TO fn-sexo END-IF
                     IF ws-estado-civil NOT = SPACES THEN
                          MOVE ws-estado-civil TO fn-estado-civil END-IF
                     IF ws-nacionalidade NOT = SPACES THEN
                          MOVE ws-nacionalidade TO fn-nacionalidade END-IF
                     IF ws-rg-orgao NOT = SPACES THEN
                          MOVE ws-rg-orgao TO fn-rg-orgao END-IF
                     IF ws-rg-uf NOT = SPACES THEN
                          MOVE ws-rg-uf TO fn-rg-uf END-IF
                     IF ws-titulo-eleitor NOT = SPACES THEN
                          MOVE ws-titulo-eleitor TO fn-titulo-eleitor END-IF
                     IF ws-cep NOT = SPACES THEN
                          MOVE ws-cep TO fn-cep END-IF
                     IF ws-cidade NOT = SPACES THEN
                          MOVE ws-cidade TO fn-cidade END-IF
                     IF ws-uf NOT = SPACES THEN
                          MOVE ws-uf TO fn-uf END-IF
                     IF ws-situacao-vinculo NOT = SPACES THEN
                          MOVE ws-situacao-vinculo TO fn-situacao-vinculo END-IF
                     IF ws-departamento NOT = SPACES THEN
                          MOVE ws-departamento TO fn-departamento END-IF
                     IF ws-data-posse-cargo NOT = SPACES THEN
                          MOVE ws-data-posse-cargo TO fn-data-posse-cargo END-IF
                     IF ws-forma-pagamento NOT = SPACES THEN
                          MOVE ws-forma-pagamento TO fn-forma-pagamento END-IF
                     IF ws-meio-pagamento NOT = SPACES THEN
                          MOVE ws-meio-pagamento TO fn-meio-pagamento END-IF
                     IF ws-carga-horaria-ed NOT = SPACES THEN
                          COMPUTE ws-carga-horaria = FUNCTION NUMVAL(ws-carga-horaria-ed)
                          MOVE ws-carga-horaria TO fn-carga-horaria-mensal END-IF
                     IF ws-exame-adm-venc NOT = SPACES THEN
                          MOVE ws-exame-adm-venc TO fn-exame-adm-venc END-IF
                     IF ws-observacoes NOT = SPACES THEN
                          MOVE ws-observacoes TO fn-observacoes END-IF
                     IF ws-pensao-tipo NOT = SPACES THEN
                          MOVE ws-pensao-tipo TO fn-pensao-tipo END-IF
                     IF ws-pensao-valor-ed NOT = SPACES THEN
                          COMPUTE ws-pensao-valor = FUNCTION NUMVAL(ws-pensao-valor-ed)
                          MOVE ws-pensao-valor TO fn-pensao-valor END-IF
                     IF ws-departamento-id NOT = SPACES THEN
                          MOVE ws-departamento-num TO fn-departamento-id END-IF
                     IF ws-cargo-id NOT = SPACES THEN
                          MOVE ws-cargo-num TO fn-cargo-id END-IF
                 END-IF
                MOVE fn-id TO tl-id
                MOVE fn-nome TO tl-nome
                MOVE fn-usuario TO tl-usuario
                MOVE fn-senha TO tl-senha
                MOVE fn-permissoes TO tl-permissoes
                MOVE fn-ativo TO tl-ativo
                MOVE fn-cpf TO tl-cpf
                MOVE fn-rg TO tl-rg
                MOVE fn-data-nasc TO tl-data-nasc
                MOVE fn-celular TO tl-celular
                MOVE fn-email TO tl-email
                MOVE fn-endereco TO tl-endereco
                MOVE fn-data-adm TO tl-data-adm
                MOVE fn-data-dem TO tl-data-dem
                MOVE fn-salario TO tl-salario
                MOVE fn-filial-id TO tl-filial-id
                MOVE fn-trab-sab TO tl-trab-sab
                MOVE fn-trab-dom TO tl-trab-dom
                MOVE fn-seg-ent TO tl-seg-ent
                MOVE fn-seg-alm TO tl-seg-alm
                MOVE fn-seg-sai TO tl-seg-sai
                MOVE fn-ter-ent TO tl-ter-ent
                MOVE fn-ter-alm TO tl-ter-alm
                MOVE fn-ter-sai TO tl-ter-sai
                MOVE fn-qua-ent TO tl-qua-ent
                MOVE fn-qua-alm TO tl-qua-alm
                MOVE fn-qua-sai TO tl-qua-sai
                MOVE fn-qui-ent TO tl-qui-ent
                MOVE fn-qui-alm TO tl-qui-alm
                MOVE fn-qui-sai TO tl-qui-sai
                MOVE fn-sex-ent TO tl-sex-ent
                MOVE fn-sex-alm TO tl-sex-alm
                MOVE fn-sex-sai TO tl-sex-sai
                MOVE fn-sab-ent TO tl-sab-ent
                MOVE fn-sab-sai TO tl-sab-sai
                MOVE fn-dom-ent TO tl-dom-ent
                MOVE fn-dom-sai TO tl-dom-sai
                MOVE fn-foto TO tl-foto
                MOVE fn-contato-emerg-nome TO tl-contato-emerg-nome
                MOVE fn-contato-emerg-tel TO tl-contato-emerg-tel
                MOVE fn-curriculo TO tl-curriculo
                MOVE fn-tipo-sanguineo TO tl-tipo-sanguineo
                MOVE fn-email-particular TO tl-email-particular
                MOVE fn-tel-comercial TO tl-tel-comercial
                MOVE fn-banco TO tl-banco
                MOVE fn-agencia TO tl-agencia
                MOVE fn-conta TO tl-conta
                MOVE fn-conta-digito TO tl-conta-digito
                MOVE fn-conta-tipo TO tl-conta-tipo
                 MOVE fn-pix TO tl-pix
                 MOVE fn-pis TO tl-pis
                 MOVE fn-ctps TO tl-ctps
                 MOVE fn-ctps-serie TO tl-ctps-serie
                 MOVE fn-ctps-uf TO tl-ctps-uf
                 MOVE fn-cbo TO tl-cbo
                 MOVE fn-grau-instrucao TO tl-grau-instrucao
                 MOVE fn-tipo-contrato TO tl-tipo-contrato
                 MOVE fn-motivo-deslig TO tl-motivo-deslig
                  MOVE fn-vt-desconto TO tl-vt-desconto
                  MOVE fn-vt-dias TO tl-vt-dias
                  MOVE fn-vt-optante TO tl-vt-optante
                  MOVE fn-vr TO tl-vr
                  MOVE fn-plano-saude TO tl-plano-saude
                 MOVE fn-plano-saude-valor TO tl-plano-saude-valor
                 MOVE fn-supervisor-id TO tl-supervisor-id
                 MOVE fn-sexo TO tl-sexo
                 MOVE fn-estado-civil TO tl-estado-civil
                 MOVE fn-nacionalidade TO tl-nacionalidade
                 MOVE fn-rg-orgao TO tl-rg-orgao
                 MOVE fn-rg-uf TO tl-rg-uf
                 MOVE fn-titulo-eleitor TO tl-titulo-eleitor
                 MOVE fn-cep TO tl-cep
                 MOVE fn-cidade TO tl-cidade
                 MOVE fn-uf TO tl-uf
                 MOVE fn-situacao-vinculo TO tl-situacao-vinculo
                 MOVE fn-departamento TO tl-departamento
                 MOVE fn-data-posse-cargo TO tl-data-posse-cargo
                 MOVE fn-forma-pagamento TO tl-forma-pagamento
                 MOVE fn-meio-pagamento TO tl-meio-pagamento
                 MOVE fn-carga-horaria-mensal TO tl-carga-horaria-mensal
                 MOVE fn-exame-adm-venc TO tl-exame-adm-venc
                 MOVE fn-observacoes TO tl-observacoes
                 MOVE fn-pensao-tipo TO tl-pensao-tipo
                 MOVE fn-pensao-valor TO tl-pensao-valor
                 MOVE fn-departamento-id TO tl-departamento-id
                 MOVE fn-cargo-id TO tl-cargo-id
                 WRITE temp-reg
             END-PERFORM
             CLOSE fn-file CLOSE temp-file
            CALL "system" USING "mv dados/funcionarios.tmp dados/funcionarios.dat"
            END-CALL
            IF ws-encontrou = "S" THEN DISPLAY "OK"
            ELSE DISPLAY "ERRO: funcionario nao encontrado".

        excluir.
            ACCEPT ws-id-in FROM ENVIRONMENT "ID"
            COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)

            MOVE "N" TO ws-encontrou
            OPEN INPUT fn-file
            IF ws-file-status = "35" THEN
                DISPLAY "ERRO: funcionario nao encontrado" STOP RUN END-IF
            OPEN OUTPUT temp-file
            PERFORM UNTIL 1 = 2
                READ fn-file NEXT RECORD
                    AT END EXIT PERFORM
                END-READ
                IF fn-id NOT = ws-id THEN
                    MOVE fn-id TO tl-id
                    MOVE fn-nome TO tl-nome
                    MOVE fn-usuario TO tl-usuario
                    MOVE fn-senha TO tl-senha
                    MOVE fn-permissoes TO tl-permissoes
                    MOVE fn-ativo TO tl-ativo
                    MOVE fn-cpf TO tl-cpf
                    MOVE fn-rg TO tl-rg
                    MOVE fn-data-nasc TO tl-data-nasc
                    MOVE fn-celular TO tl-celular
                    MOVE fn-email TO tl-email
                    MOVE fn-endereco TO tl-endereco
                    MOVE fn-data-adm TO tl-data-adm
                    MOVE fn-data-dem TO tl-data-dem
                    MOVE fn-salario TO tl-salario
                    MOVE fn-filial-id TO tl-filial-id
                    MOVE fn-trab-sab TO tl-trab-sab
                    MOVE fn-trab-dom TO tl-trab-dom
                    MOVE fn-seg-ent TO tl-seg-ent
                    MOVE fn-seg-alm TO tl-seg-alm
                    MOVE fn-seg-sai TO tl-seg-sai
                    MOVE fn-ter-ent TO tl-ter-ent
                    MOVE fn-ter-alm TO tl-ter-alm
                    MOVE fn-ter-sai TO tl-ter-sai
                    MOVE fn-qua-ent TO tl-qua-ent
                    MOVE fn-qua-alm TO tl-qua-alm
                    MOVE fn-qua-sai TO tl-qua-sai
                    MOVE fn-qui-ent TO tl-qui-ent
                    MOVE fn-qui-alm TO tl-qui-alm
                    MOVE fn-qui-sai TO tl-qui-sai
                    MOVE fn-sex-ent TO tl-sex-ent
                    MOVE fn-sex-alm TO tl-sex-alm
                    MOVE fn-sex-sai TO tl-sex-sai
                    MOVE fn-sab-ent TO tl-sab-ent
                    MOVE fn-sab-sai TO tl-sab-sai
                    MOVE fn-dom-ent TO tl-dom-ent
                    MOVE fn-dom-sai TO tl-dom-sai
                    MOVE fn-foto TO tl-foto
                    MOVE fn-contato-emerg-nome TO tl-contato-emerg-nome
                    MOVE fn-contato-emerg-tel TO tl-contato-emerg-tel
                    MOVE fn-curriculo TO tl-curriculo
                    MOVE fn-tipo-sanguineo TO tl-tipo-sanguineo
                    MOVE fn-email-particular TO tl-email-particular
                    MOVE fn-tel-comercial TO tl-tel-comercial
                    MOVE fn-banco TO tl-banco
                    MOVE fn-agencia TO tl-agencia
                    MOVE fn-conta TO tl-conta
                    MOVE fn-conta-digito TO tl-conta-digito
                    MOVE fn-conta-tipo TO tl-conta-tipo
                     MOVE fn-pix TO tl-pix
                     MOVE fn-pis TO tl-pis
                     MOVE fn-ctps TO tl-ctps
                     MOVE fn-ctps-serie TO tl-ctps-serie
                     MOVE fn-ctps-uf TO tl-ctps-uf
                     MOVE fn-cbo TO tl-cbo
                     MOVE fn-grau-instrucao TO tl-grau-instrucao
                     MOVE fn-tipo-contrato TO tl-tipo-contrato
                     MOVE fn-motivo-deslig TO tl-motivo-deslig
                      MOVE fn-vt-desconto TO tl-vt-desconto
                      MOVE fn-vt-dias TO tl-vt-dias
                      MOVE fn-vt-optante TO tl-vt-optante
                      MOVE fn-vr TO tl-vr
                      MOVE fn-plano-saude TO tl-plano-saude
                     MOVE fn-plano-saude-valor TO tl-plano-saude-valor
                     MOVE fn-supervisor-id TO tl-supervisor-id
                     MOVE fn-sexo TO tl-sexo
                     MOVE fn-estado-civil TO tl-estado-civil
                     MOVE fn-nacionalidade TO tl-nacionalidade
                     MOVE fn-rg-orgao TO tl-rg-orgao
                     MOVE fn-rg-uf TO tl-rg-uf
                     MOVE fn-titulo-eleitor TO tl-titulo-eleitor
                     MOVE fn-cep TO tl-cep
                     MOVE fn-cidade TO tl-cidade
                     MOVE fn-uf TO tl-uf
                     MOVE fn-situacao-vinculo TO tl-situacao-vinculo
                     MOVE fn-departamento TO tl-departamento
                     MOVE fn-data-posse-cargo TO tl-data-posse-cargo
                     MOVE fn-forma-pagamento TO tl-forma-pagamento
                     MOVE fn-meio-pagamento TO tl-meio-pagamento
                     MOVE fn-carga-horaria-mensal TO tl-carga-horaria-mensal
                     MOVE fn-exame-adm-venc TO tl-exame-adm-venc
                     MOVE fn-observacoes TO tl-observacoes
                     MOVE fn-pensao-tipo TO tl-pensao-tipo
                     MOVE fn-pensao-valor TO tl-pensao-valor
                     MOVE fn-departamento-id TO tl-departamento-id
                     MOVE fn-cargo-id TO tl-cargo-id
                     WRITE temp-reg
                 ELSE MOVE "S" TO ws-encontrou
                END-IF
            END-PERFORM
            CLOSE fn-file CLOSE temp-file
            CALL "system" USING "mv dados/funcionarios.tmp dados/funcionarios.dat"
            END-CALL
            IF ws-encontrou = "S" THEN DISPLAY "OK"
            ELSE DISPLAY "ERRO: funcionario nao encontrado".

       normaliza-cpf.
           MOVE SPACES TO ws-cpf-limpo
           MOVE 1 TO ws-idx
           PERFORM VARYING ws-i FROM 1 BY 1 UNTIL ws-i > 14
               IF ws-cpf(ws-i:1) >= "0" AND ws-cpf(ws-i:1) <= "9"
                  AND ws-idx < 12 THEN
                   MOVE ws-cpf(ws-i:1) TO ws-cpf-limpo(ws-idx:1)
                   ADD 1 TO ws-idx
               END-IF
           END-PERFORM.

       normaliza-cpf-lido.
           MOVE fn-cpf TO ws-temp-cpf
           MOVE SPACES TO ws-cpf-lido-limpo
           MOVE 1 TO ws-idx
           PERFORM VARYING ws-i FROM 1 BY 1 UNTIL ws-i > 14
               IF ws-temp-cpf(ws-i:1) >= "0" AND ws-temp-cpf(ws-i:1) <= "9"
                  AND ws-idx < 12 THEN
                   MOVE ws-temp-cpf(ws-i:1) TO ws-cpf-lido-limpo(ws-idx:1)
                   ADD 1 TO ws-idx
               END-IF
           END-PERFORM.

       validar-departamento.
           OPEN INPUT dep-file
           IF ws-ref-status = "35" THEN
               DISPLAY "ERRO: departamento nao cadastrado" STOP RUN END-IF
           MOVE "N" TO ws-achou-ref
           PERFORM UNTIL 1 = 2
               READ dep-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF dep-id = ws-departamento-num AND dep-status = "ativo" THEN
                   MOVE "S" TO ws-achou-ref
               END-IF
           END-PERFORM
           CLOSE dep-file
           IF ws-achou-ref = "N" THEN
               DISPLAY "ERRO: departamento invalido ou inativo" STOP RUN END-IF.

       validar-cargo.
           OPEN INPUT cr-file
           IF ws-ref-status = "35" THEN
               DISPLAY "ERRO: cargo nao cadastrado" STOP RUN END-IF
           MOVE "N" TO ws-achou-ref
           PERFORM UNTIL 1 = 2
               READ cr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF cr-id = ws-cargo-num AND cr-status = "ativo" THEN
                   MOVE "S" TO ws-achou-ref
               END-IF
           END-PERFORM
           CLOSE cr-file
           IF ws-achou-ref = "N" THEN
               DISPLAY "ERRO: cargo invalido ou inativo" STOP RUN END-IF.

       login.
           ACCEPT ws-usuario FROM ENVIRONMENT "USUARIO"
           ACCEPT ws-senha FROM ENVIRONMENT "SENHA"
           IF ws-usuario = SPACES OR ws-senha = SPACES THEN
               DISPLAY '{"status":"erro","mensagem":"usuario e senha obrigatorios"}'
               STOP RUN END-IF

           OPEN INPUT fn-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"status":"erro","mensagem":"nenhum funcionario cadastrado"}'
               STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ fn-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fn-usuario = ws-usuario AND fn-senha = ws-senha
                   AND fn-ativo = "S" THEN
                   MOVE "S" TO ws-encontrou
                   MOVE fn-id TO ws-id-ed
                   DISPLAY '{"status":"ok","tipo":"funcionario"'
                       ',"id":' FUNCTION TRIM(ws-id-ed)
                       ',"nome":"' FUNCTION TRIM(fn-nome) '"'
                       ',"usuario":"' FUNCTION TRIM(fn-usuario) '"'
                       ',"permissoes":"' FUNCTION TRIM(fn-permissoes) '"}'
                   EXIT PERFORM
               END-IF
           END-PERFORM
           CLOSE fn-file
           IF ws-encontrou = "N" THEN
               DISPLAY '{"status":"erro","mensagem":"usuario ou senha incorretos"}'
           END-IF.

       desligar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-data-dem FROM ENVIRONMENT "DATA_DEM"
           ACCEPT ws-motivo-deslig FROM ENVIRONMENT "MOTIVO_DESLIG"
           IF ws-data-dem = SPACES THEN
               MOVE FUNCTION CURRENT-DATE(1:8) TO ws-data-edit
               STRING ws-dt-ano "-" ws-dt-mes "-" ws-dt-dia
                   DELIMITED BY SIZE INTO ws-data-dem
           END-IF
           IF ws-motivo-deslig = SPACES THEN
               DISPLAY "ERRO: motivo de desligamento obrigatorio"
               STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           OPEN INPUT fn-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: funcionario nao encontrado" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ fn-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fn-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF fn-situacao-vinculo = "desligado" THEN
                       DISPLAY "ERRO: funcionario ja desligado"
                       STOP RUN END-IF
                   MOVE "desligado" TO fn-situacao-vinculo
                   MOVE ws-data-dem TO fn-data-dem
                   MOVE ws-motivo-deslig TO fn-motivo-deslig
               END-IF
               MOVE fn-id TO tl-id
               MOVE fn-nome TO tl-nome
               MOVE fn-usuario TO tl-usuario
               MOVE fn-senha TO tl-senha
               MOVE fn-permissoes TO tl-permissoes
               MOVE fn-ativo TO tl-ativo
               MOVE fn-cpf TO tl-cpf
               MOVE fn-rg TO tl-rg
               MOVE fn-data-nasc TO tl-data-nasc
               MOVE fn-celular TO tl-celular
               MOVE fn-email TO tl-email
               MOVE fn-endereco TO tl-endereco
               MOVE fn-data-adm TO tl-data-adm
               MOVE fn-data-dem TO tl-data-dem
               MOVE fn-salario TO tl-salario
               MOVE fn-filial-id TO tl-filial-id
               MOVE fn-trab-sab TO tl-trab-sab
               MOVE fn-trab-dom TO tl-trab-dom
               MOVE fn-seg-ent TO tl-seg-ent
               MOVE fn-seg-alm TO tl-seg-alm
               MOVE fn-seg-sai TO tl-seg-sai
               MOVE fn-ter-ent TO tl-ter-ent
               MOVE fn-ter-alm TO tl-ter-alm
               MOVE fn-ter-sai TO tl-ter-sai
               MOVE fn-qua-ent TO tl-qua-ent
               MOVE fn-qua-alm TO tl-qua-alm
               MOVE fn-qua-sai TO tl-qua-sai
               MOVE fn-qui-ent TO tl-qui-ent
               MOVE fn-qui-alm TO tl-qui-alm
               MOVE fn-qui-sai TO tl-qui-sai
               MOVE fn-sex-ent TO tl-sex-ent
               MOVE fn-sex-alm TO tl-sex-alm
               MOVE fn-sex-sai TO tl-sex-sai
               MOVE fn-sab-ent TO tl-sab-ent
               MOVE fn-sab-sai TO tl-sab-sai
               MOVE fn-dom-ent TO tl-dom-ent
               MOVE fn-dom-sai TO tl-dom-sai
               MOVE fn-foto TO tl-foto
               MOVE fn-contato-emerg-nome TO tl-contato-emerg-nome
               MOVE fn-contato-emerg-tel TO tl-contato-emerg-tel
               MOVE fn-curriculo TO tl-curriculo
               MOVE fn-tipo-sanguineo TO tl-tipo-sanguineo
               MOVE fn-email-particular TO tl-email-particular
               MOVE fn-tel-comercial TO tl-tel-comercial
               MOVE fn-banco TO tl-banco
               MOVE fn-agencia TO tl-agencia
               MOVE fn-conta TO tl-conta
               MOVE fn-conta-digito TO tl-conta-digito
               MOVE fn-conta-tipo TO tl-conta-tipo
               MOVE fn-pix TO tl-pix
               MOVE fn-pis TO tl-pis
               MOVE fn-ctps TO tl-ctps
               MOVE fn-ctps-serie TO tl-ctps-serie
               MOVE fn-ctps-uf TO tl-ctps-uf
               MOVE fn-cbo TO tl-cbo
               MOVE fn-grau-instrucao TO tl-grau-instrucao
               MOVE fn-tipo-contrato TO tl-tipo-contrato
               MOVE fn-motivo-deslig TO tl-motivo-deslig
               MOVE fn-vt-desconto TO tl-vt-desconto
               MOVE fn-vt-dias TO tl-vt-dias
               MOVE fn-vt-optante TO tl-vt-optante
               MOVE fn-vr TO tl-vr
               MOVE fn-plano-saude TO tl-plano-saude
               MOVE fn-plano-saude-valor TO tl-plano-saude-valor
               MOVE fn-supervisor-id TO tl-supervisor-id
               MOVE fn-sexo TO tl-sexo
               MOVE fn-estado-civil TO tl-estado-civil
               MOVE fn-nacionalidade TO tl-nacionalidade
               MOVE fn-rg-orgao TO tl-rg-orgao
               MOVE fn-rg-uf TO tl-rg-uf
               MOVE fn-titulo-eleitor TO tl-titulo-eleitor
               MOVE fn-cep TO tl-cep
               MOVE fn-cidade TO tl-cidade
               MOVE fn-uf TO tl-uf
               MOVE fn-situacao-vinculo TO tl-situacao-vinculo
               MOVE fn-departamento TO tl-departamento
               MOVE fn-data-posse-cargo TO tl-data-posse-cargo
               MOVE fn-forma-pagamento TO tl-forma-pagamento
               MOVE fn-meio-pagamento TO tl-meio-pagamento
               MOVE fn-carga-horaria-mensal TO tl-carga-horaria-mensal
               MOVE fn-exame-adm-venc TO tl-exame-adm-venc
               MOVE fn-observacoes TO tl-observacoes
               MOVE fn-pensao-tipo TO tl-pensao-tipo
               MOVE fn-pensao-valor TO tl-pensao-valor
               MOVE fn-departamento-id TO tl-departamento-id
               MOVE fn-cargo-id TO tl-cargo-id
               WRITE temp-reg
           END-PERFORM
           CLOSE fn-file CLOSE temp-file
           CALL "system" USING "mv dados/funcionarios.tmp dados/funcionarios.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: funcionario nao encontrado".

       reativar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           MOVE "N" TO ws-encontrou
           OPEN INPUT fn-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: funcionario nao encontrado" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ fn-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fn-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   MOVE "ativo" TO fn-situacao-vinculo
                   MOVE SPACES TO fn-data-dem
                   MOVE SPACES TO fn-motivo-deslig
               END-IF
               MOVE fn-id TO tl-id
               MOVE fn-nome TO tl-nome
               MOVE fn-usuario TO tl-usuario
               MOVE fn-senha TO tl-senha
               MOVE fn-permissoes TO tl-permissoes
               MOVE fn-ativo TO tl-ativo
               MOVE fn-cpf TO tl-cpf
               MOVE fn-rg TO tl-rg
               MOVE fn-data-nasc TO tl-data-nasc
               MOVE fn-celular TO tl-celular
               MOVE fn-email TO tl-email
               MOVE fn-endereco TO tl-endereco
               MOVE fn-data-adm TO tl-data-adm
               MOVE fn-data-dem TO tl-data-dem
               MOVE fn-salario TO tl-salario
               MOVE fn-filial-id TO tl-filial-id
               MOVE fn-trab-sab TO tl-trab-sab
               MOVE fn-trab-dom TO tl-trab-dom
               MOVE fn-seg-ent TO tl-seg-ent
               MOVE fn-seg-alm TO tl-seg-alm
               MOVE fn-seg-sai TO tl-seg-sai
               MOVE fn-ter-ent TO tl-ter-ent
               MOVE fn-ter-alm TO tl-ter-alm
               MOVE fn-ter-sai TO tl-ter-sai
               MOVE fn-qua-ent TO tl-qua-ent
               MOVE fn-qua-alm TO tl-qua-alm
               MOVE fn-qua-sai TO tl-qua-sai
               MOVE fn-qui-ent TO tl-qui-ent
               MOVE fn-qui-alm TO tl-qui-alm
               MOVE fn-qui-sai TO tl-qui-sai
               MOVE fn-sex-ent TO tl-sex-ent
               MOVE fn-sex-alm TO tl-sex-alm
               MOVE fn-sex-sai TO tl-sex-sai
               MOVE fn-sab-ent TO tl-sab-ent
               MOVE fn-sab-sai TO tl-sab-sai
               MOVE fn-dom-ent TO tl-dom-ent
               MOVE fn-dom-sai TO tl-dom-sai
               MOVE fn-foto TO tl-foto
               MOVE fn-contato-emerg-nome TO tl-contato-emerg-nome
               MOVE fn-contato-emerg-tel TO tl-contato-emerg-tel
               MOVE fn-curriculo TO tl-curriculo
               MOVE fn-tipo-sanguineo TO tl-tipo-sanguineo
               MOVE fn-email-particular TO tl-email-particular
               MOVE fn-tel-comercial TO tl-tel-comercial
               MOVE fn-banco TO tl-banco
               MOVE fn-agencia TO tl-agencia
               MOVE fn-conta TO tl-conta
               MOVE fn-conta-digito TO tl-conta-digito
               MOVE fn-conta-tipo TO tl-conta-tipo
               MOVE fn-pix TO tl-pix
               MOVE fn-pis TO tl-pis
               MOVE fn-ctps TO tl-ctps
               MOVE fn-ctps-serie TO tl-ctps-serie
               MOVE fn-ctps-uf TO tl-ctps-uf
               MOVE fn-cbo TO tl-cbo
               MOVE fn-grau-instrucao TO tl-grau-instrucao
               MOVE fn-tipo-contrato TO tl-tipo-contrato
               MOVE fn-motivo-deslig TO tl-motivo-deslig
               MOVE fn-vt-desconto TO tl-vt-desconto
               MOVE fn-vt-dias TO tl-vt-dias
               MOVE fn-vt-optante TO tl-vt-optante
               MOVE fn-vr TO tl-vr
               MOVE fn-plano-saude TO tl-plano-saude
               MOVE fn-plano-saude-valor TO tl-plano-saude-valor
               MOVE fn-supervisor-id TO tl-supervisor-id
               MOVE fn-sexo TO tl-sexo
               MOVE fn-estado-civil TO tl-estado-civil
               MOVE fn-nacionalidade TO tl-nacionalidade
               MOVE fn-rg-orgao TO tl-rg-orgao
               MOVE fn-rg-uf TO tl-rg-uf
               MOVE fn-titulo-eleitor TO tl-titulo-eleitor
               MOVE fn-cep TO tl-cep
               MOVE fn-cidade TO tl-cidade
               MOVE fn-uf TO tl-uf
               MOVE fn-situacao-vinculo TO tl-situacao-vinculo
               MOVE fn-departamento TO tl-departamento
               MOVE fn-data-posse-cargo TO tl-data-posse-cargo
               MOVE fn-forma-pagamento TO tl-forma-pagamento
               MOVE fn-meio-pagamento TO tl-meio-pagamento
               MOVE fn-carga-horaria-mensal TO tl-carga-horaria-mensal
               MOVE fn-exame-adm-venc TO tl-exame-adm-venc
               MOVE fn-observacoes TO tl-observacoes
               MOVE fn-pensao-tipo TO tl-pensao-tipo
               MOVE fn-pensao-valor TO tl-pensao-valor
               MOVE fn-departamento-id TO tl-departamento-id
               MOVE fn-cargo-id TO tl-cargo-id
               WRITE temp-reg
           END-PERFORM
           CLOSE fn-file CLOSE temp-file
           CALL "system" USING "mv dados/funcionarios.tmp dados/funcionarios.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: funcionario nao encontrado".

       listar.
           OPEN INPUT fn-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"funcionarios":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"funcionarios":['
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-prox-id
           PERFORM UNTIL 1 = 2
               READ fn-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-prox-id
               IF ws-encontrou = "S" THEN
                   MOVE "N" TO ws-encontrou
               ELSE DISPLAY "," END-IF
               MOVE fn-id TO ws-id-ed
               MOVE fn-salario TO ws-salario-j
               MOVE fn-filial-id TO ws-filial-j
                MOVE fn-vt-desconto TO ws-vt-desc-j
                MOVE fn-vt-dias TO ws-vt-dias-j
                MOVE fn-vr TO ws-vr-j
                MOVE fn-plano-saude-valor TO ws-plano-val-j
                MOVE fn-supervisor-id TO ws-supervisor-j
                MOVE fn-carga-horaria-mensal TO ws-carga-horaria-j
                MOVE fn-pensao-valor TO ws-pensao-valor-j
                IF fn-departamento-id = SPACES THEN MOVE 0 TO ws-dept-j
                ELSE MOVE fn-departamento-id TO ws-dept-j END-IF
                IF fn-cargo-id = SPACES THEN MOVE 0 TO ws-cargo-j
                ELSE MOVE fn-cargo-id TO ws-cargo-j END-IF
                MOVE SPACES TO ws-json-linha
               STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                      ',"nome":"' FUNCTION TRIM(fn-nome) '"'
                      ',"usuario":"' FUNCTION TRIM(fn-usuario) '"'
                      ',"permissoes":"' FUNCTION TRIM(fn-permissoes) '"'
                      ',"cpf":"' FUNCTION TRIM(fn-cpf) '"'
                      ',"rg":"' FUNCTION TRIM(fn-rg) '"'
                      ',"data_nasc":"' FUNCTION TRIM(fn-data-nasc) '"'
                      ',"celular":"' FUNCTION TRIM(fn-celular) '"'
                      ',"email":"' FUNCTION TRIM(fn-email) '"'
                      ',"endereco":"' FUNCTION TRIM(fn-endereco) '"'
                      ',"data_adm":"' FUNCTION TRIM(fn-data-adm) '"'
                      ',"data_dem":"' FUNCTION TRIM(fn-data-dem) '"'
                       ',"salario":' FUNCTION TRIM(ws-salario-j)
                       ',"filial_id":' FUNCTION TRIM(ws-filial-j)
                       ',"trab_sab":"' FUNCTION TRIM(fn-trab-sab) '"'
                       ',"trab_dom":"' FUNCTION TRIM(fn-trab-dom) '"'
                       ',"seg_ent":"' FUNCTION TRIM(fn-seg-ent) '"'
                       ',"seg_alm":"' FUNCTION TRIM(fn-seg-alm) '"'
                       ',"seg_sai":"' FUNCTION TRIM(fn-seg-sai) '"'
                       ',"ter_ent":"' FUNCTION TRIM(fn-ter-ent) '"'
                       ',"ter_alm":"' FUNCTION TRIM(fn-ter-alm) '"'
                       ',"ter_sai":"' FUNCTION TRIM(fn-ter-sai) '"'
                       ',"qua_ent":"' FUNCTION TRIM(fn-qua-ent) '"'
                       ',"qua_alm":"' FUNCTION TRIM(fn-qua-alm) '"'
                       ',"qua_sai":"' FUNCTION TRIM(fn-qua-sai) '"'
                       ',"qui_ent":"' FUNCTION TRIM(fn-qui-ent) '"'
                       ',"qui_alm":"' FUNCTION TRIM(fn-qui-alm) '"'
                       ',"qui_sai":"' FUNCTION TRIM(fn-qui-sai) '"'
                       ',"sex_ent":"' FUNCTION TRIM(fn-sex-ent) '"'
                       ',"sex_alm":"' FUNCTION TRIM(fn-sex-alm) '"'
                       ',"sex_sai":"' FUNCTION TRIM(fn-sex-sai) '"'
                       ',"sab_ent":"' FUNCTION TRIM(fn-sab-ent) '"'
                       ',"sab_sai":"' FUNCTION TRIM(fn-sab-sai) '"'
                       ',"dom_ent":"' FUNCTION TRIM(fn-dom-ent) '"'
                       ',"dom_sai":"' FUNCTION TRIM(fn-dom-sai) '"'
                       ',"foto":"' FUNCTION TRIM(fn-foto) '"'
                       ',"contato_emerg_nome":"' FUNCTION TRIM(fn-contato-emerg-nome) '"'
                       ',"contato_emerg_tel":"' FUNCTION TRIM(fn-contato-emerg-tel) '"'
                       ',"curriculo":"' FUNCTION TRIM(fn-curriculo) '"'
                       ',"tipo_sanguineo":"' FUNCTION TRIM(fn-tipo-sanguineo) '"'
                       ',"email_particular":"' FUNCTION TRIM(fn-email-particular) '"'
                       ',"tel_comercial":"' FUNCTION TRIM(fn-tel-comercial) '"'
                       ',"banco":"' FUNCTION TRIM(fn-banco) '"'
                       ',"agencia":"' FUNCTION TRIM(fn-agencia) '"'
                       ',"conta":"' FUNCTION TRIM(fn-conta) '"'
                       ',"conta_digito":"' FUNCTION TRIM(fn-conta-digito) '"'
                       ',"conta_tipo":"' FUNCTION TRIM(fn-conta-tipo) '"'
                        ',"pix":"' FUNCTION TRIM(fn-pix) '"'
                        ',"pis":"' FUNCTION TRIM(fn-pis) '"'
                        ',"ctps":"' FUNCTION TRIM(fn-ctps) '"'
                        ',"ctps_serie":"' FUNCTION TRIM(fn-ctps-serie) '"'
                        ',"ctps_uf":"' FUNCTION TRIM(fn-ctps-uf) '"'
                        ',"cbo":"' FUNCTION TRIM(fn-cbo) '"'
                        ',"grau_instrucao":"' FUNCTION TRIM(fn-grau-instrucao) '"'
                        ',"tipo_contrato":"' FUNCTION TRIM(fn-tipo-contrato) '"'
                         ',"motivo_deslig":"' FUNCTION TRIM(fn-motivo-deslig) '"'
                          ',"vt_desconto":' FUNCTION TRIM(ws-vt-desc-j)
                          ',"vt_dias":' FUNCTION TRIM(ws-vt-dias-j)
                          ',"vt_optante":"' FUNCTION TRIM(fn-vt-optante) '"'
                          ',"vr":' FUNCTION TRIM(ws-vr-j)
                          ',"plano_saude":"' FUNCTION TRIM(fn-plano-saude) '"'
                          ',"plano_saude_valor":' FUNCTION TRIM(ws-plano-val-j)
                          ',"supervisor_id":' FUNCTION TRIM(ws-supervisor-j)
                          ',"sexo":"' FUNCTION TRIM(fn-sexo) '"'
                          ',"estado_civil":"' FUNCTION TRIM(fn-estado-civil) '"'
                          ',"nacionalidade":"' FUNCTION TRIM(fn-nacionalidade) '"'
                          ',"rg_orgao":"' FUNCTION TRIM(fn-rg-orgao) '"'
                          ',"rg_uf":"' FUNCTION TRIM(fn-rg-uf) '"'
                          ',"titulo_eleitor":"' FUNCTION TRIM(fn-titulo-eleitor) '"'
                          ',"cep":"' FUNCTION TRIM(fn-cep) '"'
                          ',"cidade":"' FUNCTION TRIM(fn-cidade) '"'
                          ',"uf":"' FUNCTION TRIM(fn-uf) '"'
                          ',"situacao_vinculo":"' FUNCTION TRIM(fn-situacao-vinculo) '"'
                          ',"departamento":"' FUNCTION TRIM(fn-departamento) '"'
                          ',"data_posse_cargo":"' FUNCTION TRIM(fn-data-posse-cargo) '"'
                          ',"forma_pagamento":"' FUNCTION TRIM(fn-forma-pagamento) '"'
                          ',"meio_pagamento":"' FUNCTION TRIM(fn-meio-pagamento) '"'
                          ',"carga_horaria":' FUNCTION TRIM(ws-carga-horaria-j)
                          ',"exame_adm_venc":"' FUNCTION TRIM(fn-exame-adm-venc) '"'
                          ',"observacoes":"' FUNCTION TRIM(fn-observacoes) '"'
                          ',"pensao_tipo":"' FUNCTION TRIM(fn-pensao-tipo) '"'
                          ',"pensao_valor":' FUNCTION TRIM(ws-pensao-valor-j)
                          ',"departamento_id":' FUNCTION TRIM(ws-dept-j)
                          ',"cargo_id":' FUNCTION TRIM(ws-cargo-j) '}'
                    INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
           END-PERFORM
           MOVE ws-prox-id TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE fn-file.
