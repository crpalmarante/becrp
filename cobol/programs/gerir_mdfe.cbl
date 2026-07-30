       >>SOURCE FORMAT IS FREE
       *> gerir_mdfe.cbl - CRUD Manifesto Eletronico
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirMDFe.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT mdfe-file ASSIGN TO "dados/mdfe.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/mdfe.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD mdfe-file.
       01 mdfe-reg.
           05 md-id             PIC 9(5).
           05 md-numero         PIC 9(9).
           05 md-serie          PIC 9(3).
           05 md-chave          PIC X(44).
           05 md-cnpj-emit      PIC X(14).
           05 md-nome-emit      PIC X(60).
           05 md-modal          PIC X(2).
           05 md-uf-ini         PIC X(2).
           05 md-uf-fim         PIC X(2).
           05 md-mun-ini        PIC X(40).
           05 md-mun-fim        PIC X(40).
           05 md-valor-carga    PIC 9(9)V99.
           05 md-qtd-docs       PIC 9(5).
           05 md-placa-veic     PIC X(7).
           05 md-motorista      PIC X(60).
           05 md-cpf-motorista  PIC X(11).
           05 md-status         PIC X(20).
           05 md-proc           PIC X(15).
           05 md-data-emissao   PIC X(20).

       FD temp-file.
       01 temp-reg.
           05 td-id             PIC 9(5).
           05 td-numero         PIC 9(9).
           05 td-serie          PIC 9(3).
           05 td-chave          PIC X(44).
           05 td-cnpj-emit      PIC X(14).
           05 td-nome-emit      PIC X(60).
           05 td-modal          PIC X(2).
           05 td-uf-ini         PIC X(2).
           05 td-uf-fim         PIC X(2).
           05 td-mun-ini        PIC X(40).
           05 td-mun-fim        PIC X(40).
           05 td-valor-carga    PIC 9(9)V99.
           05 td-qtd-docs       PIC 9(5).
           05 td-placa-veic     PIC X(7).
           05 td-motorista      PIC X(60).
           05 td-cpf-motorista  PIC X(11).
           05 td-status         PIC X(20).
           05 td-proc           PIC X(15).
           05 td-data-emissao   PIC X(20).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-file-status     PIC X(2).
       01 ws-existe          PIC X(1).
       01 ws-json-linha      PIC X(800).
       01 ws-id-ed           PIC ZZZZ9.
       01 ws-total-ed        PIC ZZZZ9.
        01 ws-valor-ed        PIC ZZZZZZZZZ9.99.
        01 ws-numero-ed       PIC Z(8)9.
        01 ws-serie-ed        PIC ZZ9.
        01 ws-id              PIC 9(5).
       01 ws-id-in           PIC X(10).
       01 ws-numero          PIC 9(9).
       01 ws-serie           PIC 9(3).
       01 ws-chave           PIC X(44).
       01 ws-cnpj-emit       PIC X(14).
       01 ws-nome-emit       PIC X(60).
       01 ws-modal           PIC X(2).
       01 ws-uf-ini          PIC X(2).
       01 ws-uf-fim          PIC X(2).
       01 ws-mun-ini         PIC X(40).
       01 ws-mun-fim         PIC X(40).
       01 ws-valor-carga     PIC 9(9)V99.
       01 ws-qtd-docs        PIC 9(5).
       01 ws-placa-veic      PIC X(7).
       01 ws-motorista       PIC X(60).
       01 ws-cpf-motorista   PIC X(11).
       01 ws-status          PIC X(20).
       01 ws-proc            PIC X(15).
       01 ws-data-emissao    PIC X(20).
       01 ws-encontrou       PIC X(1).
       01 ws-prox-id         PIC 9(5).
       01 ws-valor-str       PIC X(15).
       01 ws-qtd-str         PIC X(5).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF

           EVALUATE ws-acao
               WHEN "incluir"  PERFORM incluir
               WHEN "alterar"  PERFORM alterar
               WHEN "excluir"  PERFORM excluir
               WHEN "listar"   PERFORM listar
               WHEN "buscar"   PERFORM buscar
               WHEN OTHER      DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       incluir.
           ACCEPT ws-numero FROM ENVIRONMENT "NUMERO"
           ACCEPT ws-serie FROM ENVIRONMENT "SERIE"
           ACCEPT ws-chave FROM ENVIRONMENT "CHAVE"
           ACCEPT ws-cnpj-emit FROM ENVIRONMENT "CNPJ_EMIT"
           ACCEPT ws-nome-emit FROM ENVIRONMENT "NOME_EMIT"
           ACCEPT ws-modal FROM ENVIRONMENT "MODAL"
           ACCEPT ws-uf-ini FROM ENVIRONMENT "UF_INI"
           ACCEPT ws-uf-fim FROM ENVIRONMENT "UF_FIM"
           ACCEPT ws-mun-ini FROM ENVIRONMENT "MUN_INI"
           ACCEPT ws-mun-fim FROM ENVIRONMENT "MUN_FIM"
           ACCEPT ws-valor-str FROM ENVIRONMENT "VALOR_CARGA"
           ACCEPT ws-qtd-str FROM ENVIRONMENT "QTD_DOCS"
           ACCEPT ws-placa-veic FROM ENVIRONMENT "PLACA_VEIC"
           ACCEPT ws-motorista FROM ENVIRONMENT "MOTORISTA"
           ACCEPT ws-cpf-motorista FROM ENVIRONMENT "CPF_MOTORISTA"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           ACCEPT ws-proc FROM ENVIRONMENT "PROTOCOLO"
           ACCEPT ws-data-emissao FROM ENVIRONMENT "DATA_EMISSAO"

           IF ws-nome-emit = SPACES THEN
               DISPLAY "ERRO: nome do emitente obrigatorio"
               EXIT PARAGRAPH
           END-IF

           IF ws-valor-str NOT = SPACES THEN
               COMPUTE ws-valor-carga = FUNCTION NUMVAL(ws-valor-str)
           END-IF
           IF ws-qtd-str NOT = SPACES THEN
               COMPUTE ws-qtd-docs = FUNCTION NUMVAL(ws-qtd-str)
           END-IF

           MOVE 0 TO ws-prox-id
           OPEN INPUT mdfe-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT mdfe-file CLOSE mdfe-file
               OPEN INPUT mdfe-file
           END-IF
           IF ws-file-status = "00" THEN
               PERFORM UNTIL 1 = 2
                   READ mdfe-file INTO mdfe-reg
                       AT END EXIT PERFORM
                   END-READ
                   IF md-id > ws-prox-id THEN
                       MOVE md-id TO ws-prox-id
                   END-IF
               END-PERFORM
               CLOSE mdfe-file
           END-IF
           ADD 1 TO ws-prox-id

           MOVE ws-prox-id TO md-id
           MOVE ws-numero TO md-numero
           MOVE ws-serie TO md-serie
           MOVE ws-chave TO md-chave
           MOVE ws-cnpj-emit TO md-cnpj-emit
           MOVE ws-nome-emit TO md-nome-emit
           MOVE ws-modal TO md-modal
           MOVE ws-uf-ini TO md-uf-ini
           MOVE ws-uf-fim TO md-uf-fim
           MOVE ws-mun-ini TO md-mun-ini
           MOVE ws-mun-fim TO md-mun-fim
           MOVE ws-valor-carga TO md-valor-carga
           MOVE ws-qtd-docs TO md-qtd-docs
           MOVE ws-placa-veic TO md-placa-veic
           MOVE ws-motorista TO md-motorista
           MOVE ws-cpf-motorista TO md-cpf-motorista
           MOVE ws-status TO md-status
           MOVE ws-proc TO md-proc
           MOVE ws-data-emissao TO md-data-emissao

           OPEN EXTEND mdfe-file
           WRITE mdfe-reg
           CLOSE mdfe-file

           MOVE ws-prox-id TO ws-id-ed
           DISPLAY FUNCTION TRIM(ws-id-ed)
           .

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           ACCEPT ws-numero FROM ENVIRONMENT "NUMERO"
           ACCEPT ws-serie FROM ENVIRONMENT "SERIE"
           ACCEPT ws-chave FROM ENVIRONMENT "CHAVE"
           ACCEPT ws-nome-emit FROM ENVIRONMENT "NOME_EMIT"
           ACCEPT ws-modal FROM ENVIRONMENT "MODAL"
           ACCEPT ws-uf-ini FROM ENVIRONMENT "UF_INI"
           ACCEPT ws-uf-fim FROM ENVIRONMENT "UF_FIM"
           ACCEPT ws-mun-ini FROM ENVIRONMENT "MUN_INI"
           ACCEPT ws-mun-fim FROM ENVIRONMENT "MUN_FIM"
           ACCEPT ws-valor-str FROM ENVIRONMENT "VALOR_CARGA"
           ACCEPT ws-qtd-str FROM ENVIRONMENT "QTD_DOCS"
           ACCEPT ws-placa-veic FROM ENVIRONMENT "PLACA_VEIC"
           ACCEPT ws-motorista FROM ENVIRONMENT "MOTORISTA"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           ACCEPT ws-data-emissao FROM ENVIRONMENT "DATA_EMISSAO"

           IF ws-id-in = SPACES THEN
               DISPLAY "ERRO: ID obrigatorio"
               EXIT PARAGRAPH
           END-IF
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           IF ws-valor-str NOT = SPACES THEN
               COMPUTE ws-valor-carga = FUNCTION NUMVAL(ws-valor-str)
           END-IF
           IF ws-qtd-str NOT = SPACES THEN
               COMPUTE ws-qtd-docs = FUNCTION NUMVAL(ws-qtd-str)
           END-IF

           MOVE "N" TO ws-encontrou
           OPEN INPUT mdfe-file
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ mdfe-file INTO mdfe-reg
                   AT END EXIT PERFORM
               END-READ
               IF md-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-nome-emit NOT = SPACES THEN MOVE ws-nome-emit TO md-nome-emit END-IF
                   IF ws-numero NOT = 0 THEN MOVE ws-numero TO md-numero END-IF
                   IF ws-serie NOT = 0 THEN MOVE ws-serie TO md-serie END-IF
                   IF ws-chave NOT = SPACES THEN MOVE ws-chave TO md-chave END-IF
                   IF ws-uf-ini NOT = SPACES THEN MOVE ws-uf-ini TO md-uf-ini END-IF
                   IF ws-uf-fim NOT = SPACES THEN MOVE ws-uf-fim TO md-uf-fim END-IF
                   IF ws-placa-veic NOT = SPACES THEN MOVE ws-placa-veic TO md-placa-veic END-IF
                   IF ws-motorista NOT = SPACES THEN MOVE ws-motorista TO md-motorista END-IF
                   IF ws-status NOT = SPACES THEN MOVE ws-status TO md-status END-IF
                   IF ws-valor-carga NOT = 0 THEN MOVE ws-valor-carga TO md-valor-carga END-IF
                   IF ws-qtd-docs NOT = 0 THEN MOVE ws-qtd-docs TO md-qtd-docs END-IF
               END-IF
               WRITE temp-reg FROM mdfe-reg
           END-PERFORM
           CLOSE mdfe-file temp-file
           IF ws-encontrou = "S" THEN
               CALL "system" USING "mv dados/mdfe.tmp dados/mdfe.dat"
               DISPLAY "OK"
           ELSE
               CALL "system" USING "rm -f dados/mdfe.tmp"
               DISPLAY "ERRO: registro nao encontrado"
           END-IF
           .

       excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           IF ws-id-in = SPACES THEN
               DISPLAY "ERRO: ID obrigatorio"
               EXIT PARAGRAPH
           END-IF
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)

           MOVE "N" TO ws-encontrou
           OPEN INPUT mdfe-file
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ mdfe-file INTO mdfe-reg
                   AT END EXIT PERFORM
               END-READ
               IF md-id NOT = ws-id THEN
                   WRITE temp-reg FROM mdfe-reg
               ELSE
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE mdfe-file temp-file
           IF ws-encontrou = "S" THEN
               CALL "system" USING "mv dados/mdfe.tmp dados/mdfe.dat"
               DISPLAY "OK"
           ELSE
               CALL "system" USING "rm -f dados/mdfe.tmp"
               DISPLAY "ERRO: registro nao encontrado"
           END-IF
           .

       listar.
           DISPLAY '{"mdfe":['
           MOVE 0 TO ws-id
           OPEN INPUT mdfe-file
           IF ws-file-status NOT = "00" THEN
               DISPLAY '],"total":0}'
               CLOSE mdfe-file
               EXIT PARAGRAPH
           END-IF
           PERFORM UNTIL 1 = 2
               READ mdfe-file INTO mdfe-reg
                   AT END EXIT PERFORM
               END-READ
                IF ws-id > 0 THEN DISPLAY "," END-IF
                MOVE md-id TO ws-id-ed
                 MOVE md-valor-carga TO ws-valor-ed
                 MOVE md-numero TO ws-numero-ed
                 MOVE md-serie TO ws-serie-ed
                STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                       ',"numero":' FUNCTION TRIM(ws-numero-ed)
                       ',"serie":' FUNCTION TRIM(ws-serie-ed)
                      ',"chave":"' FUNCTION TRIM(md-chave) '"'
                      ',"cnpj_emit":"' FUNCTION TRIM(md-cnpj-emit) '"'
                      ',"nome_emit":"' FUNCTION TRIM(md-nome-emit) '"'
                      ',"modal":"' FUNCTION TRIM(md-modal) '"'
                      ',"uf_ini":"' FUNCTION TRIM(md-uf-ini) '"'
                      ',"uf_fim":"' FUNCTION TRIM(md-uf-fim) '"'
                      ',"mun_ini":"' FUNCTION TRIM(md-mun-ini) '"'
                      ',"mun_fim":"' FUNCTION TRIM(md-mun-fim) '"'
                      ',"valor_carga":' FUNCTION TRIM(ws-valor-ed)
                      ',"placa_veic":"' FUNCTION TRIM(md-placa-veic) '"'
                      ',"motorista":"' FUNCTION TRIM(md-motorista) '"'
                      ',"status":"' FUNCTION TRIM(md-status) '"'
                      ',"data_emissao":"' FUNCTION TRIM(md-data-emissao) '"'
                      '}' INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
               ADD 1 TO ws-id
           END-PERFORM
           CLOSE mdfe-file
           MOVE ws-id TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           .

       buscar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           IF ws-id-in NOT = SPACES THEN
               COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           END-IF
           ACCEPT ws-chave FROM ENVIRONMENT "CHAVE"

           MOVE "N" TO ws-encontrou
           OPEN INPUT mdfe-file
           IF ws-file-status NOT = "00" THEN
               DISPLAY "{}"
               CLOSE mdfe-file
               EXIT PARAGRAPH
           END-IF
           PERFORM UNTIL 1 = 2
               READ mdfe-file INTO mdfe-reg
                   AT END EXIT PERFORM
               END-READ
               IF (ws-id-in NOT = SPACES AND md-id = ws-id)
                  OR (ws-chave NOT = SPACES AND md-chave = ws-chave) THEN
                   MOVE "S" TO ws-encontrou
                    MOVE md-valor-carga TO ws-valor-ed
                    MOVE md-numero TO ws-numero-ed
                    MOVE md-serie TO ws-serie-ed
                    STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                           ',"numero":' FUNCTION TRIM(ws-numero-ed)
                          ',"chave":"' FUNCTION TRIM(md-chave) '"'
                          ',"nome_emit":"' FUNCTION TRIM(md-nome-emit) '"'
                          ',"placa_veic":"' FUNCTION TRIM(md-placa-veic) '"'
                          ',"status":"' FUNCTION TRIM(md-status) '"'
                          '}' INTO ws-json-linha
                   DISPLAY FUNCTION TRIM(ws-json-linha)
                   EXIT PERFORM
               END-IF
           END-PERFORM
           CLOSE mdfe-file
           IF ws-encontrou = "N" THEN DISPLAY "{}" END-IF
           .
