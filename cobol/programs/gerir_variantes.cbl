       >>SOURCE FORMAT IS FREE
       *> gerir_variantes.cbl - CRUD de variantes de produtos
       *> Fonte da verdade: dados/variantes.dat (registro fixo).
       *> Ações: incluir | alterar | excluir | listar
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirVariantes.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT vt-file ASSIGN TO "dados/variantes.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/variantes.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-file-status.

       DATA DIVISION.
       FILE SECTION.
       FD vt-file.
       01 vt-reg.
           05 vt-id           PIC 9(6).
           05 vt-produto-id   PIC 9(6).
           05 vt-nome         PIC X(60).
           05 vt-atributos    PIC X(120).
           05 vt-codigo       PIC X(20).
           05 vt-preco        PIC 9(8)V99.
           05 vt-ativo        PIC X.

       FD temp-file.
       01 temp-reg.
           05 tl-id           PIC 9(6).
           05 tl-produto-id   PIC 9(6).
           05 tl-nome         PIC X(60).
           05 tl-atributos    PIC X(120).
           05 tl-codigo       PIC X(20).
           05 tl-preco        PIC 9(8)V99.
           05 tl-ativo        PIC X.

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-file-status     PIC X(2).
       01 ws-existe          PIC X(1).
       01 ws-encontrou       PIC X(1).
       01 ws-json-linha      PIC X(900).
       01 ws-id-ed           PIC Z(6)9.
       01 ws-prod-id-ed      PIC Z(6)9.
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-id              PIC 9(6).
       01 ws-id-in           PIC X(10).
       01 ws-produto-id-in   PIC X(10).
       01 ws-produto-id      PIC 9(6).
       01 ws-nome            PIC X(60).
       01 ws-atributos       PIC X(120).
       01 ws-codigo          PIC X(20).
       01 ws-preco-in        PIC X(15).
       01 ws-preco           PIC 9(8)V99.
       01 ws-preco-ed        PIC Z(8)9.99.
       01 ws-ativo           PIC X(1).
       01 ws-clear-codigo    PIC X(1).
       01 ws-clear-atributos PIC X(1).
       01 ws-prox-id         PIC 9(6).
       01 ws-nome-cmp        PIC X(60).
       01 ws-nome-arq        PIC X(60).
       01 ws-nome-arq-cmp    PIC X(60).
       01 ws-i               PIC 9(3).
       01 ws-duplicado       PIC X(1).

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

       ensure-file.
           OPEN INPUT vt-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT vt-file
               CLOSE vt-file
           ELSE
               CLOSE vt-file
           END-IF.

       *> Normaliza nome: remove espacos e deixa minusculo para comparar
       normalizar.
           MOVE SPACES TO ws-nome-cmp
           PERFORM VARYING ws-i FROM 1 BY 1 UNTIL ws-i > 60
               IF ws-nome(ws-i:1) NOT = SPACE
                   STRING ws-nome-cmp DELIMITED BY SPACES
                          ws-nome(ws-i:1) DELIMITED BY SIZE
                          INTO ws-nome-cmp
               END-IF
           END-PERFORM
           PERFORM VARYING ws-i FROM 1 BY 1 UNTIL ws-i > 60
               IF ws-nome-cmp(ws-i:1) >= "A" AND <= "Z"
                   MOVE FUNCTION LOWER-CASE(ws-nome-cmp(ws-i:1))
                     TO ws-nome-cmp(ws-i:1)
               END-IF
           END-PERFORM.

       normalizar-arq.
           MOVE SPACES TO ws-nome-arq-cmp
           PERFORM VARYING ws-i FROM 1 BY 1 UNTIL ws-i > 60
               IF ws-nome-arq(ws-i:1) NOT = SPACE
                   STRING ws-nome-arq-cmp DELIMITED BY SPACES
                          ws-nome-arq(ws-i:1) DELIMITED BY SIZE
                          INTO ws-nome-arq-cmp
               END-IF
           END-PERFORM
           PERFORM VARYING ws-i FROM 1 BY 1 UNTIL ws-i > 60
               IF ws-nome-arq-cmp(ws-i:1) >= "A" AND <= "Z"
                   MOVE FUNCTION LOWER-CASE(ws-nome-arq-cmp(ws-i:1))
                     TO ws-nome-arq-cmp(ws-i:1)
               END-IF
           END-PERFORM.

       incluir.
           ACCEPT ws-produto-id-in FROM ENVIRONMENT "PRODUTO_ID"
           ACCEPT ws-nome FROM ENVIRONMENT "NOME"
           ACCEPT ws-atributos FROM ENVIRONMENT "ATRIBUTOS"
           ACCEPT ws-codigo FROM ENVIRONMENT "CODIGO"
           ACCEPT ws-preco-in FROM ENVIRONMENT "PRECO"
           ACCEPT ws-ativo FROM ENVIRONMENT "ATIVO"
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           IF ws-produto-id-in = SPACES THEN
               DISPLAY "ERRO: produto obrigatorio" STOP RUN END-IF
           IF ws-nome = SPACES THEN
               DISPLAY "ERRO: nome obrigatorio" STOP RUN END-IF
           COMPUTE ws-produto-id = FUNCTION NUMVAL(ws-produto-id-in)
           IF ws-preco-in = SPACES THEN
               MOVE 0 TO ws-preco
           ELSE
               COMPUTE ws-preco = FUNCTION NUMVAL(ws-preco-in)
           END-IF
           IF ws-ativo = SPACES THEN MOVE "S" TO ws-ativo END-IF

           PERFORM normalizar
           MOVE "N" TO ws-duplicado
           OPEN INPUT vt-file
           IF ws-file-status NOT = "35" THEN
               PERFORM UNTIL 1 = 2
                   READ vt-file NEXT RECORD
                       AT END EXIT PERFORM
                   END-READ
                   IF vt-produto-id = ws-produto-id THEN
                       MOVE vt-nome TO ws-nome-arq
                       IF ws-nome-arq NOT = SPACES
                           PERFORM normalizar-arq
                           IF ws-nome-arq-cmp = ws-nome-cmp THEN
                               MOVE "S" TO ws-duplicado
                           END-IF
                       END-IF
                   END-IF
               END-PERFORM
               CLOSE vt-file
           END-IF
           IF ws-duplicado = "S" THEN
               DISPLAY "ERRO: variante duplicada para este produto" STOP RUN END-IF

           IF ws-id-in NOT = SPACES THEN
               COMPUTE ws-prox-id = FUNCTION NUMVAL(ws-id-in)
           ELSE
               MOVE 0 TO ws-prox-id
               OPEN INPUT vt-file
               IF ws-file-status = "35" THEN
                   MOVE 1 TO ws-prox-id
               ELSE
                   PERFORM UNTIL 1 = 2
                       READ vt-file NEXT RECORD
                           AT END EXIT PERFORM
                       END-READ
                       IF vt-id > ws-prox-id THEN
                           MOVE vt-id TO ws-prox-id END-IF
                   END-PERFORM
                   CLOSE vt-file
                   ADD 1 TO ws-prox-id
               END-IF
           END-IF

           PERFORM ensure-file
           OPEN EXTEND vt-file
           MOVE ws-prox-id TO vt-id
           MOVE ws-produto-id TO vt-produto-id
           MOVE ws-nome TO vt-nome
           MOVE ws-atributos TO vt-atributos
           MOVE ws-codigo TO vt-codigo
           MOVE ws-preco TO vt-preco
           MOVE ws-ativo TO vt-ativo
           WRITE vt-reg
           CLOSE vt-file
           MOVE ws-prox-id TO ws-id-ed
           DISPLAY FUNCTION TRIM(ws-id-ed).

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-produto-id-in FROM ENVIRONMENT "PRODUTO_ID"
           ACCEPT ws-nome FROM ENVIRONMENT "NOME"
           ACCEPT ws-atributos FROM ENVIRONMENT "ATRIBUTOS"
           ACCEPT ws-codigo FROM ENVIRONMENT "CODIGO"
           ACCEPT ws-preco-in FROM ENVIRONMENT "PRECO"
           ACCEPT ws-ativo FROM ENVIRONMENT "ATIVO"
           ACCEPT ws-clear-codigo FROM ENVIRONMENT "CODIGO_CLEAR"
           ACCEPT ws-clear-atributos FROM ENVIRONMENT "ATRIBUTOS_CLEAR"

           IF ws-produto-id-in NOT = SPACES THEN
               COMPUTE ws-produto-id = FUNCTION NUMVAL(ws-produto-id-in)
           END-IF

           IF ws-nome NOT = SPACES THEN
               PERFORM normalizar
               MOVE "N" TO ws-duplicado
               OPEN INPUT vt-file
               IF ws-file-status NOT = "35" THEN
                   PERFORM UNTIL 1 = 2
                       READ vt-file NEXT RECORD
                           AT END EXIT PERFORM
                       END-READ
                       IF vt-id NOT = ws-id AND
                          vt-produto-id = ws-produto-id THEN
                           MOVE vt-nome TO ws-nome-arq
                           IF ws-nome-arq NOT = SPACES
                               PERFORM normalizar-arq
                               IF ws-nome-arq-cmp = ws-nome-cmp THEN
                                   MOVE "S" TO ws-duplicado
                               END-IF
                           END-IF
                       END-IF
                   END-PERFORM
                   CLOSE vt-file
               END-IF
               IF ws-duplicado = "S" THEN
                   DISPLAY "ERRO: variante duplicada para este produto" STOP RUN END-IF
           END-IF

           MOVE "N" TO ws-encontrou
           OPEN INPUT vt-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: variante nao encontrada" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ vt-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF vt-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-produto-id-in NOT = SPACES THEN
                       MOVE ws-produto-id TO vt-produto-id END-IF
                   IF ws-nome NOT = SPACES THEN
                       MOVE ws-nome TO vt-nome END-IF
                   IF ws-atributos NOT = SPACES THEN
                       MOVE ws-atributos TO vt-atributos END-IF
                   IF ws-codigo NOT = SPACES THEN
                       MOVE ws-codigo TO vt-codigo END-IF
                   IF ws-preco-in NOT = SPACES THEN
                       COMPUTE ws-preco = FUNCTION NUMVAL(ws-preco-in)
                       MOVE ws-preco TO vt-preco
                   END-IF
                   IF ws-ativo NOT = SPACES THEN
                       MOVE ws-ativo TO vt-ativo END-IF
                   IF ws-clear-codigo = "S" THEN
                       MOVE SPACES TO vt-codigo END-IF
                   IF ws-clear-atributos = "S" THEN
                       MOVE SPACES TO vt-atributos END-IF
               END-IF
               MOVE vt-reg TO temp-reg
               WRITE temp-reg
           END-PERFORM
           CLOSE vt-file CLOSE temp-file
           CALL "system" USING
               "mv dados/variantes.tmp dados/variantes.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: variante nao encontrada".

       excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           MOVE "N" TO ws-encontrou
           OPEN INPUT vt-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: variante nao encontrada" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ vt-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF vt-id NOT = ws-id THEN
                   MOVE vt-reg TO temp-reg
                   WRITE temp-reg
               ELSE
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE vt-file CLOSE temp-file
           CALL "system" USING
               "mv dados/variantes.tmp dados/variantes.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: variante nao encontrada".

       listar.
           OPEN INPUT vt-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"variantes":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"variantes":[' 
           MOVE "S" TO ws-existe
           MOVE 0 TO ws-prox-id
           PERFORM UNTIL 1 = 2
               READ vt-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-prox-id
               IF ws-existe = "S" THEN
                   MOVE "N" TO ws-existe
               ELSE
                   DISPLAY ","
               END-IF
               MOVE vt-id TO ws-id-ed
               MOVE vt-produto-id TO ws-prod-id-ed
               MOVE vt-preco TO ws-preco
               MOVE ws-preco TO ws-preco-ed
               MOVE SPACES TO ws-json-linha
               IF vt-ativo = "S" OR "s" THEN
                   STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                          ',"produto_id":' FUNCTION TRIM(ws-prod-id-ed)
                          ',"nome":"' FUNCTION TRIM(vt-nome) '"'
                          ',"atributos":"' FUNCTION TRIM(vt-atributos) '"'
                          ',"codigo":"' FUNCTION TRIM(vt-codigo) '"'
                          ',"preco":' FUNCTION TRIM(ws-preco-ed)
                          ',"ativo":true}'
                          INTO ws-json-linha
               ELSE
                   STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                          ',"produto_id":' FUNCTION TRIM(ws-prod-id-ed)
                          ',"nome":"' FUNCTION TRIM(vt-nome) '"'
                          ',"atributos":"' FUNCTION TRIM(vt-atributos) '"'
                          ',"codigo":"' FUNCTION TRIM(vt-codigo) '"'
                          ',"preco":' FUNCTION TRIM(ws-preco-ed)
                          ',"ativo":false}'
                          INTO ws-json-linha
               END-IF
               DISPLAY FUNCTION TRIM(ws-json-linha)
           END-PERFORM
           MOVE ws-prox-id TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE vt-file.
