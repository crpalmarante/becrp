       >>SOURCE FORMAT IS FREE
       *> gerir_entregas.cbl — Delivery Order cabeçalho (SEQUENTIAL)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirEntregas.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT do-file ASSIGN TO "dados/entregas.dat"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO "dados/entregas.tmp"
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD do-file.
       01 do-reg.
           05 do-id              PIC X(24).
           05 do-origem-tipo     PIC X(20).
           05 do-origem-ref      PIC X(20).
           05 do-parceiro-id     PIC X(12).
           05 do-parceiro        PIC X(40).
           05 do-fonte           PIC X(12).
           05 do-fonte-nome      PIC X(30).
           05 do-status          PIC X(16).
           05 do-prioridade      PIC X(12).
           05 do-data            PIC X(10).
           05 do-janela          PIC X(12).
           05 do-recurso         PIC X(12).
           05 do-motorista       PIC X(30).
           05 do-veiculo         PIC X(12).
           05 do-expedicao       PIC X(20).
           05 do-manifesto       PIC X(20).
           05 do-obs             PIC X(60).
           05 do-seq             PIC 9(5).

       FD temp-file.
       01 temp-reg.
           05 td-id              PIC X(24).
           05 td-origem-tipo     PIC X(20).
           05 td-origem-ref      PIC X(20).
           05 td-parceiro-id     PIC X(12).
           05 td-parceiro        PIC X(40).
           05 td-fonte           PIC X(12).
           05 td-fonte-nome      PIC X(30).
           05 td-status          PIC X(16).
           05 td-prioridade      PIC X(12).
           05 td-data            PIC X(10).
           05 td-janela          PIC X(12).
           05 td-recurso         PIC X(12).
           05 td-motorista       PIC X(30).
           05 td-veiculo         PIC X(12).
           05 td-expedicao       PIC X(20).
           05 td-manifesto       PIC X(20).
           05 td-obs             PIC X(60).
           05 td-seq             PIC 9(5).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-encontrou       PIC X(1).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(5).
       01 ws-total-ed        PIC ZZZZ9.
       01 ws-prox            PIC 9(5).
       01 ws-seq-ed          PIC ZZZZ9.
       01 ws-id              PIC X(24).
       01 ws-origem-tipo     PIC X(20).
       01 ws-origem-ref      PIC X(20).
       01 ws-parceiro-id     PIC X(12).
       01 ws-parceiro        PIC X(40).
       01 ws-fonte           PIC X(12).
       01 ws-fonte-nome      PIC X(30).
       01 ws-status          PIC X(16).
       01 ws-prioridade      PIC X(12).
       01 ws-data            PIC X(10).
       01 ws-janela          PIC X(12).
       01 ws-recurso         PIC X(12).
       01 ws-motorista       PIC X(30).
       01 ws-veiculo         PIC X(12).
       01 ws-expedicao       PIC X(20).
       01 ws-manifesto       PIC X(20).
       01 ws-obs             PIC X(60).
       01 ws-seq             PIC 9(5).
       01 ws-seq-in          PIC X(8).
       01 ws-json            PIC X(900).

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
           ACCEPT ws-origem-tipo FROM ENVIRONMENT "ORIGEM_TIPO"
           ACCEPT ws-origem-ref FROM ENVIRONMENT "ORIGEM_REF"
           ACCEPT ws-parceiro-id FROM ENVIRONMENT "PARCEIRO_ID"
           ACCEPT ws-parceiro FROM ENVIRONMENT "PARCEIRO"
           ACCEPT ws-fonte FROM ENVIRONMENT "FONTE"
           ACCEPT ws-fonte-nome FROM ENVIRONMENT "FONTE_NOME"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           ACCEPT ws-prioridade FROM ENVIRONMENT "PRIORIDADE"
           ACCEPT ws-data FROM ENVIRONMENT "DATA_AGENDADA"
           ACCEPT ws-janela FROM ENVIRONMENT "JANELA"
           ACCEPT ws-recurso FROM ENVIRONMENT "RECURSO_ID"
           ACCEPT ws-motorista FROM ENVIRONMENT "MOTORISTA"
           ACCEPT ws-veiculo FROM ENVIRONMENT "VEICULO"
           ACCEPT ws-expedicao FROM ENVIRONMENT "EXPEDICAO_ID"
           ACCEPT ws-manifesto FROM ENVIRONMENT "MANIFESTO_ID"
           ACCEPT ws-obs FROM ENVIRONMENT "OBSERVACAO"
           ACCEPT ws-seq-in FROM ENVIRONMENT "SEQ"
           COMPUTE ws-seq = FUNCTION NUMVAL(ws-seq-in)
           IF ws-fonte = SPACES THEN MOVE "DC-01" TO ws-fonte END-IF
           IF ws-status = SPACES THEN MOVE "draft" TO ws-status END-IF
           IF ws-prioridade = SPACES THEN MOVE "normal" TO ws-prioridade END-IF
           IF ws-origem-tipo = SPACES THEN MOVE "manual" TO ws-origem-tipo END-IF.

       move-ws-to-do.
           MOVE ws-id TO do-id
           MOVE ws-origem-tipo TO do-origem-tipo
           MOVE ws-origem-ref TO do-origem-ref
           MOVE ws-parceiro-id TO do-parceiro-id
           MOVE ws-parceiro TO do-parceiro
           MOVE ws-fonte TO do-fonte
           MOVE ws-fonte-nome TO do-fonte-nome
           MOVE ws-status TO do-status
           MOVE ws-prioridade TO do-prioridade
           MOVE ws-data TO do-data
           MOVE ws-janela TO do-janela
           MOVE ws-recurso TO do-recurso
           MOVE ws-motorista TO do-motorista
           MOVE ws-veiculo TO do-veiculo
           MOVE ws-expedicao TO do-expedicao
           MOVE ws-manifesto TO do-manifesto
           MOVE ws-obs TO do-obs
           MOVE ws-seq TO do-seq.

       proximo-seq.
           MOVE 0 TO ws-prox
           OPEN INPUT do-file
           IF ws-fs = "35" THEN
               MOVE 1 TO ws-prox
               EXIT PARAGRAPH
           END-IF
           PERFORM UNTIL 1 = 2
               READ do-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF do-seq > ws-prox THEN MOVE do-seq TO ws-prox END-IF
           END-PERFORM
           CLOSE do-file
           ADD 1 TO ws-prox.

       incluir.
           PERFORM accept-fields
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           IF ws-seq = 0 THEN
               PERFORM proximo-seq
               MOVE ws-prox TO ws-seq
           END-IF
           IF ws-id = SPACES THEN
               MOVE ws-seq TO ws-seq-ed
               STRING "DO-" ws-seq-ed DELIMITED BY SIZE INTO ws-id
           END-IF
           OPEN INPUT do-file
           IF ws-fs = "35" THEN
               OPEN OUTPUT do-file CLOSE do-file
           ELSE CLOSE do-file END-IF
           OPEN EXTEND do-file
           PERFORM move-ws-to-do
           WRITE do-reg
           CLOSE do-file
           DISPLAY FUNCTION TRIM(ws-id).

       alterar.
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           IF ws-id = SPACES THEN
               DISPLAY "ERRO: id obrigatorio" STOP RUN END-IF
           PERFORM accept-fields
           OPEN INPUT do-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ do-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(do-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-id)) THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-seq = 0 THEN MOVE do-seq TO ws-seq END-IF
                   PERFORM move-ws-to-do
                   MOVE do-reg TO temp-reg
                   WRITE temp-reg
               ELSE
                   MOVE do-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE do-file CLOSE temp-file
           CALL "system" USING "mv dados/entregas.tmp dados/entregas.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: entrega nao encontrada".

       excluir.
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           OPEN INPUT do-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: arquivo vazio" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ do-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(do-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-id)) THEN
                   MOVE "S" TO ws-encontrou
               ELSE
                   MOVE do-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE do-file CLOSE temp-file
           CALL "system" USING "mv dados/entregas.tmp dados/entregas.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: entrega nao encontrada".

       buscar.
           ACCEPT ws-id FROM ENVIRONMENT "ID"
           OPEN INPUT do-file
           IF ws-fs = "35" THEN
               DISPLAY '{"status":"erro"}' STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ do-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(do-id)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-id)) THEN
                   PERFORM emit-json
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE do-file
           IF ws-encontrou = "N" THEN DISPLAY '{"status":"erro"}'.

       listar.
           OPEN INPUT do-file
           IF ws-fs = "35" THEN
               DISPLAY '{"entregas":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"entregas":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ do-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE do-file.

       emit-json.
           MOVE do-seq TO ws-seq-ed
           MOVE SPACES TO ws-json
           STRING '{"id":"' FUNCTION TRIM(do-id) '"'
                  ',"origem_tipo":"' FUNCTION TRIM(do-origem-tipo) '"'
                  ',"origem_ref":"' FUNCTION TRIM(do-origem-ref) '"'
                  ',"parceiro_id":"' FUNCTION TRIM(do-parceiro-id) '"'
                  ',"parceiro":"' FUNCTION TRIM(do-parceiro) '"'
                  ',"fonte":"' FUNCTION TRIM(do-fonte) '"'
                  ',"fonte_nome":"' FUNCTION TRIM(do-fonte-nome) '"'
                  ',"status":"' FUNCTION TRIM(do-status) '"'
                  ',"prioridade":"' FUNCTION TRIM(do-prioridade) '"'
                  ',"data_agendada":"' FUNCTION TRIM(do-data) '"'
                  ',"janela":"' FUNCTION TRIM(do-janela) '"'
                  ',"recurso_id":"' FUNCTION TRIM(do-recurso) '"'
                  ',"motorista":"' FUNCTION TRIM(do-motorista) '"'
                  ',"veiculo":"' FUNCTION TRIM(do-veiculo) '"'
                  ',"expedicao_id":"' FUNCTION TRIM(do-expedicao) '"'
                  ',"manifesto_id":"' FUNCTION TRIM(do-manifesto) '"'
                  ',"observacao":"' FUNCTION TRIM(do-obs) '"'
                  ',"seq":' FUNCTION TRIM(ws-seq-ed) '}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
