      *> PAYCALC - Programa orquestrador da folha (Fase 3 - Nucleo COBOL).
      *> Orquestra CALCEVENT (eventos, RFC-004) e TAXCALC (INSS/IRRF,
      *> RFC-005) para devolver o resultado completo da folha numa
      *> unica estrutura (PAYCALC-IO): proventos, descontos, bases de
      *> calculo e liquido.
      *>
      *> Cadeia de calculo (RFC-006 §3.2):
      *>   1. CALCEVENT por evento: 001 salario, 002/003 HE 50/100%,
      *>      007 comissao apurada e 008 DSR sobre comissao
      *>      (RFC-COMISSION), 022 VT (teto = custo real), 025 faltas.
      *>   2. Base INSS = soma dos proventos com incidencia INSS (RFC-004 §5).
      *>   3. TAXCALC(base INSS, competencia, depend) -> INSS e IRRF.
      *>   4. Base IRRF = base INSS - INSS - deducao por dependente.
      *>      Notas de fidelidade (RFC-005 §3):
      *>      a) a deducao 189,59 e PREMISSA compartilhada com a TAXCALC
      *>         (WS-DEP-DEDUCAO VALUE 189.59) - em producao viria da
      *>         tabela IRRF versionada por competencia; manter as duas
      *>         constantes em sincronia (ou centralizar na tabela).
      *>      b) esta base usa o INSS JA ARREDONDADO retornado pela
      *>         TAXCALC (LK-DESC-INSS), enquanto a TAXCALC calcula o
      *>         IRRF com precisao total internamente - em casos-limite
      *>         de arredondamento o valor exibido pode divergir em 1
      *>         centavo do usado no calculo real do IRRF.
      *>   5. Base FGTS = base INSS (premissa do EXEMPLO-competencia.md).
      *>   6. Total descontos = INSS + IRRF + VT + faltas.
      *>   7. Liquido = total proventos - total descontos.
      *>
      *> Convencao de arredondamento (RFC-005 §5.5 / RFC-007 §3):
      *> os valores de evento ja chegam arredondados dos subprogramas;
      *> os totais somam os valores arredondados (como no holerite).
      *>
      *> Notas de contrato (PIC):
      *> a) LK-BASE-INSS (9(12)V99) -> WS-TX-BASE (9(10)V99) pode
      *>    truncar bases acima de 9.999.999.999,99 (limite do TAXCALC).
      *> b) LK-VT-CUSTO (9(10)V99) -> WS-EV-REFERENCIA (9(6)V99) pode
      *>    truncar custos acima de 999.999,99 (limite do CALCEVENT).
      *>    Valores realisticos de folha estao muito abaixo desses tetos.
       >>SOURCE FORMAT FREE

       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYCALC.

       DATA DIVISION.

       WORKING-STORAGE SECTION.
      *> Interfaces dos subprogramas, renomeadas p/ evitar colisao com o
      *> LINKAGE (mesmo copybook, mesmo PIC, mesma ordem - contrato fiel).
      *> Nota: o COPY REPLACING do GnuCOBOL substitui por PALAVRA completa
      *> (pseudo-texto), por isso cada campo e renomeado explicitamente.
           COPY calcevent-io REPLACING
               ==LK-EV-CODIGO== BY ==WS-EV-CODIGO==
               ==LK-EV-TIPO== BY ==WS-EV-TIPO==
               ==LK-EV-REFERENCIA== BY ==WS-EV-REFERENCIA==
               ==LK-EV-REFERENCIA-2== BY ==WS-EV-REFERENCIA-2==
               ==LK-EV-BASE== BY ==WS-EV-BASE==
               ==LK-EV-CARGA-HORARIA== BY ==WS-EV-CARGA-HORARIA==
               ==LK-EV-VALOR== BY ==WS-EV-VALOR==
               ==LK-EV-INCIDE-INSS== BY ==WS-EV-INCIDE-INSS==
               ==LK-EV-INCIDE-IRRF== BY ==WS-EV-INCIDE-IRRF==
               ==LK-EV-INCIDE-FGTS== BY ==WS-EV-INCIDE-FGTS==.
           COPY taxcalc-io REPLACING
               ==LK-BASE== BY ==WS-TX-BASE==
               ==LK-COMPETENCIA== BY ==WS-TX-COMPETENCIA==
               ==LK-DEPEND== BY ==WS-TX-DEPEND==
               ==LK-INSS== BY ==WS-TX-INSS==
               ==LK-IRRF== BY ==WS-TX-IRRF==.

       01 WS-BASE-INSS     PIC 9(12)V99.
       01 WS-BASE-IRRF     PIC S9(12)V99.
       01 WS-LIQUIDO       PIC S9(12)V99.
       01 WS-DEP-DEDUCAO   PIC 9(8)V99 VALUE 189.59.

       LINKAGE SECTION.
           COPY paycalc-io.

       PROCEDURE DIVISION USING LK-PAYROLL.
       MAIN-PROCEDURE.
      *> ============================================================
      *> 1. PROVENTOS - CALCEVENT (RFC-004)
      *> ============================================================
           MOVE LK-SALARIO TO WS-EV-BASE
           MOVE LK-CARGA-HORARIA TO WS-EV-CARGA-HORARIA
           MOVE 0 TO WS-BASE-INSS

      *> Evento 001 - salario base
           MOVE 001 TO WS-EV-CODIGO
           MOVE 'P' TO WS-EV-TIPO
           MOVE 0 TO WS-EV-REFERENCIA
           MOVE 0 TO WS-EV-REFERENCIA-2
           CALL "CALCEVENT" USING WS-EV-CODIGO WS-EV-TIPO
                                  WS-EV-REFERENCIA WS-EV-REFERENCIA-2
                                  WS-EV-BASE
                                  WS-EV-CARGA-HORARIA WS-EV-VALOR
                                  WS-EV-INCIDE-INSS WS-EV-INCIDE-IRRF
                                  WS-EV-INCIDE-FGTS
           MOVE WS-EV-VALOR TO LK-PROV-SALARIO
           IF WS-EV-INCIDE-INSS = 'S'
              ADD WS-EV-VALOR TO WS-BASE-INSS
           END-IF

      *> Evento 002 - horas extras 50%
           MOVE 002 TO WS-EV-CODIGO
           MOVE 'P' TO WS-EV-TIPO
           MOVE LK-HE50 TO WS-EV-REFERENCIA
           MOVE 0 TO WS-EV-REFERENCIA-2
           CALL "CALCEVENT" USING WS-EV-CODIGO WS-EV-TIPO
                                  WS-EV-REFERENCIA WS-EV-REFERENCIA-2
                                  WS-EV-BASE
                                  WS-EV-CARGA-HORARIA WS-EV-VALOR
                                  WS-EV-INCIDE-INSS WS-EV-INCIDE-IRRF
                                  WS-EV-INCIDE-FGTS
           MOVE WS-EV-VALOR TO LK-PROV-HE50
           IF WS-EV-INCIDE-INSS = 'S'
              ADD WS-EV-VALOR TO WS-BASE-INSS
           END-IF

      *> Evento 003 - horas extras 100%
           MOVE 003 TO WS-EV-CODIGO
           MOVE 'P' TO WS-EV-TIPO
           MOVE LK-HE100 TO WS-EV-REFERENCIA
           MOVE 0 TO WS-EV-REFERENCIA-2
           CALL "CALCEVENT" USING WS-EV-CODIGO WS-EV-TIPO
                                  WS-EV-REFERENCIA WS-EV-REFERENCIA-2
                                  WS-EV-BASE
                                  WS-EV-CARGA-HORARIA WS-EV-VALOR
                                  WS-EV-INCIDE-INSS WS-EV-INCIDE-IRRF
                                  WS-EV-INCIDE-FGTS
           MOVE WS-EV-VALOR TO LK-PROV-HE100
           IF WS-EV-INCIDE-INSS = 'S'
              ADD WS-EV-VALOR TO WS-BASE-INSS
           END-IF

      *> Evento 007 - comissao de vendas apurada no PDV (RFC-COMISSION).
      *> O valor JA VEM APURADO (base = LK-COMISSAO); incide INSS/IRRF/FGTS
      *> (RFC-COMISSION/RFC-001 seccao 6). Entra nos proventos e na base INSS.
           MOVE LK-COMISSAO TO WS-EV-BASE
           MOVE 007 TO WS-EV-CODIGO
           MOVE 'P' TO WS-EV-TIPO
           MOVE 0 TO WS-EV-REFERENCIA
           MOVE 0 TO WS-EV-REFERENCIA-2
           CALL "CALCEVENT" USING WS-EV-CODIGO WS-EV-TIPO
                                  WS-EV-REFERENCIA WS-EV-REFERENCIA-2
                                  WS-EV-BASE
                                  WS-EV-CARGA-HORARIA WS-EV-VALOR
                                  WS-EV-INCIDE-INSS WS-EV-INCIDE-IRRF
                                  WS-EV-INCIDE-FGTS
           MOVE WS-EV-VALOR TO LK-PROV-COMISSAO
           IF WS-EV-INCIDE-INSS = 'S'
              ADD WS-EV-VALOR TO WS-BASE-INSS
           END-IF

      *> Evento 008 - DSR sobre comissao (RFC-COMISSION/RFC-001 seccao 7.1):
      *> DSR = comissao / dias uteis x (domingos + feriados). Base = comissao
      *> apurada; referencia = dias uteis; ref-2 = domingos/feriados. Entra
      *> nos proventos e na base INSS (S/S/S - seccao 6).
           MOVE LK-COMISSAO TO WS-EV-BASE
           MOVE 008 TO WS-EV-CODIGO
           MOVE 'P' TO WS-EV-TIPO
           MOVE LK-DSR-DIAS-UTEIS TO WS-EV-REFERENCIA
           MOVE LK-DSR-DOM-FER TO WS-EV-REFERENCIA-2
           CALL "CALCEVENT" USING WS-EV-CODIGO WS-EV-TIPO
                                  WS-EV-REFERENCIA WS-EV-REFERENCIA-2
                                  WS-EV-BASE
                                  WS-EV-CARGA-HORARIA WS-EV-VALOR
                                  WS-EV-INCIDE-INSS WS-EV-INCIDE-IRRF
                                  WS-EV-INCIDE-FGTS
           MOVE WS-EV-VALOR TO LK-PROV-DSR
           IF WS-EV-INCIDE-INSS = 'S'
              ADD WS-EV-VALOR TO WS-BASE-INSS
           END-IF

      *> Restaura a base do SALARIO em WS-EV-BASE IMEDIATAMENTE: o 007
      *> sobrescreveu a base com a comissao (base propria do evento). O
      *> invariante entre as secoes e 'WS-EV-BASE = salario' - VT (6% do
      *> salario) e faltas (salario/30) dependem disso, e qualquer novo
      *> provento (ex.: 008 DSR sobre comissao, RFC-COMISSION/RFC-001
      *> seccao 7.1) precisa da base do cadastro.
           MOVE LK-SALARIO TO WS-EV-BASE

      *> Total de proventos (soma dos valores arredondados - RFC-007 §3)
           COMPUTE LK-PROV-TOTAL = LK-PROV-SALARIO + LK-PROV-HE50
                                 + LK-PROV-HE100 + LK-PROV-COMISSAO
                                 + LK-PROV-DSR
           MOVE WS-BASE-INSS TO LK-BASE-INSS

      *> ============================================================
      *> 2. INSS e IRRF - TAXCALC (RFC-005)
      *> ============================================================
           MOVE LK-BASE-INSS TO WS-TX-BASE
           MOVE LK-COMPETENCIA TO WS-TX-COMPETENCIA
           MOVE LK-DEPEND TO WS-TX-DEPEND
           CALL "TAXCALC" USING WS-TX-BASE WS-TX-COMPETENCIA
                                WS-TX-DEPEND WS-TX-INSS WS-TX-IRRF
           MOVE WS-TX-INSS TO LK-DESC-INSS
           MOVE WS-TX-IRRF TO LK-DESC-IRRF

      *> ============================================================
      *> 3. DESCONTOS VARIAVEIS - CALCEVENT (RFC-004)
      *> ============================================================
      *> Evento 022 - vale-transporte (6% limitado ao custo real)
           MOVE 022 TO WS-EV-CODIGO
           MOVE 'D' TO WS-EV-TIPO
           MOVE LK-VT-CUSTO TO WS-EV-REFERENCIA
           MOVE 0 TO WS-EV-REFERENCIA-2
           CALL "CALCEVENT" USING WS-EV-CODIGO WS-EV-TIPO
                                  WS-EV-REFERENCIA WS-EV-REFERENCIA-2
                                  WS-EV-BASE
                                  WS-EV-CARGA-HORARIA WS-EV-VALOR
                                  WS-EV-INCIDE-INSS WS-EV-INCIDE-IRRF
                                  WS-EV-INCIDE-FGTS
           MOVE WS-EV-VALOR TO LK-DESC-VT

      *> Evento 025 - faltas
           MOVE 025 TO WS-EV-CODIGO
           MOVE 'D' TO WS-EV-TIPO
           MOVE LK-FALTAS TO WS-EV-REFERENCIA
           MOVE 0 TO WS-EV-REFERENCIA-2
           CALL "CALCEVENT" USING WS-EV-CODIGO WS-EV-TIPO
                                  WS-EV-REFERENCIA WS-EV-REFERENCIA-2
                                  WS-EV-BASE
                                  WS-EV-CARGA-HORARIA WS-EV-VALOR
                                  WS-EV-INCIDE-INSS WS-EV-INCIDE-IRRF
                                  WS-EV-INCIDE-FGTS
           MOVE WS-EV-VALOR TO LK-DESC-FALTAS

      *> ============================================================
      *> 4. TOTAIS, BASES E LIQUIDO
      *> ============================================================
           COMPUTE LK-DESC-TOTAL = LK-DESC-INSS + LK-DESC-IRRF
                                 + LK-DESC-VT + LK-DESC-FALTAS

      *> Base IRRF = base INSS - INSS - deducao por dependente
           COMPUTE WS-BASE-IRRF = LK-BASE-INSS - LK-DESC-INSS
                                - (WS-DEP-DEDUCAO * LK-DEPEND)
           IF WS-BASE-IRRF < 0
              MOVE 0 TO WS-BASE-IRRF
           END-IF
           MOVE WS-BASE-IRRF TO LK-BASE-IRRF

      *> Base FGTS = base INSS (premissa do EXEMPLO-competencia.md)
           MOVE LK-BASE-INSS TO LK-BASE-FGTS

      *> Liquido
           COMPUTE WS-LIQUIDO = LK-PROV-TOTAL - LK-DESC-TOTAL
           IF WS-LIQUIDO < 0
              MOVE 0 TO WS-LIQUIDO
           END-IF
           MOVE WS-LIQUIDO TO LK-LIQUIDO

           GOBACK.
       END PROGRAM PAYCALC.
