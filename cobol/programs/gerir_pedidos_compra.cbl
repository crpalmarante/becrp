       >>SOURCE FORMAT IS FREE
       *> gerir_pedidos_compra.cbl — cabeçalho pedido de compra (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirPedidosCompra.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ped-file ASSIGN TO "dados/pedidos_compra.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/pedidos_compra.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD ped-file.
       01 ped-reg.
           05 pd-id              PIC 9(6).
           05 pd-numero          PIC X(12).
           05 pd-status          PIC X(12).
           05 pd-data            PIC X(10).
           05 pd-previsao        PIC X(10).
           05 pd-fornecedor-id   PIC X(12).
           05 pd-razao           PIC X(60).
           05 pd-cnpj            PIC X(18).
           05 pd-ie              PIC X(20).
           05 pd-cidade          PIC X(30).
           05 pd-uf              PIC X(2).
           05 pd-end-ent         PIC X(80).
           05 pd-comprador       PIC X(30).
           05 pd-terms           PIC X(20).
           05 pd-forma-pg        PIC X(20).
           05 pd-total           PIC S9(11)V99 COMP-3.
           05 pd-receb-id        PIC X(10).
           05 pd-receb-num       PIC X(12).
           05 pd-nfe-chave       PIC X(44).
           05 pd-smart-rec       PIC 9(3).
           05 pd-notas           PIC X(80).

       FD temp-file.
       01 temp-reg.
           05 td-id              PIC 9(6).
           05 td-numero          PIC X(12).
           05 td-status          PIC X(12).
           05 td-data            PIC X(10).
           05 td-previsao        PIC X(10).
           05 td-fornecedor-id   PIC X(12).
           05 td-razao           PIC X(60).
           05 td-cnpj            PIC X(18).
           05 td-ie              PIC X(20).
           05 td-cidade          PIC X(30).
           05 td-uf              PIC X(2).
           05 td-end-ent         PIC X(80).
           05 td-comprador       PIC X(30).
           05 td-terms           PIC X(20).
           05 td-forma-pg        PIC X(20).
           05 td-total           PIC S9(11)V99 COMP-3.
           05 td-receb-id        PIC X(10).
           05 td-receb-num       PIC X(12).
           05 td-nfe-chave       PIC X(44).
           05 td-smart-rec       PIC 9(3).
           05 td-notas           PIC X(80).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-encontrou       PIC X(1).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-id              PIC 9(6).
       01 ws-id-in           PIC X(10).
       01 ws-prox            PIC 9(6).
       01 ws-id-ed           PIC ZZZZZ9.
       01 ws-id-z            PIC 9(5).
       01 ws-smart-ed        PIC ZZ9.
       01 ws-total-val       PIC S9(11)V99 COMP-3.
       01 ws-total-ed2       PIC -(10)9.99.
       01 ws-json            PIC X(2000).
       01 ws-numero          PIC X(12).
       01 ws-status          PIC X(12).
       01 ws-data            PIC X(10).
       01 ws-previsao        PIC X(10).
       01 ws-fornecedor-id   PIC X(12).
       01 ws-razao           PIC X(60).
       01 ws-cnpj            PIC X(18).
       01 ws-ie              PIC X(20).
       01 ws-cidade          PIC X(30).
       01 ws-uf              PIC X(2).
       01 ws-end-ent         PIC X(80).
       01 ws-comprador       PIC X(30).
       01 ws-terms           PIC X(20).
       01 ws-forma-pg        PIC X(20).
       01 ws-receb-id        PIC X(10).
       01 ws-receb-num       PIC X(12).
       01 ws-nfe-chave       PIC X(44).
       01 ws-smart-rec       PIC 9(3).
       01 ws-notas           PIC X(80).
       01 ws-total-in        PIC X(20).
       01 ws-smart-in        PIC X(5).
       01 ws-prox-ed         PIC ZZZZZ9.
       01 ws-idx             PIC 9(6).
       01 ws-i               PIC 9(3).
       01 ws-cmd             PIC X(80).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF
           EVALUATE ws-acao
               WHEN "incluir"      PERFORM incluir
               WHEN "alterar"      PERFORM alterar
               WHEN "excluir"      PERFORM excluir
               WHEN "listar"       PERFORM listar
               WHEN "buscar"       PERFORM buscar
               WHEN "buscar-cnpj"  PERFORM buscar-cnpj
               WHEN "proximo-id"   PERFORM proximo-id
               WHEN OTHER          DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       incluir.
           PERFORM accept-fields
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           IF ws-id-in = SPACES THEN
               PERFORM proximo-id
               MOVE ws-prox TO ws-id
           ELSE
               COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           END-IF
           IF ws-numero = SPACES THEN
               MOVE ws-id TO ws-id-z
               STRING "PC" ws-id-z DELIMITED BY SIZE INTO ws-numero
           END-IF
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT ped-file CLOSE ped-file
           ELSE
               CLOSE ped-file
           END-IF
           OPEN EXTEND ped-file
           PERFORM move-ws-to-ped
           WRITE ped-reg
           CLOSE ped-file
           MOVE ws-id TO ws-id-ed
           DISPLAY FUNCTION TRIM(ws-id-ed).

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           IF ws-id = 0 THEN
               DISPLAY "ERRO: id obrigatorio" STOP RUN END-IF
           PERFORM accept-fields
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ped-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pd-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   PERFORM move-ws-to-ped
                   MOVE ped-reg TO temp-reg
                   WRITE temp-reg
               ELSE
                   MOVE ped-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE ped-file CLOSE temp-file
           CALL "system" USING
               "mv dados/pedidos_compra.tmp dados/pedidos_compra.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: pedido nao encontrado".

       excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ped-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pd-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
               ELSE
                   MOVE ped-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE ped-file CLOSE temp-file
           CALL "system" USING
               "mv dados/pedidos_compra.tmp dados/pedidos_compra.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: pedido nao encontrado".

       listar.
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               DISPLAY '{"pedidos":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"pedidos":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ ped-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE ped-file.

       buscar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               DISPLAY '{"status":"erro"}' STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ped-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pd-id = ws-id THEN
                   PERFORM emit-json
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE ped-file
           IF ws-encontrou = "N" THEN DISPLAY '{"status":"erro"}'.

       buscar-cnpj.
           ACCEPT ws-cnpj FROM ENVIRONMENT "CNPJ"
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               DISPLAY '{"pedidos":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"pedidos":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ ped-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pd-cnpj = ws-cnpj THEN
                   ADD 1 TO ws-total
                   IF ws-first = "S" THEN MOVE "N" TO ws-first
                   ELSE DISPLAY "," END-IF
                   PERFORM emit-json
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE ped-file.

       proximo-id.
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               MOVE 0 TO ws-prox
               CLOSE ped-file
               ADD 1 TO ws-prox
               MOVE ws-prox TO ws-prox-ed
               DISPLAY FUNCTION TRIM(ws-prox-ed)
               STOP RUN
           END-IF
           MOVE 0 TO ws-prox
           PERFORM UNTIL 1 = 2
               READ ped-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pd-id > ws-prox THEN MOVE pd-id TO ws-prox END-IF
           END-PERFORM
           CLOSE ped-file
           ADD 1 TO ws-prox
           MOVE ws-prox TO ws-prox-ed
           DISPLAY FUNCTION TRIM(ws-prox-ed).

       move-ws-to-ped.
           MOVE ws-id           TO pd-id
           MOVE ws-numero       TO pd-numero
           MOVE ws-status       TO pd-status
           MOVE ws-data         TO pd-data
           MOVE ws-previsao     TO pd-previsao
           MOVE ws-fornecedor-id TO pd-fornecedor-id
           MOVE ws-razao         TO pd-razao
           MOVE ws-cnpj          TO pd-cnpj
           MOVE ws-ie            TO pd-ie
           MOVE ws-cidade        TO pd-cidade
           MOVE ws-uf            TO pd-uf
           MOVE ws-end-ent       TO pd-end-ent
           MOVE ws-comprador    TO pd-comprador
           MOVE ws-terms         TO pd-terms
           MOVE ws-forma-pg      TO pd-forma-pg
           MOVE ws-total-val     TO pd-total
           MOVE ws-receb-id      TO pd-receb-id
           MOVE ws-receb-num     TO pd-receb-num
           MOVE ws-nfe-chave     TO pd-nfe-chave
           MOVE ws-smart-rec     TO pd-smart-rec
           MOVE ws-notas         TO pd-notas.

       accept-fields.
           ACCEPT ws-numero FROM ENVIRONMENT "NUMERO"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           ACCEPT ws-data FROM ENVIRONMENT "DATA"
           ACCEPT ws-previsao FROM ENVIRONMENT "PREVISAO"
           ACCEPT ws-fornecedor-id FROM ENVIRONMENT "FORNECEDOR_ID"
           ACCEPT ws-razao FROM ENVIRONMENT "RAZAO"
           ACCEPT ws-cnpj FROM ENVIRONMENT "CNPJ"
           ACCEPT ws-ie FROM ENVIRONMENT "IE"
           ACCEPT ws-cidade FROM ENVIRONMENT "CIDADE"
           ACCEPT ws-uf FROM ENVIRONMENT "UF"
           ACCEPT ws-end-ent FROM ENVIRONMENT "END_ENT"
           ACCEPT ws-comprador FROM ENVIRONMENT "COMPRADOR"
           ACCEPT ws-terms FROM ENVIRONMENT "TERMS"
           ACCEPT ws-forma-pg FROM ENVIRONMENT "FORMA_PG"
           ACCEPT ws-total-in FROM ENVIRONMENT "TOTAL"
           IF ws-total-in NOT = SPACES THEN
               COMPUTE ws-total-val = FUNCTION NUMVAL(ws-total-in)
           ELSE
               MOVE 0 TO ws-total-val
           END-IF
           ACCEPT ws-receb-id FROM ENVIRONMENT "RECEB_ID"
           ACCEPT ws-receb-num FROM ENVIRONMENT "RECEB_NUM"
           ACCEPT ws-nfe-chave FROM ENVIRONMENT "NFE_CHAVE"
           ACCEPT ws-smart-in FROM ENVIRONMENT "SMART_REC"
           IF ws-smart-in NOT = SPACES THEN
               COMPUTE ws-smart-rec = FUNCTION NUMVAL(ws-smart-in)
           ELSE
               MOVE 0 TO ws-smart-rec
           END-IF
           ACCEPT ws-notas FROM ENVIRONMENT "NOTAS".

       emit-json.
           MOVE pd-id TO ws-id-ed
           MOVE pd-total TO ws-total-ed2
           MOVE pd-smart-rec TO ws-smart-ed
           MOVE SPACES TO ws-json
           STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                  ',"numero":"' FUNCTION TRIM(pd-numero) '"'
                  ',"status":"' FUNCTION TRIM(pd-status) '"'
                  ',"data":"' FUNCTION TRIM(pd-data) '"'
                  ',"previsao":"' FUNCTION TRIM(pd-previsao) '"'
                  ',"fornecedor_id":"' FUNCTION TRIM(pd-fornecedor-id) '"'
                  ',"razao_social":"' FUNCTION TRIM(pd-razao) '"'
                  ',"cnpj":"' FUNCTION TRIM(pd-cnpj) '"'
                  ',"ie":"' FUNCTION TRIM(pd-ie) '"'
                  ',"cidade":"' FUNCTION TRIM(pd-cidade) '"'
                  ',"uf":"' FUNCTION TRIM(pd-uf) '"'
                  ',"endereco_entrega":"' FUNCTION TRIM(pd-end-ent) '"'
                  ',"comprador":"' FUNCTION TRIM(pd-comprador) '"'
                  ',"payment_terms":"' FUNCTION TRIM(pd-terms) '"'
                  ',"forma_pg":"' FUNCTION TRIM(pd-forma-pg) '"'
                  ',"total":' FUNCTION TRIM(ws-total-ed2)
                  ',"recebimento_id":"' FUNCTION TRIM(pd-receb-id) '"'
                  ',"recebimento_num":"' FUNCTION TRIM(pd-receb-num) '"'
                  ',"nfe_chave":"' FUNCTION TRIM(pd-nfe-chave) '"'
                  ',"smart_recebimentos":' FUNCTION TRIM(ws-smart-ed)
                  ',"notas":"' FUNCTION TRIM(pd-notas) '"}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
