      *> TAXCALC-IO - Copybook de interface do modulo TAXCALC.
      *> Fase 0 (experimento) - SOMENTE DATA DIVISION.
      *> Calculo de impostos por faixas progressivas (INSS/IRRF).
      *> Referencia: RFC-005 (tabelas fiscais).
      *> Nota: a ser incluido via COPY no LINKAGE SECTION do TAXCALC.CBL.
       >>SOURCE FORMAT FREE

      *> ---- ENTRADA ----
       01 LK-BASE        PIC 9(10)V99.   *> Base de calculo (R$, 2 casas)
       01 LK-COMPETENCIA PIC 9(6).       *> Competencia AAAAMM (tabela vigente)
       01 LK-DEPEND      PIC 9(2).       *> Dependentes p/ IRRF (RFC-005)

      *> ---- SAIDA ----
       01 LK-INSS        PIC 9(10)V99.   *> INSS calculado (R$, 2 casas)
       01 LK-IRRF        PIC 9(10)V99.   *> IRRF calculado (R$, 2 casas)
