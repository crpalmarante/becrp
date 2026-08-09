       >>SOURCE FORMAT IS FREE
       *> gerir_paradas_ent.cbl — paradas da DO (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirParadasEnt.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT pa-file ASSIGN TO "dados/entregas_paradas.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/entregas_paradas.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD pa-file.
       01 pa-reg.
           05 pa-entrega-id      PIC X(24).
           05 pa-parada          PIC 9(2).
           05 pa-rotulo          PIC X(30).
           05 pa-addr-type       PIC X(16).
           05 pa-endereco        PIC X(60).
           05 pa-cidade          PIC X(30).
           05 pa-uf              PIC X(2).
           05 pa-cep             PIC X(10).
           05 pa-contato         PIC X(30).
           05 pa-telefone        PIC X(20).
           05 pa-status          PIC X(12).

       FD temp-file.
       01 temp-reg.
           05 tp-entrega-id      PIC X(24).
           05 tp-parada          PIC 9(2).
           05 tp-rotulo          PIC X(30).
           05 tp-addr-type       PIC X(16).
           05 tp-endereco        PIC X(60).
           05 tp-cidade          PIC X(30).
           05 tp-uf              PIC X(2).
           05 tp-cep             PIC X(10).
           05 tp-contato         PIC X(30).
           05 tp-telefone        PIC X(20).
           05 tp-status          PIC X(12).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-eid             PIC X(24).
       01 ws-parada          PIC 9(2).
       01 ws-parada-in       PIC X(5).
       01 ws-rotulo          PIC X(30).
       01 ws-addr-type       PIC X(16).
       01 ws-endereco        PIC X(60).
       01 ws-cidade          PIC X(30).
       01 ws-uf              PIC X(2).
       01 ws-cep             PIC X(10).
       01 ws-contato         PIC X(30).
       01 ws-telefone        PIC X(20).
       01 ws-status          PIC X(12).
       01 ws-parada-ed       PIC Z9.
       01 ws-json            PIC X(450).

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
           ACCEPT ws-rotulo FROM ENVIRONMENT "ROTULO"
           ACCEPT ws-addr-type FROM ENVIRONMENT "ADDRESS_TYPE"
           ACCEPT ws-endereco FROM ENVIRONMENT "ENDERECO"
           ACCEPT ws-cidade FROM ENVIRONMENT "CIDADE"
           ACCEPT ws-uf FROM ENVIRONMENT "UF"
           ACCEPT ws-cep FROM ENVIRONMENT "CEP"
           ACCEPT ws-contato FROM ENVIRONMENT "CONTATO"
           ACCEPT ws-telefone FROM ENVIRONMENT "TELEFONE"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           COMPUTE ws-parada = FUNCTION NUMVAL(ws-parada-in)
           IF ws-addr-type = SPACES THEN MOVE "SHIPPING" TO ws-addr-type END-IF
           IF ws-status = SPACES THEN MOVE "pending" TO ws-status END-IF
           IF ws-eid = SPACES THEN
               DISPLAY "ERRO: entrega_id" STOP RUN END-IF
           OPEN INPUT pa-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT pa-file CLOSE pa-file
           ELSE CLOSE pa-file END-IF
           OPEN EXTEND pa-file
           MOVE ws-eid TO pa-entrega-id
           MOVE ws-parada TO pa-parada
           MOVE ws-rotulo TO pa-rotulo
           MOVE ws-addr-type TO pa-addr-type
           MOVE ws-endereco TO pa-endereco
           MOVE ws-cidade TO pa-cidade
           MOVE ws-uf TO pa-uf
           MOVE ws-cep TO pa-cep
           MOVE ws-contato TO pa-contato
           MOVE ws-telefone TO pa-telefone
           MOVE ws-status TO pa-status
           WRITE pa-reg
           CLOSE pa-file
           DISPLAY "OK".

       limpar.
           ACCEPT ws-eid FROM ENVIRONMENT "ENTREGA_ID"
           OPEN INPUT pa-file
           IF ws-fs = "35" THEN DISPLAY "OK" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ pa-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(pa-entrega-id)) NOT =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-eid)) THEN
                   MOVE pa-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE pa-file CLOSE temp-file
           CALL "system" USING
               "mv dados/entregas_paradas.tmp dados/entregas_paradas.dat"
           END-CALL
           DISPLAY "OK".

       listar.
           OPEN INPUT pa-file
           IF ws-fs = "35" THEN
               DISPLAY '{"paradas":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"paradas":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ pa-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE pa-file.

       listar-do.
           ACCEPT ws-eid FROM ENVIRONMENT "ENTREGA_ID"
           OPEN INPUT pa-file
           IF ws-fs = "35" THEN
               DISPLAY '{"paradas":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"paradas":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ pa-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(pa-entrega-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-eid)) THEN
                   ADD 1 TO ws-total
                   IF ws-first = "S" THEN MOVE "N" TO ws-first
                   ELSE DISPLAY "," END-IF
                   PERFORM emit-json
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE pa-file.

       emit-json.
           MOVE pa-parada TO ws-parada-ed
           MOVE SPACES TO ws-json
           STRING '{"entrega_id":"' FUNCTION TRIM(pa-entrega-id) '"'
                  ',"parada":' FUNCTION TRIM(ws-parada-ed)
                  ',"rotulo":"' FUNCTION TRIM(pa-rotulo) '"'
                  ',"address_type":"' FUNCTION TRIM(pa-addr-type) '"'
                  ',"endereco":"' FUNCTION TRIM(pa-endereco) '"'
                  ',"cidade":"' FUNCTION TRIM(pa-cidade) '"'
                  ',"uf":"' FUNCTION TRIM(pa-uf) '"'
                  ',"cep":"' FUNCTION TRIM(pa-cep) '"'
                  ',"contato":"' FUNCTION TRIM(pa-contato) '"'
                  ',"telefone":"' FUNCTION TRIM(pa-telefone) '"'
                  ',"status":"' FUNCTION TRIM(pa-status) '"}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
