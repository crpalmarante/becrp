       >>SOURCE FORMAT IS FREE
       *> gerir_itens_acordo_compra.cbl — itens do acordo de compra (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirItensAcordoCompra.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT it-file ASSIGN TO "dados/itens_acordo_compra.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/itens_acordo_compra.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD it-file.
       01 it-reg.
           05 it-acordo-id       PIC 9(6).
           05 it-seq             PIC 9(3).
           05 it-prod-id         PIC X(10).
           05 it-produto         PIC X(40).
           05 it-qtd             PIC S9(9)V99 COMP-3.
           05 it-uom             PIC X(4).
           05 it-descricao       PIC X(80).

       FD temp-file.
       01 temp-reg.
           05 tt-acordo-id       PIC 9(6).
           05 tt-seq             PIC 9(3).
           05 tt-prod-id         PIC X(10).
           05 tt-produto         PIC X(40).
           05 tt-qtd             PIC S9(9)V99 COMP-3.
           05 tt-uom             PIC X(4).
           05 tt-descricao       PIC X(80).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-aid             PIC 9(6).
       01 ws-aid-in          PIC X(10).
       01 ws-seq             PIC 9(3).
       01 ws-seq-in          PIC X(5).
       01 ws-prod-id         PIC X(10).
       01 ws-produto         PIC X(40).
       01 ws-uom             PIC X(4).
       01 ws-qtd-in          PIC X(20).
       01 ws-qtd             PIC S9(9)V99 COMP-3.
       01 ws-aid-ed          PIC ZZZZZ9.
       01 ws-seq-ed          PIC ZZ9.
       01 ws-qtd-ed          PIC -(8)9.99.
       01 ws-json            PIC X(400).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF
           EVALUATE ws-acao
               WHEN "incluir"      PERFORM incluir
               WHEN "limpar"       PERFORM limpar
               WHEN "listar"       PERFORM listar
               WHEN "listar-ac"    PERFORM listar-ac
               WHEN OTHER          DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       incluir.
           ACCEPT ws-aid-in FROM ENVIRONMENT "ACORDO_ID"
           COMPUTE ws-aid = FUNCTION NUMVAL(ws-aid-in)
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
           OPEN INPUT it-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT it-file CLOSE it-file
           ELSE
               CLOSE it-file
           END-IF
           OPEN EXTEND it-file
           MOVE ws-aid TO it-acordo-id
           MOVE ws-seq TO it-seq
           MOVE ws-prod-id TO it-prod-id
           MOVE ws-produto TO it-produto
           MOVE ws-qtd TO it-qtd
           MOVE ws-uom TO it-uom
           WRITE it-reg
           CLOSE it-file
           MOVE ws-aid TO ws-aid-ed
           MOVE ws-seq TO ws-seq-ed
           DISPLAY FUNCTION TRIM(ws-aid-ed)
           DISPLAY FUNCTION TRIM(ws-seq-ed).

       limpar.
           ACCEPT ws-aid-in FROM ENVIRONMENT "ACORDO_ID"
           COMPUTE ws-aid = FUNCTION NUMVAL(ws-aid-in)
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
               IF it-acordo-id NOT = ws-aid THEN
                   MOVE it-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE it-file
           CLOSE temp-file
           CALL "system" USING
               "mv dados/itens_acordo_compra.tmp dados/itens_acordo_compra.dat"
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
               IF it-acordo-id = ws-aid AND it-seq > ws-seq THEN
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

       listar-ac.
           ACCEPT ws-aid-in FROM ENVIRONMENT "ACORDO_ID"
           COMPUTE ws-aid = FUNCTION NUMVAL(ws-aid-in)
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
               IF it-acordo-id = ws-aid THEN
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
           MOVE it-acordo-id TO ws-aid-ed
           MOVE it-seq TO ws-seq-ed
           MOVE it-qtd TO ws-qtd-ed
           MOVE SPACES TO ws-json
           STRING '{"acordo_id":' FUNCTION TRIM(ws-aid-ed)
                  ',"seq":' FUNCTION TRIM(ws-seq-ed)
                  ',"prod_id":"' FUNCTION TRIM(it-prod-id) '"'
                  ',"produto":"' FUNCTION TRIM(it-produto) '"'
                  ',"qtd":' FUNCTION TRIM(ws-qtd-ed)
                  ',"uom":"' FUNCTION TRIM(it-uom) '"'
                  ',"descricao":"' FUNCTION TRIM(it-descricao) '"}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
