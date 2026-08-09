       >>SOURCE FORMAT IS FREE
       *> gerir_reservas_venda.cbl — reserva B2B cabeçalho (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirReservasVenda.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT sr-file ASSIGN TO "dados/reservas_venda.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/reservas_venda.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD sr-file.
       01 sr-reg.
           05 sr-id              PIC X(12).
           05 sr-pedido-id       PIC X(12).
           05 sr-pedido-num      PIC X(12).
           05 sr-estab           PIC X(16).
           05 sr-status          PIC X(12).
           05 sr-usuario         PIC X(30).
           05 sr-seq             PIC 9(5).

       FD temp-file.
       01 temp-reg.
           05 tr-id              PIC X(12).
           05 tr-pedido-id       PIC X(12).
           05 tr-pedido-num      PIC X(12).
           05 tr-estab           PIC X(16).
           05 tr-status          PIC X(12).
           05 tr-usuario         PIC X(30).
           05 tr-seq             PIC 9(5).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-encontrou       PIC X(1).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-prox            PIC 9(5).
       01 ws-seq-ed          PIC ZZZZ9.
       01 ws-id              PIC X(12).
       01 ws-pedido-id       PIC X(12).
       01 ws-pedido-num      PIC X(12).
       01 ws-estab           PIC X(16).
       01 ws-status          PIC X(12).
       01 ws-usuario         PIC X(30).
       01 ws-seq             PIC 9(5).
       01 ws-seq-in          PIC X(8).
       01 ws-seq-z           PIC 9(5).
       01 ws-json            PIC X(400).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF
           EVALUATE ws-acao
               WHEN "incluir"  PERFORM incluir
               WHEN "alterar"  PERFORM alterar
               WHEN "listar"   PERFORM listar
               WHEN "buscar"   PERFORM buscar
               WHEN OTHER      DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       accept-fields.
           ACCEPT ws-pedido-id FROM ENVIRONMENT "PEDIDO_ID"
           ACCEPT ws-pedido-num FROM ENVIRONMENT "PEDIDO_NUM"
           ACCEPT ws-estab FROM ENVIRONMENT "ESTAB"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           ACCEPT ws-usuario FROM ENVIRONMENT "USUARIO"
           ACCEPT ws-seq-in FROM ENVIRONMENT "SEQ"
           COMPUTE ws-seq = FUNCTION NUMVAL(ws-seq-in)
           IF ws-status = SPACES THEN MOVE "active" TO ws-status END-IF
           IF ws-estab = SPACES THEN MOVE "matriz" TO ws-estab END-IF.

       move-ws-to-sr.
           MOVE ws-id TO sr-id
           MOVE ws-pedido-id TO sr-pedido-id
           MOVE ws-pedido-num TO sr-pedido-num
           MOVE ws-estab TO sr-estab
           MOVE ws-status TO sr-status
           MOVE ws-usuario TO sr-usuario
           MOVE ws-seq TO sr-seq.

       proximo-seq.
           MOVE 0 TO ws-prox
           OPEN INPUT sr-file
           IF ws-fs = "35" THEN
               MOVE 1 TO ws-prox
               EXIT PARAGRAPH
           END-IF
           PERFORM UNTIL 1 = 2
               READ sr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF sr-seq > ws-prox THEN MOVE sr-seq TO ws-prox END-IF
           END-PERFORM
           CLOSE sr-file
           ADD 1 TO ws-prox.

       incluir.
           PERFORM accept-fields
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           IF ws-seq = 0 THEN
               PERFORM proximo-seq
               MOVE ws-prox TO ws-seq
           END-IF
           IF ws-id = SPACES THEN
               MOVE ws-seq TO ws-seq-z
               STRING "SR-" ws-seq-z DELIMITED BY SIZE INTO ws-id
           END-IF
           OPEN INPUT sr-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT sr-file CLOSE sr-file
           ELSE CLOSE sr-file END-IF
           OPEN EXTEND sr-file
           PERFORM move-ws-to-sr
           WRITE sr-reg
           CLOSE sr-file
           DISPLAY FUNCTION TRIM(ws-id).

       alterar.
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           IF ws-id = SPACES THEN
               DISPLAY "ERRO: id obrigatorio" STOP RUN END-IF
           PERFORM accept-fields
           OPEN INPUT sr-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ sr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(sr-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-id)) THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-seq = 0 THEN MOVE sr-seq TO ws-seq END-IF
                   PERFORM move-ws-to-sr
                   MOVE sr-reg TO temp-reg
                   WRITE temp-reg
               ELSE
                   MOVE sr-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE sr-file CLOSE temp-file
           CALL "system" USING
               "mv dados/reservas_venda.tmp dados/reservas_venda.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: reserva nao encontrada".

       buscar.
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           OPEN INPUT sr-file
           IF ws-fs = "35" THEN
               DISPLAY '{"status":"erro"}' STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ sr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(sr-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-id)) THEN
                   PERFORM emit-json
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE sr-file
           IF ws-encontrou = "N" THEN DISPLAY '{"status":"erro"}'.

       listar.
           OPEN INPUT sr-file
           IF ws-fs = "35" THEN
               DISPLAY '{"reservas":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"reservas":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ sr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE sr-file.

       emit-json.
           MOVE sr-seq TO ws-seq-ed
           MOVE SPACES TO ws-json
           STRING '{"id":"' FUNCTION TRIM(sr-id) '"'
                  ',"pedido_id":"' FUNCTION TRIM(sr-pedido-id) '"'
                  ',"pedido_numero":"' FUNCTION TRIM(sr-pedido-num) '"'
                  ',"estabelecimento_id":"' FUNCTION TRIM(sr-estab) '"'
                  ',"status":"' FUNCTION TRIM(sr-status) '"'
                  ',"usuario":"' FUNCTION TRIM(sr-usuario) '"'
                  ',"seq":' FUNCTION TRIM(ws-seq-ed) '}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
