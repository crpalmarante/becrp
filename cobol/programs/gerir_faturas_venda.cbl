       >>SOURCE FORMAT IS FREE
       *> gerir_faturas_venda.cbl — faturas comerciais B2B (fonte da verdade)
       *> ORGANIZATION SEQUENTIAL; COMP-3 em valores.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirFaturasVenda.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT fv-file ASSIGN TO "dados/faturas_venda.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/faturas_venda.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD fv-file.
       01 fv-reg.
           05 fv-id              PIC 9(5).
           05 fv-numero          PIC X(12).
           05 fv-pedido-id       PIC X(10).
           05 fv-pedido-num      PIC X(12).
           05 fv-partner-id      PIC X(12).
           05 fv-cliente         PIC X(60).
           05 fv-cnpj            PIC X(18).
           05 fv-emissao         PIC X(10).
           05 fv-vencimento      PIC X(10).
           05 fv-subtotal        PIC S9(9)V99 COMP-3.
           05 fv-impostos        PIC S9(9)V99 COMP-3.
           05 fv-total           PIC S9(9)V99 COMP-3.
           05 fv-status          PIC X(12).
           05 fv-itens-count     PIC 9(3).
           05 fv-entrega-id      PIC X(24).
           05 fv-nfe-numero      PIC 9(9).
           05 fv-nfe-status      PIC X(12).

       FD temp-file.
       01 temp-reg.
           05 tr-id              PIC 9(5).
           05 tr-numero          PIC X(12).
           05 tr-pedido-id       PIC X(10).
           05 tr-pedido-num      PIC X(12).
           05 tr-partner-id      PIC X(12).
           05 tr-cliente         PIC X(60).
           05 tr-cnpj            PIC X(18).
           05 tr-emissao         PIC X(10).
           05 tr-vencimento      PIC X(10).
           05 tr-subtotal        PIC S9(9)V99 COMP-3.
           05 tr-impostos        PIC S9(9)V99 COMP-3.
           05 tr-total           PIC S9(9)V99 COMP-3.
           05 tr-status          PIC X(12).
           05 tr-itens-count     PIC 9(3).
           05 tr-entrega-id      PIC X(24).
           05 tr-nfe-numero      PIC 9(9).
           05 tr-nfe-status      PIC X(12).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-encontrou       PIC X(1).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-prox            PIC 9(5).
       01 ws-id              PIC 9(5).
       01 ws-id-in           PIC X(10).
       01 ws-numero          PIC X(12).
       01 ws-pedido-id       PIC X(10).
       01 ws-pedido-num      PIC X(12).
       01 ws-partner-id      PIC X(12).
       01 ws-cliente         PIC X(60).
       01 ws-cnpj            PIC X(18).
       01 ws-emissao         PIC X(10).
       01 ws-vencimento      PIC X(10).
       01 ws-sub-in          PIC X(20).
       01 ws-imp-in          PIC X(20).
       01 ws-tot-in          PIC X(20).
       01 ws-sub             PIC S9(9)V99 COMP-3.
       01 ws-imp             PIC S9(9)V99 COMP-3.
       01 ws-tot             PIC S9(9)V99 COMP-3.
       01 ws-status          PIC X(12).
       01 ws-itens-in        PIC X(5).
       01 ws-itens           PIC 9(3).
       01 ws-entrega-id      PIC X(24).
       01 ws-nfe-in          PIC X(12).
       01 ws-nfe-num         PIC 9(9).
       01 ws-nfe-status      PIC X(12).
       01 ws-id-ed           PIC ZZZZ9.
       01 ws-itens-ed        PIC ZZ9.
       01 ws-nfe-ed          PIC Z(8)9.
       01 ws-sub-ed          PIC -(8)9.99.
       01 ws-imp-ed          PIC -(8)9.99.
       01 ws-tot-ed          PIC -(8)9.99.
       01 ws-num-z           PIC 9(5).
       01 ws-json            PIC X(700).

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
           ACCEPT ws-numero FROM ENVIRONMENT "NUMERO"
           ACCEPT ws-pedido-id FROM ENVIRONMENT "PEDIDO_ID"
           ACCEPT ws-pedido-num FROM ENVIRONMENT "PEDIDO_NUM"
           ACCEPT ws-partner-id FROM ENVIRONMENT "PARTNER_ID"
           ACCEPT ws-cliente FROM ENVIRONMENT "CLIENTE"
           ACCEPT ws-cnpj FROM ENVIRONMENT "CNPJ"
           ACCEPT ws-emissao FROM ENVIRONMENT "EMISSAO"
           ACCEPT ws-vencimento FROM ENVIRONMENT "VENCIMENTO"
           ACCEPT ws-sub-in FROM ENVIRONMENT "SUBTOTAL"
           ACCEPT ws-imp-in FROM ENVIRONMENT "IMPOSTOS"
           ACCEPT ws-tot-in FROM ENVIRONMENT "TOTAL"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           ACCEPT ws-itens-in FROM ENVIRONMENT "ITENS_COUNT"
           ACCEPT ws-entrega-id FROM ENVIRONMENT "ENTREGA_ID"
           ACCEPT ws-nfe-in FROM ENVIRONMENT "NFE_NUMERO"
           ACCEPT ws-nfe-status FROM ENVIRONMENT "NFE_STATUS"
           COMPUTE ws-sub = FUNCTION NUMVAL(ws-sub-in)
           COMPUTE ws-imp = FUNCTION NUMVAL(ws-imp-in)
           COMPUTE ws-tot = FUNCTION NUMVAL(ws-tot-in)
           COMPUTE ws-itens = FUNCTION NUMVAL(ws-itens-in)
           COMPUTE ws-nfe-num = FUNCTION NUMVAL(ws-nfe-in)
           IF ws-status = SPACES THEN MOVE "PENDENTE" TO ws-status END-IF.

       proximo-id.
           MOVE 0 TO ws-prox
           OPEN INPUT fv-file
           IF ws-fs = "35" THEN
               MOVE 1 TO ws-prox
               EXIT PARAGRAPH
           END-IF
           PERFORM UNTIL 1 = 2
               READ fv-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fv-id > ws-prox THEN MOVE fv-id TO ws-prox END-IF
           END-PERFORM
           CLOSE fv-file
           ADD 1 TO ws-prox.

       move-ws-to-fv.
           MOVE ws-id TO fv-id
           MOVE ws-numero TO fv-numero
           MOVE ws-pedido-id TO fv-pedido-id
           MOVE ws-pedido-num TO fv-pedido-num
           MOVE ws-partner-id TO fv-partner-id
           MOVE ws-cliente TO fv-cliente
           MOVE ws-cnpj TO fv-cnpj
           MOVE ws-emissao TO fv-emissao
           MOVE ws-vencimento TO fv-vencimento
           MOVE ws-sub TO fv-subtotal
           MOVE ws-imp TO fv-impostos
           MOVE ws-tot TO fv-total
           MOVE ws-status TO fv-status
           MOVE ws-itens TO fv-itens-count
           MOVE ws-entrega-id TO fv-entrega-id
           MOVE ws-nfe-num TO fv-nfe-numero
           MOVE ws-nfe-status TO fv-nfe-status.

       incluir.
           PERFORM accept-fields
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           IF ws-id-in NOT = SPACES THEN
               COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ELSE
               PERFORM proximo-id
               MOVE ws-prox TO ws-id
           END-IF
           IF ws-numero = SPACES THEN
               MOVE ws-id TO ws-num-z
               STRING "FV" ws-num-z DELIMITED BY SIZE INTO ws-numero
           END-IF
           IF ws-tot <= 0 AND ws-sub > 0 THEN
               COMPUTE ws-tot = ws-sub + ws-imp
           END-IF
           OPEN INPUT fv-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT fv-file CLOSE fv-file
           ELSE CLOSE fv-file END-IF
           OPEN EXTEND fv-file
           PERFORM move-ws-to-fv
           WRITE fv-reg
           CLOSE fv-file
           MOVE ws-id TO ws-id-ed
           DISPLAY FUNCTION TRIM(ws-id-ed).

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           IF ws-id = 0 THEN
               DISPLAY "ERRO: id obrigatorio" STOP RUN END-IF
           PERFORM accept-fields
           OPEN INPUT fv-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: fatura nao encontrada" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ fv-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fv-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-numero NOT = SPACES THEN
                       MOVE ws-numero TO fv-numero END-IF
                   IF ws-pedido-id NOT = SPACES THEN
                       MOVE ws-pedido-id TO fv-pedido-id END-IF
                   IF ws-pedido-num NOT = SPACES THEN
                       MOVE ws-pedido-num TO fv-pedido-num END-IF
                   IF ws-partner-id NOT = SPACES THEN
                       MOVE ws-partner-id TO fv-partner-id END-IF
                   IF ws-cliente NOT = SPACES THEN
                       MOVE ws-cliente TO fv-cliente END-IF
                   IF ws-cnpj NOT = SPACES THEN
                       MOVE ws-cnpj TO fv-cnpj END-IF
                   IF ws-emissao NOT = SPACES THEN
                       MOVE ws-emissao TO fv-emissao END-IF
                   IF ws-vencimento NOT = SPACES THEN
                       MOVE ws-vencimento TO fv-vencimento END-IF
                   IF ws-sub-in NOT = SPACES THEN
                       MOVE ws-sub TO fv-subtotal END-IF
                   IF ws-imp-in NOT = SPACES THEN
                       MOVE ws-imp TO fv-impostos END-IF
                   IF ws-tot-in NOT = SPACES THEN
                       MOVE ws-tot TO fv-total END-IF
                   IF ws-status NOT = SPACES THEN
                       MOVE ws-status TO fv-status END-IF
                   IF ws-itens-in NOT = SPACES THEN
                       MOVE ws-itens TO fv-itens-count END-IF
                   IF ws-entrega-id NOT = SPACES THEN
                       MOVE ws-entrega-id TO fv-entrega-id END-IF
                   IF ws-nfe-in NOT = SPACES THEN
                       MOVE ws-nfe-num TO fv-nfe-numero END-IF
                   IF ws-nfe-status NOT = SPACES THEN
                       MOVE ws-nfe-status TO fv-nfe-status END-IF
               END-IF
               MOVE fv-reg TO temp-reg
               WRITE temp-reg
           END-PERFORM
           CLOSE fv-file CLOSE temp-file
           CALL "system" USING
               "mv dados/faturas_venda.tmp dados/faturas_venda.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: fatura nao encontrada".

       buscar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           OPEN INPUT fv-file
           IF ws-fs = "35" THEN
               DISPLAY '{"status":"erro"}' STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ fv-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fv-id = ws-id THEN
                   PERFORM emit-json
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE fv-file
           IF ws-encontrou = "N" THEN DISPLAY '{"status":"erro"}'.

       listar.
           OPEN INPUT fv-file
           IF ws-fs = "35" THEN
               DISPLAY '{"faturas":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"faturas":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ fv-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE fv-file.

       emit-json.
           MOVE fv-id TO ws-id-ed
           MOVE fv-itens-count TO ws-itens-ed
           MOVE fv-nfe-numero TO ws-nfe-ed
           MOVE fv-subtotal TO ws-sub-ed
           MOVE fv-impostos TO ws-imp-ed
           MOVE fv-total TO ws-tot-ed
           MOVE SPACES TO ws-json
           STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                  ',"numero":"' FUNCTION TRIM(fv-numero) '"'
                  ',"pedido_id":"' FUNCTION TRIM(fv-pedido-id) '"'
                  ',"pedido_numero":"' FUNCTION TRIM(fv-pedido-num) '"'
                  ',"partner_id":"' FUNCTION TRIM(fv-partner-id) '"'
                  ',"cliente":"' FUNCTION TRIM(fv-cliente) '"'
                  ',"cnpj":"' FUNCTION TRIM(fv-cnpj) '"'
                  ',"data_emissao":"' FUNCTION TRIM(fv-emissao) '"'
                  ',"data_vencimento":"' FUNCTION TRIM(fv-vencimento) '"'
                  ',"subtotal":' FUNCTION TRIM(ws-sub-ed)
                  ',"impostos":' FUNCTION TRIM(ws-imp-ed)
                  ',"total":' FUNCTION TRIM(ws-tot-ed)
                  ',"status":"' FUNCTION TRIM(fv-status) '"'
                  ',"itens_count":' FUNCTION TRIM(ws-itens-ed)
                  ',"entrega_id":"' FUNCTION TRIM(fv-entrega-id) '"'
                  ',"nfe_numero":' FUNCTION TRIM(ws-nfe-ed)
                  ',"nfe_status":"' FUNCTION TRIM(fv-nfe-status) '"}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
