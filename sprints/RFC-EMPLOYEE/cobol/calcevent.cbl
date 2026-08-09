      *> CALCEVENT - Programa de calculo de evento de folha (Fase 3).
      *> Fase 3 (Nucleo COBOL) - regras de calculo por evento (RFC-004).
      *> O copybook CALCEVENT-IO e incluido no LINKAGE SECTION.
      *>
      *> Eventos implementados (RFC-004 secao 3, catalogo inicial):
      *>   001 Salario Base        -> valor = base (cadastro RFC-002)
      *>   002 Horas Extras 50%    -> valor = (base / carga) x horas x 1,5
      *>   003 Horas Extras 100%   -> valor = (base / carga) x horas x 2,0
      *>   007 Comissao / Vendas   -> valor = base (comissao APURADA no PDV,
      *>                              informada pronta - RFC-COMISSION/RFC-001
      *>                              seccao 5 regra 4 alimenta o evento 7)
      *>   008 DSR sobre comissao  -> valor = base / referencia x ref-2
      *>                              (RFC-COMISSION/RFC-001 seccao 7.1:
      *>                              comissao / dias uteis x dom/feriados)
      *>   022 Vale-Transporte     -> valor = 6% da base, LIMITADO ao custo
      *>                              real de passagens (referencia) - RFC-004
      *>                              regra 7 (teto carregado no evento)
      *>   025 Faltas / Atrasos    -> valor = (base / 30) x dias (RFC-004
      *>                              regra 2: valor do dia = base / 30)
      *>
      *> Incidencias (RFC-004 secao 5):
      *>   001/002/003/007/008 -> compoem base INSS, IRRF e FGTS (S/S/S)
      *>   (007/008: RFC-COMISSION/RFC-001 seccao 6 - comissao e DSR sobre
      *>    comissao incidem nas 3 bases)
      *>   022/025     -> NAO compoem nenhuma base (N/N/N)
      *>   (descontos aplicados apos o calculo de INSS/IRRF - RFC-006)
      *>
      *> Regra RFC-005 secao 5.5: sem arredondamento intermediario - o
      *> valor e calculado em WS-VALOR-EXATO (precisao total) e so o
      *> resultado final e arredondado (ROUNDED na saida).
       >>SOURCE FORMAT FREE

       IDENTIFICATION DIVISION.
       PROGRAM-ID. CALCEVENT.

       DATA DIVISION.

       WORKING-STORAGE SECTION.
      *> Nota de precisao (RFC-005 secao 5.5): o valor de cada evento e
      *> calculado direto em LK-EV-VALOR com ROUNDED, sem campo
      *> intermediario truncado - o COBOL mantem a precisao total da
      *> expressao ate a atribuicao final arredondada.
      *> (WS-VT-6PC e necessario apenas para a comparacao do teto do VT.)
       01 WS-VT-6PC        PIC 9(12)V99999.

       LINKAGE SECTION.
           COPY calcevent-io.

       PROCEDURE DIVISION USING LK-EV-CODIGO LK-EV-TIPO LK-EV-REFERENCIA
                               LK-EV-REFERENCIA-2
                               LK-EV-BASE LK-EV-CARGA-HORARIA
                               LK-EV-VALOR LK-EV-INCIDE-INSS
                               LK-EV-INCIDE-IRRF LK-EV-INCIDE-FGTS.
       MAIN-PROCEDURE.
           EVALUATE LK-EV-CODIGO

      *> ============================================================
      *> 001 - SALARIO BASE (provento, valor informado no cadastro)
      *> ============================================================
              WHEN 001
                 MOVE LK-EV-BASE TO LK-EV-VALOR
                 MOVE 'S' TO LK-EV-INCIDE-INSS
                             LK-EV-INCIDE-IRRF
                             LK-EV-INCIDE-FGTS

      *> ============================================================
      *> 002 - HORAS EXTRAS 50% (RFC-004 regra 4)
      *> ============================================================
              WHEN 002
                 IF LK-EV-CARGA-HORARIA > 0
                    COMPUTE LK-EV-VALOR ROUNDED =
                       LK-EV-BASE / LK-EV-CARGA-HORARIA
                       * LK-EV-REFERENCIA * 1.5
                 ELSE
                    MOVE 0 TO LK-EV-VALOR
                 END-IF
                 MOVE 'S' TO LK-EV-INCIDE-INSS
                             LK-EV-INCIDE-IRRF
                             LK-EV-INCIDE-FGTS

      *> ============================================================
      *> 003 - HORAS EXTRAS 100% (RFC-004 regra 4)
      *> ============================================================
              WHEN 003
                 IF LK-EV-CARGA-HORARIA > 0
                    COMPUTE LK-EV-VALOR ROUNDED =
                       LK-EV-BASE / LK-EV-CARGA-HORARIA
                       * LK-EV-REFERENCIA * 2.0
                 ELSE
                    MOVE 0 TO LK-EV-VALOR
                 END-IF
                 MOVE 'S' TO LK-EV-INCIDE-INSS
                             LK-EV-INCIDE-IRRF
                             LK-EV-INCIDE-FGTS

      *> ============================================================
      *> 007 - COMISSAO / VENDAS (provento, valor APURADO no PDV)
      *> ============================================================
      *> RFC-COMISSION/RFC-001 seccao 5 regra 4: o apurado da comissao
      *> (pos_sales/commission_details - db/017) alimenta o evento 7 da
      *> folha como valor PRONTO (base = comissao apurada do periodo).
      *> Incidencias S/S/S (RFC-COMISSION/RFC-001 seccao 6).
              WHEN 007
                 MOVE LK-EV-BASE TO LK-EV-VALOR
                 MOVE 'S' TO LK-EV-INCIDE-INSS
                             LK-EV-INCIDE-IRRF
                             LK-EV-INCIDE-FGTS

      *> ============================================================
      *> 008 - DSR SOBRE COMISSAO (RFC-COMISSION/RFC-001 seccao 7.1)
      *> ============================================================
      *> Formula de referencia: DSR = comissao (base) / dias uteis do mes
      *> (referencia) x (domingos + feriados do mes) (ref-2). Exemplo
      *> RFC-001 seccao 4.1: 2.000,00 / 26 x 4 = 307,69. Incide S/S/S
      *> (RFC-COMISSION/RFC-001 seccao 6). Protecao contra divisor zero.
              WHEN 008
                 IF LK-EV-REFERENCIA > 0
                    COMPUTE LK-EV-VALOR ROUNDED =
                       LK-EV-BASE / LK-EV-REFERENCIA * LK-EV-REFERENCIA-2
                 ELSE
                    MOVE 0 TO LK-EV-VALOR
                 END-IF
                 MOVE 'S' TO LK-EV-INCIDE-INSS
                             LK-EV-INCIDE-IRRF
                             LK-EV-INCIDE-FGTS

      *> ============================================================
      *> 022 - VALE-TRANSPORTE (RFC-004 regra 7: 6% limitado ao custo
      *>        real de passagens informado na referencia)
      *> ============================================================
              WHEN 022
                 COMPUTE WS-VT-6PC = LK-EV-BASE * 0.06
                 IF WS-VT-6PC > LK-EV-REFERENCIA
                    COMPUTE LK-EV-VALOR ROUNDED = LK-EV-REFERENCIA
                 ELSE
                    COMPUTE LK-EV-VALOR ROUNDED = WS-VT-6PC
                 END-IF
                 MOVE 'N' TO LK-EV-INCIDE-INSS
                             LK-EV-INCIDE-IRRF
                             LK-EV-INCIDE-FGTS

      *> ============================================================
      *> 025 - FALTAS / ATRASOS (RFC-004 regra 2: valor do dia = base/30)
      *> ============================================================
              WHEN 025
                 COMPUTE LK-EV-VALOR ROUNDED =
                    LK-EV-BASE / 30 * LK-EV-REFERENCIA
                 MOVE 'N' TO LK-EV-INCIDE-INSS
                             LK-EV-INCIDE-IRRF
                             LK-EV-INCIDE-FGTS

      *> ============================================================
      *> EVENTO NAO IMPLEMENTADO -> valor 0, sem incidencia
      *> ============================================================
              WHEN OTHER
                 MOVE 0 TO LK-EV-VALOR
                 MOVE 'N' TO LK-EV-INCIDE-INSS
                             LK-EV-INCIDE-IRRF
                             LK-EV-INCIDE-FGTS

           END-EVALUATE
           GOBACK.
       END PROGRAM CALCEVENT.
