       >>SOURCE FORMAT IS FREE
       *> gerir_salarios.cbl - Historico de salarios com vigencia (RFC-002
       *> decisoes 1 e 3.3): cada alteracao registra valor + data de inicio
       *> de vigencia. O salario vigente em uma competencia e o registro
       *> ATIVO com maior data_inicio <= competencia e (data_fim vazio ou
       *> data_fim > competencia).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirSalarios.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT sal-file ASSIGN TO "dados/salarios.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/salarios.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD sal-file.
       01 sal-reg.
           05 sal-id              PIC 9(4).
           05 sal-func-id         PIC 9(3).
           05 sal-salario         PIC 9(7)V99.
           05 sal-data-inicio     PIC X(10).
           05 sal-data-fim        PIC X(10).
           05 sal-status          PIC X(8).

       FD temp-file.
       01 temp-reg.
           05 tl-id               PIC 9(4).
           05 tl-func-id          PIC 9(3).
           05 tl-salario          PIC 9(7)V99.
           05 tl-data-inicio      PIC X(10).
           05 tl-data-fim         PIC X(10).
           05 tl-status           PIC X(8).

       WORKING-STORAGE SECTION.
       01 ws-acao           PIC X(20).
       01 ws-file-status    PIC X(2).
       01 ws-encontrou      PIC X.
       01 ws-primeiro       PIC X.
       01 ws-prox-id        PIC 9(4).
       01 ws-total          PIC 9(4).
       01 ws-total-ed       PIC Z(3)9.
       01 ws-id-ed          PIC Z(3)9.
       01 ws-func-ed        PIC Z(2)9.
       01 ws-id-in          PIC X(6).
       01 ws-func-in        PIC X(6).
       01 ws-id             PIC 9(4).
       01 ws-func-id        PIC 9(3).
       01 ws-salario-ed     PIC X(12).
       01 ws-salario        PIC 9(7)V99.
       01 ws-data-inicio    PIC X(10).
       01 ws-data-inicio-max PIC X(6).
       01 ws-data-fim       PIC X(10).
       01 ws-status         PIC X(8).
       01 ws-competencia    PIC X(10).
       01 ws-json-linha     PIC X(400).
       01 ws-salario-editado PIC Z(6)9.99.
       01 ws-comp-n         PIC X(6).
       01 ws-dtini-n        PIC X(6).
       01 ws-dtfim-n        PIC X(6).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "listar" TO ws-acao END-IF

           EVALUATE ws-acao
               WHEN "incluir"        PERFORM incluir
               WHEN "listar"         PERFORM listar
               WHEN "vigente"        PERFORM vigente
               WHEN OTHER            DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       incluir.
           ACCEPT ws-func-in FROM ENVIRONMENT "FUNCIONARIO_ID"
           COMPUTE ws-func-id = FUNCTION NUMVAL(ws-func-in)
           ACCEPT ws-salario-ed FROM ENVIRONMENT "SALARIO"
           IF ws-salario-ed = SPACES THEN
               DISPLAY "ERRO: salario obrigatorio" STOP RUN END-IF
           COMPUTE ws-salario = FUNCTION NUMVAL(ws-salario-ed)
           ACCEPT ws-data-inicio FROM ENVIRONMENT "DATA_INICIO"
           IF ws-data-inicio = SPACES THEN
               DISPLAY "ERRO: data de inicio de vigencia obrigatoria"
               STOP RUN END-IF

           MOVE 0 TO ws-prox-id
           OPEN INPUT sal-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT sal-file CLOSE sal-file
               OPEN INPUT sal-file END-IF
           PERFORM UNTIL 1 = 2
               READ sal-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF sal-id > ws-prox-id THEN MOVE sal-id TO ws-prox-id END-IF
           END-PERFORM
           CLOSE sal-file
           ADD 1 TO ws-prox-id

           *> Fecha o registro vigente anterior (data_fim = inicio do novo),
           *> reescrevendo o arquivo em temp (padrao do MIGRATION-COBOL-CRUD).
           OPEN INPUT sal-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: falha ao abrir historico" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ sal-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF sal-func-id = ws-func-id AND sal-status = "ativo"
                  AND sal-data-fim = SPACES
                  AND sal-data-inicio < ws-data-inicio THEN
                   MOVE ws-data-inicio TO sal-data-fim
               END-IF
               MOVE sal-id TO tl-id
               MOVE sal-func-id TO tl-func-id
               MOVE sal-salario TO tl-salario
               MOVE sal-data-inicio TO tl-data-inicio
               MOVE sal-data-fim TO tl-data-fim
               MOVE sal-status TO tl-status
               WRITE temp-reg
           END-PERFORM
           CLOSE sal-file CLOSE temp-file
           CALL "system" USING "mv dados/salarios.tmp dados/salarios.dat"
           END-CALL

           OPEN EXTEND sal-file
           MOVE ws-prox-id TO sal-id
           MOVE ws-func-id TO sal-func-id
           MOVE ws-salario TO sal-salario
           MOVE ws-data-inicio TO sal-data-inicio
           MOVE SPACES TO sal-data-fim
           MOVE "ativo" TO sal-status
           WRITE sal-reg
           CLOSE sal-file
           DISPLAY ws-prox-id.

       listar.
           ACCEPT ws-func-in FROM ENVIRONMENT "FUNCIONARIO_ID"
           COMPUTE ws-func-id = FUNCTION NUMVAL(ws-func-in)

           OPEN INPUT sal-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"salarios":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"salarios":['
           MOVE "S" TO ws-primeiro
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ sal-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF sal-func-id = ws-func-id AND sal-status = "ativo" THEN
                   ADD 1 TO ws-total
                   IF ws-primeiro = "S" THEN
                       MOVE "N" TO ws-primeiro
                   ELSE DISPLAY "," END-IF
                   MOVE sal-id TO ws-id-ed
                   MOVE sal-func-id TO ws-func-ed
                   MOVE sal-salario TO ws-salario-editado
                   MOVE SPACES TO ws-json-linha
                   STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                          ',"funcionario_id":' FUNCTION TRIM(ws-func-ed)
                          ',"salario":' FUNCTION TRIM(ws-salario-editado)
                          ',"data_inicio":"' FUNCTION TRIM(sal-data-inicio) '"'
                          ',"data_fim":"' FUNCTION TRIM(sal-data-fim) '"'
                          ',"status":"' FUNCTION TRIM(sal-status) '"}'
                       INTO ws-json-linha
                   DISPLAY FUNCTION TRIM(ws-json-linha)
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE sal-file.

       vigente.
           ACCEPT ws-func-in FROM ENVIRONMENT "FUNCIONARIO_ID"
           COMPUTE ws-func-id = FUNCTION NUMVAL(ws-func-in)
           ACCEPT ws-competencia FROM ENVIRONMENT "COMPETENCIA"

           *> Normaliza competencia "YYYY/MM" e datas "YYYY-MM-DD" para "YYYYMM"
           *> (compara apenas ano/mês; separador - / / não interfere).
           MOVE ws-competencia(1:4) TO ws-comp-n(1:4)
           MOVE ws-competencia(6:2) TO ws-comp-n(5:2)

           OPEN INPUT sal-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"salario":0,"data_inicio":""}'
               STOP RUN END-IF
           MOVE 0 TO ws-salario
           MOVE SPACES TO ws-data-inicio
           PERFORM UNTIL 1 = 2
               READ sal-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF sal-func-id = ws-func-id AND sal-status = "ativo" THEN
                   MOVE sal-data-inicio(1:4) TO ws-dtini-n(1:4)
                   MOVE sal-data-inicio(6:2) TO ws-dtini-n(5:2)
                   IF sal-data-fim = SPACES THEN
                       MOVE SPACES TO ws-dtfim-n
                   ELSE
                       MOVE sal-data-fim(1:4) TO ws-dtfim-n(1:4)
                       MOVE sal-data-fim(6:2) TO ws-dtfim-n(5:2)
                   END-IF
                   IF ws-dtini-n <= ws-comp-n
                      AND (ws-dtfim-n = SPACES
                           OR ws-dtfim-n > ws-comp-n) THEN
                       IF ws-dtini-n >= ws-data-inicio-max THEN
                           MOVE sal-salario TO ws-salario
                           MOVE sal-data-inicio TO ws-data-inicio
                           MOVE ws-dtini-n TO ws-data-inicio-max
                       END-IF
                   END-IF
               END-IF
           END-PERFORM
           CLOSE sal-file
           MOVE ws-salario TO ws-salario-editado
           DISPLAY '{"salario":' FUNCTION TRIM(ws-salario-editado)
                   ',"data_inicio":"' FUNCTION TRIM(ws-data-inicio) '"}'.
