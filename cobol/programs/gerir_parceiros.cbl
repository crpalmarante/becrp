       >>SOURCE FORMAT IS FREE
       *> gerir_parceiros.cbl — Business Partner core (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirParceiros.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT pn-file ASSIGN TO "dados/parceiros.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/parceiros.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD pn-file.
       01 pn-reg.
           05 pn-id              PIC X(12).
           05 pn-code            PIC X(16).
           05 pn-person          PIC X(10).
           05 pn-display         PIC X(40).
           05 pn-legal           PIC X(60).
           05 pn-trade           PIC X(40).
           05 pn-status          PIC X(10).
           05 pn-roles           PIC X(40).
           05 pn-cnpj            PIC X(18).
           05 pn-ie              PIC X(20).
           05 pn-price-list      PIC X(20).
           05 pn-credit          PIC S9(11)V99 COMP-3.
           05 pn-terms           PIC X(20).
           05 pn-blocked         PIC X(1).
           05 pn-regime          PIC X(4).
           05 pn-contrib         PIC X(2).
           05 pn-obs             PIC X(60).
           05 pn-ativo           PIC X(1).

       FD temp-file.
       01 temp-reg.
           05 tn-id              PIC X(12).
           05 tn-code            PIC X(16).
           05 tn-person          PIC X(10).
           05 tn-display         PIC X(40).
           05 tn-legal           PIC X(60).
           05 tn-trade           PIC X(40).
           05 tn-status          PIC X(10).
           05 tn-roles           PIC X(40).
           05 tn-cnpj            PIC X(18).
           05 tn-ie              PIC X(20).
           05 tn-price-list      PIC X(20).
           05 tn-credit          PIC S9(11)V99 COMP-3.
           05 tn-terms           PIC X(20).
           05 tn-blocked         PIC X(1).
           05 tn-regime          PIC X(4).
           05 tn-contrib         PIC X(2).
           05 tn-obs             PIC X(60).
           05 tn-ativo           PIC X(1).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-encontrou       PIC X(1).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-seq             PIC 9(5).
       01 ws-seq-z           PIC 9(5).
       01 ws-id              PIC X(12).
       01 ws-code            PIC X(16).
       01 ws-person          PIC X(10).
       01 ws-display         PIC X(40).
       01 ws-legal           PIC X(60).
       01 ws-trade           PIC X(40).
       01 ws-status          PIC X(10).
       01 ws-roles           PIC X(40).
       01 ws-cnpj            PIC X(18).
       01 ws-ie              PIC X(20).
       01 ws-price-list      PIC X(20).
       01 ws-credit-in       PIC X(20).
       01 ws-credit          PIC S9(11)V99 COMP-3.
       01 ws-credit-ed       PIC -(10)9.99.
       01 ws-terms           PIC X(20).
       01 ws-blocked         PIC X(1).
       01 ws-regime          PIC X(4).
       01 ws-contrib         PIC X(2).
       01 ws-obs             PIC X(60).
       01 ws-ativo           PIC X(1).
       01 ws-json            PIC X(900).

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

       accept-fields.
           ACCEPT ws-code FROM ENVIRONMENT "PARTNER_CODE"
           ACCEPT ws-person FROM ENVIRONMENT "PERSON_TYPE"
           ACCEPT ws-display FROM ENVIRONMENT "DISPLAY_NAME"
           ACCEPT ws-legal FROM ENVIRONMENT "LEGAL_NAME"
           ACCEPT ws-trade FROM ENVIRONMENT "TRADE_NAME"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           ACCEPT ws-roles FROM ENVIRONMENT "ROLES"
           ACCEPT ws-cnpj FROM ENVIRONMENT "CNPJ"
           ACCEPT ws-ie FROM ENVIRONMENT "IE"
           ACCEPT ws-price-list FROM ENVIRONMENT "PRICE_LIST"
           ACCEPT ws-credit-in FROM ENVIRONMENT "CREDIT_LIMIT"
           ACCEPT ws-terms FROM ENVIRONMENT "PAYMENT_TERMS"
           ACCEPT ws-blocked FROM ENVIRONMENT "CREDIT_BLOCKED"
           ACCEPT ws-regime FROM ENVIRONMENT "REGIME"
           ACCEPT ws-contrib FROM ENVIRONMENT "CONTRIBUINTE"
           ACCEPT ws-obs FROM ENVIRONMENT "OBSERVACAO"
           ACCEPT ws-ativo FROM ENVIRONMENT "ATIVO"
           COMPUTE ws-credit = FUNCTION NUMVAL(ws-credit-in)
           IF ws-person = SPACES THEN MOVE "COMPANY" TO ws-person END-IF
           IF ws-status = SPACES THEN MOVE "ACTIVE" TO ws-status END-IF
           IF ws-roles = SPACES THEN MOVE "CUSTOMER" TO ws-roles END-IF
           IF ws-terms = SPACES THEN MOVE "30" TO ws-terms END-IF
           IF ws-blocked = SPACES THEN MOVE "N" TO ws-blocked END-IF
           IF ws-ativo = SPACES THEN MOVE "S" TO ws-ativo END-IF
           IF ws-regime = SPACES THEN MOVE "SN" TO ws-regime END-IF
           IF ws-contrib = SPACES THEN MOVE "1" TO ws-contrib END-IF
           IF ws-legal = SPACES THEN
               DISPLAY "ERRO: legal_name obrigatorio" STOP RUN END-IF.

       move-ws-to-pn.
           MOVE ws-id TO pn-id
           MOVE ws-code TO pn-code
           MOVE ws-person TO pn-person
           MOVE ws-display TO pn-display
           MOVE ws-legal TO pn-legal
           MOVE ws-trade TO pn-trade
           MOVE ws-status TO pn-status
           MOVE ws-roles TO pn-roles
           MOVE ws-cnpj TO pn-cnpj
           MOVE ws-ie TO pn-ie
           MOVE ws-price-list TO pn-price-list
           MOVE ws-credit TO pn-credit
           MOVE ws-terms TO pn-terms
           MOVE ws-blocked TO pn-blocked
           MOVE ws-regime TO pn-regime
           MOVE ws-contrib TO pn-contrib
           MOVE ws-obs TO pn-obs
           MOVE ws-ativo TO pn-ativo.

       proximo-id.
           MOVE 0 TO ws-seq
           OPEN INPUT pn-file
           IF ws-fs = "35" THEN
               MOVE 1 TO ws-seq
               EXIT PARAGRAPH
           END-IF
           PERFORM UNTIL 1 = 2
               READ pn-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-seq
           END-PERFORM
           CLOSE pn-file
           ADD 1 TO ws-seq.

       incluir.
           PERFORM accept-fields
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           IF ws-id = SPACES THEN
               PERFORM proximo-id
               MOVE ws-seq TO ws-seq-z
               MOVE SPACES TO ws-id
               STRING "bp" ws-seq-z DELIMITED BY SIZE INTO ws-id
           END-IF
           IF ws-code = SPACES THEN
               MOVE ws-seq TO ws-seq-z
               STRING "BP" ws-seq-z DELIMITED BY SIZE INTO ws-code
           END-IF
           IF ws-display = SPACES THEN
               MOVE ws-legal TO ws-display
           END-IF
           OPEN INPUT pn-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT pn-file CLOSE pn-file
           ELSE
               CLOSE pn-file
           END-IF
           OPEN EXTEND pn-file
           PERFORM move-ws-to-pn
           WRITE pn-reg
           CLOSE pn-file
           DISPLAY FUNCTION TRIM(ws-id).

       alterar.
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           IF ws-id = SPACES THEN
               DISPLAY "ERRO: id obrigatorio" STOP RUN END-IF
           PERFORM accept-fields
           OPEN INPUT pn-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ pn-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(pn-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-id)) THEN
                   MOVE "S" TO ws-encontrou
                   PERFORM move-ws-to-pn
                   MOVE pn-reg TO temp-reg
                   WRITE temp-reg
               ELSE
                   MOVE pn-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE pn-file CLOSE temp-file
           CALL "system" USING "mv dados/parceiros.tmp dados/parceiros.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: parceiro nao encontrado".

       excluir.
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           OPEN INPUT pn-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ pn-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(pn-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-id)) THEN
                   MOVE "S" TO ws-encontrou
               ELSE
                   MOVE pn-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE pn-file CLOSE temp-file
           CALL "system" USING "mv dados/parceiros.tmp dados/parceiros.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: parceiro nao encontrado".

       buscar.
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           OPEN INPUT pn-file
           IF ws-fs = "35" THEN
               DISPLAY '{"status":"erro"}' STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ pn-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(pn-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-id)) THEN
                   PERFORM emit-json
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE pn-file
           IF ws-encontrou = "N" THEN DISPLAY '{"status":"erro"}'.

       listar.
           OPEN INPUT pn-file
           IF ws-fs = "35" THEN
               DISPLAY '{"parceiros":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"parceiros":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ pn-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE pn-file.

       emit-json.
           MOVE pn-credit TO ws-credit-ed
           MOVE SPACES TO ws-json
           STRING '{"id":"' FUNCTION TRIM(pn-id) '"'
                  ',"partner_code":"' FUNCTION TRIM(pn-code) '"'
                  ',"person_type":"' FUNCTION TRIM(pn-person) '"'
                  ',"display_name":"' FUNCTION TRIM(pn-display) '"'
                  ',"legal_name":"' FUNCTION TRIM(pn-legal) '"'
                  ',"trade_name":"' FUNCTION TRIM(pn-trade) '"'
                  ',"status":"' FUNCTION TRIM(pn-status) '"'
                  ',"roles":"' FUNCTION TRIM(pn-roles) '"'
                  ',"cnpj":"' FUNCTION TRIM(pn-cnpj) '"'
                  ',"ie":"' FUNCTION TRIM(pn-ie) '"'
                  ',"default_price_list_id":"' FUNCTION TRIM(pn-price-list) '"'
                  ',"credit_limit":' FUNCTION TRIM(ws-credit-ed)
                  ',"payment_terms":"' FUNCTION TRIM(pn-terms) '"'
                  ',"credit_blocked":"' FUNCTION TRIM(pn-blocked) '"'
                  ',"regime":"' FUNCTION TRIM(pn-regime) '"'
                  ',"contribuinte_icms":"' FUNCTION TRIM(pn-contrib) '"'
                  ',"observacao":"' FUNCTION TRIM(pn-obs) '"'
                  ',"ativo":"' FUNCTION TRIM(pn-ativo) '"}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
