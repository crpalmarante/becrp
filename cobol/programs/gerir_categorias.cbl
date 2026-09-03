       >>SOURCE FORMAT IS FREE
       *> gerir_categorias.cbl - CRUD de categorias de produtos
       *> Fonte da verdade: dados/categorias.dat (registro fixo).
       *> Ações: incluir | alterar | excluir | listar
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirCategorias.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT cat-file ASSIGN TO "dados/categorias.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/categorias.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-file-status.

       DATA DIVISION.
       FILE SECTION.
       FD cat-file.
       01 cat-reg.
           05 ct-id           PIC 9(5).
           05 ct-nome         PIC X(40).
           05 ct-descricao    PIC X(60).
           05 ct-ativo        PIC X.
           05 ct-pai-id       PIC 9(5).

       FD temp-file.
       01 temp-reg.
           05 tl-id           PIC 9(5).
           05 tl-nome         PIC X(40).
           05 tl-descricao    PIC X(60).
           05 tl-ativo        PIC X.
           05 tl-pai-id       PIC 9(5).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-file-status     PIC X(2).
       01 ws-existe          PIC X(1).
       01 ws-encontrou       PIC X(1).
       01 ws-json-linha      PIC X(500).
       01 ws-id-ed           PIC ZZZZ9.
       01 ws-pai-ed          PIC ZZZZ9.
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-id              PIC 9(5).
       01 ws-id-in           PIC X(10).
       01 ws-nome            PIC X(40).
       01 ws-descricao       PIC X(60).
       01 ws-ativo           PIC X(1).
       01 ws-prox-id         PIC 9(5).
       01 ws-nome-cmp        PIC X(40).
       01 ws-nome-arq        PIC X(40).
       01 ws-nome-arq-cmp    PIC X(40).
       01 ws-i               PIC 9(2).
       01 ws-duplicado       PIC X(1).
       01 ws-pai-id-in       PIC X(10).
       01 ws-pai-id          PIC 9(5).
       01 ws-tem-filho       PIC X(1).

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
           OPEN INPUT cat-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT cat-file
               CLOSE cat-file
           ELSE
               CLOSE cat-file
           END-IF.

       *> Normaliza nome: remove espacos e deixa minusculo para comparar
       normalizar.
           MOVE SPACES TO ws-nome-cmp
           PERFORM VARYING ws-i FROM 1 BY 1 UNTIL ws-i > 40
               IF ws-nome(ws-i:1) NOT = SPACE
                   STRING ws-nome-cmp DELIMITED BY SPACES
                          ws-nome(ws-i:1) DELIMITED BY SIZE
                          INTO ws-nome-cmp
               END-IF
           END-PERFORM
           PERFORM VARYING ws-i FROM 1 BY 1 UNTIL ws-i > 40
               IF ws-nome-cmp(ws-i:1) >= "A" AND <= "Z"
                   MOVE FUNCTION LOWER-CASE(ws-nome-cmp(ws-i:1))
                     TO ws-nome-cmp(ws-i:1)
               END-IF
           END-PERFORM.

       normalizar-arq.
           MOVE SPACES TO ws-nome-arq-cmp
           PERFORM VARYING ws-i FROM 1 BY 1 UNTIL ws-i > 40
               IF ws-nome-arq(ws-i:1) NOT = SPACE
                   STRING ws-nome-arq-cmp DELIMITED BY SPACES
                          ws-nome-arq(ws-i:1) DELIMITED BY SIZE
                          INTO ws-nome-arq-cmp
               END-IF
           END-PERFORM
           PERFORM VARYING ws-i FROM 1 BY 1 UNTIL ws-i > 40
               IF ws-nome-arq-cmp(ws-i:1) >= "A" AND <= "Z"
                   MOVE FUNCTION LOWER-CASE(ws-nome-arq-cmp(ws-i:1))
                     TO ws-nome-arq-cmp(ws-i:1)
               END-IF
           END-PERFORM.

       incluir.
           ACCEPT ws-nome FROM ENVIRONMENT "NOME"
           ACCEPT ws-descricao FROM ENVIRONMENT "DESCRICAO"
           ACCEPT ws-ativo FROM ENVIRONMENT "ATIVO"
           ACCEPT ws-pai-id-in FROM ENVIRONMENT "PAI_ID"
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           IF ws-nome = SPACES THEN
               DISPLAY "ERRO: nome obrigatorio" STOP RUN END-IF
           IF ws-ativo = SPACES THEN MOVE "S" TO ws-ativo END-IF
           IF ws-pai-id-in = SPACES THEN
               MOVE 0 TO ws-pai-id
           ELSE
               COMPUTE ws-pai-id = FUNCTION NUMVAL(ws-pai-id-in)
           END-IF

           PERFORM normalizar
           MOVE "N" TO ws-duplicado
           OPEN INPUT cat-file
           IF ws-file-status NOT = "35" THEN
               PERFORM UNTIL 1 = 2
                   READ cat-file NEXT RECORD
                       AT END EXIT PERFORM
                   END-READ
                   MOVE ct-nome TO ws-nome-arq
                   IF ws-nome-arq NOT = SPACES
                       PERFORM normalizar-arq
                       IF ws-nome-arq-cmp = ws-nome-cmp THEN
                           MOVE "S" TO ws-duplicado
                       END-IF
                   END-IF
               END-PERFORM
               CLOSE cat-file
           END-IF
           IF ws-duplicado = "S" THEN
               DISPLAY "ERRO: nome duplicado" STOP RUN END-IF

           IF ws-id-in NOT = SPACES THEN
               COMPUTE ws-prox-id = FUNCTION NUMVAL(ws-id-in)
           ELSE
               MOVE 0 TO ws-prox-id
               OPEN INPUT cat-file
               IF ws-file-status = "35" THEN
                   MOVE 1 TO ws-prox-id
               ELSE
                   PERFORM UNTIL 1 = 2
                       READ cat-file NEXT RECORD
                           AT END EXIT PERFORM
                       END-READ
                       IF ct-id > ws-prox-id THEN
                           MOVE ct-id TO ws-prox-id END-IF
                   END-PERFORM
                   CLOSE cat-file
                   ADD 1 TO ws-prox-id
               END-IF
           END-IF

           PERFORM ensure-file
           OPEN EXTEND cat-file
           MOVE ws-prox-id TO ct-id
           MOVE ws-nome TO ct-nome
           MOVE ws-descricao TO ct-descricao
           MOVE ws-ativo TO ct-ativo
           MOVE ws-pai-id TO ct-pai-id
           WRITE cat-reg
           CLOSE cat-file
           MOVE ws-prox-id TO ws-id-ed
           DISPLAY FUNCTION TRIM(ws-id-ed).

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-nome FROM ENVIRONMENT "NOME"
           ACCEPT ws-descricao FROM ENVIRONMENT "DESCRICAO"
           ACCEPT ws-ativo FROM ENVIRONMENT "ATIVO"
           ACCEPT ws-pai-id-in FROM ENVIRONMENT "PAI_ID"
           IF ws-pai-id-in = SPACES THEN
               MOVE 0 TO ws-pai-id
           ELSE
               COMPUTE ws-pai-id = FUNCTION NUMVAL(ws-pai-id-in)
           END-IF

           IF ws-nome NOT = SPACES THEN
               PERFORM normalizar
               MOVE "N" TO ws-duplicado
               OPEN INPUT cat-file
               IF ws-file-status NOT = "35" THEN
                   PERFORM UNTIL 1 = 2
                       READ cat-file NEXT RECORD
                           AT END EXIT PERFORM
                       END-READ
                       IF ct-id NOT = ws-id THEN
                           MOVE ct-nome TO ws-nome-arq
                           IF ws-nome-arq NOT = SPACES
                               PERFORM normalizar-arq
                               IF ws-nome-arq-cmp = ws-nome-cmp THEN
                                   MOVE "S" TO ws-duplicado
                               END-IF
                           END-IF
                       END-IF
                   END-PERFORM
                   CLOSE cat-file
               END-IF
               IF ws-duplicado = "S" THEN
                   DISPLAY "ERRO: nome duplicado" STOP RUN END-IF
           END-IF

           MOVE "N" TO ws-encontrou
           OPEN INPUT cat-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: categoria nao encontrada" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ cat-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF ct-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-nome NOT = SPACES THEN
                       MOVE ws-nome TO ct-nome END-IF
                   IF ws-descricao NOT = SPACES THEN
                       MOVE ws-descricao TO ct-descricao END-IF
                   IF ws-ativo NOT = SPACES THEN
                       MOVE ws-ativo TO ct-ativo END-IF
                   IF ws-pai-id-in NOT = SPACES THEN
                       MOVE ws-pai-id TO ct-pai-id END-IF
               END-IF
               MOVE cat-reg TO temp-reg
               WRITE temp-reg
           END-PERFORM
           CLOSE cat-file CLOSE temp-file
           CALL "system" USING
               "mv dados/categorias.tmp dados/categorias.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: categoria nao encontrada".

       excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           MOVE "N" TO ws-encontrou
           MOVE "N" TO ws-tem-filho
           OPEN INPUT cat-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: categoria nao encontrada" STOP RUN END-IF
           PERFORM UNTIL 1 = 2
               READ cat-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF ct-pai-id = ws-id THEN
                   MOVE "S" TO ws-tem-filho
                   EXIT PERFORM
               END-IF
           END-PERFORM
           CLOSE cat-file
           IF ws-tem-filho = "S" THEN
               DISPLAY "ERRO: categoria possui subcategorias, exclua-as antes"
               STOP RUN END-IF
           OPEN INPUT cat-file
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ cat-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF ct-id NOT = ws-id THEN
                   MOVE cat-reg TO temp-reg
                   WRITE temp-reg
               ELSE
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE cat-file CLOSE temp-file
           CALL "system" USING
               "mv dados/categorias.tmp dados/categorias.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: categoria nao encontrada".

       listar.
           OPEN INPUT cat-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"categorias":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"categorias":[' 
           MOVE "S" TO ws-existe
           MOVE 0 TO ws-prox-id
           PERFORM UNTIL 1 = 2
               READ cat-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-prox-id
               IF ws-existe = "S" THEN
                   MOVE "N" TO ws-existe
               ELSE
                   DISPLAY ","
               END-IF
               MOVE ct-id TO ws-id-ed
               MOVE ct-pai-id TO ws-pai-ed
               MOVE SPACES TO ws-json-linha
               IF ct-ativo = "S" OR "s" THEN
                   STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                          ',"nome":"' FUNCTION TRIM(ct-nome) '"'
                          ',"descricao":"' FUNCTION TRIM(ct-descricao) '"'
                          ',"ativo":true'
                          ',"pai_id":' FUNCTION TRIM(ws-pai-ed) '}'
                          INTO ws-json-linha
               ELSE
                   STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                          ',"nome":"' FUNCTION TRIM(ct-nome) '"'
                          ',"descricao":"' FUNCTION TRIM(ct-descricao) '"'
                          ',"ativo":false'
                          ',"pai_id":' FUNCTION TRIM(ws-pai-ed) '}'
                          INTO ws-json-linha
               END-IF
               DISPLAY FUNCTION TRIM(ws-json-linha)
           END-PERFORM
           MOVE ws-prox-id TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE cat-file.
