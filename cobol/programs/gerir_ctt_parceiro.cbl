       >>SOURCE FORMAT IS FREE
       *> gerir_ctt_parceiro.cbl — contatos do BP (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirCttParceiro.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ct-file ASSIGN TO "dados/parceiros_ctt.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/parceiros_ctt.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD ct-file.
       01 ct-reg.
           05 ct-partner-id      PIC X(12).
           05 ct-seq             PIC 9(2).
           05 ct-name            PIC X(40).
           05 ct-dept            PIC X(20).
           05 ct-title           PIC X(20).
           05 ct-email           PIC X(40).
           05 ct-phone           PIC X(20).
           05 ct-mobile          PIC X(20).
           05 ct-pref            PIC X(1).

       FD temp-file.
       01 temp-reg.
           05 tt-partner-id      PIC X(12).
           05 tt-seq             PIC 9(2).
           05 tt-name            PIC X(40).
           05 tt-dept            PIC X(20).
           05 tt-title           PIC X(20).
           05 tt-email           PIC X(40).
           05 tt-phone           PIC X(20).
           05 tt-mobile          PIC X(20).
           05 tt-pref            PIC X(1).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-pid             PIC X(12).
       01 ws-seq             PIC 9(2).
       01 ws-seq-in          PIC X(5).
       01 ws-name            PIC X(40).
       01 ws-dept            PIC X(20).
       01 ws-title           PIC X(20).
       01 ws-email           PIC X(40).
       01 ws-phone           PIC X(20).
       01 ws-mobile          PIC X(20).
       01 ws-pref            PIC X(1).
       01 ws-seq-ed          PIC Z9.
       01 ws-json            PIC X(350).

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
           ACCEPT ws-name FROM ENVIRONMENT "NAME"
           ACCEPT ws-dept FROM ENVIRONMENT "DEPARTMENT"
           ACCEPT ws-title FROM ENVIRONMENT "JOB_TITLE"
           ACCEPT ws-email FROM ENVIRONMENT "EMAIL"
           ACCEPT ws-phone FROM ENVIRONMENT "PHONE"
           ACCEPT ws-mobile FROM ENVIRONMENT "MOBILE"
           ACCEPT ws-pref FROM ENVIRONMENT "PREFERRED"
           COMPUTE ws-seq = FUNCTION NUMVAL(ws-seq-in)
           IF ws-pref = SPACES THEN MOVE "N" TO ws-pref END-IF
           IF ws-pid = SPACES THEN
               DISPLAY "ERRO: partner_id" STOP RUN END-IF
           OPEN INPUT ct-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT ct-file CLOSE ct-file
           ELSE CLOSE ct-file END-IF
           OPEN EXTEND ct-file
           MOVE ws-pid TO ct-partner-id
           MOVE ws-seq TO ct-seq
           MOVE ws-name TO ct-name
           MOVE ws-dept TO ct-dept
           MOVE ws-title TO ct-title
           MOVE ws-email TO ct-email
           MOVE ws-phone TO ct-phone
           MOVE ws-mobile TO ct-mobile
           MOVE ws-pref TO ct-pref
           WRITE ct-reg
           CLOSE ct-file
           DISPLAY "OK".

       limpar.
           ACCEPT ws-pid FROM ENVIRONMENT "PARTNER_ID"
           OPEN INPUT ct-file
           IF ws-fs = "35" THEN DISPLAY "OK" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ ct-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(ct-partner-id)) NOT =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-pid)) THEN
                   MOVE ct-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE ct-file CLOSE temp-file
           CALL "system" USING
               "mv dados/parceiros_ctt.tmp dados/parceiros_ctt.dat"
           END-CALL
           DISPLAY "OK".

       listar.
           OPEN INPUT ct-file
           IF ws-fs = "35" THEN
               DISPLAY '{"contatos":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"contatos":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ ct-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE ct-file.

       listar-bp.
           ACCEPT ws-pid FROM ENVIRONMENT "PARTNER_ID"
           OPEN INPUT ct-file
           IF ws-fs = "35" THEN
               DISPLAY '{"contatos":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"contatos":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ ct-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(ct-partner-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-pid)) THEN
                   ADD 1 TO ws-total
                   IF ws-first = "S" THEN MOVE "N" TO ws-first
                   ELSE DISPLAY "," END-IF
                   PERFORM emit-json
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE ct-file.

       emit-json.
           MOVE ct-seq TO ws-seq-ed
           MOVE SPACES TO ws-json
           STRING '{"partner_id":"' FUNCTION TRIM(ct-partner-id) '"'
                  ',"seq":' FUNCTION TRIM(ws-seq-ed)
                  ',"name":"' FUNCTION TRIM(ct-name) '"'
                  ',"department":"' FUNCTION TRIM(ct-dept) '"'
                  ',"job_title":"' FUNCTION TRIM(ct-title) '"'
                  ',"email":"' FUNCTION TRIM(ct-email) '"'
                  ',"phone":"' FUNCTION TRIM(ct-phone) '"'
                  ',"mobile":"' FUNCTION TRIM(ct-mobile) '"'
                  ',"preferred":"' FUNCTION TRIM(ct-pref) '"}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
