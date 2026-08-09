       >>SOURCE FORMAT IS FREE
       *> gerir_pedidos_b2b.cbl — cabeçalho pedido/cotação B2B (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirPedidosB2b.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ped-file ASSIGN TO "dados/pedidos_b2b.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/pedidos_b2b.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD ped-file.
       01 ped-reg.
           05 pd-id              PIC 9(6).
           05 pd-numero          PIC X(12).
           05 pd-tipo            PIC X(10).
           05 pd-status          PIC X(12).
           05 pd-data            PIC X(10).
           05 pd-validade        PIC X(10).
           05 pd-cliente-id      PIC X(12).
           05 pd-razao           PIC X(60).
           05 pd-cnpj            PIC X(18).
           05 pd-ie              PIC X(20).
           05 pd-cidade          PIC X(30).
           05 pd-uf              PIC X(2).
           05 pd-end-cob         PIC X(80).
           05 pd-end-ent         PIC X(80).
           05 pd-lista           PIC X(40).
           05 pd-lista-id        PIC X(20).
           05 pd-vendedor        PIC X(30).
           05 pd-terms           PIC X(20).
           05 pd-forma-pg        PIC X(20).
           05 pd-total           PIC S9(11)V99 COMP-3.
           05 pd-fatura-id       PIC X(10).
           05 pd-fatura-num      PIC X(12).
           05 pd-nfe-num         PIC 9(9).
           05 pd-nfe-status      PIC X(12).
           05 pd-entrega-id      PIC X(24).
           05 pd-reserva-id      PIC X(16).
           05 pd-smart-ent       PIC 9(3).
           05 pd-smart-fat       PIC 9(3).
           05 pd-notas           PIC X(80).

       FD temp-file.
       01 temp-reg.
           05 td-id              PIC 9(6).
           05 td-numero          PIC X(12).
           05 td-tipo            PIC X(10).
           05 td-status          PIC X(12).
           05 td-data            PIC X(10).
           05 td-validade        PIC X(10).
           05 td-cliente-id      PIC X(12).
           05 td-razao           PIC X(60).
           05 td-cnpj            PIC X(18).
           05 td-ie              PIC X(20).
           05 td-cidade          PIC X(30).
           05 td-uf              PIC X(2).
           05 td-end-cob         PIC X(80).
           05 td-end-ent         PIC X(80).
           05 td-lista           PIC X(40).
           05 td-lista-id        PIC X(20).
           05 td-vendedor        PIC X(30).
           05 td-terms           PIC X(20).
           05 td-forma-pg        PIC X(20).
           05 td-total           PIC S9(11)V99 COMP-3.
           05 td-fatura-id       PIC X(10).
           05 td-fatura-num      PIC X(12).
           05 td-nfe-num         PIC 9(9).
           05 td-nfe-status      PIC X(12).
           05 td-entrega-id      PIC X(24).
           05 td-reserva-id      PIC X(16).
           05 td-smart-ent       PIC 9(3).
           05 td-smart-fat       PIC 9(3).
           05 td-notas           PIC X(80).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-encontrou       PIC X(1).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-id              PIC 9(6).
       01 ws-id-in           PIC X(10).
       01 ws-prox            PIC 9(6).
       01 ws-id-ed           PIC ZZZZZ9.
       01 ws-id-z            PIC 9(5).

       01 ws-nfe-ed          PIC ZZZZZZZZ9.
       01 ws-smart-ed        PIC ZZ9.
       01 ws-smart2-ed       PIC ZZ9.
       01 ws-total-val       PIC S9(11)V99 COMP-3.
       01 ws-total-ed2       PIC -(10)9.99.
       01 ws-json            PIC X(2000).
       01 ws-numero          PIC X(12).
       01 ws-tipo            PIC X(10).
       01 ws-status          PIC X(12).
       01 ws-data            PIC X(10).
       01 ws-validade        PIC X(10).
       01 ws-cliente-id      PIC X(12).
       01 ws-razao           PIC X(60).
       01 ws-cnpj            PIC X(18).
       01 ws-ie              PIC X(20).
       01 ws-cidade          PIC X(30).
       01 ws-uf              PIC X(2).
       01 ws-end-cob         PIC X(80).
       01 ws-end-ent         PIC X(80).
       01 ws-lista           PIC X(40).
       01 ws-lista-id        PIC X(20).
       01 ws-vendedor        PIC X(30).
       01 ws-terms           PIC X(20).
       01 ws-forma-pg        PIC X(20).
       01 ws-total-in        PIC X(20).
       01 ws-fatura-id       PIC X(10).
       01 ws-fatura-num      PIC X(12).
       01 ws-nfe-in          PIC X(12).
       01 ws-nfe-status      PIC X(12).
       01 ws-entrega-id      PIC X(24).
       01 ws-reserva-id      PIC X(16).
       01 ws-smart-ent-in    PIC X(5).
       01 ws-smart-fat-in    PIC X(5).
       01 ws-notas           PIC X(80).
       01 ws-nfe-num         PIC 9(9).
       01 ws-smart-ent       PIC 9(3).
       01 ws-smart-fat       PIC 9(3).

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
           ACCEPT ws-numero FROM ENVIRONMENT "NUMERO"
           ACCEPT ws-tipo FROM ENVIRONMENT "TIPO"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           ACCEPT ws-data FROM ENVIRONMENT "DATA"
           ACCEPT ws-validade FROM ENVIRONMENT "VALIDADE"
           ACCEPT ws-cliente-id FROM ENVIRONMENT "CLIENTE_ID"
           ACCEPT ws-razao FROM ENVIRONMENT "RAZAO_SOCIAL"
           ACCEPT ws-cnpj FROM ENVIRONMENT "CNPJ"
           ACCEPT ws-ie FROM ENVIRONMENT "IE"
           ACCEPT ws-cidade FROM ENVIRONMENT "CIDADE"
           ACCEPT ws-uf FROM ENVIRONMENT "UF"
           ACCEPT ws-end-cob FROM ENVIRONMENT "ENDERECO_COBRANCA"
           ACCEPT ws-end-ent FROM ENVIRONMENT "ENDERECO_ENTREGA"
           ACCEPT ws-lista FROM ENVIRONMENT "LISTA_PRECOS"
           ACCEPT ws-lista-id FROM ENVIRONMENT "LISTA_PRECOS_ID"
           ACCEPT ws-vendedor FROM ENVIRONMENT "VENDEDOR"
           ACCEPT ws-terms FROM ENVIRONMENT "PAYMENT_TERMS"
           ACCEPT ws-forma-pg FROM ENVIRONMENT "FORMA_PG"
           ACCEPT ws-total-in FROM ENVIRONMENT "TOTAL"
           ACCEPT ws-fatura-id FROM ENVIRONMENT "FATURA_ID"
           ACCEPT ws-fatura-num FROM ENVIRONMENT "FATURA_NUMERO"
           ACCEPT ws-nfe-in FROM ENVIRONMENT "NFE_NUMERO"
           ACCEPT ws-nfe-status FROM ENVIRONMENT "NFE_STATUS"
           ACCEPT ws-entrega-id FROM ENVIRONMENT "ENTREGA_ID"
           ACCEPT ws-reserva-id FROM ENVIRONMENT "RESERVA_ID"
           ACCEPT ws-smart-ent-in FROM ENVIRONMENT "SMART_ENTREGAS"
           ACCEPT ws-smart-fat-in FROM ENVIRONMENT "SMART_FATURAS"
           ACCEPT ws-notas FROM ENVIRONMENT "NOTAS"
           COMPUTE ws-total-val = FUNCTION NUMVAL(ws-total-in)
           COMPUTE ws-nfe-num = FUNCTION NUMVAL(ws-nfe-in)
           COMPUTE ws-smart-ent = FUNCTION NUMVAL(ws-smart-ent-in)
           COMPUTE ws-smart-fat = FUNCTION NUMVAL(ws-smart-fat-in)
           IF ws-tipo = SPACES THEN MOVE "pedido" TO ws-tipo END-IF
           IF ws-status = SPACES THEN MOVE "rascunho" TO ws-status END-IF.

       move-ws-to-ped.
           MOVE ws-id TO pd-id
           MOVE ws-numero TO pd-numero
           MOVE ws-tipo TO pd-tipo
           MOVE ws-status TO pd-status
           MOVE ws-data TO pd-data
           MOVE ws-validade TO pd-validade
           MOVE ws-cliente-id TO pd-cliente-id
           MOVE ws-razao TO pd-razao
           MOVE ws-cnpj TO pd-cnpj
           MOVE ws-ie TO pd-ie
           MOVE ws-cidade TO pd-cidade
           MOVE ws-uf TO pd-uf
           MOVE ws-end-cob TO pd-end-cob
           MOVE ws-end-ent TO pd-end-ent
           MOVE ws-lista TO pd-lista
           MOVE ws-lista-id TO pd-lista-id
           MOVE ws-vendedor TO pd-vendedor
           MOVE ws-terms TO pd-terms
           MOVE ws-forma-pg TO pd-forma-pg
           MOVE ws-total-val TO pd-total
           MOVE ws-fatura-id TO pd-fatura-id
           MOVE ws-fatura-num TO pd-fatura-num
           MOVE ws-nfe-num TO pd-nfe-num
           MOVE ws-nfe-status TO pd-nfe-status
           MOVE ws-entrega-id TO pd-entrega-id
           MOVE ws-reserva-id TO pd-reserva-id
           MOVE ws-smart-ent TO pd-smart-ent
           MOVE ws-smart-fat TO pd-smart-fat
           MOVE ws-notas TO pd-notas.

       proximo-id.
           MOVE 1000 TO ws-prox
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               EXIT PARAGRAPH
           END-IF
           PERFORM UNTIL 1 = 2
               READ ped-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pd-id > ws-prox THEN MOVE pd-id TO ws-prox END-IF
           END-PERFORM
           CLOSE ped-file
           ADD 1 TO ws-prox.

       incluir.
           PERFORM accept-fields
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           IF ws-id-in = SPACES THEN
               PERFORM proximo-id
               MOVE ws-prox TO ws-id
           ELSE
               COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           END-IF
           IF ws-numero = SPACES THEN
               MOVE ws-id TO ws-id-z
               IF ws-tipo = "cotacao" THEN
                   STRING "S" ws-id-z DELIMITED BY SIZE INTO ws-numero
               ELSE
                   STRING "PV" ws-id-z DELIMITED BY SIZE INTO ws-numero
               END-IF
           END-IF
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT ped-file CLOSE ped-file
           ELSE
               CLOSE ped-file
           END-IF
           OPEN EXTEND ped-file
           PERFORM move-ws-to-ped
           WRITE ped-reg
           CLOSE ped-file
           MOVE ws-id TO ws-id-ed
           DISPLAY FUNCTION TRIM(ws-id-ed).

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           IF ws-id = 0 THEN
               DISPLAY "ERRO: id obrigatorio" STOP RUN END-IF
           PERFORM accept-fields
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ped-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pd-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   PERFORM move-ws-to-ped
                   MOVE ped-reg TO temp-reg
                   WRITE temp-reg
               ELSE
                   MOVE ped-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE ped-file CLOSE temp-file
           CALL "system" USING
               "mv dados/pedidos_b2b.tmp dados/pedidos_b2b.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: pedido nao encontrado".

       excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ped-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pd-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
               ELSE
                   MOVE ped-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE ped-file CLOSE temp-file
           CALL "system" USING
               "mv dados/pedidos_b2b.tmp dados/pedidos_b2b.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: pedido nao encontrado".

       buscar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               DISPLAY '{"status":"erro"}' STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ ped-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pd-id = ws-id THEN
                   PERFORM emit-json
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE ped-file
           IF ws-encontrou = "N" THEN DISPLAY '{"status":"erro"}'.

       listar.
           OPEN INPUT ped-file
           IF ws-fs = "35" THEN
               DISPLAY '{"pedidos":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"pedidos":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ ped-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE ped-file.

       emit-json.
           MOVE pd-id TO ws-id-ed
           MOVE pd-total TO ws-total-ed2
           MOVE pd-nfe-num TO ws-nfe-ed
           MOVE pd-smart-ent TO ws-smart-ed
           MOVE pd-smart-fat TO ws-smart2-ed
           MOVE SPACES TO ws-json
           STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                  ',"numero":"' FUNCTION TRIM(pd-numero) '"'
                  ',"tipo":"' FUNCTION TRIM(pd-tipo) '"'
                  ',"status":"' FUNCTION TRIM(pd-status) '"'
                  ',"data":"' FUNCTION TRIM(pd-data) '"'
                  ',"validade":"' FUNCTION TRIM(pd-validade) '"'
                  ',"cliente_id":"' FUNCTION TRIM(pd-cliente-id) '"'
                  ',"razao_social":"' FUNCTION TRIM(pd-razao) '"'
                  ',"cnpj":"' FUNCTION TRIM(pd-cnpj) '"'
                  ',"ie":"' FUNCTION TRIM(pd-ie) '"'
                  ',"cidade":"' FUNCTION TRIM(pd-cidade) '"'
                  ',"uf":"' FUNCTION TRIM(pd-uf) '"'
                  ',"endereco_cobranca":"' FUNCTION TRIM(pd-end-cob) '"'
                  ',"endereco_entrega":"' FUNCTION TRIM(pd-end-ent) '"'
                  ',"lista_precos":"' FUNCTION TRIM(pd-lista) '"'
                  ',"lista_precos_id":"' FUNCTION TRIM(pd-lista-id) '"'
                  ',"vendedor":"' FUNCTION TRIM(pd-vendedor) '"'
                  ',"payment_terms":"' FUNCTION TRIM(pd-terms) '"'
                  ',"forma_pg":"' FUNCTION TRIM(pd-forma-pg) '"'
                  ',"total":' FUNCTION TRIM(ws-total-ed2)
                  ',"fatura_id":"' FUNCTION TRIM(pd-fatura-id) '"'
                  ',"fatura_numero":"' FUNCTION TRIM(pd-fatura-num) '"'
                  ',"nfe_numero":' FUNCTION TRIM(ws-nfe-ed)
                  ',"nfe_status":"' FUNCTION TRIM(pd-nfe-status) '"'
                  ',"entrega_id":"' FUNCTION TRIM(pd-entrega-id) '"'
                  ',"reserva_id":"' FUNCTION TRIM(pd-reserva-id) '"'
                  ',"smart":{"entregas":' FUNCTION TRIM(ws-smart-ed)
                  ',"faturas":' FUNCTION TRIM(ws-smart2-ed) '}'
                  ',"notas":"' FUNCTION TRIM(pd-notas) '"}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
