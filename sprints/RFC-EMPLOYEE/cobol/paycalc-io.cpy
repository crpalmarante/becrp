      *> PAYCALC-IO - Copybook de interface do modulo PAYCALC.
      *> Fase 3 (Nucleo COBOL) - orquestrador da folha completa.
      *> Entrada unica (struct) + resultado completo da folha:
      *> proventos, descontos, bases de calculo e liquido.
      *> Referencia: RFC-004 (eventos), RFC-005 (tabelas fiscais),
      *> RFC-006 §3.2 (cadeia de calculo) e RFC-007 (holerite).
      *> Nota: a ser incluido via COPY no LINKAGE SECTION do PAYCALC.CBL.
       >>SOURCE FORMAT FREE

      *> ---- ENTRADA (cadastro + lancamentos da competencia) ----
       01 LK-PAYROLL.
          05 LK-SALARIO        PIC 9(10)V99.  *> Salario base (RFC-002)
          05 LK-CARGA-HORARIA  PIC 9(4)V99.   *> Carga mensal contratual (RFC-004 dec.2)
          05 LK-DEPEND         PIC 9(2).      *> Dependentes p/ IRRF (RFC-005)
          05 LK-HE50           PIC 9(6)V99.   *> Horas extras 50% (evento 002)
          05 LK-HE100          PIC 9(6)V99.   *> Horas extras 100% (evento 003)
          05 LK-FALTAS         PIC 9(6)V99.   *> Faltas em dias (evento 025)
          05 LK-VT-CUSTO       PIC 9(10)V99.  *> Custo real VT p/ teto (evento 022)
          05 LK-COMISSAO       PIC 9(10)V99.  *> Comissao apurada no PDV (evento 007, RFC-COMISSION)
          05 LK-DSR-DIAS-UTEIS PIC 9(6)V99.   *> Dias uteis do mes - DSR (evento 008, RFC-COMISSION/RFC-001 §7.1)
          05 LK-DSR-DOM-FER    PIC 9(6)V99.   *> Domingos + feriados do mes - DSR (evento 008)
          05 LK-COMPETENCIA    PIC 9(6).      *> Competencia AAAAMM

      *> ---- RESULTADO: proventos ----
          05 LK-PROV-SALARIO   PIC 9(10)V99.
          05 LK-PROV-HE50      PIC 9(10)V99.
          05 LK-PROV-HE100     PIC 9(10)V99.
          05 LK-PROV-COMISSAO  PIC 9(10)V99.  *> Comissao/Vendas (evento 007)
          05 LK-PROV-DSR       PIC 9(10)V99.  *> DSR sobre comissao (evento 008)
          05 LK-PROV-TOTAL     PIC 9(12)V99.

      *> ---- RESULTADO: descontos ----
          05 LK-DESC-INSS      PIC 9(10)V99.
          05 LK-DESC-IRRF      PIC 9(10)V99.
          05 LK-DESC-VT        PIC 9(10)V99.
          05 LK-DESC-FALTAS    PIC 9(10)V99.
          05 LK-DESC-TOTAL     PIC 9(12)V99.

      *> ---- RESULTADO: bases de calculo ----
          05 LK-BASE-INSS      PIC 9(12)V99.
          05 LK-BASE-IRRF      PIC 9(12)V99.
          05 LK-BASE-FGTS      PIC 9(12)V99.

      *> ---- RESULTADO: liquido ----
          05 LK-LIQUIDO        PIC 9(12)V99.
