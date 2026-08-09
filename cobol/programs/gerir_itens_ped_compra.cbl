       >>SOURCE FORMAT IS FREE
       *> gerir_itens_ped_compra.cbl — itens do pedido de compra (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirItensPedCompra.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT it-file ASSIGN TO "dados/itens_pedido_compra.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/itens_pedido_compra.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD it-file.
       01 it-reg.
           05 it-pedido-id       PIC 9(6).
           05 it-seq             PIC 9(3).
           05 it-prod-id         PIC X(10).
           05 it-produto         PIC X(40).
           05 it-qtd             PIC S9(9)V99 COMP-3.
           05 it-uom             PIC X(4).
           05 it-preco           PIC S9(9)V99 COMP-3.
           05 it-desconto        PIC S9(5)V99 COMP-3.
           05 it-imposto         PIC S9(5)V99 COMP-3.

       FD temp-file.
       01 temp-reg.
           05 tt-pedido-id       PIC 9(6).
           05 tt-seq             PIC 9(3).
           05 tt-prod-id         PIC X(10).
           05 tt-produto         PIC X(40).
           05 tt-qtd             PIC S9(9)V99 COMP-3.
           05 tt-uom             PIC X(4).
           05 tt-preco           PIC S9(9)V99 COMP-3.
           05 tt-desconto        PIC S9(5)V99 COMP-3.
           05 tt-imposto         PIC S9(5)V99 COMP-3.

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-pid             PIC 9(6).
       01 ws-pid-in          PIC X(10).
       01 ws-seq             PIC 9(3).
       01 ws-seq-in          PIC X(5).
       01 ws-prod-id         PIC X(10).
       01 ws-produto         PIC X(40).
       01 ws-uom             PIC X(4).
       01 ws-qtd-in          PIC X(20).
       01 ws-preco-in        PIC X(20).
       01 ws-desc-in         PIC X(20).
       01 ws-imp-in          PIC X(20).
       01 ws-qtd             PIC S9(9)V99 COMP-3.
       01 ws-preco           PIC S9(9)V99 COMP-3.
       01 ws-desc            PIC S9(5)V99 COMP-3.
       01 ws-imp             PIC S9(5)V99 COMP-3.
       01 ws-pid-ed          PIC ZZZZZ9.
       01 ws-seq-ed          PIC ZZ9.
       01 ws-qtd-ed          PIC -(8)9.99.
       01 ws-preco-ed        PIC -(8)9.99.
       01 ws-desc-ed         PIC -(4)9.99.
       01 ws-imp-ed          PIC -(4)9.99.
       01 ws-json            PIC X(400).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF
           EVALUATE ws-acao
               WHEN "incluir"      PERFORM incluir
               WHEN "limpar"       PERFORM limpar
               WHEN "listar"       PERFORM listar
               WHEN "listar-ped"   PERFORM listar-ped
               WHEN OTHER          DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       incluir.
           ACCEPT ws-pid-in FROM ENVIRONMENT "PEDIDO_ID"
           COMPUTE ws-pid = FUNCTION NUMVAL(ws-pid-in)
           ACCEPT ws-seq-in FROM ENVIRONMENT "SEQ"
           IF ws-seq-in NOT = SPACES THEN
               COMPUTE ws-seq = FUNCTION NUMVAL(ws-seq-in)
           ELSE
               PERFORM find-next-seq
           END-IF
           ACCEPT ws-prod-id FROM ENVIRONMENT "PROD_ID"
           ACCEPT ws-produto FROM ENVIRONMENT "PRODUTO"
           ACCEPT ws-uom FROM ENVIRONMENT "UOM"
           ACCEPT ws-qtd-in FROM ENVIRONMENT "QTD"
           IF ws-qtd-in NOT = SPACES THEN
               COMPUTE ws-qtd = FUNCTION NUMVAL(ws-qtd-in)
           ELSE
               MOVE 0 TO ws-qtd
           END-IF
           ACCEPT ws-preco-in FROM ENVIRONMENT "PRECO"
           IF ws-preco-in NOT = SPACES THEN
               COMPUTE ws-preco = FUNCTION NUMVAL(ws-preco-in)
           ELSE
               MOVE 0 TO ws-preco
           END-IF
           ACCEPT ws-desc-in FROM ENVIRONMENT "DESCONTO"
           IF ws-desc-in NOT = SPACES THEN
               COMPUTE ws-desc = FUNCTION NUMVAL(ws-desc-in)
           ELSE
               MOVE 0 TO ws-desc
           END-IF
           ACCEPT ws-imp-in FROM ENVIRONMENT "IMPOSTO"
           IF ws-imp-in NOT = SPACES THEN
               COMPUTE ws-imp = FUNCTION NUMVAL(ws-imp-in)
           ELSE
               MOVE 0 TO ws-imp
           END-IF
           OPEN INPUT it-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT it-file CLOSE it-file
           ELSE
               CLOSE it-file
           END-IF
           OPEN EXTEND it-file
           MOVE ws-pid TO it-pedido-id
           MOVE ws-seq TO it-seq
           MOVE ws-prod-id TO it-prod-id
           MOVE ws-produto TO it-produto
           MOVE ws-qtd TO it-qtd
           MOVE ws-uom TO it-uom
           MOVE ws-preco TO it-preco
           MOVE ws-desc TO it-desconto
           MOVE ws-imp TO it-imposto
           WRITE it-reg
           CLOSE it-file
           MOVE ws-pid TO ws-pid-ed
           MOVE ws-seq TO ws-seq-ed
           DISPLAY FUNCTION TRIM(ws-pid-ed)
           DISPLAY FUNCTION TRIM(ws-seq-ed).

       limpar.
           ACCEPT ws-pid-in FROM ENVIRONMENT "PEDIDO_ID"
           COMPUTE ws-pid = FUNCTION NUMVAL(ws-pid-in)
           OPEN INPUT it-file
           IF ws-fs = "35" THEN
               CLOSE it-file
               DISPLAY "OK"
               STOP RUN
           END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ it-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF it-pedido-id NOT = ws-pid
                   MOVE it-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE it-file
           CLOSE temp-file
           CALL "system" USING
               "mv dados/itens_pedido_compra.tmp dados/itens_pedido_compra.dat"
           END-CALL
           DISPLAY "OK".

       find-next-seq.
           OPEN INPUT it-file
           IF ws-fs = "35" THEN
               MOVE 0 TO ws-seq
               CLOSE it-file
               ADD 1 TO ws-seq
               EXIT PARAGRAPH
           END-IF
           MOVE 0 TO ws-seq
           PERFORM UNTIL 1 = 2
               READ it-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF it-pedido-id = ws-pid AND it-seq > ws-seq
                   MOVE it-seq TO ws-seq
               END-IF
           END-PERFORM
           CLOSE it-file
           ADD 1 TO ws-seq.

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

       listar-ped.
           ACCEPT ws-pid-in FROM ENVIRONMENT "PEDIDO_ID"
           COMPUTE ws-pid = FUNCTION NUMVAL(ws-pid-in)
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
               IF it-pedido-id = ws-pid
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
           MOVE it-pedido-id TO ws-pid-ed
           MOVE it-seq TO ws-seq-ed
           MOVE it-qtd TO ws-qtd-ed
           MOVE it-preco TO ws-preco-ed
           MOVE it-desconto TO ws-desc-ed
           MOVE it-imposto TO ws-imp-ed
           MOVE SPACES TO ws-json
           STRING '{"pedido_id":' FUNCTION TRIM(ws-pid-ed)
                  ',"seq":' FUNCTION TRIM(ws-seq-ed)
                  ',"prod_id":"' FUNCTION TRIM(it-prod-id) '"'
                  ',"produto":"' FUNCTION TRIM(it-produto) '"'
                  ',"qtd":' FUNCTION TRIM(ws-qtd-ed)
                  ',"uom":"' FUNCTION TRIM(it-uom) '"'
                  ',"preco":' FUNCTION TRIM(ws-preco-ed)
                  ',"desconto":' FUNCTION TRIM(ws-desc-ed)
                  ',"imposto":' FUNCTION TRIM(ws-imp-ed) '}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
