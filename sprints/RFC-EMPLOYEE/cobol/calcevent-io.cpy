      *> CALCEVENT-IO - Copybook de interface do modulo CALCEVENT.
      *> Fase 3 (Nucleo COBOL) - regras de calculo por evento (RFC-004).
      *> Calculo de evento de folha (provento/desconto/informativo).
      *> Referencia: RFC-004 (eventos) e RFC-005 (incidencias).
      *> Nota: a ser incluido via COPY no LINKAGE SECTION do CALCEVENT.CBL.
      *>
      *> Fase 3: campo LK-EV-CARGA-HORARIA ADICIONADO (RFC-004, decisao 2):
      *>   valor da hora = salario / carga horaria mensal contratual do
      *>   cadastro (RFC-002) - nunca 220h fixo. Por isso o modulo recebe
      *>   a carga horaria do funcionario como entrada.
       >>SOURCE FORMAT FREE

      *> ---- ENTRADA ----
       01 LK-EV-CODIGO        PIC 9(3).     *> Codigo do evento (RFC-004)
       01 LK-EV-TIPO          PIC X(1).     *> P=provento D=desconto I=informativo
       01 LK-EV-REFERENCIA    PIC 9(6)V99.  *> Referencia: horas (HE), dias (faltas), custo (VT)
       01 LK-EV-REFERENCIA-2  PIC 9(6)V99.  *> 2o parametro (ex.: domingos/feriados do DSR - evento 008)
       01 LK-EV-BASE          PIC 9(10)V99. *> Base do calculo (ex.: salario)
       01 LK-EV-CARGA-HORARIA PIC 9(4)V99.  *> Carga horaria mensal contratual (RFC-002)

      *> ---- SAIDA ----
       01 LK-EV-VALOR         PIC 9(10)V99. *> Valor calculado (R$, 2 casas)
       01 LK-EV-INCIDE-INSS   PIC X(1).     *> S/N - compoe base INSS
       01 LK-EV-INCIDE-IRRF   PIC X(1).     *> S/N - compoe base IRRF
       01 LK-EV-INCIDE-FGTS   PIC X(1).     *> S/N - compoe base FGTS
