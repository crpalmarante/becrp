       >>SOURCE FORMAT IS FREE
       *> cadastrar_produto.cbl — CRUD produtos (fonte da verdade)
       *> ORGANIZATION SEQUENTIAL: registro fixo; COMP-3 em valores.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CadastrarProduto.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT prod-file ASSIGN TO "dados/produtos.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/produtos.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD prod-file.
       01 prod-reg.
           05 pr-id              PIC 9(6).
           05 pr-nome            PIC X(50).
           05 pr-preco           PIC S9(7)V99 COMP-3.
           05 pr-preco-custo     PIC S9(7)V99 COMP-3.
           05 pr-stock           PIC S9(6) COMP-3.
           05 pr-margem          PIC S9(3)V99 COMP-3.
           05 pr-ativo           PIC X(1).
           05 pr-codigo-barras   PIC X(14).
           05 pr-categoria       PIC X(20).
           05 pr-sub-categoria   PIC X(20).
           05 pr-unidade         PIC X(4).
           05 pr-ncm             PIC X(8).
           05 pr-fornecedor      PIC X(30).
           05 pr-localizacao     PIC X(15).
           05 pr-filial-id       PIC 9(3).
           05 pr-cst             PIC X(3).
           05 pr-cfop            PIC X(4).
           05 pr-icms-alq        PIC S9(3)V99 COMP-3.
           05 pr-servico         PIC X(1).
           05 pr-iss-alq         PIC S9(3)V99 COMP-3.
           05 pr-cod-serv-mun    PIC X(20).

       FD temp-file.
       01 temp-reg.
           05 tr-id              PIC 9(6).
           05 tr-nome            PIC X(50).
           05 tr-preco           PIC S9(7)V99 COMP-3.
           05 tr-preco-custo     PIC S9(7)V99 COMP-3.
           05 tr-stock           PIC S9(6) COMP-3.
           05 tr-margem          PIC S9(3)V99 COMP-3.
           05 tr-ativo           PIC X(1).
           05 tr-codigo-barras   PIC X(14).
           05 tr-categoria       PIC X(20).
           05 tr-sub-categoria   PIC X(20).
           05 tr-unidade         PIC X(4).
           05 tr-ncm             PIC X(8).
           05 tr-fornecedor      PIC X(30).
           05 tr-localizacao     PIC X(15).
           05 tr-filial-id       PIC 9(3).
           05 tr-cst             PIC X(3).
           05 tr-cfop            PIC X(4).
           05 tr-icms-alq        PIC S9(3)V99 COMP-3.
           05 tr-servico         PIC X(1).
           05 tr-iss-alq         PIC S9(3)V99 COMP-3.
           05 tr-cod-serv-mun    PIC X(20).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-encontrou       PIC X(1).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-prox-id         PIC 9(6).
       01 ws-id              PIC 9(6).
       01 ws-id-in           PIC X(10).
       01 ws-nome            PIC X(50).
       01 ws-preco           PIC S9(7)V99 COMP-3.
       01 ws-preco-custo     PIC S9(7)V99 COMP-3.
       01 ws-stock           PIC S9(6) COMP-3.
       01 ws-margem          PIC S9(3)V99 COMP-3.
       01 ws-ativo           PIC X(1).
       01 ws-codigo-barras   PIC X(14).
       01 ws-categoria       PIC X(20).
       01 ws-sub-categoria   PIC X(20).
       01 ws-unidade         PIC X(4).
       01 ws-ncm             PIC X(8).
       01 ws-fornecedor      PIC X(30).
       01 ws-localizacao     PIC X(15).
       01 ws-filial-id       PIC 9(3).
       01 ws-cst             PIC X(3).
       01 ws-cfop            PIC X(4).
       01 ws-icms-alq        PIC S9(3)V99 COMP-3.
       01 ws-servico         PIC X(1).
       01 ws-iss-alq         PIC S9(3)V99 COMP-3.
       01 ws-cod-serv-mun    PIC X(20).
       01 ws-preco-in        PIC X(15).
       01 ws-custo-in        PIC X(15).
       01 ws-stock-in        PIC X(10).
       01 ws-margem-in       PIC X(10).
       01 ws-filial-in       PIC X(5).
       01 ws-icms-in         PIC X(10).
       01 ws-iss-in          PIC X(10).
       01 ws-id-ed           PIC ZZZZZ9.
       01 ws-stock-ed        PIC -(5)9.
       01 ws-preco-ed        PIC -(6)9.99.
       01 ws-custo-ed        PIC -(6)9.99.
       01 ws-margem-ed       PIC -(2)9.99.
       01 ws-filial-ed       PIC ZZ9.
       01 ws-icms-ed         PIC -(2)9.99.
       01 ws-iss-ed          PIC -(2)9.99.
       01 ws-json            PIC X(800).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF
           EVALUATE ws-acao
               WHEN "incluir"  PERFORM incluir
               WHEN "alterar"  PERFORM alterar
               WHEN "excluir"  PERFORM excluir
               WHEN "listar"   PERFORM listar
               WHEN OTHER      DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       accept-fields.
           ACCEPT ws-nome FROM ENVIRONMENT "NOME"
           ACCEPT ws-preco-in FROM ENVIRONMENT "PRECO"
           ACCEPT ws-custo-in FROM ENVIRONMENT "PRECO_CUSTO"
           ACCEPT ws-stock-in FROM ENVIRONMENT "STOCK"
           ACCEPT ws-margem-in FROM ENVIRONMENT "MARGEM"
           ACCEPT ws-ativo FROM ENVIRONMENT "ATIVO"
           ACCEPT ws-codigo-barras FROM ENVIRONMENT "CODIGO_BARRAS"
           ACCEPT ws-categoria FROM ENVIRONMENT "CATEGORIA"
           ACCEPT ws-sub-categoria FROM ENVIRONMENT "SUB_CATEGORIA"
           ACCEPT ws-unidade FROM ENVIRONMENT "UNIDADE"
           ACCEPT ws-ncm FROM ENVIRONMENT "NCM"
           ACCEPT ws-fornecedor FROM ENVIRONMENT "FORNECEDOR"
           ACCEPT ws-localizacao FROM ENVIRONMENT "LOCALIZACAO"
           ACCEPT ws-filial-in FROM ENVIRONMENT "FILIAL_ID"
           ACCEPT ws-cst FROM ENVIRONMENT "CST"
           ACCEPT ws-cfop FROM ENVIRONMENT "CFOP"
           ACCEPT ws-icms-in FROM ENVIRONMENT "ICMS_ALQ"
           ACCEPT ws-servico FROM ENVIRONMENT "SERVICO"
           ACCEPT ws-iss-in FROM ENVIRONMENT "ISS_ALQ"
           ACCEPT ws-cod-serv-mun FROM ENVIRONMENT "COD_SERV_MUN"
           IF ws-preco-in NOT = SPACES THEN
               COMPUTE ws-preco = FUNCTION NUMVAL(ws-preco-in) END-IF
           IF ws-custo-in NOT = SPACES THEN
               COMPUTE ws-preco-custo = FUNCTION NUMVAL(ws-custo-in) END-IF
           IF ws-stock-in NOT = SPACES THEN
               COMPUTE ws-stock = FUNCTION NUMVAL(ws-stock-in) END-IF
           IF ws-margem-in NOT = SPACES THEN
               COMPUTE ws-margem = FUNCTION NUMVAL(ws-margem-in) END-IF
           IF ws-filial-in NOT = SPACES THEN
               COMPUTE ws-filial-id = FUNCTION NUMVAL(ws-filial-in)
           ELSE
               MOVE 0 TO ws-filial-id
           END-IF
           IF ws-icms-in NOT = SPACES THEN
               COMPUTE ws-icms-alq = FUNCTION NUMVAL(ws-icms-in) END-IF
           IF ws-iss-in NOT = SPACES THEN
               COMPUTE ws-iss-alq = FUNCTION NUMVAL(ws-iss-in) END-IF.

       ensure-file.
           OPEN INPUT prod-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT prod-file
               CLOSE prod-file
           ELSE
               CLOSE prod-file
           END-IF.

       proximo-id.
           MOVE 0 TO ws-prox-id
           OPEN INPUT prod-file
           IF ws-fs = "35" THEN
               MOVE 1 TO ws-prox-id
               EXIT PARAGRAPH
           END-IF
           PERFORM UNTIL 1 = 2
               READ prod-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pr-id > ws-prox-id THEN MOVE pr-id TO ws-prox-id END-IF
           END-PERFORM
           CLOSE prod-file
           ADD 1 TO ws-prox-id.

       move-ws-to-pr.
           MOVE ws-id TO pr-id
           MOVE ws-nome TO pr-nome
           MOVE ws-preco TO pr-preco
           MOVE ws-preco-custo TO pr-preco-custo
           MOVE ws-stock TO pr-stock
           MOVE ws-margem TO pr-margem
           MOVE ws-ativo TO pr-ativo
           MOVE ws-codigo-barras TO pr-codigo-barras
           MOVE ws-categoria TO pr-categoria
           MOVE ws-sub-categoria TO pr-sub-categoria
           MOVE ws-unidade TO pr-unidade
           MOVE ws-ncm TO pr-ncm
           MOVE ws-fornecedor TO pr-fornecedor
           MOVE ws-localizacao TO pr-localizacao
           MOVE ws-filial-id TO pr-filial-id
           MOVE ws-cst TO pr-cst
           MOVE ws-cfop TO pr-cfop
           MOVE ws-icms-alq TO pr-icms-alq
           MOVE ws-servico TO pr-servico
           MOVE ws-iss-alq TO pr-iss-alq
           MOVE ws-cod-serv-mun TO pr-cod-serv-mun.

       incluir.
           PERFORM accept-fields
           IF ws-nome = SPACES THEN
               DISPLAY "ERRO: nome obrigatorio" STOP RUN END-IF
           IF ws-categoria = SPACES THEN
               DISPLAY "ERRO: categoria obrigatoria" STOP RUN END-IF
           IF ws-sub-categoria = SPACES THEN
               MOVE ws-categoria TO ws-sub-categoria END-IF
           IF ws-ativo = SPACES THEN MOVE "S" TO ws-ativo END-IF
           IF ws-servico = SPACES THEN MOVE "N" TO ws-servico END-IF
           IF ws-unidade = SPACES THEN MOVE "UN" TO ws-unidade END-IF
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           IF ws-id-in NOT = SPACES THEN
               COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ELSE
               PERFORM proximo-id
               MOVE ws-prox-id TO ws-id
           END-IF
           PERFORM ensure-file
           OPEN EXTEND prod-file
           PERFORM move-ws-to-pr
           WRITE prod-reg
           CLOSE prod-file
           MOVE ws-id TO ws-id-ed
           DISPLAY FUNCTION TRIM(ws-id-ed).

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           IF ws-id = 0 THEN
               DISPLAY "ERRO: id obrigatorio" STOP RUN END-IF
           PERFORM accept-fields
           OPEN INPUT prod-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: produto nao encontrado" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ prod-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pr-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-nome NOT = SPACES THEN
                       MOVE ws-nome TO pr-nome END-IF
                   IF ws-preco-in NOT = SPACES THEN
                       MOVE ws-preco TO pr-preco END-IF
                   IF ws-custo-in NOT = SPACES THEN
                       MOVE ws-preco-custo TO pr-preco-custo END-IF
                   IF ws-stock-in NOT = SPACES THEN
                       MOVE ws-stock TO pr-stock END-IF
                   IF ws-margem-in NOT = SPACES THEN
                       MOVE ws-margem TO pr-margem END-IF
                   IF ws-ativo NOT = SPACES THEN
                       MOVE ws-ativo TO pr-ativo END-IF
                   IF ws-codigo-barras NOT = SPACES THEN
                       MOVE ws-codigo-barras TO pr-codigo-barras END-IF
                   IF ws-categoria NOT = SPACES THEN
                       MOVE ws-categoria TO pr-categoria END-IF
                   IF ws-sub-categoria NOT = SPACES THEN
                       MOVE ws-sub-categoria TO pr-sub-categoria END-IF
                   IF ws-unidade NOT = SPACES THEN
                       MOVE ws-unidade TO pr-unidade END-IF
                   IF ws-ncm NOT = SPACES THEN
                       MOVE ws-ncm TO pr-ncm END-IF
                   IF ws-fornecedor NOT = SPACES THEN
                       MOVE ws-fornecedor TO pr-fornecedor END-IF
                   IF ws-localizacao NOT = SPACES THEN
                       MOVE ws-localizacao TO pr-localizacao END-IF
                   IF ws-filial-in NOT = SPACES THEN
                       MOVE ws-filial-id TO pr-filial-id END-IF
                   IF ws-cst NOT = SPACES THEN
                       MOVE ws-cst TO pr-cst END-IF
                   IF ws-cfop NOT = SPACES THEN
                       MOVE ws-cfop TO pr-cfop END-IF
                   IF ws-icms-in NOT = SPACES THEN
                       MOVE ws-icms-alq TO pr-icms-alq END-IF
                   IF ws-servico NOT = SPACES THEN
                       MOVE ws-servico TO pr-servico END-IF
                   IF ws-iss-in NOT = SPACES THEN
                       MOVE ws-iss-alq TO pr-iss-alq END-IF
                   IF ws-cod-serv-mun NOT = SPACES THEN
                       MOVE ws-cod-serv-mun TO pr-cod-serv-mun END-IF
               END-IF
               MOVE prod-reg TO temp-reg
               WRITE temp-reg
           END-PERFORM
           CLOSE prod-file CLOSE temp-file
           CALL "system" USING "mv dados/produtos.tmp dados/produtos.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: produto nao encontrado".

       excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           OPEN INPUT prod-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: produto nao encontrado" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ prod-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pr-id NOT = ws-id THEN
                   MOVE prod-reg TO temp-reg
                   WRITE temp-reg
               ELSE
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE prod-file CLOSE temp-file
           CALL "system" USING "mv dados/produtos.tmp dados/produtos.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: produto nao encontrado".

       listar.
           OPEN INPUT prod-file
           IF ws-fs = "35" THEN
               DISPLAY '{"produtos":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"produtos":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ prod-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF pr-ativo = "S" THEN
                   ADD 1 TO ws-total
                   IF ws-first = "S" THEN MOVE "N" TO ws-first
                   ELSE DISPLAY "," END-IF
                   PERFORM emit-json
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE prod-file.

       emit-json.
           MOVE pr-id TO ws-id-ed
           MOVE pr-preco TO ws-preco-ed
           MOVE pr-preco-custo TO ws-custo-ed
           MOVE pr-stock TO ws-stock-ed
           MOVE pr-margem TO ws-margem-ed
           MOVE pr-filial-id TO ws-filial-ed
           MOVE pr-icms-alq TO ws-icms-ed
           MOVE pr-iss-alq TO ws-iss-ed
           MOVE SPACES TO ws-json
           STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                  ',"nome":"' FUNCTION TRIM(pr-nome) '"'
                  ',"preco":' FUNCTION TRIM(ws-preco-ed)
                  ',"preco_custo":' FUNCTION TRIM(ws-custo-ed)
                  ',"stock":' FUNCTION TRIM(ws-stock-ed)
                  ',"margem":' FUNCTION TRIM(ws-margem-ed)
                  ',"codigo_barras":"' FUNCTION TRIM(pr-codigo-barras) '"'
                  ',"categoria":"' FUNCTION TRIM(pr-categoria) '"'
                  ',"sub_categoria":"' FUNCTION TRIM(pr-sub-categoria) '"'
                  ',"unidade":"' FUNCTION TRIM(pr-unidade) '"'
                  ',"ncm":"' FUNCTION TRIM(pr-ncm) '"'
                  ',"fornecedor":"' FUNCTION TRIM(pr-fornecedor) '"'
                  ',"localizacao":"' FUNCTION TRIM(pr-localizacao) '"'
                  ',"filial_id":' FUNCTION TRIM(ws-filial-ed)
                  ',"cst":"' FUNCTION TRIM(pr-cst) '"'
                  ',"cfop":"' FUNCTION TRIM(pr-cfop) '"'
                  ',"icms_alq":' FUNCTION TRIM(ws-icms-ed)
                  ',"servico":"' FUNCTION TRIM(pr-servico) '"'
                  ',"iss_alq":' FUNCTION TRIM(ws-iss-ed)
                  ',"cod_serv_mun":"' FUNCTION TRIM(pr-cod-serv-mun) '"'
                  '}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
