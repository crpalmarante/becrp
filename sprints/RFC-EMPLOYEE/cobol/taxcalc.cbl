      *> TAXCALC - Programa de calculo de impostos por faixas (Fase 3).
      *> Fase 3 (Nucleo COBOL) - regras progressivas de INSS/IRRF
      *> implementadas conforme RFC-005 (tabelas ilustrativas, nao oficiais).
      *> O copybook TAXCALC-IO e incluido no LINKAGE SECTION (contrato
      *> de interface inalterado desde a Fase 0).
      *>
      *> Tabela INSS (RFC-005 secao 2, progressivo por faixa):
      *>   ate 1.500,00        -> 7,5%
      *>   1.500,01 - 3.000,00 -> 9%
      *>   3.000,01 - 5.000,00 -> 12%
      *>   acima de 5.000,00   -> 14%
      *>
      *> Tabela IRRF (RFC-005 secao 3, progressivo com deducao da faixa):
      *>   ate 2.000,00        -> isento
      *>   2.000,01 - 4.000,00 -> 10%  (deducao 100,00)
      *>   4.000,01 - 6.000,00 -> 15%  (deducao 300,00)
      *>   acima de 6.000,00   -> 22,5% (deducao 700,00)
      *>
      *> Base IRRF = base INSS - INSS - deducao por dependente.
      *> Deducao por dependente: 189,59 (premissa do exemplo; em producao
      *> viria da tabela IRRF versionada por competencia - RFC-005 secao 3).
      *>
      *> Regra RFC-005 secao 5.5: sem arredondamento intermediario - as
      *> parcelas sao somadas com precisao total e so o valor final do
      *> holerite e arredondado (ROUNDED na saida).
       >>SOURCE FORMAT FREE

       IDENTIFICATION DIVISION.
       PROGRAM-ID. TAXCALC.

       DATA DIVISION.

       WORKING-STORAGE SECTION.
       01 WS-BASE          PIC 9(10)V99.
       01 WS-INSS-F1       PIC 9(12)V99999.
       01 WS-INSS-F2       PIC 9(12)V99999.
       01 WS-INSS-F3       PIC 9(12)V99999.
       01 WS-INSS-F4       PIC 9(12)V99999.
       01 WS-INSS-TOT      PIC 9(12)V99999.
       01 WS-BASE-IRRF     PIC S9(12)V99999.
       01 WS-DEP-DEDUCAO   PIC 9(8)V99 VALUE 189.59.

       LINKAGE SECTION.
           COPY taxcalc-io.

       PROCEDURE DIVISION USING LK-BASE LK-COMPETENCIA LK-DEPEND
                               LK-INSS LK-IRRF.
       MAIN-PROCEDURE.
      *> ============================================================
      *> INSS progressivo por faixa (RFC-005 secao 2)
      *> ============================================================
           MOVE LK-BASE TO WS-BASE
           MOVE 0 TO WS-INSS-F1 WS-INSS-F2 WS-INSS-F3 WS-INSS-F4

      *> Faixa 1: ate 1.500,00 -> 7,5%
           IF WS-BASE > 1500.00
              MOVE 1500.00 TO WS-INSS-F1
           ELSE
              MOVE WS-BASE TO WS-INSS-F1
           END-IF
           COMPUTE WS-INSS-F1 = WS-INSS-F1 * 0.075

      *> Faixa 2: de 1.500,01 ate 3.000,00 -> 9%
           IF WS-BASE > 1500.00
              IF WS-BASE > 3000.00
                 MOVE 1500.00 TO WS-INSS-F2
              ELSE
                 COMPUTE WS-INSS-F2 = WS-BASE - 1500.00
              END-IF
           END-IF
           COMPUTE WS-INSS-F2 = WS-INSS-F2 * 0.09

      *> Faixa 3: de 3.000,01 ate 5.000,00 -> 12%
           IF WS-BASE > 3000.00
              IF WS-BASE > 5000.00
                 MOVE 2000.00 TO WS-INSS-F3
              ELSE
                 COMPUTE WS-INSS-F3 = WS-BASE - 3000.00
              END-IF
           END-IF
           COMPUTE WS-INSS-F3 = WS-INSS-F3 * 0.12

      *> Faixa 4: acima de 5.000,00 -> 14%
           IF WS-BASE > 5000.00
              COMPUTE WS-INSS-F4 = WS-BASE - 5000.00
           END-IF
           COMPUTE WS-INSS-F4 = WS-INSS-F4 * 0.14

           COMPUTE WS-INSS-TOT = WS-INSS-F1 + WS-INSS-F2
                               + WS-INSS-F3 + WS-INSS-F4
           COMPUTE LK-INSS ROUNDED = WS-INSS-TOT

      *> ============================================================
      *> Base IRRF = base INSS - INSS (precisao total) - dependentes
      *> ============================================================
           COMPUTE WS-BASE-IRRF = WS-BASE - WS-INSS-TOT
                                - (WS-DEP-DEDUCAO * LK-DEPEND)

      *> ============================================================
      *> IRRF progressivo com deducao da faixa (RFC-005 secao 3)
      *> O calculo e feito direto em LK-IRRF com ROUNDED (precisao
      *> total, sem truncamento intermediario - RFC-005 secao 5.5).
      *> Nas condicoes das faixas o resultado e sempre >= 0.
      *> ============================================================
           IF WS-BASE-IRRF > 2000.00
              IF WS-BASE-IRRF <= 4000.00
                 COMPUTE LK-IRRF ROUNDED = WS-BASE-IRRF * 0.10 - 100.00
              ELSE
                 IF WS-BASE-IRRF <= 6000.00
                    COMPUTE LK-IRRF ROUNDED = WS-BASE-IRRF * 0.15 - 300.00
                 ELSE
                    COMPUTE LK-IRRF ROUNDED = WS-BASE-IRRF * 0.225 - 700.00
                 END-IF
              END-IF
           ELSE
              MOVE 0 TO LK-IRRF
           END-IF

           GOBACK.
       END PROGRAM TAXCALC.
