       >>SOURCE FORMAT IS FREE
       *> gerir_itens_ent.cbl — itens por parada da DO (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirItensEnt.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT it-file ASSIGN TO "dados/entregas_itens.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/entregas_itens.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD it-file.
       01 it-reg.
           05 it-entrega-id      PIC X(24).
           05 it-parada          PIC 9(2).
           05 it-seq             PIC 9(3).
           05 it-prod-id         PIC X(10).
           05 it-produto         PIC X(40).
           05 it-qtd             PIC S9(9)V99 COMP-3.

       FD temp-file.
       01 temp-reg.
           05 tt-entrega-id      PIC X(24).
           05 tt-parada          PIC 9(2).
           05 tt-seq             PIC 9(3).
           05 tt-prod-id         PIC X(10).
           05 tt-produto         PIC X(40).
           05 tt-qtd             PIC S9(9)V99 COMP-3.

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-eid             PIC X(24).
       01 ws-parada          PIC 9(2).
       01 ws-seq             PIC 9(3).
       01 ws-parada-in       PIC X(5).
       01 ws-seq-in          PIC X(5).
       01 ws-prod-id         PIC X(10).
       01 ws-produto         PIC X(40).
       01 ws-qtd-in          PIC X(20).
       01 ws-qtd             PIC S9(9)V99 COMP-3.
       01 ws-parada-ed       PIC Z9.
       01 ws-seq-ed          PIC ZZ9.
       01 ws-qtd-ed          PIC -(8)9.99.
       01 ws-json            PIC X(300).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF
           EVALUATE ws-acao
               WHEN "incluir"    PERFORM incluir
               WHEN "limpar"     PERFORM limpar
               WHEN "listar"     PERFORM listar
               WHEN "listar-do"  PERFORM listar-do
               WHEN OTHER        DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       incluir.
           ACCEPT ws-eid FROM ENVIRONMENT "ENTREGA_ID"
           ACCEPT ws-parada-in FROM ENVIRONMENT "PARADA"
           ACCEPT ws-seq-in FROM ENVIRONMENT "SEQ"
           ACCEPT ws-prod-id FROM ENVIRONMENT "PRODUTO_ID"
           ACCEPT ws-produto FROM ENVIRONMENT "PRODUTO"
           ACCEPT ws-qtd-in FROM ENVIRONMENT "QTD"
           COMPUTE ws-parada = FUNCTION NUMVAL(ws-parada-in)
           COMPUTE ws-seq = FUNCTION NUMVAL(ws-seq-in)
           COMPUTE ws-qtd = FUNCTION NUMVAL(ws-qtd-in)
           IF ws-eid = SPACES THEN
               DISPLAY "ERRO: entrega_id" STOP RUN END-IF
           OPEN INPUT it-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT it-file CLOSE it-file
           ELSE CLOSE it-file END-IF
           OPEN EXTEND it-file
           MOVE ws-eid TO it-entrega-id
           MOVE ws-parada TO it-parada
           MOVE ws-seq TO it-seq
           MOVE ws-prod-id TO it-prod-id
           MOVE ws-produto TO it-produto
           MOVE ws-qtd TO it-qtd
           WRITE it-reg
           CLOSE it-file
           DISPLAY "OK".

       limpar.
           ACCEPT ws-eid FROM ENVIRONMENT "ENTREGA_ID"
           OPEN INPUT it-file
           IF ws-fs = "35" THEN DISPLAY "OK" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ it-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(it-entrega-id)) NOT =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-eid)) THEN
                   MOVE it-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE it-file CLOSE temp-file
           CALL "system" USING
               "mv dados/entregas_itens.tmp dados/entregas_itens.dat"
           END-CALL
           DISPLAY "OK".

       listar.
           OPEN INPUT it-file
           IF ws-fs = "35" THEN
               DISPLAY '{"itens":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"itens":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ it-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE it-file.

       listar-do.
           ACCEPT ws-eid FROM ENVIRONMENT "ENTREGA_ID"
           OPEN INPUT it-file
           IF ws-fs = "35" THEN
               DISPLAY '{"itens":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"itens":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ it-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(it-entrega-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-eid)) THEN
                   ADD 1 TO ws-total
                   IF ws-first = "S" THEN MOVE "N" TO ws-first
                   ELSE DISPLAY "," END-IF
                   PERFORM emit-json
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE it-file.

       emit-json.
           MOVE it-parada TO ws-parada-ed
           MOVE it-seq TO ws-seq-ed
           MOVE it-qtd TO ws-qtd-ed
           MOVE SPACES TO ws-json
           STRING '{"entrega_id":"' FUNCTION TRIM(it-entrega-id) '"'
                  ',"parada":' FUNCTION TRIM(ws-parada-ed)
                  ',"seq":' FUNCTION TRIM(ws-seq-ed)
                  ',"produto_id":"' FUNCTION TRIM(it-prod-id) '"'
                  ',"produto":"' FUNCTION TRIM(it-produto) '"'
                  ',"qtd":' FUNCTION TRIM(ws-qtd-ed) '}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
