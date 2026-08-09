       >>SOURCE FORMAT IS FREE
       *> gerir_end_parceiro.cbl — endereços do BP (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirEndParceiro.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ea-file ASSIGN TO "dados/parceiros_end.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/parceiros_end.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD ea-file.
       01 ea-reg.
           05 ea-partner-id      PIC X(12).
           05 ea-seq             PIC 9(2).
           05 ea-type            PIC X(16).
           05 ea-zip             PIC X(10).
           05 ea-street          PIC X(40).
           05 ea-number          PIC X(10).
           05 ea-district        PIC X(30).
           05 ea-city            PIC X(30).
           05 ea-state           PIC X(2).
           05 ea-country         PIC X(2).
           05 ea-pref            PIC X(1).

       FD temp-file.
       01 temp-reg.
           05 te-partner-id      PIC X(12).
           05 te-seq             PIC 9(2).
           05 te-type            PIC X(16).
           05 te-zip             PIC X(10).
           05 te-street          PIC X(40).
           05 te-number          PIC X(10).
           05 te-district        PIC X(30).
           05 te-city            PIC X(30).
           05 te-state           PIC X(2).
           05 te-country         PIC X(2).
           05 te-pref            PIC X(1).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-pid             PIC X(12).
       01 ws-seq             PIC 9(2).
       01 ws-seq-in          PIC X(5).
       01 ws-type            PIC X(16).
       01 ws-zip             PIC X(10).
       01 ws-street          PIC X(40).
       01 ws-number          PIC X(10).
       01 ws-district        PIC X(30).
       01 ws-city            PIC X(30).
       01 ws-state           PIC X(2).
       01 ws-country         PIC X(2).
       01 ws-pref            PIC X(1).
       01 ws-seq-ed          PIC Z9.
       01 ws-json            PIC X(400).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF
           EVALUATE ws-acao
               WHEN "incluir"    PERFORM incluir
               WHEN "limpar"     PERFORM limpar
               WHEN "listar"     PERFORM listar
               WHEN "listar-bp"  PERFORM listar-bp
               WHEN OTHER        DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       incluir.
           ACCEPT ws-pid FROM ENVIRONMENT "PARTNER_ID"
           ACCEPT ws-seq-in FROM ENVIRONMENT "SEQ"
           ACCEPT ws-type FROM ENVIRONMENT "ADDRESS_TYPE"
           ACCEPT ws-zip FROM ENVIRONMENT "ZIP"
           ACCEPT ws-street FROM ENVIRONMENT "STREET"
           ACCEPT ws-number FROM ENVIRONMENT "NUMBER"
           ACCEPT ws-district FROM ENVIRONMENT "DISTRICT"
           ACCEPT ws-city FROM ENVIRONMENT "CITY"
           ACCEPT ws-state FROM ENVIRONMENT "STATE"
           ACCEPT ws-country FROM ENVIRONMENT "COUNTRY"
           ACCEPT ws-pref FROM ENVIRONMENT "PREFERRED"
           COMPUTE ws-seq = FUNCTION NUMVAL(ws-seq-in)
           IF ws-country = SPACES THEN MOVE "BR" TO ws-country END-IF
           IF ws-pref = SPACES THEN MOVE "N" TO ws-pref END-IF
           IF ws-pid = SPACES THEN
               DISPLAY "ERRO: partner_id" STOP RUN END-IF
           OPEN INPUT ea-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT ea-file CLOSE ea-file
           ELSE CLOSE ea-file END-IF
           OPEN EXTEND ea-file
           MOVE ws-pid TO ea-partner-id
           MOVE ws-seq TO ea-seq
           MOVE ws-type TO ea-type
           MOVE ws-zip TO ea-zip
           MOVE ws-street TO ea-street
           MOVE ws-number TO ea-number
           MOVE ws-district TO ea-district
           MOVE ws-city TO ea-city
           MOVE ws-state TO ea-state
           MOVE ws-country TO ea-country
           MOVE ws-pref TO ea-pref
           WRITE ea-reg
           CLOSE ea-file
           DISPLAY "OK".

       limpar.
           ACCEPT ws-pid FROM ENVIRONMENT "PARTNER_ID"
           OPEN INPUT ea-file
           IF ws-fs = "35" THEN DISPLAY "OK" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ ea-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(ea-partner-id)) NOT =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-pid)) THEN
                   MOVE ea-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE ea-file CLOSE temp-file
           CALL "system" USING
               "mv dados/parceiros_end.tmp dados/parceiros_end.dat"
           END-CALL
           DISPLAY "OK".

       listar.
           OPEN INPUT ea-file
           IF ws-fs = "35" THEN
               DISPLAY '{"enderecos":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"enderecos":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ ea-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE ea-file.

       listar-bp.
           ACCEPT ws-pid FROM ENVIRONMENT "PARTNER_ID"
           OPEN INPUT ea-file
           IF ws-fs = "35" THEN
               DISPLAY '{"enderecos":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"enderecos":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ ea-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(ea-partner-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-pid)) THEN
                   ADD 1 TO ws-total
                   IF ws-first = "S" THEN MOVE "N" TO ws-first
                   ELSE DISPLAY "," END-IF
                   PERFORM emit-json
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE ea-file.

       emit-json.
           MOVE ea-seq TO ws-seq-ed
           MOVE SPACES TO ws-json
           STRING '{"partner_id":"' FUNCTION TRIM(ea-partner-id) '"'
                  ',"seq":' FUNCTION TRIM(ws-seq-ed)
                  ',"address_type":"' FUNCTION TRIM(ea-type) '"'
                  ',"zip_code":"' FUNCTION TRIM(ea-zip) '"'
                  ',"street":"' FUNCTION TRIM(ea-street) '"'
                  ',"number":"' FUNCTION TRIM(ea-number) '"'
                  ',"district":"' FUNCTION TRIM(ea-district) '"'
                  ',"city":"' FUNCTION TRIM(ea-city) '"'
                  ',"state":"' FUNCTION TRIM(ea-state) '"'
                  ',"country":"' FUNCTION TRIM(ea-country) '"'
                  ',"preferred":"' FUNCTION TRIM(ea-pref) '"}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
