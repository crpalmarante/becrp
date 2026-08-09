       >>SOURCE FORMAT IS FREE
       *> gerir_departamentos.cbl - CRUD de departamentos (RFC-008 §3)
       *> Inativação lógica: NUNCA exclusão física (RFC-008 decisão 4).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirDepartamentos.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT dep-file ASSIGN TO "dados/departamentos.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/departamentos.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD dep-file.
       01 dep-reg.
           05 dep-id              PIC 9(3).
           05 dep-codigo          PIC X(10).
           05 dep-descricao       PIC X(50).
           05 dep-centro-custo    PIC X(20).
           05 dep-responsavel     PIC X(40).
           05 dep-status          PIC X(8).

       FD temp-file.
       01 temp-reg.
           05 tl-id              PIC 9(3).
           05 tl-codigo          PIC X(10).
           05 tl-descricao       PIC X(50).
           05 tl-centro-custo    PIC X(20).
           05 tl-responsavel     PIC X(40).
           05 tl-status          PIC X(8).

       WORKING-STORAGE SECTION.
       01 ws-acao           PIC X(20).
       01 ws-file-status    PIC X(2).
       01 ws-encontrou      PIC X.
       01 ws-prox-id        PIC 9(3).
       01 ws-total          PIC 9(4).
       01 ws-total-ed       PIC Z(3)9.
       01 ws-id-ed          PIC Z(3)9.
       01 ws-id-in          PIC X(5).
       01 ws-id             PIC 9(3).
       01 ws-codigo         PIC X(10).
       01 ws-descricao      PIC X(50).
       01 ws-centro-custo   PIC X(20).
       01 ws-responsavel    PIC X(40).
       01 ws-status         PIC X(8).
       01 ws-json-linha     PIC X(500).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF

           EVALUATE ws-acao
               WHEN "incluir"        PERFORM incluir
               WHEN "alterar"        PERFORM alterar
               WHEN "excluir"        PERFORM excluir
               WHEN "listar"         PERFORM listar
               WHEN "listar-ativos"  PERFORM listar-ativos
               WHEN OTHER            DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       incluir.
           ACCEPT ws-codigo FROM ENVIRONMENT "CODIGO"
           ACCEPT ws-descricao FROM ENVIRONMENT "DESCRICAO"
           ACCEPT ws-centro-custo FROM ENVIRONMENT "CENTRO_CUSTO"
           ACCEPT ws-responsavel FROM ENVIRONMENT "RESPONSAVEL"
           IF ws-codigo = SPACES THEN
               DISPLAY "ERRO: codigo obrigatorio" STOP RUN END-IF
           IF ws-descricao = SPACES THEN
               DISPLAY "ERRO: descricao obrigatoria" STOP RUN END-IF

           MOVE 0 TO ws-prox-id
           OPEN INPUT dep-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT dep-file CLOSE dep-file
               OPEN INPUT dep-file END-IF
           PERFORM UNTIL 1 = 2
               READ dep-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF dep-id > ws-prox-id THEN MOVE dep-id TO ws-prox-id END-IF
               IF dep-codigo = ws-codigo AND dep-status NOT = "inativo" THEN
                   DISPLAY "ERRO: codigo ja cadastrado" STOP RUN END-IF
           END-PERFORM
           CLOSE dep-file
           ADD 1 TO ws-prox-id

           OPEN EXTEND dep-file
           MOVE ws-prox-id TO dep-id
           MOVE ws-codigo TO dep-codigo
           MOVE ws-descricao TO dep-descricao
           MOVE ws-centro-custo TO dep-centro-custo
           MOVE ws-responsavel TO dep-responsavel
           MOVE "ativo" TO dep-status
           WRITE dep-reg
           CLOSE dep-file
           DISPLAY ws-prox-id.

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-codigo FROM ENVIRONMENT "CODIGO"
           ACCEPT ws-descricao FROM ENVIRONMENT "DESCRICAO"
           ACCEPT ws-centro-custo FROM ENVIRONMENT "CENTRO_CUSTO"
           ACCEPT ws-responsavel FROM ENVIRONMENT "RESPONSAVEL"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"

           MOVE "N" TO ws-encontrou
           OPEN INPUT dep-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: departamento nao encontrado" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ dep-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF dep-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-codigo NOT = SPACES THEN MOVE ws-codigo TO dep-codigo END-IF
                   IF ws-descricao NOT = SPACES THEN MOVE ws-descricao TO dep-descricao END-IF
                   IF ws-centro-custo NOT = SPACES THEN
                       MOVE ws-centro-custo TO dep-centro-custo END-IF
                   IF ws-responsavel NOT = SPACES THEN
                       MOVE ws-responsavel TO dep-responsavel END-IF
                   IF ws-status NOT = SPACES THEN MOVE ws-status TO dep-status END-IF
               END-IF
               MOVE dep-id TO tl-id
               MOVE dep-codigo TO tl-codigo
               MOVE dep-descricao TO tl-descricao
               MOVE dep-centro-custo TO tl-centro-custo
               MOVE dep-responsavel TO tl-responsavel
               MOVE dep-status TO tl-status
               WRITE temp-reg
           END-PERFORM
           CLOSE dep-file CLOSE temp-file
           CALL "system" USING "mv dados/departamentos.tmp dados/departamentos.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: departamento nao encontrado".

       excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)

           MOVE "N" TO ws-encontrou
           OPEN INPUT dep-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: departamento nao encontrado" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ dep-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF dep-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   MOVE "inativo" TO dep-status
               END-IF
               MOVE dep-id TO tl-id
               MOVE dep-codigo TO tl-codigo
               MOVE dep-descricao TO tl-descricao
               MOVE dep-centro-custo TO tl-centro-custo
               MOVE dep-responsavel TO tl-responsavel
               MOVE dep-status TO tl-status
               WRITE temp-reg
           END-PERFORM
           CLOSE dep-file CLOSE temp-file
           CALL "system" USING "mv dados/departamentos.tmp dados/departamentos.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: departamento nao encontrado".

       listar.
           OPEN INPUT dep-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"departamentos":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"departamentos":['
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ dep-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-encontrou = "S" THEN
                   MOVE "N" TO ws-encontrou
               ELSE DISPLAY "," END-IF
               MOVE dep-id TO ws-id-ed
               STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                      ',"codigo":"' FUNCTION TRIM(dep-codigo) '"'
                      ',"descricao":"' FUNCTION TRIM(dep-descricao) '"'
                      ',"centro_custo":"' FUNCTION TRIM(dep-centro-custo) '"'
                      ',"responsavel":"' FUNCTION TRIM(dep-responsavel) '"'
                      ',"status":"' FUNCTION TRIM(dep-status) '"}'
                  INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE dep-file.

       listar-ativos.
           OPEN INPUT dep-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"departamentos":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"departamentos":['
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ dep-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF dep-status = "ativo" THEN
                   ADD 1 TO ws-total
                   IF ws-encontrou = "S" THEN
                       MOVE "N" TO ws-encontrou
                   ELSE DISPLAY "," END-IF
                   MOVE dep-id TO ws-id-ed
                   STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                          ',"codigo":"' FUNCTION TRIM(dep-codigo) '"'
                          ',"descricao":"' FUNCTION TRIM(dep-descricao) '"'
                          ',"centro_custo":"' FUNCTION TRIM(dep-centro-custo) '"'
                          ',"responsavel":"' FUNCTION TRIM(dep-responsavel) '"'
                          ',"status":"' FUNCTION TRIM(dep-status) '"}'
                      INTO ws-json-linha
                   DISPLAY FUNCTION TRIM(ws-json-linha)
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE dep-file.
