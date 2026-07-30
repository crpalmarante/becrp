       >>SOURCE FORMAT IS FREE
       *> gerir_cte.cbl - CRUD Conhecimento de Transporte Eletronico
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GerirCTe.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT cte-file ASSIGN TO "dados/cte.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/cte.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD cte-file.
       01 cte-reg.
           05 ct-id             PIC 9(5).
           05 ct-numero         PIC 9(9).
           05 ct-serie          PIC 9(3).
           05 ct-chave          PIC X(44).
           05 ct-cnpj-emit      PIC X(14).
           05 ct-ie-emit        PIC X(14).
           05 ct-nome-emit      PIC X(60).
           05 ct-cnpj-dest      PIC X(14).
           05 ct-nome-dest      PIC X(60).
           05 ct-mun-ini        PIC X(40).
           05 ct-uf-ini         PIC X(2).
           05 ct-mun-fim        PIC X(40).
           05 ct-uf-fim         PIC X(2).
           05 ct-valor          PIC 9(9)V99.
           05 ct-cfop           PIC X(4).
           05 ct-status         PIC X(20).
           05 ct-proc           PIC X(15).
           05 ct-data-emissao   PIC X(20).

       FD temp-file.
       01 temp-reg.
           05 tt-id             PIC 9(5).
           05 tt-numero         PIC 9(9).
           05 tt-serie          PIC 9(3).
           05 tt-chave          PIC X(44).
           05 tt-cnpj-emit      PIC X(14).
           05 tt-ie-emit        PIC X(14).
           05 tt-nome-emit      PIC X(60).
           05 tt-cnpj-dest      PIC X(14).
           05 tt-nome-dest      PIC X(60).
           05 tt-mun-ini        PIC X(40).
           05 tt-uf-ini         PIC X(2).
           05 tt-mun-fim        PIC X(40).
           05 tt-uf-fim         PIC X(2).
           05 tt-valor          PIC 9(9)V99.
           05 tt-cfop           PIC X(4).
           05 tt-status         PIC X(20).
           05 tt-proc           PIC X(15).
           05 tt-data-emissao   PIC X(20).

       WORKING-STORAGE SECTION.
       01 ws-acao            PIC X(15).
       01 ws-file-status     PIC X(2).
       01 ws-existe          PIC X(1).
       01 ws-json-linha      PIC X(800).
       01 ws-id-ed           PIC ZZZZ9.
       01 ws-total-ed        PIC ZZZZ9.
        01 ws-valor-ed        PIC ZZZZZZZZZ9.99.
        01 ws-numero-ed       PIC Z(8)9.
        01 ws-serie-ed        PIC ZZ9.
        01 ws-id              PIC 9(5).
       01 ws-id-in           PIC X(10).
       01 ws-numero          PIC 9(9).
       01 ws-serie           PIC 9(3).
       01 ws-chave           PIC X(44).
       01 ws-cnpj-emit       PIC X(14).
       01 ws-ie-emit         PIC X(14).
       01 ws-nome-emit       PIC X(60).
       01 ws-cnpj-dest       PIC X(14).
       01 ws-nome-dest       PIC X(60).
       01 ws-mun-ini         PIC X(40).
       01 ws-uf-ini          PIC X(2).
       01 ws-mun-fim         PIC X(40).
       01 ws-uf-fim          PIC X(2).
       01 ws-valor           PIC 9(9)V99.
       01 ws-cfop            PIC X(4).
       01 ws-status          PIC X(20).
       01 ws-proc            PIC X(15).
       01 ws-data-emissao    PIC X(20).
       01 ws-encontrou       PIC X(1).
       01 ws-prox-id         PIC 9(5).
       01 ws-i               PIC 9(2).
       01 ws-valor-str       PIC X(15).

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

       incluir.
           ACCEPT ws-numero FROM ENVIRONMENT "NUMERO"
           ACCEPT ws-serie FROM ENVIRONMENT "SERIE"
           ACCEPT ws-chave FROM ENVIRONMENT "CHAVE"
           ACCEPT ws-cnpj-emit FROM ENVIRONMENT "CNPJ_EMIT"
           ACCEPT ws-ie-emit FROM ENVIRONMENT "IE_EMIT"
           ACCEPT ws-nome-emit FROM ENVIRONMENT "NOME_EMIT"
           ACCEPT ws-cnpj-dest FROM ENVIRONMENT "CNPJ_DEST"
           ACCEPT ws-nome-dest FROM ENVIRONMENT "NOME_DEST"
           ACCEPT ws-mun-ini FROM ENVIRONMENT "MUN_INI"
           ACCEPT ws-uf-ini FROM ENVIRONMENT "UF_INI"
           ACCEPT ws-mun-fim FROM ENVIRONMENT "MUN_FIM"
           ACCEPT ws-uf-fim FROM ENVIRONMENT "UF_FIM"
           ACCEPT ws-valor-str FROM ENVIRONMENT "VALOR"
           ACCEPT ws-cfop FROM ENVIRONMENT "CFOP"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           ACCEPT ws-proc FROM ENVIRONMENT "PROTOCOLO"
           ACCEPT ws-data-emissao FROM ENVIRONMENT "DATA_EMISSAO"

           IF ws-nome-emit = SPACES THEN
               DISPLAY "ERRO: nome do emitente obrigatorio"
               EXIT PARAGRAPH
           END-IF

           IF ws-valor-str NOT = SPACES THEN
               COMPUTE ws-valor = FUNCTION NUMVAL(ws-valor-str)
           END-IF

           MOVE 0 TO ws-prox-id
           OPEN INPUT cte-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT cte-file CLOSE cte-file
               OPEN INPUT cte-file
           END-IF
           IF ws-file-status = "00" THEN
               PERFORM UNTIL 1 = 2
                   READ cte-file INTO cte-reg
                       AT END EXIT PERFORM
                   END-READ
                   IF ct-id > ws-prox-id THEN
                       MOVE ct-id TO ws-prox-id
                   END-IF
               END-PERFORM
               CLOSE cte-file
           END-IF
           ADD 1 TO ws-prox-id

           MOVE ws-prox-id TO ct-id
           MOVE ws-numero TO ct-numero
           MOVE ws-serie TO ct-serie
           MOVE ws-chave TO ct-chave
           MOVE ws-cnpj-emit TO ct-cnpj-emit
           MOVE ws-ie-emit TO ct-ie-emit
           MOVE ws-nome-emit TO ct-nome-emit
           MOVE ws-cnpj-dest TO ct-cnpj-dest
           MOVE ws-nome-dest TO ct-nome-dest
           MOVE ws-mun-ini TO ct-mun-ini
           MOVE ws-uf-ini TO ct-uf-ini
           MOVE ws-mun-fim TO ct-mun-fim
           MOVE ws-uf-fim TO ct-uf-fim
           MOVE ws-valor TO ct-valor
           MOVE ws-cfop TO ct-cfop
           MOVE ws-status TO ct-status
           MOVE ws-proc TO ct-proc
           MOVE ws-data-emissao TO ct-data-emissao

           OPEN EXTEND cte-file
           WRITE cte-reg
           CLOSE cte-file

           MOVE ws-prox-id TO ws-id-ed
           DISPLAY FUNCTION TRIM(ws-id-ed)
           .

       alterar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           ACCEPT ws-numero FROM ENVIRONMENT "NUMERO"
           ACCEPT ws-serie FROM ENVIRONMENT "SERIE"
           ACCEPT ws-chave FROM ENVIRONMENT "CHAVE"
           ACCEPT ws-cnpj-emit FROM ENVIRONMENT "CNPJ_EMIT"
           ACCEPT ws-ie-emit FROM ENVIRONMENT "IE_EMIT"
           ACCEPT ws-nome-emit FROM ENVIRONMENT "NOME_EMIT"
           ACCEPT ws-cnpj-dest FROM ENVIRONMENT "CNPJ_DEST"
           ACCEPT ws-nome-dest FROM ENVIRONMENT "NOME_DEST"
           ACCEPT ws-mun-ini FROM ENVIRONMENT "MUN_INI"
           ACCEPT ws-uf-ini FROM ENVIRONMENT "UF_INI"
           ACCEPT ws-mun-fim FROM ENVIRONMENT "MUN_FIM"
           ACCEPT ws-uf-fim FROM ENVIRONMENT "UF_FIM"
           ACCEPT ws-valor-str FROM ENVIRONMENT "VALOR"
           ACCEPT ws-cfop FROM ENVIRONMENT "CFOP"
           ACCEPT ws-status FROM ENVIRONMENT "STATUS"
           ACCEPT ws-proc FROM ENVIRONMENT "PROTOCOLO"
           ACCEPT ws-data-emissao FROM ENVIRONMENT "DATA_EMISSAO"

           IF ws-id-in = SPACES THEN
               DISPLAY "ERRO: ID obrigatorio"
               EXIT PARAGRAPH
           END-IF
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           IF ws-valor-str NOT = SPACES THEN
               COMPUTE ws-valor = FUNCTION NUMVAL(ws-valor-str)
           END-IF

           MOVE "N" TO ws-encontrou
           OPEN INPUT cte-file
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ cte-file INTO cte-reg
                   AT END EXIT PERFORM
               END-READ
               IF ct-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF ws-nome-emit NOT = SPACES THEN
                       MOVE ws-nome-emit TO ct-nome-emit
                   END-IF
                   IF ws-numero NOT = 0 THEN MOVE ws-numero TO ct-numero END-IF
                   IF ws-serie NOT = 0 THEN MOVE ws-serie TO ct-serie END-IF
                   IF ws-chave NOT = SPACES THEN MOVE ws-chave TO ct-chave END-IF
                   IF ws-cnpj-emit NOT = SPACES THEN MOVE ws-cnpj-emit TO ct-cnpj-emit END-IF
                   IF ws-cnpj-dest NOT = SPACES THEN MOVE ws-cnpj-dest TO ct-cnpj-dest END-IF
                   IF ws-nome-dest NOT = SPACES THEN MOVE ws-nome-dest TO ct-nome-dest END-IF
                   IF ws-status NOT = SPACES THEN MOVE ws-status TO ct-status END-IF
                   IF ws-valor NOT = 0 THEN MOVE ws-valor TO ct-valor END-IF
               END-IF
               WRITE temp-reg FROM cte-reg
           END-PERFORM
           CLOSE cte-file temp-file
           IF ws-encontrou = "S" THEN
               CALL "system" USING "mv dados/cte.tmp dados/cte.dat"
               DISPLAY "OK"
           ELSE
               CALL "system" USING "rm -f dados/cte.tmp"
               DISPLAY "ERRO: registro nao encontrado"
           END-IF
           .

       excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           IF ws-id-in = SPACES THEN
               DISPLAY "ERRO: ID obrigatorio"
               EXIT PARAGRAPH
           END-IF
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)

           MOVE "N" TO ws-encontrou
           OPEN INPUT cte-file
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ cte-file INTO cte-reg
                   AT END EXIT PERFORM
               END-READ
               IF ct-id NOT = ws-id THEN
                   WRITE temp-reg FROM cte-reg
               ELSE
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE cte-file temp-file
           IF ws-encontrou = "S" THEN
               CALL "system" USING "mv dados/cte.tmp dados/cte.dat"
               DISPLAY "OK"
           ELSE
               CALL "system" USING "rm -f dados/cte.tmp"
               DISPLAY "ERRO: registro nao encontrado"
           END-IF
           .

        listar.
            DISPLAY '{"cte":['
            MOVE 0 TO ws-id
            OPEN INPUT cte-file
            IF ws-file-status NOT = "00" THEN
                DISPLAY '],"total":0}'
                CLOSE cte-file
                EXIT PARAGRAPH
            END-IF
            PERFORM UNTIL 1 = 2
                READ cte-file INTO cte-reg
                    AT END EXIT PERFORM
                END-READ
                IF ws-id > 0 THEN DISPLAY "," END-IF
                MOVE ct-id TO ws-id-ed
                MOVE ct-valor TO ws-valor-ed
                MOVE ct-numero TO ws-numero-ed
                MOVE ct-serie TO ws-serie-ed
                STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                       ',"numero":' FUNCTION TRIM(ws-numero-ed)
                       ',"serie":' FUNCTION TRIM(ws-serie-ed)
                      ',"chave":"' FUNCTION TRIM(ct-chave) '"'
                      ',"cnpj_emit":"' FUNCTION TRIM(ct-cnpj-emit) '"'
                      ',"nome_emit":"' FUNCTION TRIM(ct-nome-emit) '"'
                      ',"cnpj_dest":"' FUNCTION TRIM(ct-cnpj-dest) '"'
                      ',"nome_dest":"' FUNCTION TRIM(ct-nome-dest) '"'
                      ',"mun_ini":"' FUNCTION TRIM(ct-mun-ini) '"'
                      ',"uf_ini":"' FUNCTION TRIM(ct-uf-ini) '"'
                      ',"mun_fim":"' FUNCTION TRIM(ct-mun-fim) '"'
                      ',"uf_fim":"' FUNCTION TRIM(ct-uf-fim) '"'
                      ',"valor":' FUNCTION TRIM(ws-valor-ed)
                      ',"cfop":"' FUNCTION TRIM(ct-cfop) '"'
                      ',"status":"' FUNCTION TRIM(ct-status) '"'
                      ',"protocolo":"' FUNCTION TRIM(ct-proc) '"'
                      ',"data_emissao":"' FUNCTION TRIM(ct-data-emissao) '"'
                      '}' INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
               ADD 1 TO ws-id
           END-PERFORM
           CLOSE cte-file
           MOVE ws-id TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           .

       buscar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           IF ws-id-in NOT = SPACES THEN
               COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           END-IF
           ACCEPT ws-chave FROM ENVIRONMENT "CHAVE"

           MOVE "N" TO ws-encontrou
           OPEN INPUT cte-file
           IF ws-file-status NOT = "00" THEN
               DISPLAY "{}"
               CLOSE cte-file
               EXIT PARAGRAPH
           END-IF
           PERFORM UNTIL 1 = 2
               READ cte-file INTO cte-reg
                   AT END EXIT PERFORM
               END-READ
               IF (ws-id-in NOT = SPACES AND ct-id = ws-id)
                  OR (ws-chave NOT = SPACES AND ct-chave = ws-chave) THEN
                   MOVE "S" TO ws-encontrou
                    MOVE ct-valor TO ws-valor-ed
                    MOVE ct-numero TO ws-numero-ed
                    MOVE ct-serie TO ws-serie-ed
                    STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                           ',"numero":' FUNCTION TRIM(ws-numero-ed)
                           ',"serie":' FUNCTION TRIM(ws-serie-ed)
                          ',"chave":"' FUNCTION TRIM(ct-chave) '"'
                          ',"cnpj_emit":"' FUNCTION TRIM(ct-cnpj-emit) '"'
                          ',"nome_emit":"' FUNCTION TRIM(ct-nome-emit) '"'
                          ',"cnpj_dest":"' FUNCTION TRIM(ct-cnpj-dest) '"'
                          ',"nome_dest":"' FUNCTION TRIM(ct-nome-dest) '"'
                          ',"valor":' FUNCTION TRIM(ws-valor-ed)
                          ',"cfop":"' FUNCTION TRIM(ct-cfop) '"'
                          ',"status":"' FUNCTION TRIM(ct-status) '"'
                          '}' INTO ws-json-linha
                   DISPLAY FUNCTION TRIM(ws-json-linha)
                   EXIT PERFORM
               END-IF
           END-PERFORM
           CLOSE cte-file
           IF ws-encontrou = "N" THEN DISPLAY "{}" END-IF
           .
