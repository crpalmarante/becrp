       >>SOURCE FORMAT IS FREE
       *> gerir_lin_reserva.cbl — linhas da reserva B2B (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirLinReserva.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT lr-file ASSIGN TO "dados/reservas_linhas.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/reservas_linhas.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD lr-file.
       01 lr-reg.
           05 lr-reserva-id      PIC X(12).
           05 lr-seq             PIC 9(3).
           05 lr-prod-id         PIC X(10).
           05 lr-produto         PIC X(40).
           05 lr-qtd             PIC S9(9) COMP-3.
           05 lr-qtd-pedida      PIC S9(9) COMP-3.

       FD temp-file.
       01 temp-reg.
           05 tr-reserva-id      PIC X(12).
           05 tr-seq             PIC 9(3).
           05 tr-prod-id         PIC X(10).
           05 tr-produto         PIC X(40).
           05 tr-qtd             PIC S9(9) COMP-3.
           05 tr-qtd-pedida      PIC S9(9) COMP-3.

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-rid             PIC X(12).
       01 ws-seq             PIC 9(3).
       01 ws-seq-in          PIC X(5).
       01 ws-prod-id         PIC X(10).
       01 ws-produto         PIC X(40).
       01 ws-qtd-in          PIC X(15).
       01 ws-ped-in          PIC X(15).
       01 ws-qtd             PIC S9(9) COMP-3.
       01 ws-ped             PIC S9(9) COMP-3.
       01 ws-seq-ed          PIC ZZ9.
       01 ws-qtd-ed          PIC -(8)9.
       01 ws-ped-ed          PIC -(8)9.
       01 ws-json            PIC X(280).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF
           EVALUATE ws-acao
               WHEN "incluir"    PERFORM incluir
               WHEN "limpar"     PERFORM limpar
               WHEN "listar"     PERFORM listar
               WHEN "listar-sr"  PERFORM listar-sr
               WHEN OTHER        DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       incluir.
           ACCEPT ws-rid FROM ENVIRONMENT "RESERVA_ID"
           ACCEPT ws-seq-in FROM ENVIRONMENT "SEQ"
           ACCEPT ws-prod-id FROM ENVIRONMENT "PRODUTO_ID"
           ACCEPT ws-produto FROM ENVIRONMENT "PRODUTO"
           ACCEPT ws-qtd-in FROM ENVIRONMENT "QTD"
           ACCEPT ws-ped-in FROM ENVIRONMENT "QTD_PEDIDA"
           COMPUTE ws-seq = FUNCTION NUMVAL(ws-seq-in)
           COMPUTE ws-qtd = FUNCTION NUMVAL(ws-qtd-in)
           COMPUTE ws-ped = FUNCTION NUMVAL(ws-ped-in)
           IF ws-rid = SPACES THEN
               DISPLAY "ERRO: reserva_id" STOP RUN END-IF
           OPEN INPUT lr-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT lr-file CLOSE lr-file
           ELSE CLOSE lr-file END-IF
           OPEN EXTEND lr-file
           MOVE ws-rid TO lr-reserva-id
           MOVE ws-seq TO lr-seq
           MOVE ws-prod-id TO lr-prod-id
           MOVE ws-produto TO lr-produto
           MOVE ws-qtd TO lr-qtd
           MOVE ws-ped TO lr-qtd-pedida
           WRITE lr-reg
           CLOSE lr-file
           DISPLAY "OK".

       limpar.
           ACCEPT ws-rid FROM ENVIRONMENT "RESERVA_ID"
           OPEN INPUT lr-file
           IF ws-fs = "35" THEN DISPLAY "OK" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ lr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(lr-reserva-id)) NOT =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-rid)) THEN
                   MOVE lr-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE lr-file CLOSE temp-file
           CALL "system" USING
               "mv dados/reservas_linhas.tmp dados/reservas_linhas.dat"
           END-CALL
           DISPLAY "OK".

       listar.
           OPEN INPUT lr-file
           IF ws-fs = "35" THEN
               DISPLAY '{"linhas":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"linhas":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ lr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE lr-file.

       listar-sr.
           ACCEPT ws-rid FROM ENVIRONMENT "RESERVA_ID"
           OPEN INPUT lr-file
           IF ws-fs = "35" THEN
               DISPLAY '{"linhas":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"linhas":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ lr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(lr-reserva-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-rid)) THEN
                   ADD 1 TO ws-total
                   IF ws-first = "S" THEN MOVE "N" TO ws-first
                   ELSE DISPLAY "," END-IF
                   PERFORM emit-json
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE lr-file.

       emit-json.
           MOVE lr-seq TO ws-seq-ed
           MOVE lr-qtd TO ws-qtd-ed
           MOVE lr-qtd-pedida TO ws-ped-ed
           MOVE SPACES TO ws-json
           STRING '{"reserva_id":"' FUNCTION TRIM(lr-reserva-id) '"'
                  ',"seq":' FUNCTION TRIM(ws-seq-ed)
                  ',"produto_id":"' FUNCTION TRIM(lr-prod-id) '"'
                  ',"produto":"' FUNCTION TRIM(lr-produto) '"'
                  ',"qtd":' FUNCTION TRIM(ws-qtd-ed)
                  ',"qtd_pedida":' FUNCTION TRIM(ws-ped-ed) '}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
