       >>SOURCE FORMAT IS FREE
       *> gerir_cargos.cbl - CRUD de cargos (RFC-008 §4)
       *> Inativação lógica: NUNCA exclusão física (RFC-008 decisão 4).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirCargos.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT cr-file ASSIGN TO "dados/cargos.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/cargos.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD cr-file.
       01 cr-reg.
           05 cr-id               PIC 9(3).
           05 cr-codigo           PIC X(10).
           05 cr-descricao        PIC X(50).
           05 cr-cbo              PIC X(6).
           05 cr-salario-ref      PIC 9(7)V99.
           05 cr-status           PIC X(8).

       FD temp-file.
       01 temp-reg.
           05 tl-id               PIC 9(3).
           05 tl-codigo           PIC X(10).
           05 tl-descricao        PIC X(50).
           05 tl-cbo              PIC X(6).
           05 tl-salario-ref      PIC 9(7)V99.
           05 tl-status           PIC X(8).

       WORKING-STORAGE SECTION.
       01 ws-acao           PIC X(20).
       01 ws-file-status    PIC X(2).
       01 ws-encontrou      PIC X.
       01 ws-prox-id        PIC 9(3).
       01 ws-total          PIC 9(4).
       01 ws-total-ed       PIC Z(3)9.
       01 ws-id-ed          PIC Z(3)9.
       01 ws-salario-j      PIC Z(6)9.99.
       01 ws-salario-ed     PIC X(12).
       01 ws-salario        PIC 9(7)V99.
       01 ws-id-in          PIC X(5).
       01 ws-id             PIC 9(3).
       01 ws-codigo         PIC X(10).
       01 ws-descricao      PIC X(50).
       01 ws-cbo            PIC X(6).
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
           ACCEPT ws-cbo FROM ENVIRONMENT "CBO"
           ACCEPT ws-salario-ed FROM ENVIRONMENT "SALARIO_REFERENCIA"
           IF ws-codigo = SPACES THEN
               DISPLAY "ERRO: codigo obrigatorio" STOP RUN END-IF
           IF ws-descricao = SPACES THEN
               DISPLAY "ERRO: descricao obrigatoria" STOP RUN END-IF
           IF ws-salario-ed NOT = SPACES THEN
               COMPUTE ws-salario = FUNCTION NUMVAL(ws-salario-ed) END-IF

           MOVE 0 TO ws-prox-id
           OPEN INPUT cr-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT cr-file CLOSE cr-file
               OPEN INPUT cr-file END-IF
           PERFORM UNTIL 1 = 2
               READ cr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF cr-id > ws-prox-id THEN MOVE cr-id TO ws-prox-id END-IF
               IF cr-codigo = ws-codigo AND cr-status NOT = "inativo" THEN
                   DISPLAY "ERRO: codigo ja cadastrado" STOP RUN END-IF
           END-PERFORM
           CLOSE cr-file
           ADD 1 TO ws-prox-id

           OPEN EXTEND cr-file
           MOVE ws-prox-id TO cr-id
           MOVE ws-codigo TO cr-codigo
           MOVE ws-descricao TO cr-descricao
           MOVE ws-cbo TO cr-cbo
           MOVE ws-salario TO cr-salario-ref
           MOVE "ativo" TO cr-status
           WRITE cr-reg
           CLOSE cr-file
           DISPLAY ws-prox-id.

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-codigo FROM ENVIRONMENT "CODIGO"
           ACCEPT ws-descricao FROM ENVIRONMENT "DESCRICAO"
           ACCEPT ws-cbo FROM ENVIRONMENT "CBO"
           ACCEPT ws-salario-ed FROM ENVIRONMENT "SALARIO_REFERENCIA"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"

           MOVE "N" TO ws-encontrou
           OPEN INPUT cr-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: cargo nao encontrado" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ cr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF cr-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-codigo NOT = SPACES THEN MOVE ws-codigo TO cr-codigo END-IF
                   IF ws-descricao NOT = SPACES THEN MOVE ws-descricao TO cr-descricao END-IF
                   IF ws-cbo NOT = SPACES THEN MOVE ws-cbo TO cr-cbo END-IF
                   IF ws-salario-ed NOT = SPACES THEN
                       COMPUTE ws-salario = FUNCTION NUMVAL(ws-salario-ed)
                       MOVE ws-salario TO cr-salario-ref END-IF
                   IF ws-status NOT = SPACES THEN MOVE ws-status TO cr-status END-IF
               END-IF
               MOVE cr-id TO tl-id
               MOVE cr-codigo TO tl-codigo
               MOVE cr-descricao TO tl-descricao
               MOVE cr-cbo TO tl-cbo
               MOVE cr-salario-ref TO tl-salario-ref
               MOVE cr-status TO tl-status
               WRITE temp-reg
           END-PERFORM
           CLOSE cr-file CLOSE temp-file
           CALL "system" USING "mv dados/cargos.tmp dados/cargos.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: cargo nao encontrado".

       excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)

           MOVE "N" TO ws-encontrou
           OPEN INPUT cr-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: cargo nao encontrado" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ cr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF cr-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   MOVE "inativo" TO cr-status
               END-IF
               MOVE cr-id TO tl-id
               MOVE cr-codigo TO tl-codigo
               MOVE cr-descricao TO tl-descricao
               MOVE cr-cbo TO tl-cbo
               MOVE cr-salario-ref TO tl-salario-ref
               MOVE cr-status TO tl-status
               WRITE temp-reg
           END-PERFORM
           CLOSE cr-file CLOSE temp-file
           CALL "system" USING "mv dados/cargos.tmp dados/cargos.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: cargo nao encontrado".

       listar.
           OPEN INPUT cr-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"cargos":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"cargos":['
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ cr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-encontrou = "S" THEN
                   MOVE "N" TO ws-encontrou
               ELSE DISPLAY "," END-IF
               MOVE cr-id TO ws-id-ed
               MOVE cr-salario-ref TO ws-salario-j
               STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                      ',"codigo":"' FUNCTION TRIM(cr-codigo) '"'
                      ',"descricao":"' FUNCTION TRIM(cr-descricao) '"'
                      ',"cbo":"' FUNCTION TRIM(cr-cbo) '"'
                      ',"salario_referencia":' FUNCTION TRIM(ws-salario-j)
                      ',"status":"' FUNCTION TRIM(cr-status) '"}'
                  INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE cr-file.

       listar-ativos.
           OPEN INPUT cr-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"cargos":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"cargos":['
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ cr-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF cr-status = "ativo" THEN
                   ADD 1 TO ws-total
                   IF ws-encontrou = "S" THEN
                       MOVE "N" TO ws-encontrou
                   ELSE DISPLAY "," END-IF
                   MOVE cr-id TO ws-id-ed
                   MOVE cr-salario-ref TO ws-salario-j
                   STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                          ',"codigo":"' FUNCTION TRIM(cr-codigo) '"'
                          ',"descricao":"' FUNCTION TRIM(cr-descricao) '"'
                          ',"cbo":"' FUNCTION TRIM(cr-cbo) '"'
                          ',"salario_referencia":' FUNCTION TRIM(ws-salario-j)
                          ',"status":"' FUNCTION TRIM(cr-status) '"}'
                      INTO ws-json-linha
                   DISPLAY FUNCTION TRIM(ws-json-linha)
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE cr-file.
