       >>SOURCE FORMAT IS FREE
       *> gerir_titulos_ar.cbl - CRUD Contas a Receber (fonte da verdade)
       *> ORGANIZATION SEQUENTIAL: registro fixo; COMP-3 em valores.
       *> LINE SEQUENTIAL fica para projeção texto/CSV — nunca com COMP-*.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirTitulosAr.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ar-file ASSIGN TO "dados/titulos_ar.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/titulos_ar.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-file-status.

       DATA DIVISION.
       FILE SECTION.
       FD ar-file.
       01 ar-reg.
           05 ar-id             PIC X(12).
           05 ar-partner-id     PIC X(12).
           05 ar-cliente        PIC X(60).
           05 ar-cnpj           PIC X(18).
           05 ar-pedido-id      PIC X(10).
           05 ar-pedido-num     PIC X(12).
           05 ar-fatura-id      PIC X(10).
           05 ar-fatura-num     PIC X(12).
           05 ar-parcela        PIC 9(2).
           05 ar-parcelas       PIC 9(2).
           05 ar-valor          PIC S9(9)V99 COMP-3.
           05 ar-saldo          PIC S9(9)V99 COMP-3.
           05 ar-vencimento     PIC X(10).
           05 ar-status         PIC X(10).
           05 ar-terms          PIC X(20).
           05 ar-usuario        PIC X(30).

       FD temp-file.
       01 temp-reg.
           05 tr-id             PIC X(12).
           05 tr-partner-id     PIC X(12).
           05 tr-cliente        PIC X(60).
           05 tr-cnpj           PIC X(18).
           05 tr-pedido-id      PIC X(10).
           05 tr-pedido-num     PIC X(12).
           05 tr-fatura-id      PIC X(10).
           05 tr-fatura-num     PIC X(12).
           05 tr-parcela        PIC 9(2).
           05 tr-parcelas       PIC 9(2).
           05 tr-valor          PIC S9(9)V99 COMP-3.
           05 tr-saldo          PIC S9(9)V99 COMP-3.
           05 tr-vencimento     PIC X(10).
           05 tr-status         PIC X(10).
           05 tr-terms          PIC X(20).
           05 tr-usuario        PIC X(30).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-file-status     PIC X(2).
       01 ws-encontrou       PIC X(1).
       01 ws-json-linha      PIC X(800).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-seq             PIC 9(5).
       01 ws-seq-ed          PIC 9(5).
       01 ws-id              PIC X(12).
       01 ws-partner-id      PIC X(12).
       01 ws-cliente         PIC X(60).
       01 ws-cnpj            PIC X(18).
       01 ws-pedido-id       PIC X(10).
       01 ws-pedido-num      PIC X(12).
       01 ws-fatura-id       PIC X(10).
       01 ws-fatura-num      PIC X(12).
       01 ws-parcela-in      PIC X(5).
       01 ws-parcelas-in     PIC X(5).
       01 ws-parcela         PIC 9(2).
       01 ws-parcelas        PIC 9(2).
       01 ws-valor-in        PIC X(20).
       01 ws-saldo-in        PIC X(20).
       01 ws-valor           PIC S9(9)V99 COMP-3.
       01 ws-saldo           PIC S9(9)V99 COMP-3.
       01 ws-pay             PIC S9(9)V99 COMP-3.
       01 ws-vencimento      PIC X(10).
       01 ws-status          PIC X(10).
       01 ws-terms           PIC X(20).
       01 ws-usuario         PIC X(30).
       01 ws-valor-ed        PIC Z(8)9.99.
       01 ws-saldo-ed        PIC Z(8)9.99.
       01 ws-parcela-ed      PIC Z9.
       01 ws-parcelas-ed     PIC Z9.
       01 ws-total           PIC 9(5).
       01 ws-first           PIC X(1).
       01 ws-num-txt         PIC X(12).
       01 ws-i               PIC 9(2).
       01 ws-digit           PIC X(1).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF

           EVALUATE ws-acao
               WHEN "incluir"   PERFORM incluir
               WHEN "baixar"    PERFORM baixar
               WHEN "cancelar"  PERFORM cancelar
               WHEN "listar"    PERFORM listar
               WHEN "buscar"    PERFORM buscar
               WHEN OTHER       DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       incluir.
           ACCEPT ws-partner-id FROM ENVIRONMENT "PARTNER_ID"
           ACCEPT ws-cliente FROM ENVIRONMENT "CLIENTE"
           ACCEPT ws-cnpj FROM ENVIRONMENT "CNPJ"
           ACCEPT ws-pedido-id FROM ENVIRONMENT "PEDIDO_ID"
           ACCEPT ws-pedido-num FROM ENVIRONMENT "PEDIDO_NUM"
           ACCEPT ws-fatura-id FROM ENVIRONMENT "FATURA_ID"
           ACCEPT ws-fatura-num FROM ENVIRONMENT "FATURA_NUM"
           ACCEPT ws-parcela-in FROM ENVIRONMENT "PARCELA"
           ACCEPT ws-parcelas-in FROM ENVIRONMENT "PARCELAS"
           ACCEPT ws-valor-in FROM ENVIRONMENT "VALOR"
           ACCEPT ws-vencimento FROM ENVIRONMENT "VENCIMENTO"
           ACCEPT ws-terms FROM ENVIRONMENT "PAYMENT_TERMS"
           ACCEPT ws-usuario FROM ENVIRONMENT "USUARIO"
           ACCEPT ws-id FROM ENVIRONMENT "ID"

           COMPUTE ws-parcela = FUNCTION NUMVAL(ws-parcela-in)
           COMPUTE ws-parcelas = FUNCTION NUMVAL(ws-parcelas-in)
           IF ws-parcela < 1 THEN MOVE 1 TO ws-parcela END-IF
           IF ws-parcelas < 1 THEN MOVE 1 TO ws-parcelas END-IF
           COMPUTE ws-valor = FUNCTION NUMVAL(ws-valor-in)
           IF ws-valor <= 0 THEN
               DISPLAY "ERRO: valor invalido" STOP RUN END-IF
           MOVE ws-valor TO ws-saldo
           IF ws-status = SPACES THEN MOVE "aberto" TO ws-status END-IF
           MOVE "aberto" TO ws-status

           IF ws-id = SPACES THEN
               PERFORM proximo-id
               MOVE SPACES TO ws-id
               MOVE ws-seq TO ws-seq-ed
               STRING "AR-" ws-seq-ed DELIMITED BY SIZE INTO ws-id
           END-IF

           OPEN INPUT ar-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT ar-file
               CLOSE ar-file
           ELSE
               CLOSE ar-file
           END-IF
           OPEN EXTEND ar-file

           MOVE ws-id TO ar-id
           MOVE ws-partner-id TO ar-partner-id
           MOVE ws-cliente TO ar-cliente
           MOVE ws-cnpj TO ar-cnpj
           MOVE ws-pedido-id TO ar-pedido-id
           MOVE ws-pedido-num TO ar-pedido-num
           MOVE ws-fatura-id TO ar-fatura-id
           MOVE ws-fatura-num TO ar-fatura-num
           MOVE ws-parcela TO ar-parcela
           MOVE ws-parcelas TO ar-parcelas
           MOVE ws-valor TO ar-valor
           MOVE ws-saldo TO ar-saldo
           MOVE ws-vencimento TO ar-vencimento
           MOVE ws-status TO ar-status
           MOVE ws-terms TO ar-terms
           MOVE ws-usuario TO ar-usuario
           WRITE ar-reg
           CLOSE ar-file
           DISPLAY FUNCTION TRIM(ws-id).

       proximo-id.
           MOVE 0 TO ws-seq
           OPEN INPUT ar-file
           IF ws-file-status = "35" THEN
               MOVE 0 TO ws-seq
               EXIT PARAGRAPH
           END-IF
           PERFORM UNTIL 1 = 2
               READ ar-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               MOVE SPACES TO ws-num-txt
               MOVE 0 TO ws-i
               *> extrai dígitos após AR-
               PERFORM VARYING ws-i FROM 1 BY 1 UNTIL ws-i > 12
                   MOVE ar-id(ws-i:1) TO ws-digit
                   IF ws-digit >= "0" AND ws-digit <= "9"
                       STRING ws-num-txt DELIMITED BY SPACES
                              ws-digit DELIMITED BY SIZE
                              INTO ws-num-txt
                   END-IF
               END-PERFORM
               IF FUNCTION NUMVAL(ws-num-txt) > ws-seq THEN
                   COMPUTE ws-seq = FUNCTION NUMVAL(ws-num-txt)
               END-IF
           END-PERFORM
           CLOSE ar-file
           ADD 1 TO ws-seq.

       baixar.
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           ACCEPT ws-valor-in FROM ENVIRONMENT "VALOR"
           ACCEPT ws-usuario FROM ENVIRONMENT "USUARIO"
           IF ws-id = SPACES THEN
               DISPLAY "ERRO: id obrigatorio" STOP RUN END-IF

           OPEN INPUT ar-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ar-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(ar-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-id)) THEN
                   MOVE "S" TO ws-encontrou
                   IF ar-status = "pago" OR ar-status = "cancelado" THEN
                       MOVE ar-reg TO temp-reg
                       WRITE temp-reg
                   ELSE
                       IF ws-valor-in = SPACES THEN
                           MOVE ar-saldo TO ws-pay
                       ELSE
                           COMPUTE ws-pay = FUNCTION NUMVAL(ws-valor-in)
                       END-IF
                       IF ws-pay <= 0 THEN MOVE ar-saldo TO ws-pay END-IF
                       IF ws-pay > ar-saldo THEN MOVE ar-saldo TO ws-pay END-IF
                       COMPUTE ar-saldo = ar-saldo - ws-pay
                       IF ar-saldo <= 0 THEN
                           MOVE 0 TO ar-saldo
                           MOVE "pago" TO ar-status
                       ELSE
                           MOVE "parcial" TO ar-status
                       END-IF
                       IF ws-usuario NOT = SPACES THEN
                           MOVE ws-usuario TO ar-usuario
                       END-IF
                       MOVE ar-reg TO temp-reg
                       WRITE temp-reg
                       PERFORM emit-row-json
                   END-IF
               ELSE
                   MOVE ar-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE ar-file CLOSE temp-file
           CALL "system" USING "mv dados/titulos_ar.tmp dados/titulos_ar.dat"
           END-CALL
           IF ws-encontrou = "N" THEN
               DISPLAY "ERRO: titulo nao encontrado"
           END-IF.

       cancelar.
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           OPEN INPUT ar-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ar-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(ar-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-id)) THEN
                   MOVE "S" TO ws-encontrou
                   MOVE "cancelado" TO ar-status
                   MOVE 0 TO ar-saldo
               END-IF
               MOVE ar-reg TO temp-reg
               WRITE temp-reg
           END-PERFORM
           CLOSE ar-file CLOSE temp-file
           CALL "system" USING "mv dados/titulos_ar.tmp dados/titulos_ar.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: titulo nao encontrado".

       buscar.
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           OPEN INPUT ar-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"status":"erro","mensagem":"nao encontrado"}'
               STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ar-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(ar-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-id)) THEN
                   PERFORM emit-row-json
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE ar-file
           IF ws-encontrou = "N" THEN
               DISPLAY '{"status":"erro","mensagem":"nao encontrado"}'
           END-IF.

       listar.
           OPEN INPUT ar-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"titulos":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"titulos":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ ar-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN
                   MOVE "N" TO ws-first
               ELSE
                   DISPLAY ","
               END-IF
               PERFORM emit-row-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE ar-file.

       emit-row-json.
           MOVE ar-valor TO ws-valor-ed
           MOVE ar-saldo TO ws-saldo-ed
           MOVE ar-parcela TO ws-parcela-ed
           MOVE ar-parcelas TO ws-parcelas-ed
           MOVE SPACES TO ws-json-linha
           STRING '{"id":"' FUNCTION TRIM(ar-id) '"'
                  ',"partner_id":"' FUNCTION TRIM(ar-partner-id) '"'
                  ',"cliente":"' FUNCTION TRIM(ar-cliente) '"'
                  ',"cnpj":"' FUNCTION TRIM(ar-cnpj) '"'
                  ',"pedido_id":"' FUNCTION TRIM(ar-pedido-id) '"'
                  ',"pedido_numero":"' FUNCTION TRIM(ar-pedido-num) '"'
                  ',"fatura_id":"' FUNCTION TRIM(ar-fatura-id) '"'
                  ',"fatura_numero":"' FUNCTION TRIM(ar-fatura-num) '"'
                  ',"parcela":' FUNCTION TRIM(ws-parcela-ed)
                  ',"parcelas":' FUNCTION TRIM(ws-parcelas-ed)
                  ',"valor":' FUNCTION TRIM(ws-valor-ed)
                  ',"saldo":' FUNCTION TRIM(ws-saldo-ed)
                  ',"vencimento":"' FUNCTION TRIM(ar-vencimento) '"'
                  ',"status":"' FUNCTION TRIM(ar-status) '"'
                  ',"payment_terms":"' FUNCTION TRIM(ar-terms) '"'
                  ',"usuario":"' FUNCTION TRIM(ar-usuario) '"}'
               INTO ws-json-linha
           DISPLAY FUNCTION TRIM(ws-json-linha).
