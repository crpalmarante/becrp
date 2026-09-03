       >>SOURCE FORMAT IS FREE
       *> gerir_localizacoes.cbl — WMS locations CRUD (SEQUENTIAL)
       *> Fonte da verdade das localizações do armazém (piloto WMS → COBOL).
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirLocalizacoes.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT loc-file ASSIGN TO ws-loc-path
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.
           SELECT temp-file ASSIGN TO ws-temp-path
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL
               FILE STATUS IS ws-fs.

       DATA DIVISION.
       FILE SECTION.
       FD loc-file.
       01 loc-reg.
           05 loc-codigo          PIC X(32).
           05 loc-nome            PIC X(100).
           05 loc-tipo            PIC X(20).
           05 loc-armazem         PIC X(16).
           05 loc-area            PIC X(12).
           05 loc-zona            PIC X(24).
           05 loc-corredor        PIC X(12).
           05 loc-rack            PIC X(12).
           05 loc-nivel           PIC X(12).
           05 loc-posicao         PIC X(12).
           05 loc-capacidade      PIC 9(9).
           05 loc-peso-max        PIC 9(9).
           05 loc-volume-max      PIC 9(9)V99.
           05 loc-status          PIC X(10).
           05 loc-bloqueio        PIC X(120).
           05 loc-origem          PIC X(20).
           05 loc-atualizado      PIC X(20).

       FD temp-file.
       01 temp-reg.
           05 tn-codigo           PIC X(32).
           05 tn-nome             PIC X(100).
           05 tn-tipo             PIC X(20).
           05 tn-armazem          PIC X(16).
           05 tn-area             PIC X(12).
           05 tn-zona             PIC X(24).
           05 tn-corredor         PIC X(12).
           05 tn-rack             PIC X(12).
           05 tn-nivel            PIC X(12).
           05 tn-posicao          PIC X(12).
           05 tn-capacidade       PIC 9(9).
           05 tn-peso-max         PIC 9(9).
           05 tn-volume-max       PIC 9(9)V99.
           05 tn-status           PIC X(10).
           05 tn-bloqueio         PIC X(120).
           05 tn-origem           PIC X(20).
           05 tn-atualizado       PIC X(20).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-fs              PIC X(2).
       01 ws-encontrou       PIC X(1).
       01 ws-first           PIC X(1).
       01 ws-total           PIC 9(6).
       01 ws-total-ed        PIC ZZZZZ9.
       01 ws-codigo          PIC X(32).
       01 ws-nome            PIC X(100).
       01 ws-tipo            PIC X(20).
       01 ws-armazem         PIC X(16).
       01 ws-area            PIC X(12).
       01 ws-zona            PIC X(24).
       01 ws-corredor        PIC X(12).
       01 ws-rack            PIC X(12).
       01 ws-nivel           PIC X(12).
       01 ws-posicao         PIC X(12).
       01 ws-capacidade-in   PIC X(15).
       01 ws-peso-in         PIC X(15).
       01 ws-volume-in       PIC X(15).
       01 ws-status          PIC X(10).
       01 ws-bloqueio        PIC X(120).
       01 ws-origem          PIC X(20).
       01 ws-atualizado      PIC X(20).
       01 ws-cap-ed          PIC Z(8)9.
       01 ws-peso-ed         PIC Z(8)9.
       01 ws-volume-ed       PIC Z(8)9.99.
       01 ws-cap-json        PIC X(30).
       01 ws-peso-json       PIC X(30).
       01 ws-volume-json     PIC X(30).
       01 ws-json            PIC X(2000).
       01 ws-loc-path        PIC X(120).
       01 ws-temp-path       PIC X(120).
       01 ws-mv-cmd          PIC X(300).

       PROCEDURE DIVISION.
           ACCEPT ws-loc-path FROM ENVIRONMENT "LOCALIZACOES_DAT"
           IF ws-loc-path = SPACES THEN
               MOVE "dados/localizacoes.dat" TO ws-loc-path END-IF
           ACCEPT ws-temp-path FROM ENVIRONMENT "LOCALIZACOES_TMP"
           IF ws-temp-path = SPACES THEN
               MOVE "dados/localizacoes.tmp" TO ws-temp-path END-IF
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
           ACCEPT ws-codigo FROM ENVIRONMENT "CODIGO"
           ACCEPT ws-nome FROM ENVIRONMENT "NOME"
           ACCEPT ws-tipo FROM ENVIRONMENT "TIPO"
           ACCEPT ws-armazem FROM ENVIRONMENT "ARMAZEM"
           ACCEPT ws-area FROM ENVIRONMENT "AREA"
           ACCEPT ws-zona FROM ENVIRONMENT "ZONA"
           ACCEPT ws-corredor FROM ENVIRONMENT "CORREDOR"
           ACCEPT ws-rack FROM ENVIRONMENT "RACK"
           ACCEPT ws-nivel FROM ENVIRONMENT "NIVEL"
           ACCEPT ws-posicao FROM ENVIRONMENT "POSICAO"
           ACCEPT ws-capacidade-in FROM ENVIRONMENT "CAPACIDADE"
           ACCEPT ws-peso-in FROM ENVIRONMENT "PESO_MAX"
           ACCEPT ws-volume-in FROM ENVIRONMENT "VOLUME_MAX"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           ACCEPT ws-bloqueio FROM ENVIRONMENT "BLOQUEIO"
           ACCEPT ws-origem FROM ENVIRONMENT "ORIGEM"
           ACCEPT ws-atualizado FROM ENVIRONMENT "ATUALIZADO"
           IF ws-tipo = SPACES THEN MOVE "storage" TO ws-tipo END-IF
           IF ws-status = SPACES THEN MOVE "available" TO ws-status END-IF
           IF ws-origem = SPACES THEN MOVE "manual" TO ws-origem END-IF
           IF ws-capacidade-in = SPACES THEN MOVE "0" TO ws-capacidade-in END-IF
           IF ws-peso-in = SPACES THEN MOVE "0" TO ws-peso-in END-IF
           IF ws-volume-in = SPACES THEN MOVE "0" TO ws-volume-in END-IF.

       move-ws-to-loc.
           MOVE ws-codigo TO loc-codigo
           MOVE ws-nome TO loc-nome
           MOVE ws-tipo TO loc-tipo
           MOVE ws-armazem TO loc-armazem
           MOVE ws-area TO loc-area
           MOVE ws-zona TO loc-zona
           MOVE ws-corredor TO loc-corredor
           MOVE ws-rack TO loc-rack
           MOVE ws-nivel TO loc-nivel
           MOVE ws-posicao TO loc-posicao
           COMPUTE loc-capacidade = FUNCTION NUMVAL(ws-capacidade-in)
           COMPUTE loc-peso-max = FUNCTION NUMVAL(ws-peso-in)
           COMPUTE loc-volume-max = FUNCTION NUMVAL(ws-volume-in)
           MOVE ws-status TO loc-status
           MOVE ws-bloqueio TO loc-bloqueio
           MOVE ws-origem TO loc-origem
           MOVE ws-atualizado TO loc-atualizado.

       incluir.
           PERFORM accept-fields
           IF ws-codigo = SPACES THEN
               DISPLAY "ERRO: codigo obrigatorio" STOP RUN END-IF
           IF ws-nome = SPACES THEN
               DISPLAY "ERRO: nome obrigatorio" STOP RUN END-IF
           IF ws-armazem = SPACES THEN
               DISPLAY "ERRO: armazem obrigatorio" STOP RUN END-IF
           IF ws-area = SPACES THEN
               DISPLAY "ERRO: area obrigatoria" STOP RUN END-IF
           OPEN INPUT loc-file
           IF ws-fs NOT = "35" THEN
               MOVE "N" TO ws-encontrou
               PERFORM UNTIL 1 = 2
                   READ loc-file NEXT RECORD
                       AT END EXIT PERFORM
                   END-READ
                   IF FUNCTION UPPER-CASE(FUNCTION TRIM(loc-codigo)) =
                      FUNCTION UPPER-CASE(FUNCTION TRIM(ws-codigo)) THEN
                       MOVE "S" TO ws-encontrou
                   END-IF
               END-PERFORM
               CLOSE loc-file
               IF ws-encontrou = "S" THEN
                   DISPLAY "ERRO: codigo ja existe" STOP RUN END-IF
           ELSE
               CLOSE loc-file
               OPEN OUTPUT loc-file CLOSE loc-file
           END-IF
           OPEN EXTEND loc-file
           PERFORM move-ws-to-loc
           WRITE loc-reg
           CLOSE loc-file
           DISPLAY FUNCTION TRIM(ws-codigo).

       alterar.
           ACCEPT ws-codigo FROM ENVIRONMENT "CODIGO"
           IF ws-codigo = SPACES THEN
               DISPLAY "ERRO: codigo obrigatorio" STOP RUN END-IF
           PERFORM accept-fields
           OPEN INPUT loc-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: localizacao nao encontrada" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ loc-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(loc-codigo)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-codigo)) THEN
                   MOVE "S" TO ws-encontrou
                   PERFORM move-ws-to-loc
                   MOVE loc-reg TO temp-reg
                   WRITE temp-reg
               ELSE
                   MOVE loc-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE loc-file CLOSE temp-file
           STRING "mv " FUNCTION TRIM(ws-temp-path) " "
                  FUNCTION TRIM(ws-loc-path) INTO ws-mv-cmd
           CALL "system" USING ws-mv-cmd
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: localizacao nao encontrada".

       excluir.
           ACCEPT ws-codigo FROM ENVIRONMENT "CODIGO"
           IF ws-codigo = SPACES THEN
               DISPLAY "ERRO: codigo obrigatorio" STOP RUN END-IF
           OPEN INPUT loc-file
           IF ws-fs = "35" THEN
               DISPLAY "ERRO: localizacao nao encontrada" STOP RUN END-IF
           OPEN OUTPUT temp-file
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ loc-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(loc-codigo)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-codigo)) THEN
                   MOVE "S" TO ws-encontrou
               ELSE
                   MOVE loc-reg TO temp-reg
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE loc-file CLOSE temp-file
           STRING "mv " FUNCTION TRIM(ws-temp-path) " "
                  FUNCTION TRIM(ws-loc-path) INTO ws-mv-cmd
           CALL "system" USING ws-mv-cmd
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: localizacao nao encontrada".

       buscar.
           ACCEPT ws-codigo FROM ENVIRONMENT "CODIGO"
           OPEN INPUT loc-file
           IF ws-fs = "35" THEN
               DISPLAY '{"status":"erro"}' STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ loc-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF FUNCTION UPPER-CASE(FUNCTION TRIM(loc-codigo)) =
                  FUNCTION UPPER-CASE(FUNCTION TRIM(ws-codigo)) THEN
                   PERFORM emit-json
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE loc-file
           IF ws-encontrou = "N" THEN DISPLAY '{"status":"erro"}'.

       listar.
           OPEN INPUT loc-file
           IF ws-fs = "35" THEN
               DISPLAY '{"localizacoes":[],"total":0}' STOP RUN END-IF
           DISPLAY '{"localizacoes":['
           MOVE "S" TO ws-first
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ loc-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-first = "S" THEN MOVE "N" TO ws-first
               ELSE DISPLAY "," END-IF
               PERFORM emit-json
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE loc-file.

       emit-json.
           MOVE SPACES TO ws-cap-json ws-peso-json ws-volume-json
           IF loc-capacidade = 0 THEN
               MOVE ',"capacidade_qtd":null' TO ws-cap-json
           ELSE
               MOVE loc-capacidade TO ws-cap-ed
               STRING ',"capacidade_qtd":' FUNCTION TRIM(ws-cap-ed)
                   INTO ws-cap-json
           END-IF
           IF loc-peso-max = 0 THEN
               MOVE ',"peso_max_kg":null' TO ws-peso-json
           ELSE
               MOVE loc-peso-max TO ws-peso-ed
               STRING ',"peso_max_kg":' FUNCTION TRIM(ws-peso-ed)
                   INTO ws-peso-json
           END-IF
           IF loc-volume-max = 0 THEN
               MOVE ',"volume_max_m3":null' TO ws-volume-json
           ELSE
               MOVE loc-volume-max TO ws-volume-ed
               STRING ',"volume_max_m3":' FUNCTION TRIM(ws-volume-ed)
                   INTO ws-volume-json
           END-IF
           MOVE SPACES TO ws-json
           STRING '{"codigo":"' FUNCTION TRIM(loc-codigo) '"'
                  ',"nome":"' FUNCTION TRIM(loc-nome) '"'
                  ',"tipo":"' FUNCTION TRIM(loc-tipo) '"'
                  ',"armazem":"' FUNCTION TRIM(loc-armazem) '"'
                  ',"area":"' FUNCTION TRIM(loc-area) '"'
                  ',"zona":"' FUNCTION TRIM(loc-zona) '"'
                  ',"corredor":"' FUNCTION TRIM(loc-corredor) '"'
                  ',"rack":"' FUNCTION TRIM(loc-rack) '"'
                  ',"nivel":"' FUNCTION TRIM(loc-nivel) '"'
                  ',"posicao":"' FUNCTION TRIM(loc-posicao) '"'
                  FUNCTION TRIM(ws-cap-json)
                  FUNCTION TRIM(ws-peso-json)
                  FUNCTION TRIM(ws-volume-json)
                  ',"status":"' FUNCTION TRIM(loc-status) '"'
                  ',"bloqueio_motivo":"' FUNCTION TRIM(loc-bloqueio) '"'
                  ',"origem":"' FUNCTION TRIM(loc-origem) '"'
                  ',"atualizado_em":"' FUNCTION TRIM(loc-atualizado) '"}'
               INTO ws-json
           DISPLAY FUNCTION TRIM(ws-json).
