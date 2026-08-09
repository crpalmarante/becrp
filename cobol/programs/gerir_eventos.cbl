       >>SOURCE FORMAT IS FREE
       *> gerir_eventos.cbl - CRUD de eventos da folha (RFC-004)
       *> Evento = menor unidade de crédito (provento) ou débito (desconto)
       *> que entra na folha. Inativação lógica: NUNCA exclusão física.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirEventos.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ev-file ASSIGN TO "dados/eventos.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/eventos.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD ev-file.
       01 ev-reg.
           05 ev-id              PIC 9(3).
           05 ev-codigo          PIC 9(3).
           05 ev-descricao       PIC X(40).
           05 ev-tipo            PIC X(12).
           05 ev-categoria       PIC X(20).
           05 ev-referencia      PIC X(20).
           05 ev-formula         PIC X(60).
           05 ev-incide-inss     PIC X.
           05 ev-incide-irrf     PIC X.
           05 ev-incide-fgts     PIC X.
           05 ev-ordem           PIC 9(3).
           05 ev-uso             PIC X(30).
           05 ev-teto            PIC 9(7)V99.
           05 ev-status          PIC X(8).

       FD temp-file.
       01 temp-reg.
           05 tl-id              PIC 9(3).
           05 tl-codigo          PIC 9(3).
           05 tl-descricao       PIC X(40).
           05 tl-tipo            PIC X(12).
           05 tl-categoria       PIC X(20).
           05 tl-referencia      PIC X(20).
           05 tl-formula         PIC X(60).
           05 tl-incide-inss     PIC X.
           05 tl-incide-irrf     PIC X.
           05 tl-incide-fgts     PIC X.
           05 tl-ordem           PIC 9(3).
           05 tl-uso             PIC X(30).
           05 tl-teto            PIC 9(7)V99.
           05 tl-status          PIC X(8).

       WORKING-STORAGE SECTION.
       01 ws-acao           PIC X(20).
       01 ws-file-status    PIC X(2).
       01 ws-encontrou      PIC X.
       01 ws-prox-id        PIC 9(3).
       01 ws-total          PIC 9(4).
       01 ws-total-ed       PIC Z(3)9.
       01 ws-id-ed          PIC Z(3)9.
       01 ws-codigo-ed      PIC Z(3)9.
       01 ws-ordem-ed       PIC Z(3)9.
       01 ws-teto-ed        PIC Z(7)9.99.
       01 ws-id-in          PIC X(5).
       01 ws-id             PIC 9(3).
       01 ws-codigo-in      PIC X(5).
       01 ws-codigo         PIC 9(3).
       01 ws-descricao      PIC X(40).
       01 ws-tipo           PIC X(12).
       01 ws-categoria      PIC X(20).
       01 ws-referencia     PIC X(20).
       01 ws-formula        PIC X(60).
       01 ws-incide-inss    PIC X.
       01 ws-incide-irrf    PIC X.
       01 ws-incide-fgts    PIC X.
       01 ws-ordem-in       PIC X(5).
       01 ws-ordem          PIC 9(3).
       01 ws-uso            PIC X(30).
       01 ws-teto-in        PIC X(12).
       01 ws-teto           PIC 9(7)V99.
       01 ws-status         PIC X(8).
       01 ws-duplicado      PIC X.
       01 ws-json-linha     PIC X(600).

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
           ACCEPT ws-codigo-in FROM ENVIRONMENT "CODIGO"
           COMPUTE ws-codigo = FUNCTION NUMVAL(ws-codigo-in)
           ACCEPT ws-descricao FROM ENVIRONMENT "DESCRICAO"
           ACCEPT ws-tipo FROM ENVIRONMENT "TIPO"
           ACCEPT ws-categoria FROM ENVIRONMENT "CATEGORIA"
           ACCEPT ws-referencia FROM ENVIRONMENT "REFERENCIA"
           ACCEPT ws-formula FROM ENVIRONMENT "FORMULA"
           ACCEPT ws-incide-inss FROM ENVIRONMENT "INCIDE_INSS"
           ACCEPT ws-incide-irrf FROM ENVIRONMENT "INCIDE_IRRF"
           ACCEPT ws-incide-fgts FROM ENVIRONMENT "INCIDE_FGTS"
           ACCEPT ws-ordem-in FROM ENVIRONMENT "ORDEM"
           ACCEPT ws-uso FROM ENVIRONMENT "USO"
           ACCEPT ws-teto-in FROM ENVIRONMENT "TETO"
           IF ws-codigo = 0 THEN
               DISPLAY "ERRO: codigo obrigatorio" STOP RUN END-IF
           IF ws-descricao = SPACES THEN
               DISPLAY "ERRO: descricao obrigatoria" STOP RUN END-IF
           PERFORM validar-tipo
           COMPUTE ws-ordem = FUNCTION NUMVAL(ws-ordem-in)
           COMPUTE ws-teto = FUNCTION NUMVAL(ws-teto-in)
           IF ws-incide-inss NOT = "S" THEN MOVE "N" TO ws-incide-inss END-IF
           IF ws-incide-irrf NOT = "S" THEN MOVE "N" TO ws-incide-irrf END-IF
           IF ws-incide-fgts NOT = "S" THEN MOVE "N" TO ws-incide-fgts END-IF

           MOVE 0 TO ws-prox-id
           OPEN INPUT ev-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT ev-file CLOSE ev-file
               OPEN INPUT ev-file END-IF
           PERFORM UNTIL 1 = 2
               READ ev-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF ev-id > ws-prox-id THEN MOVE ev-id TO ws-prox-id END-IF
               IF ev-codigo = ws-codigo AND ev-status NOT = "inativo" THEN
                   DISPLAY "ERRO: codigo de evento ja cadastrado"
                   STOP RUN END-IF
           END-PERFORM
           CLOSE ev-file
           ADD 1 TO ws-prox-id

           OPEN EXTEND ev-file
           MOVE ws-prox-id TO ev-id
           MOVE ws-codigo TO ev-codigo
           MOVE ws-descricao TO ev-descricao
           MOVE ws-tipo TO ev-tipo
           MOVE ws-categoria TO ev-categoria
           MOVE ws-referencia TO ev-referencia
           MOVE ws-formula TO ev-formula
           MOVE ws-incide-inss TO ev-incide-inss
           MOVE ws-incide-irrf TO ev-incide-irrf
           MOVE ws-incide-fgts TO ev-incide-fgts
           MOVE ws-ordem TO ev-ordem
           MOVE ws-uso TO ev-uso
           MOVE ws-teto TO ev-teto
           MOVE "ativo" TO ev-status
           WRITE ev-reg
           CLOSE ev-file
           DISPLAY ws-prox-id.

       validar-tipo.
           EVALUATE ws-tipo
               WHEN "provento"    CONTINUE
               WHEN "desconto"    CONTINUE
               WHEN "informativo" CONTINUE
               WHEN OTHER
                   DISPLAY "ERRO: tipo de evento invalido (provento|desconto|informativo)"
                   STOP RUN
           END-EVALUATE.

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-codigo-in FROM ENVIRONMENT "CODIGO"
           ACCEPT ws-descricao FROM ENVIRONMENT "DESCRICAO"
           ACCEPT ws-tipo FROM ENVIRONMENT "TIPO"
           ACCEPT ws-categoria FROM ENVIRONMENT "CATEGORIA"
           ACCEPT ws-referencia FROM ENVIRONMENT "REFERENCIA"
           ACCEPT ws-formula FROM ENVIRONMENT "FORMULA"
           ACCEPT ws-incide-inss FROM ENVIRONMENT "INCIDE_INSS"
           ACCEPT ws-incide-irrf FROM ENVIRONMENT "INCIDE_IRRF"
           ACCEPT ws-incide-fgts FROM ENVIRONMENT "INCIDE_FGTS"
           ACCEPT ws-ordem-in FROM ENVIRONMENT "ORDEM"
           ACCEPT ws-uso FROM ENVIRONMENT "USO"
           ACCEPT ws-teto-in FROM ENVIRONMENT "TETO"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           IF ws-tipo NOT = SPACES THEN PERFORM validar-tipo END-IF

      *>   Código novo não pode colidir com outro evento ativo
           IF ws-codigo-in NOT = SPACES THEN
               COMPUTE ws-codigo = FUNCTION NUMVAL(ws-codigo-in)
               MOVE "N" TO ws-duplicado
               OPEN INPUT ev-file
               IF ws-file-status NOT = "35" THEN
                   PERFORM UNTIL 1 = 2
                       READ ev-file NEXT RECORD
                           AT END EXIT PERFORM
                       END-READ
                       IF ev-id NOT = ws-id AND ev-codigo = ws-codigo
                           AND ev-status NOT = "inativo" THEN
                           MOVE "S" TO ws-duplicado
                       END-IF
                   END-PERFORM
               END-IF
               CLOSE ev-file
               IF ws-duplicado = "S" THEN
                   DISPLAY "ERRO: codigo de evento ja cadastrado"
                   STOP RUN END-IF
           END-IF

           MOVE "N" TO ws-encontrou
           OPEN INPUT ev-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: evento nao encontrado" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ ev-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF ev-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-codigo-in NOT = SPACES THEN
                       COMPUTE ws-codigo = FUNCTION NUMVAL(ws-codigo-in)
                       MOVE ws-codigo TO ev-codigo END-IF
                   IF ws-descricao NOT = SPACES THEN
                       MOVE ws-descricao TO ev-descricao END-IF
                   IF ws-tipo NOT = SPACES THEN MOVE ws-tipo TO ev-tipo END-IF
                   IF ws-categoria NOT = SPACES THEN
                       MOVE ws-categoria TO ev-categoria END-IF
                   IF ws-referencia NOT = SPACES THEN
                       MOVE ws-referencia TO ev-referencia END-IF
                   IF ws-formula NOT = SPACES THEN
                       MOVE ws-formula TO ev-formula END-IF
                   IF ws-incide-inss NOT = SPACES THEN
                       MOVE ws-incide-inss TO ev-incide-inss END-IF
                   IF ws-incide-irrf NOT = SPACES THEN
                       MOVE ws-incide-irrf TO ev-incide-irrf END-IF
                   IF ws-incide-fgts NOT = SPACES THEN
                       MOVE ws-incide-fgts TO ev-incide-fgts END-IF
                   IF ws-ordem-in NOT = SPACES THEN
                       COMPUTE ws-ordem = FUNCTION NUMVAL(ws-ordem-in)
                       MOVE ws-ordem TO ev-ordem END-IF
                   IF ws-uso NOT = SPACES THEN MOVE ws-uso TO ev-uso END-IF
                   IF ws-teto-in NOT = SPACES THEN
                       COMPUTE ws-teto = FUNCTION NUMVAL(ws-teto-in)
                       MOVE ws-teto TO ev-teto END-IF
                   IF ws-status NOT = SPACES THEN MOVE ws-status TO ev-status END-IF
               END-IF
               MOVE ev-id TO tl-id
               MOVE ev-codigo TO tl-codigo
               MOVE ev-descricao TO tl-descricao
               MOVE ev-tipo TO tl-tipo
               MOVE ev-categoria TO tl-categoria
               MOVE ev-referencia TO tl-referencia
               MOVE ev-formula TO tl-formula
               MOVE ev-incide-inss TO tl-incide-inss
               MOVE ev-incide-irrf TO tl-incide-irrf
               MOVE ev-incide-fgts TO tl-incide-fgts
               MOVE ev-ordem TO tl-ordem
               MOVE ev-uso TO tl-uso
               MOVE ev-teto TO tl-teto
               MOVE ev-status TO tl-status
               WRITE temp-reg
           END-PERFORM
           CLOSE ev-file CLOSE temp-file
           CALL "system" USING "mv dados/eventos.tmp dados/eventos.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: evento nao encontrado".

       excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)

           MOVE "N" TO ws-encontrou
           OPEN INPUT ev-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: evento nao encontrado" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ ev-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF ev-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   MOVE "inativo" TO ev-status
               END-IF
               MOVE ev-id TO tl-id
               MOVE ev-codigo TO tl-codigo
               MOVE ev-descricao TO tl-descricao
               MOVE ev-tipo TO tl-tipo
               MOVE ev-categoria TO tl-categoria
               MOVE ev-referencia TO tl-referencia
               MOVE ev-formula TO tl-formula
               MOVE ev-incide-inss TO tl-incide-inss
               MOVE ev-incide-irrf TO tl-incide-irrf
               MOVE ev-incide-fgts TO tl-incide-fgts
               MOVE ev-ordem TO tl-ordem
               MOVE ev-uso TO tl-uso
               MOVE ev-teto TO tl-teto
               MOVE ev-status TO tl-status
               WRITE temp-reg
           END-PERFORM
           CLOSE ev-file CLOSE temp-file
           CALL "system" USING "mv dados/eventos.tmp dados/eventos.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO: evento nao encontrado".

       listar.
           OPEN INPUT ev-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"eventos":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"eventos":[' 
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ ev-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-encontrou = "S" THEN
                   MOVE "N" TO ws-encontrou
               ELSE DISPLAY "," END-IF
               PERFORM emitir-evento
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE ev-file.

       listar-ativos.
           OPEN INPUT ev-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"eventos":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"eventos":[' 
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ ev-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF ev-status = "ativo" THEN
                   ADD 1 TO ws-total
                   IF ws-encontrou = "S" THEN
                       MOVE "N" TO ws-encontrou
                   ELSE DISPLAY "," END-IF
                   PERFORM emitir-evento
               END-IF
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE ev-file.

       emitir-evento.
           MOVE SPACES TO ws-json-linha
           MOVE ev-id TO ws-id-ed
           MOVE ev-codigo TO ws-codigo-ed
           MOVE ev-ordem TO ws-ordem-ed
           MOVE ev-teto TO ws-teto-ed
           STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                  ',"codigo":' FUNCTION TRIM(ws-codigo-ed)
                  ',"descricao":"' FUNCTION TRIM(ev-descricao) '"'
                  ',"tipo":"' FUNCTION TRIM(ev-tipo) '"'
                  ',"categoria":"' FUNCTION TRIM(ev-categoria) '"'
                  ',"referencia":"' FUNCTION TRIM(ev-referencia) '"'
                  ',"formula":"' FUNCTION TRIM(ev-formula) '"'
                  ',"incide_inss":"' ev-incide-inss '"'
                  ',"incide_irrf":"' ev-incide-irrf '"'
                  ',"incide_fgts":"' ev-incide-fgts '"'
                  ',"ordem":' FUNCTION TRIM(ws-ordem-ed)
                  ',"uso":"' FUNCTION TRIM(ev-uso) '"'
                  ',"teto":' FUNCTION TRIM(ws-teto-ed)
                  ',"status":"' FUNCTION TRIM(ev-status) '"}'
                  INTO ws-json-linha
           DISPLAY FUNCTION TRIM(ws-json-linha).
