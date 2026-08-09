       >>SOURCE FORMAT IS FREE
       *> gerir_acordos_compra.cbl — acordos de compra / cotações (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirAcordosCompra.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ac-file ASSIGN TO "dados/acordos_compra.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/acordos_compra.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD ac-file.
       01 ac-reg.
           05 ac-id              PIC 9(6).
           05 ac-numero          PIC X(12).
           05 ac-tipo            PIC X(12).
           05 ac-status          PIC X(12).
           05 ac-data            PIC X(10).
           05 ac-fechamento      PIC X(10).
           05 ac-descricao       PIC X(60).
           05 ac-comprador       PIC X(30).
           05 ac-terms           PIC X(20).
           05 ac-forma-pg        PIC X(20).
           05 ac-total           PIC S9(11)V99 COMP-3.
           05 ac-pedido-id       PIC X(10).
           05 ac-pedido-num      PIC X(12).
           05 ac-notas           PIC X(80).

       FD temp-file.
       01 temp-reg.
           05 ta-id              PIC 9(6).
           05 ta-numero          PIC X(12).
           05 ta-tipo            PIC X(12).
           05 ta-status          PIC X(12).
           05 ta-data            PIC X(10).
           05 ta-fechamento      PIC X(10).
           05 ta-descricao       PIC X(60).
           05 ta-comprador       PIC X(30).
           05 ta-terms           PIC X(20).
           05 ta-forma-pg        PIC X(20).
           05 ta-total           PIC S9(11)V99 COMP-3.
           05 ta-pedido-id       PIC X(10).
           05 ta-pedido-num      PIC X(12).
           05 ta-notas           PIC X(80).

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
       01 ws-total-val       PIC S9(11)V99 COMP-3.
       01 ws-total-ed2       PIC -(10)9.99.
       01 ws-json            PIC X(1800).
       01 ws-numero          PIC X(12).
       01 ws-tipo            PIC X(12).
       01 ws-status          PIC X(12).
       01 ws-data            PIC X(10).
       01 ws-fechamento      PIC X(10).
       01 ws-descricao       PIC X(60).
       01 ws-comprador       PIC X(30).
       01 ws-terms           PIC X(20).
       01 ws-forma-pg        PIC X(20).
       01 ws-pedido-id       PIC X(10).
       01 ws-pedido-num      PIC X(12).
       01 ws-notas           PIC X(80).
       01 ws-total-in        PIC X(20).
       01 ws-prox-ed         PIC ZZZZZ9.

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF
           EVALUATE ws-acao
               WHEN "incluir"      PERFORM incluir
               WHEN "alterar"      PERFORM alterar
               WHEN "excluir"      PERFORM excluir
               WHEN "listar"       PERFORM listar
               WHEN "buscar"       PERFORM buscar
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
               IF FUNCTION TRIM(ws-tipo) = "tender" THEN
                   STRING "CT" ws-id-z DELIMITED BY SIZE INTO ws-numero
               ELSE
                   STRING "AC" ws-id-z DELIMITED BY SIZE INTO ws-numero
               END-IF
           END-IF
           OPEN INPUT ac-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT ac-file CLOSE ac-file
           ELSE
               CLOSE ac-file
           END-IF
           OPEN EXTEND ac-file
           PERFORM move-ws-to-ac
           WRITE ac-reg
           CLOSE ac-file
           MOVE ws-id TO ws-id-ed
           DISPLAY FUNCTION TRIM(ws-id-ed).

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           IF ws-id = 0 THEN
               DISPLAY "ERRO: id obrigatorio" STOP RUN END-IF
           PERFORM accept-fields
           OPEN INPUT ac-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ac-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF ac-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   PERFORM move-ws-to-ac
                   MOVE ac-reg TO temp-reg
                   WRITE temp-reg
               ELSE
                   MOVE ac-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE ac-file CLOSE temp-file
           CALL "system" USING
               "mv dados/acordos_compra.tmp dados/acordos_compra.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: acordo nao encontrado".

       excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           OPEN INPUT ac-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ac-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF ac-id NOT = ws-id THEN
                   MOVE ac-reg TO temp-reg
                   WRITE temp-reg
               ELSE
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE ac-file CLOSE temp-file
           CALL "system" USING
               "mv dados/acordos_compra.tmp dados/acordos_compra.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: acordo nao encontrado".

       listar.
           OPEN INPUT ac-file
           IF ws-fs = "35" THEN
               DISPLAY '{"acordos":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"acordos":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ ac-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE ac-file.

       buscar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           OPEN INPUT ac-file
           IF ws-fs = "35" THEN
               DISPLAY '{"status":"erro"}' STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ac-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF ac-id = ws-id THEN
                   PERFORM emit-json
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE ac-file
           IF ws-encontrou = "N" THEN DISPLAY '{"status":"erro"}'.

       proximo-id.
           OPEN INPUT ac-file
           IF ws-fs = "35" THEN
               MOVE 0 TO ws-prox
               CLOSE ac-file
               ADD 1 TO ws-prox
               MOVE ws-prox TO ws-prox-ed
               DISPLAY FUNCTION TRIM(ws-prox-ed)
               STOP RUN
           END-IF
           MOVE 0 TO ws-prox
           PERFORM UNTIL 1 = 2
               READ ac-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF ac-id > ws-prox THEN MOVE ac-id TO ws-prox END-IF
           END-PERFORM
           CLOSE ac-file
           ADD 1 TO ws-prox
           MOVE ws-prox TO ws-prox-ed
           DISPLAY FUNCTION TRIM(ws-prox-ed).

       move-ws-to-ac.
           MOVE ws-id           TO ac-id
           MOVE ws-numero       TO ac-numero
           MOVE ws-tipo         TO ac-tipo
           MOVE ws-status       TO ac-status
           MOVE ws-data         TO ac-data
           MOVE ws-fechamento   TO ac-fechamento
           MOVE ws-descricao    TO ac-descricao
           MOVE ws-comprador    TO ac-comprador
           MOVE ws-terms        TO ac-terms
           MOVE ws-forma-pg     TO ac-forma-pg
           MOVE ws-total-val     TO ac-total
           MOVE ws-pedido-id     TO ac-pedido-id
           MOVE ws-pedido-num    TO ac-pedido-num
           MOVE ws-notas         TO ac-notas.

       accept-fields.
           ACCEPT ws-numero FROM ENVIRONMENT "NUMERO"
           ACCEPT ws-tipo FROM ENVIRONMENT "TIPO"
           IF ws-tipo = SPACES THEN MOVE "tender" TO ws-tipo END-IF
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           IF ws-status = SPACES THEN MOVE "rascunho" TO ws-status END-IF
           ACCEPT ws-data FROM ENVIRONMENT "DATA"
           ACCEPT ws-fechamento FROM ENVIRONMENT "FECHAMENTO"
           ACCEPT ws-descricao FROM ENVIRONMENT "DESCRICAO"
           ACCEPT ws-comprador FROM ENVIRONMENT "COMPRADOR"
           ACCEPT ws-terms FROM ENVIRONMENT "TERMS"
           ACCEPT ws-forma-pg FROM ENVIRONMENT "FORMA_PG"
           ACCEPT ws-total-in FROM ENVIRONMENT "TOTAL"
           IF ws-total-in NOT = SPACES THEN
               COMPUTE ws-total-val = FUNCTION NUMVAL(ws-total-in)
           ELSE
               MOVE 0 TO ws-total-val
           END-IF
           ACCEPT ws-pedido-id FROM ENVIRONMENT "PEDIDO_ID"
           ACCEPT ws-pedido-num FROM ENVIRONMENT "PEDIDO_NUM"
           ACCEPT ws-notas FROM ENVIRONMENT "NOTAS".

       emit-json.
           MOVE ac-id TO ws-id-ed
           MOVE ac-total TO ws-total-ed2
           MOVE SPACES TO ws-json
           STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                  ',"numero":"' FUNCTION TRIM(ac-numero) '"'
                  ',"tipo":"' FUNCTION TRIM(ac-tipo) '"'
                  ',"status":"' FUNCTION TRIM(ac-status) '"'
                  ',"data":"' FUNCTION TRIM(ac-data) '"'
                  ',"fechamento":"' FUNCTION TRIM(ac-fechamento) '"'
                  ',"descricao":"' FUNCTION TRIM(ac-descricao) '"'
                  ',"comprador":"' FUNCTION TRIM(ac-comprador) '"'
                  ',"payment_terms":"' FUNCTION TRIM(ac-terms) '"'
                  ',"forma_pg":"' FUNCTION TRIM(ac-forma-pg) '"'
                  ',"total":' FUNCTION TRIM(ws-total-ed2)
                  ',"pedido_id":"' FUNCTION TRIM(ac-pedido-id) '"'
                  ',"pedido_num":"' FUNCTION TRIM(ac-pedido-num) '"'
                  ',"notas":"' FUNCTION TRIM(ac-notas) '"}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
