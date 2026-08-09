       >>SOURCE FORMAT IS FREE
       *> calc_reforma_tributaria.cbl — cálculo IBS/CBS (Reforma Tributária)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CalcReformaTributaria.

       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       REPOSITORY.
           FUNCTION ALL INTRINSIC.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 ws-valor           PIC 9(13)V99 COMP-3.
       01 ws-valor-in        PIC X(18).
       01 ws-ncm             PIC X(10).
       01 ws-aliq-cbs        PIC 9(3)V99 COMP-3.
       01 ws-aliq-ibs        PIC 9(3)V99 COMP-3.
       01 ws-reducao         PIC 9(3)V99 COMP-3.
       01 ws-cbs-in          PIC X(8).
       01 ws-ibs-in          PIC X(8).
       01 ws-red-in          PIC X(8).
       01 ws-base            PIC 9(13)V99 COMP-3.
       01 ws-cbs             PIC 9(13)V99 COMP-3.
       01 ws-ibs             PIC 9(13)V99 COMP-3.
       01 ws-total           PIC 9(13)V99 COMP-3.
       01 ws-base-ed         PIC -(11)9.99.
       01 ws-cbs-ed          PIC -(11)9.99.
       01 ws-ibs-ed          PIC -(11)9.99.
       01 ws-total-ed        PIC -(11)9.99.
       01 ws-json            PIC X(1000).
       01 ws-part1           PIC X(80).
       01 ws-part2           PIC X(80).
       01 ws-part3           PIC X(80).
       01 ws-part4           PIC X(80).

       PROCEDURE DIVISION.
       MAIN.
           ACCEPT ws-valor-in FROM ENVIRONMENT "VALOR"
           ACCEPT ws-ncm FROM ENVIRONMENT "NCM"
           ACCEPT ws-cbs-in FROM ENVIRONMENT "ALIQ_CBS"
           ACCEPT ws-ibs-in FROM ENVIRONMENT "ALIQ_IBS"
           ACCEPT ws-red-in FROM ENVIRONMENT "REDUCAO"

           IF ws-valor-in = SPACES
               MOVE "0" TO ws-valor-in
           END-IF
           IF ws-cbs-in = SPACES
               MOVE "0.60" TO ws-cbs-in
           END-IF
           IF ws-ibs-in = SPACES
               MOVE "17.00" TO ws-ibs-in
           END-IF
           IF ws-red-in = SPACES
               MOVE "0.00" TO ws-red-in
           END-IF

           COMPUTE ws-valor = FUNCTION NUMVAL(FUNCTION TRIM(ws-valor-in))
           COMPUTE ws-aliq-cbs = FUNCTION NUMVAL(FUNCTION TRIM(ws-cbs-in))
           COMPUTE ws-aliq-ibs = FUNCTION NUMVAL(FUNCTION TRIM(ws-ibs-in))
           COMPUTE ws-reducao = FUNCTION NUMVAL(FUNCTION TRIM(ws-red-in))

           COMPUTE ws-base = ws-valor * (1 - (ws-reducao / 100))
           COMPUTE ws-cbs = ws-base * (ws-aliq-cbs / 100)
           COMPUTE ws-ibs = ws-base * (ws-aliq-ibs / 100)
           COMPUTE ws-total = ws-base + ws-cbs + ws-ibs

           MOVE ws-base TO ws-base-ed
           MOVE ws-cbs TO ws-cbs-ed
           MOVE ws-ibs TO ws-ibs-ed
           MOVE ws-total TO ws-total-ed

           STRING ' {"status":"ok",'
                  ' "ncm":"' FUNCTION TRIM(ws-ncm) '",'
                  ' "valor_operacao":' FUNCTION TRIM(ws-base-ed) ','
                  ' "aliquota_cbs":' FUNCTION TRIM(ws-cbs-in) ','
                  ' "aliquota_ibs":' FUNCTION TRIM(ws-ibs-in) ','
                  ' "reducao_base":' FUNCTION TRIM(ws-red-in) ','
                  ' "cbs":' FUNCTION TRIM(ws-cbs-ed) ','
                  ' "ibs":' FUNCTION TRIM(ws-ibs-ed) ','
                  ' "total_com_impostos":' FUNCTION TRIM(ws-total-ed) '}'
                  INTO ws-json

           DISPLAY FUNCTION TRIM(ws-json)
           GOBACK.
