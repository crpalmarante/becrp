       >>SOURCE FORMAT IS FREE
       *> gerir_movimentacoes.cbl - Movimentacoes contratuais com vigencia
       *> (RFC-016 / RFC-002 regra 3): alteracoes de CARGO e DEPARTAMENTO
       *> registram valor (id de cargo/departamento) + data de inicio de
       *> vigencia. O valor vigente em uma competencia e o registro ATIVO
       *> do tipo com maior data_inicio <= competencia e (data_fim vazio ou
       *> data_fim > competencia).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirMovimentacoes.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT mv-file ASSIGN TO "dados/movimentacoes.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/movimentacoes.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD mv-file.
       01 mv-reg.
           05 mv-id              PIC 9(4).
           05 mv-func-id         PIC 9(3).
           05 mv-tipo            PIC X(20).
           05 mv-valor-ref       PIC 9(3).
           05 mv-data-inicio     PIC X(10).
           05 mv-data-fim        PIC X(10).
           05 mv-status          PIC X(8).

       FD temp-file.
       01 temp-reg.
           05 tl-id              PIC 9(4).
           05 tl-func-id         PIC 9(3).
           05 tl-tipo            PIC X(20).
           05 tl-valor-ref       PIC 9(3).
           05 tl-data-inicio     PIC X(10).
           05 tl-data-fim        PIC X(10).
           05 tl-status          PIC X(8).

       WORKING-STORAGE SECTION.
       01 ws-acao           PIC X(20).
       01 ws-file-status    PIC X(2).
       01 ws-primeiro       PIC X.
       01 ws-prox-id        PIC 9(4).
       01 ws-total          PIC 9(4).
       01 ws-total-ed       PIC Z(3)9.
       01 ws-id-ed          PIC Z(3)9.
       01 ws-func-ed        PIC Z(2)9.
       01 ws-valor-ed       PIC Z(2)9.
       01 ws-id-in          PIC X(6).
       01 ws-func-in        PIC X(6).
       01 ws-valor-in       PIC X(6).
       01 ws-id             PIC 9(4).
       01 ws-func-id        PIC 9(3).
       01 ws-valor-ref      PIC 9(3).
       01 ws-tipo           PIC X(20).
       01 ws-data-inicio    PIC X(10).
       01 ws-data-inicio-max PIC X(6).
       01 ws-data-fim       PIC X(10).
       01 ws-status         PIC X(8).
       01 ws-competencia    PIC X(10).
       01 ws-json-linha     PIC X(400).
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
           ACCEPT ws-tipo FROM ENVIRONMENT "TIPO"
           IF ws-tipo = SPACES THEN
               DISPLAY "ERRO: tipo obrigatorio (cargo|departamento)"
               STOP RUN END-IF
           ACCEPT ws-valor-in FROM ENVIRONMENT "VALOR_REFERENCIA"
           IF ws-valor-in = SPACES THEN
               DISPLAY "ERRO: valor de referencia obrigatorio"
               STOP RUN END-IF
           COMPUTE ws-valor-ref = FUNCTION NUMVAL(ws-valor-in)
           ACCEPT ws-data-inicio FROM ENVIRONMENT "DATA_INICIO"
           IF ws-data-inicio = SPACES THEN
               DISPLAY "ERRO: data de inicio de vigencia obrigatoria"
               STOP RUN END-IF

           MOVE 0 TO ws-prox-id
           OPEN INPUT mv-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT mv-file CLOSE mv-file
               OPEN INPUT mv-file END-IF
           PERFORM UNTIL 1 = 2
               READ mv-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF mv-id > ws-prox-id THEN MOVE mv-id TO ws-prox-id END-IF
           END-PERFORM
           CLOSE mv-file
           ADD 1 TO ws-prox-id

           *> Fecha o registro vigente anterior do MESMO tipo e funcionario
           *> (data_fim = inicio do novo), reescrevendo em temp.
           OPEN INPUT mv-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: falha ao abrir historico" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ mv-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF mv-func-id = ws-func-id AND mv-tipo = ws-tipo
                  AND mv-status = "ativo"
                  AND mv-data-fim = SPACES
                  AND mv-data-inicio < ws-data-inicio THEN
                   MOVE ws-data-inicio TO mv-data-fim
               END-IF
               MOVE mv-id TO tl-id
               MOVE mv-func-id TO tl-func-id
               MOVE mv-tipo TO tl-tipo
               MOVE mv-valor-ref TO tl-valor-ref
               MOVE mv-data-inicio TO tl-data-inicio
               MOVE mv-data-fim TO tl-data-fim
               MOVE mv-status TO tl-status
               WRITE temp-reg
           END-PERFORM
           CLOSE mv-file CLOSE temp-file
           CALL "system" USING "mv dados/movimentacoes.tmp dados/movimentacoes.dat"
           END-CALL

           OPEN EXTEND mv-file
           MOVE ws-prox-id TO mv-id
           MOVE ws-func-id TO mv-func-id
           MOVE ws-tipo TO mv-tipo
           MOVE ws-valor-ref TO mv-valor-ref
           MOVE ws-data-inicio TO mv-data-inicio
           MOVE SPACES TO mv-data-fim
           MOVE "ativo" TO mv-status
           WRITE mv-reg
           CLOSE mv-file
           DISPLAY ws-prox-id.

       listar.
           ACCEPT ws-func-in FROM ENVIRONMENT "FUNCIONARIO_ID"
           COMPUTE ws-func-id = FUNCTION NUMVAL(ws-func-in)
           ACCEPT ws-tipo FROM ENVIRONMENT "TIPO"
           IF ws-tipo = SPACES THEN MOVE "cargo" TO ws-tipo END-IF

           OPEN INPUT mv-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"movimentacoes":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"movimentacoes":['
           MOVE "S" TO ws-primeiro
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ mv-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF mv-func-id = ws-func-id AND mv-tipo = ws-tipo
                  AND mv-status = "ativo" THEN
                   ADD 1 TO ws-total
                   IF ws-primeiro = "S" THEN
                       MOVE "N" TO ws-primeiro
                   ELSE DISPLAY "," END-IF
                   MOVE mv-id TO ws-id-ed
                   MOVE mv-func-id TO ws-func-ed
                   MOVE mv-valor-ref TO ws-valor-ed
                   MOVE SPACES TO ws-json-linha
                   STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                          ',"funcionario_id":' FUNCTION TRIM(ws-func-ed)
                          ',"tipo":"' FUNCTION TRIM(mv-tipo) '"'
                          ',"valor_referencia":' FUNCTION TRIM(ws-valor-ed)
                          ',"data_inicio":"' FUNCTION TRIM(mv-data-inicio) '"'
                          ',"data_fim":"' FUNCTION TRIM(mv-data-fim) '"'
                          ',"status":"' FUNCTION TRIM(mv-status) '"}'
                       INTO ws-json-linha
                   DISPLAY FUNCTION TRIM(ws-json-linha)
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE mv-file.

       vigente.
           ACCEPT ws-func-in FROM ENVIRONMENT "FUNCIONARIO_ID"
           COMPUTE ws-func-id = FUNCTION NUMVAL(ws-func-in)
           ACCEPT ws-tipo FROM ENVIRONMENT "TIPO"
           IF ws-tipo = SPACES THEN MOVE "cargo" TO ws-tipo END-IF
           ACCEPT ws-competencia FROM ENVIRONMENT "COMPETENCIA"

           *> Normaliza competencia "YYYY/MM" e datas "YYYY-MM-DD" para "YYYYMM"
           MOVE ws-competencia(1:4) TO ws-comp-n(1:4)
           MOVE ws-competencia(6:2) TO ws-comp-n(5:2)

           OPEN INPUT mv-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"valor_referencia":0,"data_inicio":""}'
               STOP RUN END-IF
           MOVE 0 TO ws-valor-ref
           MOVE SPACES TO ws-data-inicio
           PERFORM UNTIL 1 = 2
               READ mv-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF mv-func-id = ws-func-id AND mv-tipo = ws-tipo
                  AND mv-status = "ativo" THEN
                   MOVE mv-data-inicio(1:4) TO ws-dtini-n(1:4)
                   MOVE mv-data-inicio(6:2) TO ws-dtini-n(5:2)
                   IF mv-data-fim = SPACES THEN
                       MOVE SPACES TO ws-dtfim-n
                   ELSE
                       MOVE mv-data-fim(1:4) TO ws-dtfim-n(1:4)
                       MOVE mv-data-fim(6:2) TO ws-dtfim-n(5:2)
                   END-IF
                   IF ws-dtini-n <= ws-comp-n
                      AND (ws-dtfim-n = SPACES
                           OR ws-dtfim-n > ws-comp-n) THEN
                       IF ws-dtini-n >= ws-data-inicio-max THEN
                           MOVE mv-valor-ref TO ws-valor-ref
                           MOVE mv-data-inicio TO ws-data-inicio
                           MOVE ws-dtini-n TO ws-data-inicio-max
                       END-IF
                   END-IF
               END-IF
           END-PERFORM
           CLOSE mv-file
           MOVE ws-valor-ref TO ws-valor-ed
           DISPLAY '{"valor_referencia":' FUNCTION TRIM(ws-valor-ed)
                   ',"data_inicio":"' FUNCTION TRIM(ws-data-inicio) '"}'.
