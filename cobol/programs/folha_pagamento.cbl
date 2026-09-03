       >>SOURCE FORMAT IS FREE
       *> folha_pagamento.cbl - Folha de pagamento (payroll)
       IDENTIFICATION DIVISION.
       PROGRAM-ID. FolhaPagamento.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT cf-file ASSIGN TO "dados/folha_config.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT cfg-temp ASSIGN TO "dados/folha_config.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT hl-file ASSIGN TO "dados/holerites.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT temp-file ASSIGN TO "dados/holerites.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT fe-file ASSIGN TO "dados/ferias.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT fe-temp ASSIGN TO "dados/ferias.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT de-file ASSIGN TO "dados/decimo.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT de-temp ASSIGN TO "dados/decimo.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT re-file ASSIGN TO "dados/rescisoes.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT re-temp ASSIGN TO "dados/rescisoes.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT fo-file ASSIGN TO "dados/folhas.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT fo-temp-file ASSIGN TO "dados/folhas.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT en-file ASSIGN TO "dados/encargos.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT en-temp ASSIGN TO "dados/encargos.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT cp-file ASSIGN TO "dados/complementar.dat"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS ws-file-status.
           SELECT cp-temp ASSIGN TO "dados/complementar.tmp"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD cf-file.
       01 cf-reg.
           05 cf-competencia       PIC X(7).
           05 cf-salario-minimo    PIC 9(7)V99.
           05 cf-inss-f1-teto      PIC 9(6)V99.
           05 cf-inss-f1-aliq      PIC 9(3)V99.
           05 cf-inss-f2-teto      PIC 9(6)V99.
           05 cf-inss-f2-aliq      PIC 9(3)V99.
           05 cf-inss-f3-teto      PIC 9(6)V99.
           05 cf-inss-f3-aliq      PIC 9(3)V99.
           05 cf-inss-f4-teto      PIC 9(6)V99.
           05 cf-inss-f4-aliq      PIC 9(3)V99.
           05 cf-irrf-ded-dep      PIC 9(5)V99.
           05 cf-irrf-f1-teto      PIC 9(6)V99.
           05 cf-irrf-f1-aliq      PIC 9(3)V99.
           05 cf-irrf-f2-teto      PIC 9(6)V99.
           05 cf-irrf-f2-aliq      PIC 9(3)V99.
           05 cf-irrf-f3-teto      PIC 9(6)V99.
           05 cf-irrf-f3-aliq      PIC 9(3)V99.
           05 cf-irrf-f4-teto      PIC 9(6)V99.
           05 cf-irrf-f4-aliq      PIC 9(3)V99.
           05 cf-irrf-f1-ded       PIC 9(5)V99.
           05 cf-irrf-f2-ded       PIC 9(5)V99.
           05 cf-irrf-f3-ded       PIC 9(5)V99.
           05 cf-irrf-f4-ded       PIC 9(5)V99.
           05 cf-irrf-f5-teto      PIC 9(6)V99.
           05 cf-irrf-f5-aliq      PIC 9(3)V99.
           05 cf-irrf-f5-ded       PIC 9(5)V99.
           05 cf-fgts-aliquota     PIC 9(3)V99.
           05 cf-hora-extra-aliq   PIC 9(3)V99.
           05 cf-sf-f1-teto        PIC 9(6)V99.
           05 cf-sf-f1-valor       PIC 9(5)V99.
           05 cf-sf-f2-teto        PIC 9(6)V99.
           05 cf-sf-f2-valor       PIC 9(5)V99.
      *> Encargos patronais (RFC-014 §2/Decisão 1): INSS patronal, RAT/SAT
      *> e terceiros — versionados por competência como as demais tabelas
           05 cf-inss-patronal-aliq PIC 9(3)V99.
           05 cf-rat-aliq           PIC 9(3)V99.
           05 cf-terceiros-aliq     PIC 9(3)V99.

       FD cfg-temp.
       01 cfg-temp-reg.
           05 ct-competencia       PIC X(7).
           05 ct-salario-minimo    PIC 9(7)V99.
           05 ct-inss-f1-teto      PIC 9(6)V99.
           05 ct-inss-f1-aliq      PIC 9(3)V99.
           05 ct-inss-f2-teto      PIC 9(6)V99.
           05 ct-inss-f2-aliq      PIC 9(3)V99.
           05 ct-inss-f3-teto      PIC 9(6)V99.
           05 ct-inss-f3-aliq      PIC 9(3)V99.
           05 ct-inss-f4-teto      PIC 9(6)V99.
           05 ct-inss-f4-aliq      PIC 9(3)V99.
           05 ct-irrf-ded-dep      PIC 9(5)V99.
           05 ct-irrf-f1-teto      PIC 9(6)V99.
           05 ct-irrf-f1-aliq      PIC 9(3)V99.
           05 ct-irrf-f2-teto      PIC 9(6)V99.
           05 ct-irrf-f2-aliq      PIC 9(3)V99.
           05 ct-irrf-f3-teto      PIC 9(6)V99.
           05 ct-irrf-f3-aliq      PIC 9(3)V99.
           05 ct-irrf-f4-teto      PIC 9(6)V99.
           05 ct-irrf-f4-aliq      PIC 9(3)V99.
           05 ct-irrf-f1-ded       PIC 9(5)V99.
           05 ct-irrf-f2-ded       PIC 9(5)V99.
           05 ct-irrf-f3-ded       PIC 9(5)V99.
           05 ct-irrf-f4-ded       PIC 9(5)V99.
           05 ct-irrf-f5-teto      PIC 9(6)V99.
           05 ct-irrf-f5-aliq      PIC 9(3)V99.
           05 ct-irrf-f5-ded       PIC 9(5)V99.
           05 ct-fgts-aliquota     PIC 9(3)V99.
           05 ct-hora-extra-aliq   PIC 9(3)V99.
           05 ct-sf-f1-teto        PIC 9(6)V99.
           05 ct-sf-f1-valor       PIC 9(5)V99.
           05 ct-sf-f2-teto        PIC 9(6)V99.
           05 ct-sf-f2-valor       PIC 9(5)V99.
           05 ct-inss-patronal-aliq PIC 9(3)V99.
           05 ct-rat-aliq           PIC 9(3)V99.
           05 ct-terceiros-aliq     PIC 9(3)V99.

       FD fo-file.
       01 fo-reg.
           05 fo-competencia       PIC X(7).
           05 fo-func-id           PIC 9(4).
           05 fo-nome              PIC X(50).
           05 fo-salario-base      PIC 9(7)V99.
           05 fo-horas-extras      PIC 9(7)V99.
           05 fo-dsr               PIC 9(7)V99.
           05 fo-faltas-dias       PIC 9(2).
           05 fo-dependentes       PIC 9(2).
           05 fo-outros-prov       PIC 9(7)V99.
           05 fo-outros-desc       PIC 9(7)V99.
           05 fo-sal-familia       PIC 9(7)V99.
           05 fo-fgts              PIC 9(7)V99.
           05 fo-proventos         PIC 9(8)V99.
           05 fo-base-inss         PIC 9(8)V99.
           05 fo-inss              PIC 9(7)V99.
           05 fo-base-irrf         PIC S9(8)V99.
           05 fo-irrf              PIC S9(7)V99.
           05 fo-total-desc        PIC 9(8)V99.
           05 fo-liquido           PIC 9(8)V99.
           05 fo-situacao          PIC X.
           05 fo-data-pag          PIC X(10).

       FD fo-temp-file.
       01 fo-temp-reg.
           05 ft-competencia       PIC X(7).
           05 ft-func-id           PIC 9(4).
           05 ft-nome              PIC X(50).
           05 ft-salario-base      PIC 9(7)V99.
           05 ft-horas-extras      PIC 9(7)V99.
           05 ft-dsr               PIC 9(7)V99.
           05 ft-faltas-dias       PIC 9(2).
           05 ft-dependentes       PIC 9(2).
           05 ft-outros-prov       PIC 9(7)V99.
           05 ft-outros-desc       PIC 9(7)V99.
           05 ft-sal-familia       PIC 9(7)V99.
           05 ft-fgts              PIC 9(7)V99.
           05 ft-proventos         PIC 9(8)V99.
           05 ft-base-inss         PIC 9(8)V99.
           05 ft-inss              PIC 9(7)V99.
           05 ft-base-irrf         PIC S9(8)V99.
           05 ft-irrf              PIC S9(7)V99.
           05 ft-total-desc        PIC 9(8)V99.
           05 ft-liquido           PIC 9(8)V99.
           05 ft-situacao          PIC X.
           05 ft-data-pag          PIC X(10).

       FD en-file.
       01 en-reg.
           05 en-competencia       PIC X(7).
           05 en-regime            PIC X(10).
           05 en-base              PIC 9(9)V99.
           05 en-fgts              PIC 9(9)V99.
           05 en-inss-patronal     PIC 9(9)V99.
           05 en-rat               PIC 9(9)V99.
           05 en-terceiros         PIC 9(9)V99.
           05 en-total             PIC 9(9)V99.

       FD en-temp.
       01 en-temp-reg.
           05 ent-competencia      PIC X(7).
           05 ent-regime           PIC X(10).
           05 ent-base             PIC 9(9)V99.
           05 ent-fgts             PIC 9(9)V99.
           05 ent-inss-patronal    PIC 9(9)V99.
           05 ent-rat              PIC 9(9)V99.
           05 ent-terceiros        PIC 9(9)V99.
           05 ent-total            PIC 9(9)V99.

       FD cp-file.
       01 cp-reg.
           05 cp-id                PIC 9(4).
           05 cp-funcionario-id    PIC 9(3).
           05 cp-nome              PIC X(50).
           05 cp-competencia       PIC X(7).
           05 cp-competencia-ref   PIC X(7).
           05 cp-motivo            PIC X(60).
           05 cp-valor             PIC S9(8)V99.
           05 cp-inss              PIC S9(7)V99.
           05 cp-irrf              PIC S9(7)V99.
           05 cp-liquido           PIC S9(8)V99.
           05 cp-situacao          PIC X.
           05 cp-data-pag          PIC X(10).

       FD cp-temp.
       01 cp-temp-reg.
           05 qt-id                PIC 9(4).
           05 qt-funcionario-id    PIC 9(3).
           05 qt-nome              PIC X(50).
           05 qt-competencia       PIC X(7).
           05 qt-competencia-ref   PIC X(7).
           05 qt-motivo            PIC X(60).
           05 qt-valor             PIC S9(8)V99.
           05 qt-inss              PIC S9(7)V99.
           05 qt-irrf              PIC S9(7)V99.
           05 qt-liquido           PIC S9(8)V99.
           05 qt-situacao          PIC X.
           05 qt-data-pag          PIC X(10).

       FD hl-file.
       01 hl-reg.
           05 hl-id                PIC 9(4).
           05 hl-func-id           PIC 9(4).
           05 hl-nome              PIC X(50).
           05 hl-competencia       PIC X(7).
           05 hl-salario-base      PIC 9(7)V99.
           05 hl-horas-extras      PIC 9(7)V99.
           05 hl-dsr               PIC 9(7)V99.
           05 hl-faltas-dias       PIC 9(2).
           05 hl-dependentes       PIC 9(2).
           05 hl-outros-prov       PIC 9(7)V99.
           05 hl-sal-familia       PIC 9(7)V99.
           05 hl-proventos         PIC 9(8)V99.
           05 hl-base-inss         PIC 9(8)V99.
           05 hl-inss              PIC 9(7)V99.
           05 hl-base-irrf         PIC S9(8)V99.
           05 hl-irrf              PIC S9(7)V99.
           05 hl-fgts              PIC 9(7)V99.
           05 hl-outros-desc       PIC 9(7)V99.
           05 hl-total-desc        PIC 9(8)V99.
           05 hl-liquido           PIC 9(8)V99.
           05 hl-observacoes       PIC X(200).
           05 hl-situacao          PIC X.
           05 hl-data-pagamento    PIC X(10).

       FD temp-file.
       01 temp-reg.
           05 tl-id                PIC 9(4).
           05 tl-func-id           PIC 9(4).
           05 tl-nome              PIC X(50).
           05 tl-competencia       PIC X(7).
           05 tl-salario-base      PIC 9(7)V99.
           05 tl-horas-extras      PIC 9(7)V99.
           05 tl-dsr               PIC 9(7)V99.
           05 tl-faltas-dias       PIC 9(2).
           05 tl-dependentes       PIC 9(2).
           05 tl-outros-prov       PIC 9(7)V99.
           05 tl-sal-familia       PIC 9(7)V99.
           05 tl-proventos         PIC 9(8)V99.
           05 tl-base-inss         PIC 9(8)V99.
           05 tl-inss              PIC 9(7)V99.
           05 tl-base-irrf         PIC S9(8)V99.
           05 tl-irrf              PIC S9(7)V99.
           05 tl-fgts              PIC 9(7)V99.
           05 tl-outros-desc       PIC 9(7)V99.
           05 tl-total-desc        PIC 9(8)V99.
           05 tl-liquido           PIC 9(8)V99.
           05 tl-observacoes       PIC X(200).
           05 tl-situacao          PIC X.
           05 tl-data-pagamento    PIC X(10).

       FD fe-file.
       01 fe-reg.
           05 fe-id                PIC 9(4).
           05 fe-funcionario-id    PIC 9(3).
           05 fe-nome              PIC X(50).
           05 fe-aquis-inicio      PIC X(10).
           05 fe-aquis-fim         PIC X(10).
           05 fe-inicio            PIC X(10).
           05 fe-fim               PIC X(10).
           05 fe-dias              PIC 9(2).
           05 fe-dias-abono        PIC 9(2).
           05 fe-valor-base        PIC 9(7)V99.
           05 fe-1-3               PIC 9(7)V99.
           05 fe-abono             PIC 9(7)V99.
           05 fe-abono-1-3         PIC 9(7)V99.
           05 fe-inss              PIC 9(7)V99.
           05 fe-irrf              PIC 9(7)V99.
           05 fe-liquido           PIC 9(8)V99.
           05 fe-situacao          PIC X.
           05 fe-data-pagamento    PIC X(10).

       FD fe-temp.
       01 fe-temp-reg.
           05 te-id                PIC 9(4).
           05 te-funcionario-id    PIC 9(3).
           05 te-nome              PIC X(50).
           05 te-aquis-inicio      PIC X(10).
           05 te-aquis-fim         PIC X(10).
           05 te-inicio            PIC X(10).
           05 te-fim               PIC X(10).
           05 te-dias              PIC 9(2).
           05 te-dias-abono        PIC 9(2).
           05 te-valor-base        PIC 9(7)V99.
           05 te-1-3               PIC 9(7)V99.
           05 te-abono             PIC 9(7)V99.
           05 te-abono-1-3         PIC 9(7)V99.
           05 te-inss              PIC 9(7)V99.
           05 te-irrf              PIC 9(7)V99.
           05 te-liquido           PIC 9(8)V99.
           05 te-situacao          PIC X.
           05 te-data-pagamento    PIC X(10).

       FD de-file.
       01 de-reg.
           05 de-id                PIC 9(4).
           05 de-funcionario-id    PIC 9(3).
           05 de-nome              PIC X(50).
           05 de-ano               PIC X(4).
           05 de-parcela           PIC X(1).
           05 de-valor-base        PIC 9(7)V99.
           05 de-inss              PIC 9(7)V99.
           05 de-irrf              PIC 9(7)V99.
           05 de-liquido           PIC 9(8)V99.
           05 de-situacao          PIC X.
           05 de-data-pagamento    PIC X(10).

       FD de-temp.
       01 de-temp-reg.
           05 qe-id                PIC 9(4).
           05 qe-funcionario-id    PIC 9(3).
           05 qe-nome              PIC X(50).
           05 qe-ano               PIC X(4).
           05 qe-parcela           PIC X(1).
           05 qe-valor-base        PIC 9(7)V99.
           05 qe-inss              PIC 9(7)V99.
           05 qe-irrf              PIC 9(7)V99.
           05 qe-liquido           PIC 9(8)V99.
           05 qe-situacao          PIC X.
           05 qe-data-pagamento    PIC X(10).

       FD re-file.
       01 re-reg.
           05 re-id                PIC 9(4).
           05 re-funcionario-id    PIC 9(3).
           05 re-nome              PIC X(50).
           05 re-motivo            PIC X(30).
           05 re-data-deslig       PIC X(10).
           05 re-tipo-aviso        PIC X(20).
           05 re-dias-aviso        PIC 9(2).
           05 re-aviso-previo      PIC 9(7)V99.
           05 re-saldo-salario     PIC 9(7)V99.
           05 re-ferias-venc       PIC 9(7)V99.
           05 re-ferias-prop       PIC 9(7)V99.
           05 re-1-3-ferias        PIC 9(7)V99.
           05 re-13-prop           PIC 9(7)V99.
           05 re-fgts              PIC 9(7)V99.
           05 re-multa-fgts        PIC 9(7)V99.
           05 re-inss              PIC 9(7)V99.
           05 re-irrf              PIC 9(7)V99.
           05 re-liquido           PIC 9(8)V99.
           05 re-situacao          PIC X.
           05 re-data-pagamento    PIC X(10).
           05 re-prazo-pag         PIC X(10).

       FD re-temp.
       01 re-temp-reg.
           05 se-id                PIC 9(4).
           05 se-funcionario-id    PIC 9(3).
           05 se-nome              PIC X(50).
           05 se-motivo            PIC X(30).
           05 se-data-deslig       PIC X(10).
           05 se-tipo-aviso        PIC X(20).
           05 se-dias-aviso        PIC 9(2).
           05 se-aviso-previo      PIC 9(7)V99.
           05 se-saldo-salario     PIC 9(7)V99.
           05 se-ferias-venc       PIC 9(7)V99.
           05 se-ferias-prop       PIC 9(7)V99.
           05 se-1-3-ferias        PIC 9(7)V99.
           05 se-13-prop           PIC 9(7)V99.
           05 se-fgts              PIC 9(7)V99.
           05 se-multa-fgts        PIC 9(7)V99.
           05 se-inss              PIC 9(7)V99.
           05 se-irrf              PIC 9(7)V99.
           05 se-liquido           PIC 9(8)V99.
           05 se-situacao          PIC X.
           05 se-data-pagamento    PIC X(10).
           05 se-prazo-pag         PIC X(10).

       WORKING-STORAGE SECTION.
      *> Backup do registro calculado — o loop de READ do gravar-rescisao
      *> sobrescreve re-reg com o ultimo registro do arquivo; sem este backup
      *> os campos calculados (saldo, ferias, 13o, FGTS, liquido) da 2a+
      *> rescisao herdam valores do registro anterior (bug de gravação).
       01 ws-re-backup.
           05 ws-b-id                PIC 9(4).
           05 ws-b-funcionario-id    PIC 9(3).
           05 ws-b-nome              PIC X(50).
           05 ws-b-motivo            PIC X(30).
           05 ws-b-data-deslig       PIC X(10).
           05 ws-b-tipo-aviso        PIC X(20).
           05 ws-b-dias-aviso        PIC 9(2).
           05 ws-b-aviso-previo      PIC 9(7)V99.
           05 ws-b-saldo-salario     PIC 9(7)V99.
           05 ws-b-ferias-venc       PIC 9(7)V99.
           05 ws-b-ferias-prop       PIC 9(7)V99.
           05 ws-b-1-3-ferias        PIC 9(7)V99.
           05 ws-b-13-prop           PIC 9(7)V99.
           05 ws-b-fgts              PIC 9(7)V99.
           05 ws-b-multa-fgts        PIC 9(7)V99.
           05 ws-b-inss              PIC 9(7)V99.
           05 ws-b-irrf              PIC 9(7)V99.
           05 ws-b-liquido           PIC 9(8)V99.
           05 ws-b-situacao          PIC X.
           05 ws-b-data-pagamento    PIC X(10).
           05 ws-b-prazo-pag         PIC X(10).
       01 ws-acao              PIC X(20).
       01 ws-file-status       PIC X(2).
       01 ws-encontrou         PIC X.
       01 ws-prox-id           PIC 9(4).
       01 ws-total             PIC 9(4).
       01 ws-total-ed          PIC Z(3)9.
       01 ws-id-ed             PIC Z(3)9.
       01 ws-func-id-ed        PIC Z(3)9.
       01 ws-ed                PIC -(9)9.99.
       01 ws-ne                PIC -(7)9.99.
       01 ws-je                PIC Z(7)9.99.
       01 ws-json-linha        PIC X(4000).
       01 ws-id-in             PIC X(5).
       01 ws-id                PIC 9(4).
       01 ws-func-id           PIC 9(3).
       01 ws-func-id-in        PIC X(5).
       01 ws-valor-in          PIC X(12).
       01 ws-horas-in          PIC X(6).
       01 ws-data-in           PIC X(10).
       01 ws-faltas-in         PIC X(3).
       01 ws-nome-in           PIC X(50).
       01 ws-dias-in           PIC X(3).
       01 ws-ano-in            PIC X(4).
       01 ws-parcela-in        PIC X(1).
       01 ws-tipo-aviso-in     PIC X(20).
       01 ws-motivo-in         PIC X(30).
       01 ws-saldo-dias-in     PIC X(3).
       01 ws-ferias-venc-dias-in PIC X(3).
       01 ws-ferias-prop-meses-in PIC X(3).
       01 ws-13-prop-meses-in  PIC X(3).
       01 ws-salario-base-in   PIC X(12).
       01 ws-saldo-dias        PIC 9(2).
       01 ws-ferias-venc-dias  PIC 9(2).
       01 ws-ferias-prop-meses PIC 9(2).
       01 ws-13-prop-meses     PIC 9(2).
       01 ws-salario-base      PIC 9(7)V99.
      *> Férias (RFC-010) — cálculo no COBOL (padrão rescisão)
       01 ws-ferias-dias        PIC 9(2).
       01 ws-ferias-dias-abono  PIC 9(2).
       01 ws-ferias-dias-abono-in PIC X(3).
       01 ws-ferias-valor-base  PIC 9(7)V99.
       01 ws-ferias-1-3         PIC 9(7)V99.
       01 ws-ferias-abono       PIC 9(7)V99.
       01 ws-ferias-abono-1-3   PIC 9(7)V99.
       01 ws-ferias-bruto       PIC 9(8)V99.
       01 ws-ferias-inss        PIC 9(7)V99.
       01 ws-ferias-irrf        PIC 9(7)V99.
       01 ws-ferias-liquido     PIC 9(8)V99.
       01 ws-aquis-inicio       PIC X(10).
       01 ws-aquis-fim          PIC X(10).
       01 ws-inicio-ferias      PIC X(10).
       01 ws-fim-ferias         PIC X(10).
       01 ws-ferias-base-normal PIC 9(7)V99.
       01 ws-ferias-vencida     PIC X.
       01 ws-bool-ed            PIC X(5).
       01 ws-ferias-venc-normal PIC 9(7)V99.
       01 ws-ferias-1-3-base    PIC 9(7)V99.
       01 ws-concessivo-num     PIC 9(8).
       01 ws-inicio-num         PIC 9(8).
      *> 13º (RFC-011) — cálculo no COBOL (padrão rescisão)
       01 ws-meses-in           PIC X(3).
       01 ws-meses              PIC 9(2).
       01 ws-decimo-valor-base  PIC 9(7)V99.
       01 ws-decimo-inss        PIC 9(7)V99.
       01 ws-decimo-irrf        PIC 9(7)V99.
       01 ws-decimo-liquido     PIC 9(8)V99.
      *> Folha complementar (RFC-013) — ajuste de competência fechada
       01 ws-comp-motivo-in     PIC X(60).
       01 ws-comp-competencia   PIC X(7).
       01 ws-comp-competencia-ref PIC X(7).
       01 ws-comp-motivo        PIC X(60).
       01 ws-comp-valor         PIC S9(8)V99.
       01 ws-comp-inss          PIC S9(7)V99.
       01 ws-comp-irrf          PIC S9(7)V99.
       01 ws-comp-liquido       PIC S9(8)V99.
       01 ws-sit-origem         PIC X.
       01 ws-sit-destino        PIC X.
       01 ws-limite-desc        PIC 9(8)V99.
       01 ws-he-extra          PIC 9(7)V99.
       01 ws-dsr               PIC 9(7)V99.
       01 ws-faltas            PIC 9(2).
       01 ws-outros-prov       PIC 9(7)V99.
       01 ws-outros-desc       PIC 9(7)V99.
       01 ws-fgts              PIC 9(7)V99.
       01 ws-salario-dia       PIC 9(7)V99.
       01 ws-aviso-previo      PIC 9(7)V99.
       01 ws-ferias-total      PIC 9(8)V99.
       01 ws-total-verbas      PIC 9(8)V99.
       01 ws-jl                PIC Z(8)9.99.
       01 ws-jx                PIC Z(8)9.99.
       01 ws-comp-in           PIC X(7).
       01 ws-comp-cfg           PIC X(7).
       01 ws-dep-in            PIC X(3).
       01 ws-dependentes       PIC 9(2).
      *> Salário-família (RFC-005 §4): cotas por dependente elegível
       01 ws-cotas-sf-in       PIC X(3).
       01 ws-cotas-sf          PIC 9(2).
       01 ws-sal-familia       PIC 9(7)V99.
      *> Cópia da versão vigente (multi-versão por competência, RFC-005 Regra 1)
       01 ws-cf-sel.
           05 wsf-competencia       PIC X(7).
           05 wsf-salario-minimo    PIC 9(7)V99.
           05 wsf-inss-f1-teto      PIC 9(6)V99.
           05 wsf-inss-f1-aliq      PIC 9(3)V99.
           05 wsf-inss-f2-teto      PIC 9(6)V99.
           05 wsf-inss-f2-aliq      PIC 9(3)V99.
           05 wsf-inss-f3-teto      PIC 9(6)V99.
           05 wsf-inss-f3-aliq      PIC 9(3)V99.
           05 wsf-inss-f4-teto      PIC 9(6)V99.
           05 wsf-inss-f4-aliq      PIC 9(3)V99.
           05 wsf-irrf-ded-dep      PIC 9(5)V99.
           05 wsf-irrf-f1-teto      PIC 9(6)V99.
           05 wsf-irrf-f1-aliq      PIC 9(3)V99.
           05 wsf-irrf-f2-teto      PIC 9(6)V99.
           05 wsf-irrf-f2-aliq      PIC 9(3)V99.
           05 wsf-irrf-f3-teto      PIC 9(6)V99.
           05 wsf-irrf-f3-aliq      PIC 9(3)V99.
           05 wsf-irrf-f4-teto      PIC 9(6)V99.
           05 wsf-irrf-f4-aliq      PIC 9(3)V99.
           05 wsf-irrf-f1-ded       PIC 9(5)V99.
           05 wsf-irrf-f2-ded       PIC 9(5)V99.
           05 wsf-irrf-f3-ded       PIC 9(5)V99.
           05 wsf-irrf-f4-ded       PIC 9(5)V99.
           05 wsf-irrf-f5-teto      PIC 9(6)V99.
           05 wsf-irrf-f5-aliq      PIC 9(3)V99.
           05 wsf-irrf-f5-ded       PIC 9(5)V99.
           05 wsf-fgts-aliquota     PIC 9(3)V99.
           05 wsf-hora-extra-aliq   PIC 9(3)V99.
           05 wsf-sf-f1-teto        PIC 9(6)V99.
           05 wsf-sf-f1-valor       PIC 9(5)V99.
           05 wsf-sf-f2-teto        PIC 9(6)V99.
           05 wsf-sf-f2-valor       PIC 9(5)V99.
           05 wsf-inss-patronal-aliq PIC 9(3)V99.
           05 wsf-rat-aliq           PIC 9(3)V99.
           05 wsf-terceiros-aliq     PIC 9(3)V99.
       01 ws-versoes            PIC X(200).
       01 ws-total-versoes      PIC 9(4).
       01 ws-total-vers-ed      PIC Z(3)9.
      *> Encargos (RFC-014): totais consolidados no fechamento
       01 ws-enc-base           PIC 9(9)V99.
       01 ws-enc-fgts           PIC 9(9)V99.
       01 ws-enc-inss-patronal  PIC 9(9)V99.
       01 ws-enc-rat            PIC 9(9)V99.
       01 ws-enc-terceiros      PIC 9(9)V99.
       01 ws-enc-total          PIC 9(9)V99.
       01 ws-regime-in          PIC X(10).
      *> Cópia do registro de encargos (o READ sobrescreve en-reg)
       01 ws-en-sel.
           05 wsen-competencia     PIC X(7).
           05 wsen-regime          PIC X(10).
           05 wsen-base            PIC 9(9)V99.
           05 wsen-fgts            PIC 9(9)V99.
           05 wsen-inss-patronal   PIC 9(9)V99.
           05 wsen-rat             PIC 9(9)V99.
           05 wsen-terceiros       PIC 9(9)V99.
           05 wsen-total           PIC 9(9)V99.
       01 ws-total-prov        PIC 9(8)V99.
       01 ws-total-desc        PIC 9(8)V99.
       01 ws-liquido           PIC 9(8)V99.
       01 ws-base-inss         PIC 9(8)V99.
       01 ws-inss              PIC 9(7)V99.
       01 ws-base-irrf         PIC S9(8)V99.
       01 ws-irrf              PIC S9(7)V99.
       01 ws-desc-faltas       PIC 9(7)V99.
       01 ws-p1                PIC 9(8)V9999.
       01 ws-p2                PIC 9(8)V9999.
       01 ws-p3                PIC 9(8)V9999.
       01 ws-p4                PIC 9(8)V9999.
       01 ws-resto             PIC 9(8)V99.
       01 ws-teto1             PIC 9(7)V99.
       01 ws-teto2             PIC 9(7)V99.
       01 ws-teto3             PIC 9(7)V99.
       01 ws-achou-comp        PIC X.
       01 ws-folha-sit         PIC X.
       01 ws-obs-in            PIC X(200).
       01 ws-gerados           PIC 9(4).
       01 ws-gerados-ed        PIC Z(4)9.
       01 ws-json-linha2       PIC X(2200).
       01 ws-qtde-func         PIC 9(4).
       01 ws-qtde-ed           PIC Z(3)9.
       01 ws-total-prov-ed     PIC Z(8)9.99.
       01 ws-total-desc-ed     PIC Z(8)9.99.
       01 ws-liquido-ed        PIC Z(8)9.99.
       01 ws-comp-ant          PIC X(7).
       01 ws-sit-ant           PIC X.
       01 ws-emitiu            PIC X.
       01 ws-dias-ed           PIC Z9.
       01 ws-prazo-pag         PIC X(10).
       01 ws-data-num          PIC 9(8).
       01 ws-data-int          PIC 9(8).
       01 ws-data-edit         PIC 9(8).
       01 FILLER REDEFINES ws-data-edit.
           05 ws-dt-ano        PIC 9(4).
           05 ws-dt-mes        PIC 9(2).
           05 ws-dt-dia        PIC 9(2).
       01 ws-ano-x             PIC X(4).
       01 ws-mes-x             PIC X(2).
       01 ws-dia-x             PIC X(2).
       01 ws-ano-n             PIC 9(4).
       01 ws-mes-n             PIC 9(2).
       01 ws-dia-n             PIC 9(2).

       PROCEDURE DIVISION.
           ACCEPT ws-acao FROM ENVIRONMENT "ACAO"
           IF ws-acao = SPACES THEN MOVE "config-ler" TO ws-acao END-IF

           EVALUATE ws-acao
               WHEN "config-ler"         PERFORM config-ler
               WHEN "config-salvar"      PERFORM config-salvar
               WHEN "holerite-gerar"     PERFORM holerite-gerar
               WHEN "holerite-listar"    PERFORM holerite-listar
               WHEN "holerite-mostrar"   PERFORM holerite-mostrar
               WHEN "holerite-obs"       PERFORM holerite-obs
               WHEN "holerite-pagar"     PERFORM holerite-pagar
               WHEN "holerite-excluir"   PERFORM holerite-excluir
               WHEN "ferias-calcular"    PERFORM ferias-calcular
               WHEN "ferias-incluir"     PERFORM ferias-incluir
               WHEN "ferias-listar"      PERFORM ferias-listar
               WHEN "ferias-pagar"       PERFORM ferias-pagar
               WHEN "ferias-excluir"     PERFORM ferias-excluir
               WHEN "decimo-calcular"    PERFORM decimo-calcular
               WHEN "decimo-incluir"     PERFORM decimo-incluir
               WHEN "decimo-listar"      PERFORM decimo-listar
               WHEN "decimo-pagar"       PERFORM decimo-pagar
               WHEN "decimo-excluir"     PERFORM decimo-excluir
               WHEN "comp-calcular"      PERFORM comp-calcular
               WHEN "comp-incluir"       PERFORM comp-incluir
               WHEN "comp-listar"        PERFORM comp-listar
               WHEN "comp-validar"       PERFORM comp-validar
               WHEN "comp-fechar"        PERFORM comp-fechar
               WHEN "comp-pagar"         PERFORM comp-pagar
               WHEN "comp-excluir"       PERFORM comp-excluir
               WHEN "comp-encargos"      PERFORM comp-encargos
               WHEN "rescisao-calcular"  PERFORM rescisao-calcular
               WHEN "rescisao-incluir"   PERFORM rescisao-incluir
               WHEN "rescisao-listar"    PERFORM rescisao-listar
               WHEN "rescisao-pagar"     PERFORM rescisao-pagar
               WHEN "rescisao-excluir"   PERFORM rescisao-excluir
               WHEN "folha-abrir"       PERFORM folha-abrir
               WHEN "folha-calcular"    PERFORM folha-calcular
               WHEN "folha-concluir"    PERFORM folha-concluir
               WHEN "folha-validar"     PERFORM folha-validar
               WHEN "folha-fechar"      PERFORM folha-fechar
               WHEN "folha-pagar"       PERFORM folha-pagar
               WHEN "folha-listar"      PERFORM folha-listar
               WHEN "folha-mostrar"     PERFORM folha-mostrar
               WHEN "encargos-calcular"  PERFORM encargos-calcular
               WHEN "encargos-mostrar"   PERFORM encargos-mostrar
               WHEN OTHER DISPLAY "ERRO: acao invalida"
           END-EVALUATE
           STOP RUN.

       config-ler.
      *>   RFC-005 Regra 1/Decisão 1: tabela vigente na competência;
      *>   o arquivo guarda uma linha por versão (histórico preservado).
           ACCEPT ws-comp-cfg FROM ENVIRONMENT "COMPETENCIA"
           PERFORM config-defaults
           OPEN INPUT cf-file
           IF ws-file-status = "35" THEN
               MOVE SPACES TO ws-json-linha
               STRING '{"competencia":"","salario_minimo":1518.00,'
                   '"inss_f1_teto":1518.00,'
                   '"inss_f1_aliq":7.50,"inss_f2_teto":2793.88,'
                   '"inss_f2_aliq":9.00,"inss_f3_teto":4190.83,'
                   '"inss_f3_aliq":12.00,"inss_f4_teto":8157.41,'
                   '"inss_f4_aliq":14.00,"irrf_ded_dep":189.59,'
                   '"irrf_f1_teto":2259.20,"irrf_f1_aliq":0.00,'
                   '"irrf_f2_teto":2826.65,"irrf_f2_aliq":7.50,'
                   '"irrf_f3_teto":3751.05,"irrf_f3_aliq":15.00,'
                   '"irrf_f4_teto":4664.68,"irrf_f4_aliq":22.50,'
                   '"irrf_f1_ded":0.00,"irrf_f2_ded":169.44,'
                   '"irrf_f3_ded":381.44,"irrf_f4_ded":662.77,'
                   '"irrf_f5_teto":0.00,"irrf_f5_aliq":27.50,'
                   '"irrf_f5_ded":896.00,"fgts_aliquota":8.00,'
                   '"hora_extra_aliq":50.00,'
                   '"sf_f1_teto":1905.52,"sf_f1_valor":62.04,'
                   '"sf_f2_teto":3047.00,"sf_f2_valor":43.17,'
                   '"inss_patronal_aliq":20.00,"rat_aliq":2.00,'
                   '"terceiros_aliq":0.00,'
                   '"versoes":[]}'
                   INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
               STOP RUN
           END-IF
      *>   Seleciona a versão vigente da competência (última com competência
      *>   menor/igual à pedida; sem pedido, a mais recente = última linha)
           MOVE SPACES TO ws-cf-sel
           MOVE 0 TO ws-total-versoes
           MOVE SPACES TO ws-versoes
           PERFORM UNTIL 1 = 2
               READ cf-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
      *>   Ignora linha vazia residual (newline final) que o READ devolve
               IF cf-competencia = SPACES THEN
                   CONTINUE
               ELSE
                   ADD 1 TO ws-total-versoes
                   IF ws-total-versoes = 1 THEN
                       MOVE cf-competencia TO ws-versoes
                   ELSE
                       STRING FUNCTION TRIM(ws-versoes) ','
                           FUNCTION TRIM(cf-competencia) INTO ws-versoes
                   END-IF
                   IF ws-comp-cfg = SPACES THEN
      *>               sem filtro: fica a última linha (vigente mais recente)
                       MOVE cf-reg TO ws-cf-sel
                   ELSE
                       IF cf-competencia <= ws-comp-cfg THEN
                           MOVE cf-reg TO ws-cf-sel
                       END-IF
                   END-IF
               END-IF
           END-PERFORM
           CLOSE cf-file
           IF ws-cf-sel NOT = SPACES THEN
               MOVE ws-cf-sel TO cf-reg
           END-IF
           MOVE cf-salario-minimo TO ws-je
           STRING '{"competencia":"' FUNCTION TRIM(cf-competencia) '",'
               '"salario_minimo":' FUNCTION TRIM(ws-je)
               INTO ws-json-linha
           MOVE cf-inss-f1-teto TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss_f1_teto":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-inss-f1-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss_f1_aliq":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-inss-f2-teto TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss_f2_teto":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-inss-f2-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss_f2_aliq":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-inss-f3-teto TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss_f3_teto":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-inss-f3-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss_f3_aliq":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-inss-f4-teto TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss_f4_teto":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-inss-f4-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss_f4_aliq":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-ded-dep TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_ded_dep":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f1-teto TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f1_teto":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f1-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f1_aliq":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f2-teto TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f2_teto":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f2-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f2_aliq":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f3-teto TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f3_teto":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f3-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f3_aliq":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f4-teto TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f4_teto":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f4-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f4_aliq":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f1-ded TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f1_ded":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f2-ded TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f2_ded":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f3-ded TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f3_ded":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f4-ded TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f4_ded":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f5-teto TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f5_teto":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f5-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f5_aliq":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-irrf-f5-ded TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf_f5_ded":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-fgts-aliquota TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"fgts_aliquota":' FUNCTION TRIM(ws-je) INTO ws-json-linha
           MOVE cf-hora-extra-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"hora_extra_aliq":' FUNCTION TRIM(ws-je)
               INTO ws-json-linha
           MOVE cf-sf-f1-teto TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"sf_f1_teto":' FUNCTION TRIM(ws-je)
               INTO ws-json-linha
           MOVE cf-sf-f1-valor TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"sf_f1_valor":' FUNCTION TRIM(ws-je)
               INTO ws-json-linha
           MOVE cf-sf-f2-teto TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"sf_f2_teto":' FUNCTION TRIM(ws-je)
               INTO ws-json-linha
           MOVE cf-sf-f2-valor TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"sf_f2_valor":' FUNCTION TRIM(ws-je)
               INTO ws-json-linha
           MOVE cf-inss-patronal-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss_patronal_aliq":' FUNCTION TRIM(ws-je)
               INTO ws-json-linha
           MOVE cf-rat-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"rat_aliq":' FUNCTION TRIM(ws-je)
               INTO ws-json-linha
           MOVE cf-terceiros-aliq TO ws-je
           STRING FUNCTION TRIM(ws-json-linha)
               ',"terceiros_aliq":' FUNCTION TRIM(ws-je)
               INTO ws-json-linha
           MOVE ws-total-versoes TO ws-total-vers-ed
           STRING FUNCTION TRIM(ws-json-linha)
               ',"versoes":"' FUNCTION TRIM(ws-versoes) '"'
               ',"total_versoes":' FUNCTION TRIM(ws-total-vers-ed) '}'
               INTO ws-json-linha
           DISPLAY FUNCTION TRIM(ws-json-linha).

       config-salvar.
      *>   RFC-005 Regra 2/Decisão 1: tabelas imutáveis após uso — salvar
      *>   grava uma nova versão por competência; histórico é preservado.
           ACCEPT ws-comp-cfg FROM ENVIRONMENT "COMPETENCIA"
           ACCEPT ws-valor-in FROM ENVIRONMENT "SALARIO_MINIMO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-salario-minimo
           ACCEPT ws-valor-in FROM ENVIRONMENT "INSS_F1_TETO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-inss-f1-teto
           ACCEPT ws-valor-in FROM ENVIRONMENT "INSS_F1_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-inss-f1-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "INSS_F2_TETO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-inss-f2-teto
           ACCEPT ws-valor-in FROM ENVIRONMENT "INSS_F2_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-inss-f2-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "INSS_F3_TETO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-inss-f3-teto
           ACCEPT ws-valor-in FROM ENVIRONMENT "INSS_F3_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-inss-f3-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "INSS_F4_TETO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-inss-f4-teto
           ACCEPT ws-valor-in FROM ENVIRONMENT "INSS_F4_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-inss-f4-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_DED_DEP"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-ded-dep
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F1_TETO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f1-teto
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F1_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f1-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F2_TETO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f2-teto
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F2_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f2-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F3_TETO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f3-teto
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F3_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f3-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F4_TETO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f4-teto
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F4_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f4-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F1_DED"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f1-ded
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F2_DED"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f2-ded
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F3_DED"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f3-ded
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F4_DED"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f4-ded
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F5_TETO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f5-teto
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F5_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f5-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "IRRF_F5_DED"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-irrf-f5-ded
           ACCEPT ws-valor-in FROM ENVIRONMENT "FGTS_ALIQUOTA"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-fgts-aliquota
           ACCEPT ws-valor-in FROM ENVIRONMENT "HORA_EXTRA_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-hora-extra-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "SF_F1_TETO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-sf-f1-teto
           ACCEPT ws-valor-in FROM ENVIRONMENT "SF_F1_VALOR"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-sf-f1-valor
           ACCEPT ws-valor-in FROM ENVIRONMENT "SF_F2_TETO"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-sf-f2-teto
           ACCEPT ws-valor-in FROM ENVIRONMENT "SF_F2_VALOR"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-sf-f2-valor
           ACCEPT ws-valor-in FROM ENVIRONMENT "INSS_PATRONAL_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-inss-patronal-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "RAT_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-rat-aliq
           ACCEPT ws-valor-in FROM ENVIRONMENT "TERCEIROS_ALIQ"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO cf-terceiros-aliq
           MOVE ws-comp-cfg TO cf-competencia
      *>   Preserva a nova versão (o loop abaixo sobrescreve cf-reg)
           MOVE cf-reg TO ws-cf-sel
      *>   Guard (Regra 2): não sobrescreve versão usada em folha fechada/paga
           MOVE "N" TO ws-achou-comp
           OPEN INPUT fo-file
           IF ws-file-status NOT = "35" THEN
               PERFORM UNTIL 1 = 2
                   READ fo-file NEXT RECORD
                       AT END EXIT PERFORM
                   END-READ
                   IF fo-func-id = 0 AND fo-competencia = ws-comp-cfg
                       AND (fo-situacao = "F" OR fo-situacao = "P") THEN
                       MOVE "S" TO ws-achou-comp
                   END-IF
               END-PERFORM
           END-IF
           CLOSE fo-file
           IF ws-achou-comp = "S" THEN
               DISPLAY "ERRO: competencia ja fechada - tabela imutavel (RFC-005 Regra 2)"
               STOP RUN END-IF
      *>   Reescreve o arquivo mantendo as outras versões e a nova por último
           OPEN INPUT cf-file
           OPEN OUTPUT cfg-temp
           IF ws-file-status NOT = "35" THEN
               PERFORM UNTIL 1 = 2
                   READ cf-file NEXT RECORD
                       AT END EXIT PERFORM
                   END-READ
                   IF cf-competencia NOT = SPACES
                       AND cf-competencia NOT = ws-comp-cfg THEN
                       MOVE cf-reg TO cfg-temp-reg
                       WRITE cfg-temp-reg
                   END-IF
               END-PERFORM
           END-IF
           MOVE ws-cf-sel TO cfg-temp-reg
           WRITE cfg-temp-reg
           CLOSE cf-file CLOSE cfg-temp
           CALL "system" USING
               "mv dados/folha_config.tmp dados/folha_config.dat"
           END-CALL
           DISPLAY "OK".

       holerite-gerar.
      *>   RFC-007: holerite e visao do processamento (folhas.dat).
      *>   Nada e digitado; regenerar substitui os holerites da competencia.
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           IF ws-comp-in = SPACES THEN
               DISPLAY "ERRO: competencia obrigatoria" STOP RUN END-IF
      *>   Valida a competencia no processamento (estado diferente de aberta)
           MOVE "N" TO ws-achou-comp
           OPEN INPUT fo-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: competencia nao processada" STOP RUN END-IF
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fo-func-id = 0 AND fo-competencia = ws-comp-in THEN
                   MOVE "S" TO ws-achou-comp
                   MOVE fo-situacao TO ws-folha-sit
                   IF fo-situacao = "A" THEN
                       DISPLAY "ERRO: processe a folha antes de gerar holerites"
                       STOP RUN END-IF
               END-IF
           END-PERFORM
           CLOSE fo-file
           IF ws-achou-comp NOT = "S" THEN
               DISPLAY "ERRO: competencia nao processada" STOP RUN END-IF

      *>   Passo 1: remove os holerites atuais da competencia (regeneracao)
           OPEN INPUT hl-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT hl-file CLOSE hl-file
               OPEN INPUT hl-file END-IF
           MOVE 0 TO ws-prox-id
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ hl-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF hl-id > ws-prox-id THEN MOVE hl-id TO ws-prox-id END-IF
               IF hl-competencia NOT = ws-comp-in THEN
                   MOVE hl-id TO tl-id
                   MOVE hl-func-id TO tl-func-id
                   MOVE hl-nome TO tl-nome
                   MOVE hl-competencia TO tl-competencia
                   MOVE hl-salario-base TO tl-salario-base
                   MOVE hl-horas-extras TO tl-horas-extras
                   MOVE hl-dsr TO tl-dsr
                   MOVE hl-faltas-dias TO tl-faltas-dias
                   MOVE hl-dependentes TO tl-dependentes
                   MOVE hl-outros-prov TO tl-outros-prov
                   MOVE hl-proventos TO tl-proventos
                   MOVE hl-base-inss TO tl-base-inss
                   MOVE hl-inss TO tl-inss
                   MOVE hl-base-irrf TO tl-base-irrf
                   MOVE hl-irrf TO tl-irrf
                   MOVE hl-fgts TO tl-fgts
                   MOVE hl-outros-desc TO tl-outros-desc
                   MOVE hl-sal-familia TO tl-sal-familia
                   MOVE hl-total-desc TO tl-total-desc
                   MOVE hl-liquido TO tl-liquido
                   MOVE hl-observacoes TO tl-observacoes
                   MOVE hl-situacao TO tl-situacao
                   MOVE hl-data-pagamento TO tl-data-pagamento
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE hl-file CLOSE temp-file

      *>   Passo 2: gera um holerite por funcionario processado
           MOVE 0 TO ws-gerados
           OPEN INPUT fo-file
           OPEN EXTEND temp-file
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fo-func-id > 0 AND fo-competencia = ws-comp-in THEN
                   ADD 1 TO ws-prox-id
                   MOVE ws-prox-id TO tl-id
                   MOVE fo-func-id TO tl-func-id
                   MOVE fo-nome TO tl-nome
                   MOVE ws-comp-in TO tl-competencia
                   MOVE fo-salario-base TO tl-salario-base
                   MOVE fo-horas-extras TO tl-horas-extras
                   MOVE fo-dsr TO tl-dsr
                   MOVE fo-faltas-dias TO tl-faltas-dias
                   MOVE fo-dependentes TO tl-dependentes
                   MOVE fo-outros-prov TO tl-outros-prov
                   MOVE fo-proventos TO tl-proventos
                   MOVE fo-base-inss TO tl-base-inss
                   MOVE fo-inss TO tl-inss
                   MOVE fo-base-irrf TO tl-base-irrf
                   MOVE fo-irrf TO tl-irrf
                   MOVE fo-fgts TO tl-fgts
                   MOVE fo-outros-desc TO tl-outros-desc
                   MOVE fo-sal-familia TO tl-sal-familia
                   MOVE fo-total-desc TO tl-total-desc
                   MOVE fo-liquido TO tl-liquido
                   MOVE SPACES TO tl-observacoes
      *>           Espelha a situação do HEADER da competência (não do registro)
                   IF ws-folha-sit = "P" THEN
                       MOVE "P" TO tl-situacao
                       MOVE fo-data-pag TO tl-data-pagamento
                   ELSE
                       MOVE "C" TO tl-situacao
                       MOVE SPACES TO tl-data-pagamento
                   END-IF
                   WRITE temp-reg
                   ADD 1 TO ws-gerados
               END-IF
           END-PERFORM
           CLOSE fo-file CLOSE temp-file
           CALL "system" USING "mv dados/holerites.tmp dados/holerites.dat"
           END-CALL
           MOVE ws-gerados TO ws-gerados-ed
           DISPLAY '{"status":"ok","gerados":'
               FUNCTION TRIM(ws-gerados-ed) '}'.

       holerite-listar.
           OPEN INPUT hl-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"holerites":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"holerites":['
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ hl-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-encontrou = "S" THEN MOVE "N" TO ws-encontrou
               ELSE DISPLAY "," END-IF
               MOVE SPACES TO ws-json-linha
               MOVE hl-id TO ws-id-ed
               MOVE hl-func-id TO ws-func-id-ed
               STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                   ',"funcionario_id":' FUNCTION TRIM(ws-func-id-ed)
                   ',"nome":"' FUNCTION TRIM(hl-nome) '"'
                   ',"competencia":"' FUNCTION TRIM(hl-competencia) '"'
                   INTO ws-json-linha
               MOVE hl-salario-base TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"salario_base":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE hl-horas-extras TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"horas_extras":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE hl-dsr TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"dsr":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE hl-faltas-dias TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"faltas":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE hl-dependentes TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"dependentes":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE hl-outros-prov TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"outros_proventos":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE hl-sal-familia TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"salario_familia":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE hl-proventos TO ws-jx
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"proventos":' FUNCTION TRIM(ws-jx)
                   INTO ws-json-linha
               MOVE hl-base-inss TO ws-jx
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"base_inss":' FUNCTION TRIM(ws-jx)
                   INTO ws-json-linha
               MOVE hl-inss TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"inss":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE hl-base-irrf TO ws-ne
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"base_irrf":' FUNCTION TRIM(ws-ne)
                   INTO ws-json-linha
               MOVE hl-irrf TO ws-ne
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"irrf":' FUNCTION TRIM(ws-ne)
                   INTO ws-json-linha
               MOVE hl-fgts TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"fgts":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE hl-outros-desc TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"outros_descontos":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE hl-total-desc TO ws-jx
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"total_descontos":' FUNCTION TRIM(ws-jx)
                   INTO ws-json-linha
               MOVE hl-liquido TO ws-jx
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"liquido":' FUNCTION TRIM(ws-jx)
                   ',"situacao":"' hl-situacao '"'
                   ',"data_pagamento":"' FUNCTION TRIM(hl-data-pagamento) '"}'
                   INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE hl-file.

       holerite-pagar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-data-in FROM ENVIRONMENT "DATA_PAGAMENTO"
           MOVE "N" TO ws-encontrou
           OPEN INPUT hl-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: holerite nao encontrado" STOP RUN END-IF
           PERFORM UNTIL 1 = 2
               READ hl-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF hl-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   MOVE hl-competencia TO ws-comp-in
               END-IF
           END-PERFORM
           CLOSE hl-file
           IF ws-encontrou NOT = "S" THEN
               DISPLAY "ERRO: holerite nao encontrado" STOP RUN END-IF
      *>   Guard (RFC-006): so paga holerite de competencia fechada
           MOVE "N" TO ws-achou-comp
           OPEN INPUT fo-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: competencia nao processada" STOP RUN END-IF
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fo-func-id = 0 AND fo-competencia = ws-comp-in THEN
                   MOVE "S" TO ws-achou-comp
                   IF fo-situacao NOT = "F" AND fo-situacao NOT = "P" THEN
                       DISPLAY "ERRO: competencia deve estar fechada para pagar"
                       STOP RUN END-IF
               END-IF
           END-PERFORM
           CLOSE fo-file
           IF ws-achou-comp NOT = "S" THEN
               DISPLAY "ERRO: competencia nao processada" STOP RUN END-IF
           MOVE "N" TO ws-encontrou
           OPEN INPUT hl-file
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ hl-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF hl-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   MOVE "P" TO hl-situacao
                   MOVE ws-data-in TO hl-data-pagamento
               END-IF
               MOVE hl-id TO tl-id
               MOVE hl-func-id TO tl-func-id
               MOVE hl-nome TO tl-nome
               MOVE hl-competencia TO tl-competencia
               MOVE hl-salario-base TO tl-salario-base
               MOVE hl-horas-extras TO tl-horas-extras
               MOVE hl-dsr TO tl-dsr
               MOVE hl-faltas-dias TO tl-faltas-dias
               MOVE hl-dependentes TO tl-dependentes
               MOVE hl-outros-prov TO tl-outros-prov
               MOVE hl-proventos TO tl-proventos
               MOVE hl-base-inss TO tl-base-inss
               MOVE hl-inss TO tl-inss
               MOVE hl-base-irrf TO tl-base-irrf
               MOVE hl-irrf TO tl-irrf
               MOVE hl-fgts TO tl-fgts
               MOVE hl-outros-desc TO tl-outros-desc
               MOVE hl-sal-familia TO tl-sal-familia
               MOVE hl-total-desc TO tl-total-desc
               MOVE hl-liquido TO tl-liquido
               MOVE hl-observacoes TO tl-observacoes
               MOVE hl-situacao TO tl-situacao
               MOVE hl-data-pagamento TO tl-data-pagamento
               WRITE temp-reg
           END-PERFORM
           CLOSE hl-file CLOSE temp-file
           CALL "system" USING "mv dados/holerites.tmp dados/holerites.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO".

       holerite-excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           MOVE "N" TO ws-encontrou
           MOVE "N" TO ws-achou-comp
           OPEN INPUT hl-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: holerite nao encontrado" STOP RUN END-IF
           PERFORM UNTIL 1 = 2
               READ hl-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF hl-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF hl-situacao = "P" THEN MOVE "S" TO ws-achou-comp END-IF
               END-IF
           END-PERFORM
           CLOSE hl-file
           IF ws-encontrou NOT = "S" THEN
               DISPLAY "ERRO: holerite nao encontrado" STOP RUN END-IF
           IF ws-achou-comp = "S" THEN
               DISPLAY "ERRO: holerite pago nao pode ser excluido"
               STOP RUN END-IF
           OPEN INPUT hl-file
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ hl-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF hl-id NOT = ws-id THEN
                   MOVE hl-id TO tl-id
                   MOVE hl-func-id TO tl-func-id
                   MOVE hl-nome TO tl-nome
                   MOVE hl-competencia TO tl-competencia
                   MOVE hl-salario-base TO tl-salario-base
                   MOVE hl-horas-extras TO tl-horas-extras
                   MOVE hl-dsr TO tl-dsr
                   MOVE hl-faltas-dias TO tl-faltas-dias
                   MOVE hl-dependentes TO tl-dependentes
                   MOVE hl-outros-prov TO tl-outros-prov
                   MOVE hl-proventos TO tl-proventos
                   MOVE hl-base-inss TO tl-base-inss
                   MOVE hl-inss TO tl-inss
                   MOVE hl-base-irrf TO tl-base-irrf
                   MOVE hl-irrf TO tl-irrf
                   MOVE hl-fgts TO tl-fgts
                   MOVE hl-outros-desc TO tl-outros-desc
                   MOVE hl-sal-familia TO tl-sal-familia
                   MOVE hl-total-desc TO tl-total-desc
                   MOVE hl-liquido TO tl-liquido
                   MOVE hl-observacoes TO tl-observacoes
                   MOVE hl-situacao TO tl-situacao
                   MOVE hl-data-pagamento TO tl-data-pagamento
                   WRITE temp-reg
               END-IF
           END-PERFORM
           CLOSE hl-file CLOSE temp-file
           CALL "system" USING "mv dados/holerites.tmp dados/holerites.dat"
           END-CALL
           DISPLAY "OK".

       holerite-mostrar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           MOVE "N" TO ws-encontrou
           OPEN INPUT hl-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: holerite nao encontrado" STOP RUN END-IF
           PERFORM UNTIL 1 = 2
               READ hl-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF hl-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   MOVE SPACES TO ws-json-linha
                   MOVE hl-id TO ws-id-ed
                   MOVE hl-func-id TO ws-func-id-ed
                   STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                       ',"funcionario_id":' FUNCTION TRIM(ws-func-id-ed)
                       ',"nome":"' FUNCTION TRIM(hl-nome) '"'
                       ',"competencia":"' FUNCTION TRIM(hl-competencia) '"'
                       ',"situacao":"' hl-situacao '"'
                       ',"data_pagamento":"' FUNCTION TRIM(hl-data-pagamento) '"'
                       ',"observacoes":"' FUNCTION TRIM(hl-observacoes) '"'
                       INTO ws-json-linha
                   MOVE hl-salario-base TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"bases":{"salario":' FUNCTION TRIM(ws-jx)
                       INTO ws-json-linha
                   MOVE hl-base-inss TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"base_inss":' FUNCTION TRIM(ws-jx)
                       INTO ws-json-linha
                   MOVE hl-base-irrf TO ws-ne
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"base_irrf":' FUNCTION TRIM(ws-ne)
                       INTO ws-json-linha
                   MOVE hl-sal-familia TO ws-je
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"salario_familia":' FUNCTION TRIM(ws-je)
                       INTO ws-json-linha
                   MOVE hl-fgts TO ws-je
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"fgts":' FUNCTION TRIM(ws-je) '}'
                       INTO ws-json-linha
      *>           Componentes do holerite (proventos e descontos)
                   MOVE SPACES TO ws-json-linha2
                   MOVE hl-salario-base TO ws-jx
                   STRING '{"tipo":"provento","nome":"Salario Base"'
                       ',"formula":"base","metodo":"auto","valor_auto":'
                       FUNCTION TRIM(ws-jx) '}' INTO ws-json-linha2
                   IF hl-horas-extras > 0 THEN
                       MOVE hl-horas-extras TO ws-jx
                       STRING FUNCTION TRIM(ws-json-linha2) ','
                           '{"tipo":"provento","nome":"Horas Extras"'
                           ',"formula":"lancamento","metodo":"auto",'
                           '"valor_auto":' FUNCTION TRIM(ws-jx) '}'
                           INTO ws-json-linha2 END-IF
                   IF hl-dsr > 0 THEN
                       MOVE hl-dsr TO ws-jx
                       STRING FUNCTION TRIM(ws-json-linha2) ','
                           '{"tipo":"provento","nome":"DSR"'
                           ',"formula":"proporcional","metodo":"auto",'
                           '"valor_auto":' FUNCTION TRIM(ws-jx) '}'
                           INTO ws-json-linha2 END-IF
                   IF hl-outros-prov > 0 THEN
                       MOVE hl-outros-prov TO ws-jx
                       STRING FUNCTION TRIM(ws-json-linha2) ','
                           '{"tipo":"provento","nome":"Outros Proventos"'
                           ',"formula":"lancamento","metodo":"auto",'
                           '"valor_auto":' FUNCTION TRIM(ws-jx) '}'
                           INTO ws-json-linha2 END-IF
                   IF hl-sal-familia > 0 THEN
                       MOVE hl-sal-familia TO ws-jx
                       STRING FUNCTION TRIM(ws-json-linha2) ','
                           '{"tipo":"provento","nome":"Salario Familia"'
                           ',"formula":"cotas x tabela","metodo":"auto",'
                           '"valor_auto":' FUNCTION TRIM(ws-jx) '}'
                           INTO ws-json-linha2 END-IF
                   IF hl-faltas-dias > 0 THEN
                       COMPUTE ws-desc-faltas ROUNDED =
                           (hl-salario-base / 30) * hl-faltas-dias
                       MOVE ws-desc-faltas TO ws-jx
                       STRING FUNCTION TRIM(ws-json-linha2) ','
                           '{"tipo":"desconto","nome":"Faltas"'
                           ',"formula":"salario/30 x dias","metodo":"auto",'
                           '"valor_auto":' FUNCTION TRIM(ws-jx) '}'
                           INTO ws-json-linha2 END-IF
                   MOVE hl-inss TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha2) ','
                       '{"tipo":"desconto","nome":"INSS"'
                       ',"formula":"progressivo por faixa","metodo":"auto",'
                       '"valor_auto":' FUNCTION TRIM(ws-jx) '}'
                       INTO ws-json-linha2
                   MOVE hl-irrf TO ws-ne
                   STRING FUNCTION TRIM(ws-json-linha2) ','
                       '{"tipo":"desconto","nome":"IRRF"'
                       ',"formula":"base - deducao","metodo":"auto",'
                       '"valor_auto":' FUNCTION TRIM(ws-ne) '}'
                       INTO ws-json-linha2
                   IF hl-outros-desc > 0 THEN
                       MOVE hl-outros-desc TO ws-jx
                       STRING FUNCTION TRIM(ws-json-linha2) ','
                           '{"tipo":"desconto","nome":"Outros Descontos"'
                           ',"formula":"lancamento","metodo":"auto",'
                           '"valor_auto":' FUNCTION TRIM(ws-jx) '}'
                           INTO ws-json-linha2 END-IF
                   MOVE hl-proventos TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha) ',"proventos":'
                       FUNCTION TRIM(ws-jx) INTO ws-json-linha
                   MOVE hl-total-desc TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha) ',"total_descontos":'
                       FUNCTION TRIM(ws-jx) INTO ws-json-linha
                   MOVE hl-liquido TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha) ',"liquido":'
                       FUNCTION TRIM(ws-jx) INTO ws-json-linha
                   STRING FUNCTION TRIM(ws-json-linha) ',"componentes":['
                       FUNCTION TRIM(ws-json-linha2) ']}'
                       INTO ws-json-linha
                   DISPLAY FUNCTION TRIM(ws-json-linha)
               END-IF
           END-PERFORM
           CLOSE hl-file
           IF ws-encontrou NOT = "S" THEN
               DISPLAY "ERRO: holerite nao encontrado" END-IF.

       holerite-obs.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-obs-in FROM ENVIRONMENT "OBSERVACOES"
           MOVE "N" TO ws-encontrou
           OPEN INPUT hl-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO" STOP RUN END-IF
           OPEN OUTPUT temp-file
           PERFORM UNTIL 1 = 2
               READ hl-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF hl-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   MOVE ws-obs-in TO hl-observacoes
               END-IF
               MOVE hl-id TO tl-id
               MOVE hl-func-id TO tl-func-id
               MOVE hl-nome TO tl-nome
               MOVE hl-competencia TO tl-competencia
               MOVE hl-salario-base TO tl-salario-base
               MOVE hl-horas-extras TO tl-horas-extras
               MOVE hl-dsr TO tl-dsr
               MOVE hl-faltas-dias TO tl-faltas-dias
               MOVE hl-dependentes TO tl-dependentes
               MOVE hl-outros-prov TO tl-outros-prov
               MOVE hl-proventos TO tl-proventos
               MOVE hl-base-inss TO tl-base-inss
               MOVE hl-inss TO tl-inss
               MOVE hl-base-irrf TO tl-base-irrf
               MOVE hl-irrf TO tl-irrf
               MOVE hl-fgts TO tl-fgts
               MOVE hl-outros-desc TO tl-outros-desc
               MOVE hl-sal-familia TO tl-sal-familia
               MOVE hl-total-desc TO tl-total-desc
               MOVE hl-liquido TO tl-liquido
               MOVE hl-observacoes TO tl-observacoes
               MOVE hl-situacao TO tl-situacao
               MOVE hl-data-pagamento TO tl-data-pagamento
               WRITE temp-reg
           END-PERFORM
           CLOSE hl-file CLOSE temp-file
           CALL "system" USING "mv dados/holerites.tmp dados/holerites.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO".

       ferias-incluir.
           PERFORM ler-dados-ferias
           PERFORM calcular-ferias
           PERFORM gravar-ferias
           PERFORM mostrar-ferias-calculo.

       ferias-calcular.
           PERFORM ler-dados-ferias
           PERFORM calcular-ferias
           MOVE 0 TO ws-prox-id
           PERFORM mostrar-ferias-calculo.

       ler-dados-ferias.
           ACCEPT ws-func-id-in FROM ENVIRONMENT "FUNCIONARIO_ID"
           COMPUTE ws-func-id = FUNCTION NUMVAL(ws-func-id-in)
           ACCEPT ws-nome-in FROM ENVIRONMENT "NOME"
           ACCEPT ws-data-in FROM ENVIRONMENT "AQUIS_INICIO"
           MOVE ws-data-in TO ws-aquis-inicio
           ACCEPT ws-data-in FROM ENVIRONMENT "AQUIS_FIM"
           MOVE ws-data-in TO ws-aquis-fim
           ACCEPT ws-data-in FROM ENVIRONMENT "INICIO"
           MOVE ws-data-in TO ws-inicio-ferias
           ACCEPT ws-data-in FROM ENVIRONMENT "FIM"
           MOVE ws-data-in TO ws-fim-ferias
           ACCEPT ws-dias-in FROM ENVIRONMENT "DIAS"
           COMPUTE ws-ferias-dias = FUNCTION NUMVAL(ws-dias-in)
           ACCEPT ws-ferias-dias-abono-in FROM ENVIRONMENT "DIAS_ABONO"
           COMPUTE ws-ferias-dias-abono =
               FUNCTION NUMVAL(ws-ferias-dias-abono-in)
           ACCEPT ws-salario-base-in FROM ENVIRONMENT "SALARIO_BASE"
           COMPUTE ws-salario-base = FUNCTION NUMVAL(ws-salario-base-in)
           IF ws-func-id = 0 THEN
               DISPLAY "ERRO: funcionario obrigatorio" STOP RUN END-IF
           IF ws-ferias-dias = 0 THEN
               DISPLAY "ERRO: dias de ferias obrigatorios"
               STOP RUN END-IF
           IF ws-ferias-dias-abono > ws-ferias-dias / 3 THEN
               DISPLAY "ERRO: abono maximo de 1/3 dos dias de ferias"
               STOP RUN END-IF.

       calcula-vencida.
      *>   RFC-010 Decisao 4: ferias concedidas apos o fim do periodo
      *>   concessivo (aquis_fim + 12 meses) sao VENCIDAS — alerta e
      *>   pagamento em dobro. Decisao de produto: so o salario dobra;
      *>   1/3 e abono permanecem na base normal. Comparacao numerica
      *>   YYYYMMDD (nao muda o layout do arquivo de ferias).
           MOVE "N" TO ws-ferias-vencida
           IF ws-aquis-fim = SPACES OR ws-inicio-ferias = SPACES
               EXIT PARAGRAPH END-IF
           UNSTRING ws-aquis-fim DELIMITED BY "-"
               INTO ws-ano-x ws-mes-x ws-dia-x
           END-UNSTRING
           MOVE ws-ano-x TO ws-ano-n
           MOVE ws-mes-x TO ws-mes-n
           MOVE ws-dia-x TO ws-dia-n
           COMPUTE ws-concessivo-num =
               ws-ano-n * 10000 + ws-mes-n * 100 + ws-dia-n
           ADD 12 TO ws-mes-n
           IF ws-mes-n > 12 THEN
               SUBTRACT 12 FROM ws-mes-n
               ADD 1 TO ws-ano-n
           END-IF
           COMPUTE ws-concessivo-num =
               ws-ano-n * 10000 + ws-mes-n * 100 + ws-dia-n
           UNSTRING ws-inicio-ferias DELIMITED BY "-"
               INTO ws-ano-x ws-mes-x ws-dia-x
           END-UNSTRING
           MOVE ws-ano-x TO ws-ano-n
           MOVE ws-mes-x TO ws-mes-n
           MOVE ws-dia-x TO ws-dia-n
           COMPUTE ws-inicio-num =
               ws-ano-n * 10000 + ws-mes-n * 100 + ws-dia-n
           IF ws-inicio-num > ws-concessivo-num THEN
               MOVE "S" TO ws-ferias-vencida
           END-IF.

       calcular-ferias.
      *>   RFC-010: base = salario/30 x dias; +1/3 constitucional;
      *>   abono pecuniario (venda de ate 1/3 dos dias) com 1/3 proprio.
      *>   INSS/IRRF sobre o total (valor + 1/3 + abono + 1/3 abono).
      *>   Vencidas: salario em dobro; 1/3 e abono na base normal.
           PERFORM calcula-vencida
           COMPUTE ws-salario-dia = ws-salario-base / 30
           COMPUTE ws-ferias-base-normal ROUNDED =
               ws-salario-dia * ws-ferias-dias
           IF ws-ferias-vencida = "S" THEN
               COMPUTE ws-ferias-valor-base =
                   ws-ferias-base-normal * 2
           ELSE
               MOVE ws-ferias-base-normal TO ws-ferias-valor-base
           END-IF
           COMPUTE ws-ferias-1-3 ROUNDED = ws-ferias-base-normal / 3
           COMPUTE ws-ferias-abono ROUNDED =
               ws-salario-dia * ws-ferias-dias-abono
           COMPUTE ws-ferias-abono-1-3 ROUNDED = ws-ferias-abono / 3
           COMPUTE ws-ferias-bruto = ws-ferias-valor-base
               + ws-ferias-1-3 + ws-ferias-abono + ws-ferias-abono-1-3
           PERFORM folha-carregar-config
           MOVE ws-ferias-bruto TO ws-base-inss
           PERFORM calcular-inss
           MOVE ws-inss TO ws-ferias-inss
           COMPUTE ws-base-irrf = ws-base-inss - ws-inss
           IF ws-base-irrf < 0 THEN MOVE 0 TO ws-base-irrf END-IF
           PERFORM calcular-irrf
           MOVE ws-irrf TO ws-ferias-irrf
           COMPUTE ws-ferias-liquido = ws-ferias-bruto
               - ws-ferias-inss - ws-ferias-irrf
           IF ws-ferias-vencida = "S" THEN
               DISPLAY "ALERTA: ferias vencidas - salario em dobro (RFC-010)"
           END-IF.

       gravar-ferias.
           MOVE 0 TO ws-prox-id
           OPEN INPUT fe-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT fe-file CLOSE fe-file
               OPEN INPUT fe-file END-IF
           PERFORM UNTIL 1 = 2
               READ fe-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fe-id > ws-prox-id THEN MOVE fe-id TO ws-prox-id END-IF
           END-PERFORM
           CLOSE fe-file
           ADD 1 TO ws-prox-id
           OPEN EXTEND fe-file
           MOVE ws-prox-id TO fe-id
           MOVE ws-func-id TO fe-funcionario-id
           MOVE ws-nome-in TO fe-nome
           MOVE ws-aquis-inicio TO fe-aquis-inicio
           MOVE ws-aquis-fim TO fe-aquis-fim
           MOVE ws-inicio-ferias TO fe-inicio
           MOVE ws-fim-ferias TO fe-fim
           MOVE ws-ferias-dias TO fe-dias
           MOVE ws-ferias-dias-abono TO fe-dias-abono
           MOVE ws-ferias-valor-base TO fe-valor-base
           MOVE ws-ferias-1-3 TO fe-1-3
           MOVE ws-ferias-abono TO fe-abono
           MOVE ws-ferias-abono-1-3 TO fe-abono-1-3
           MOVE ws-ferias-inss TO fe-inss
           MOVE ws-ferias-irrf TO fe-irrf
           MOVE ws-ferias-liquido TO fe-liquido
           MOVE "C" TO fe-situacao
           MOVE SPACES TO fe-data-pagamento
           WRITE fe-reg
           CLOSE fe-file.

       mostrar-ferias-calculo.
           MOVE SPACES TO ws-json-linha
           MOVE ws-prox-id TO ws-id-ed
           MOVE ws-func-id TO ws-func-id-ed
           MOVE ws-ferias-dias TO ws-dias-ed
           STRING '{"id":' FUNCTION TRIM(ws-id-ed)
               ',"funcionario_id":' FUNCTION TRIM(ws-func-id-ed)
               ',"nome":"' FUNCTION TRIM(ws-nome-in) '"'
               ',"aquis_inicio":"' FUNCTION TRIM(ws-aquis-inicio) '"'
               ',"aquis_fim":"' FUNCTION TRIM(ws-aquis-fim) '"'
               ',"inicio":"' FUNCTION TRIM(ws-inicio-ferias) '"'
               ',"fim":"' FUNCTION TRIM(ws-fim-ferias) '"'
               ',"dias":' FUNCTION TRIM(ws-dias-ed)
               INTO ws-json-linha
           MOVE ws-ferias-dias-abono TO ws-dias-ed
           STRING FUNCTION TRIM(ws-json-linha)
               ',"dias_abono":' FUNCTION TRIM(ws-dias-ed)
               INTO ws-json-linha
           MOVE ws-ferias-valor-base TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"valor_base":' FUNCTION TRIM(ws-jl)
               INTO ws-json-linha
           MOVE ws-ferias-1-3 TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"1_3":' FUNCTION TRIM(ws-jl)
               ',"um_terco":' FUNCTION TRIM(ws-jl)
               INTO ws-json-linha
           MOVE ws-ferias-abono TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"abono":' FUNCTION TRIM(ws-jl)
               INTO ws-json-linha
           MOVE ws-ferias-abono-1-3 TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"abono_1_3":' FUNCTION TRIM(ws-jl)
               ',"abono_terco":' FUNCTION TRIM(ws-jl)
               INTO ws-json-linha
           MOVE ws-ferias-bruto TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"bruto":' FUNCTION TRIM(ws-jl)
               INTO ws-json-linha
           MOVE ws-ferias-inss TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss":' FUNCTION TRIM(ws-jl)
               INTO ws-json-linha
           MOVE ws-ferias-irrf TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf":' FUNCTION TRIM(ws-jl)
               INTO ws-json-linha
           MOVE ws-ferias-liquido TO ws-jl
           IF ws-ferias-vencida = "S" THEN MOVE "true" TO ws-bool-ed
           ELSE MOVE "false" TO ws-bool-ed END-IF
           STRING FUNCTION TRIM(ws-json-linha)
               ',"liquido":' FUNCTION TRIM(ws-jl)
               ',"vencida":' FUNCTION TRIM(ws-bool-ed)
               ',"situacao":"C"}'
               INTO ws-json-linha
           DISPLAY FUNCTION TRIM(ws-json-linha).

       ferias-listar.
           OPEN INPUT fe-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"ferias":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"ferias":['
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ fe-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-encontrou = "S" THEN MOVE "N" TO ws-encontrou
               ELSE DISPLAY "," END-IF
               MOVE SPACES TO ws-json-linha
               MOVE fe-id TO ws-id-ed
               MOVE fe-funcionario-id TO ws-func-id-ed
               MOVE fe-dias TO ws-je
               STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                   ',"funcionario_id":' FUNCTION TRIM(ws-func-id-ed)
                   ',"nome":"' FUNCTION TRIM(fe-nome) '"'
                   ',"aquis_inicio":"' FUNCTION TRIM(fe-aquis-inicio) '"'
                   ',"aquis_fim":"' FUNCTION TRIM(fe-aquis-fim) '"'
                   ',"inicio":"' FUNCTION TRIM(fe-inicio) '"'
                   ',"fim":"' FUNCTION TRIM(fe-fim) '"'
                   ',"dias":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE fe-dias-abono TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"dias_abono":' FUNCTION TRIM(ws-je) INTO ws-json-linha
               MOVE fe-valor-base TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"valor_base":' FUNCTION TRIM(ws-je) INTO ws-json-linha
               MOVE fe-1-3 TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"1_3":' FUNCTION TRIM(ws-je) INTO ws-json-linha
               MOVE fe-abono TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"abono":' FUNCTION TRIM(ws-je) INTO ws-json-linha
               MOVE fe-abono-1-3 TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"abono_1_3":' FUNCTION TRIM(ws-je) INTO ws-json-linha
               MOVE fe-inss TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"inss":' FUNCTION TRIM(ws-je) INTO ws-json-linha
               MOVE fe-irrf TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"irrf":' FUNCTION TRIM(ws-je) INTO ws-json-linha
               MOVE fe-aquis-fim TO ws-aquis-fim
               MOVE fe-inicio TO ws-inicio-ferias
               PERFORM calcula-vencida
               IF ws-ferias-vencida = "S" THEN MOVE "true" TO ws-bool-ed
               ELSE MOVE "false" TO ws-bool-ed END-IF
               MOVE fe-liquido TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"liquido":' FUNCTION TRIM(ws-je)
                   ',"vencida":' FUNCTION TRIM(ws-bool-ed)
                   ',"situacao":"' fe-situacao '"'
                   ',"data_pagamento":"' FUNCTION TRIM(fe-data-pagamento) '"}'
                   INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE fe-file.

       ferias-pagar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-data-in FROM ENVIRONMENT "DATA_PAGAMENTO"
           MOVE "N" TO ws-encontrou
           OPEN INPUT fe-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO" STOP RUN END-IF
           OPEN OUTPUT fe-temp
           PERFORM UNTIL 1 = 2
               READ fe-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fe-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   MOVE "P" TO fe-situacao
                   MOVE ws-data-in TO fe-data-pagamento
               END-IF
               MOVE fe-id TO te-id
               MOVE fe-funcionario-id TO te-funcionario-id
               MOVE fe-nome TO te-nome
               MOVE fe-aquis-inicio TO te-aquis-inicio
               MOVE fe-aquis-fim TO te-aquis-fim
               MOVE fe-inicio TO te-inicio
               MOVE fe-fim TO te-fim
               MOVE fe-dias TO te-dias
               MOVE fe-dias-abono TO te-dias-abono
               MOVE fe-valor-base TO te-valor-base
               MOVE fe-1-3 TO te-1-3
               MOVE fe-abono TO te-abono
               MOVE fe-abono-1-3 TO te-abono-1-3
               MOVE fe-inss TO te-inss
               MOVE fe-irrf TO te-irrf
               MOVE fe-liquido TO te-liquido
               MOVE fe-situacao TO te-situacao
               MOVE fe-data-pagamento TO te-data-pagamento
               WRITE fe-temp-reg
           END-PERFORM
           CLOSE fe-file CLOSE fe-temp
           CALL "system" USING "mv dados/ferias.tmp dados/ferias.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO".

       ferias-excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           MOVE "N" TO ws-encontrou
           OPEN INPUT fe-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO" STOP RUN END-IF
           OPEN OUTPUT fe-temp
           PERFORM UNTIL 1 = 2
               READ fe-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fe-id NOT = ws-id THEN
                   MOVE fe-id TO te-id
                   MOVE fe-funcionario-id TO te-funcionario-id
                   MOVE fe-nome TO te-nome
                   MOVE fe-aquis-inicio TO te-aquis-inicio
                   MOVE fe-aquis-fim TO te-aquis-fim
                   MOVE fe-inicio TO te-inicio
                   MOVE fe-fim TO te-fim
                   MOVE fe-dias TO te-dias
                   MOVE fe-dias-abono TO te-dias-abono
                   MOVE fe-valor-base TO te-valor-base
                   MOVE fe-1-3 TO te-1-3
                   MOVE fe-abono TO te-abono
                   MOVE fe-abono-1-3 TO te-abono-1-3
                   MOVE fe-inss TO te-inss
                   MOVE fe-irrf TO te-irrf
                   MOVE fe-liquido TO te-liquido
                   MOVE fe-situacao TO te-situacao
                   MOVE fe-data-pagamento TO te-data-pagamento
                   WRITE fe-temp-reg
               ELSE MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE fe-file CLOSE fe-temp
           CALL "system" USING "mv dados/ferias.tmp dados/ferias.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO".

       decimo-incluir.
           PERFORM ler-dados-decimo
           PERFORM calcular-decimo
           PERFORM gravar-decimo
           PERFORM mostrar-decimo-calculo.

       decimo-calcular.
           PERFORM ler-dados-decimo
           PERFORM calcular-decimo
           MOVE 0 TO ws-prox-id
           PERFORM mostrar-decimo-calculo.

       ler-dados-decimo.
           ACCEPT ws-func-id-in FROM ENVIRONMENT "FUNCIONARIO_ID"
           COMPUTE ws-func-id = FUNCTION NUMVAL(ws-func-id-in)
           ACCEPT ws-nome-in FROM ENVIRONMENT "NOME"
           ACCEPT ws-ano-in FROM ENVIRONMENT "ANO"
           ACCEPT ws-parcela-in FROM ENVIRONMENT "PARCELA"
           ACCEPT ws-meses-in FROM ENVIRONMENT "MESES"
           COMPUTE ws-meses = FUNCTION NUMVAL(ws-meses-in)
           ACCEPT ws-salario-base-in FROM ENVIRONMENT "SALARIO_BASE"
           COMPUTE ws-salario-base = FUNCTION NUMVAL(ws-salario-base-in)
           IF ws-func-id = 0 THEN
               DISPLAY "ERRO: funcionario obrigatorio" STOP RUN END-IF
           IF ws-parcela-in NOT = "1" AND ws-parcela-in NOT = "2"
               AND ws-parcela-in NOT = "U" THEN
               DISPLAY "ERRO: parcela invalida" STOP RUN END-IF
           IF ws-meses < 1 OR ws-meses > 12 THEN
               DISPLAY "ERRO: meses trabalhados devem estar entre 1 e 12"
               STOP RUN END-IF.

       calcular-decimo.
      *>   RFC-011: base = salario/12 x meses; 1a parcela sem descontos,
      *>   2a parcela (e unica) com INSS/IRRF das tabelas da config.
           COMPUTE ws-decimo-valor-base ROUNDED =
               ws-salario-base / 12 * ws-meses
           IF ws-parcela-in = "1" THEN
               MOVE 0 TO ws-decimo-inss ws-decimo-irrf
           ELSE
               PERFORM folha-carregar-config
               MOVE ws-decimo-valor-base TO ws-base-inss
               PERFORM calcular-inss
               MOVE ws-inss TO ws-decimo-inss
               COMPUTE ws-base-irrf = ws-base-inss - ws-inss
               IF ws-base-irrf < 0 THEN MOVE 0 TO ws-base-irrf END-IF
               PERFORM calcular-irrf
               MOVE ws-irrf TO ws-decimo-irrf
           END-IF
           COMPUTE ws-decimo-liquido = ws-decimo-valor-base
               - ws-decimo-inss - ws-decimo-irrf.

       gravar-decimo.
           MOVE 0 TO ws-prox-id
           OPEN INPUT de-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT de-file CLOSE de-file
               OPEN INPUT de-file END-IF
           PERFORM UNTIL 1 = 2
               READ de-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF de-id > ws-prox-id THEN MOVE de-id TO ws-prox-id END-IF
           END-PERFORM
           CLOSE de-file
           ADD 1 TO ws-prox-id
           OPEN EXTEND de-file
           MOVE ws-prox-id TO de-id
           MOVE ws-func-id TO de-funcionario-id
           MOVE ws-nome-in TO de-nome
           MOVE ws-ano-in TO de-ano
           MOVE ws-parcela-in TO de-parcela
           MOVE ws-decimo-valor-base TO de-valor-base
           MOVE ws-decimo-inss TO de-inss
           MOVE ws-decimo-irrf TO de-irrf
           MOVE ws-decimo-liquido TO de-liquido
           MOVE "C" TO de-situacao
           MOVE SPACES TO de-data-pagamento
           WRITE de-reg
           CLOSE de-file.

       mostrar-decimo-calculo.
           MOVE SPACES TO ws-json-linha
           MOVE ws-prox-id TO ws-id-ed
           MOVE ws-func-id TO ws-func-id-ed
           MOVE ws-meses TO ws-dias-ed
           STRING '{"id":' FUNCTION TRIM(ws-id-ed)
               ',"funcionario_id":' FUNCTION TRIM(ws-func-id-ed)
               ',"nome":"' FUNCTION TRIM(ws-nome-in) '"'
               ',"ano":"' FUNCTION TRIM(ws-ano-in) '"'
               ',"parcela":"' ws-parcela-in '"'
               ',"meses":' FUNCTION TRIM(ws-dias-ed)
               INTO ws-json-linha
           MOVE ws-decimo-valor-base TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"valor_base":' FUNCTION TRIM(ws-jl)
               INTO ws-json-linha
           MOVE ws-decimo-inss TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss":' FUNCTION TRIM(ws-jl)
               INTO ws-json-linha
           MOVE ws-decimo-irrf TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf":' FUNCTION TRIM(ws-jl)
               INTO ws-json-linha
           MOVE ws-decimo-liquido TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"liquido":' FUNCTION TRIM(ws-jl)
               ',"situacao":"C"}'
               INTO ws-json-linha
           DISPLAY FUNCTION TRIM(ws-json-linha).

       decimo-listar.
           OPEN INPUT de-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"decimos":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"decimos":['
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ de-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-encontrou = "S" THEN MOVE "N" TO ws-encontrou
               ELSE DISPLAY "," END-IF
               MOVE SPACES TO ws-json-linha
               MOVE de-id TO ws-id-ed
               MOVE de-funcionario-id TO ws-func-id-ed
               MOVE de-valor-base TO ws-je
               STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                   ',"funcionario_id":' FUNCTION TRIM(ws-func-id-ed)
                   ',"nome":"' FUNCTION TRIM(de-nome) '"'
                   ',"ano":"' FUNCTION TRIM(de-ano) '"'
                   ',"parcela":"' de-parcela '"'
                   ',"valor_base":' FUNCTION TRIM(ws-je)
                   INTO ws-json-linha
               MOVE de-inss TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"inss":' FUNCTION TRIM(ws-je) INTO ws-json-linha
               MOVE de-irrf TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"irrf":' FUNCTION TRIM(ws-je) INTO ws-json-linha
               MOVE de-liquido TO ws-je
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"liquido":' FUNCTION TRIM(ws-je)
                   ',"situacao":"' de-situacao '"'
                   ',"data_pagamento":"' FUNCTION TRIM(de-data-pagamento) '"}'
                   INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE de-file.

       decimo-pagar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-data-in FROM ENVIRONMENT "DATA_PAGAMENTO"
           MOVE "N" TO ws-encontrou
           OPEN INPUT de-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO" STOP RUN END-IF
           OPEN OUTPUT de-temp
           PERFORM UNTIL 1 = 2
               READ de-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF de-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   MOVE "P" TO de-situacao
                   MOVE ws-data-in TO de-data-pagamento
               END-IF
               MOVE de-id TO qe-id
               MOVE de-funcionario-id TO qe-funcionario-id
               MOVE de-nome TO qe-nome
               MOVE de-ano TO qe-ano
               MOVE de-parcela TO qe-parcela
               MOVE de-valor-base TO qe-valor-base
               MOVE de-inss TO qe-inss
               MOVE de-irrf TO qe-irrf
               MOVE de-liquido TO qe-liquido
               MOVE de-situacao TO qe-situacao
               MOVE de-data-pagamento TO qe-data-pagamento
               WRITE de-temp-reg
           END-PERFORM
           CLOSE de-file CLOSE de-temp
           CALL "system" USING "mv dados/decimo.tmp dados/decimo.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO".

       decimo-excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           MOVE "N" TO ws-encontrou
           OPEN INPUT de-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO" STOP RUN END-IF
           OPEN OUTPUT de-temp
           PERFORM UNTIL 1 = 2
               READ de-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF de-id NOT = ws-id THEN
                   MOVE de-id TO qe-id
                   MOVE de-funcionario-id TO qe-funcionario-id
                   MOVE de-nome TO qe-nome
                   MOVE de-ano TO qe-ano
                   MOVE de-parcela TO qe-parcela
                   MOVE de-valor-base TO qe-valor-base
                   MOVE de-inss TO qe-inss
                   MOVE de-irrf TO qe-irrf
                   MOVE de-liquido TO qe-liquido
                   MOVE de-situacao TO qe-situacao
                   MOVE de-data-pagamento TO qe-data-pagamento
                   WRITE de-temp-reg
               ELSE MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE de-file CLOSE de-temp
           CALL "system" USING "mv dados/decimo.tmp dados/decimo.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO".

       comp-calcular.
      *>   RFC-013 — Folha complementar (ajuste de competência fechada).
      *>   Calcula a diferença (positiva = a favor; negativa = contra) com
      *>   INSS/IRRF sobre a diferença quando a favor; devolução não tributa.
      *>   Não grava — retorna o JSON do cálculo.
           PERFORM ler-dados-comp
           PERFORM validar-motivo-comp
           PERFORM calcular-comp
           MOVE 0 TO ws-prox-id
           PERFORM mostrar-comp-calculo.

       comp-incluir.
      *>   Valida (motivo obrigatório; negativo com motivo específico e
      *>   dentro do limite legal de desconto), calcula e grava a
      *>   complementar com situação "C" (calculada).
           PERFORM ler-dados-comp
           PERFORM validar-motivo-comp
           PERFORM calcular-comp
           PERFORM gravar-comp
           PERFORM mostrar-comp-calculo.

       ler-dados-comp.
           ACCEPT ws-func-id-in FROM ENVIRONMENT "FUNCIONARIO_ID"
           COMPUTE ws-func-id = FUNCTION NUMVAL(ws-func-id-in)
           ACCEPT ws-nome-in FROM ENVIRONMENT "NOME"
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           MOVE ws-comp-in TO ws-comp-competencia
           ACCEPT ws-comp-cfg FROM ENVIRONMENT "COMPETENCIA_REF"
           MOVE ws-comp-cfg TO ws-comp-competencia-ref
           ACCEPT ws-comp-motivo-in FROM ENVIRONMENT "MOTIVO"
           MOVE ws-comp-motivo-in TO ws-comp-motivo
           ACCEPT ws-valor-in FROM ENVIRONMENT "VALOR"
           COMPUTE ws-comp-valor = FUNCTION NUMVAL(ws-valor-in)
           ACCEPT ws-salario-base-in FROM ENVIRONMENT "SALARIO_BASE"
           COMPUTE ws-salario-base = FUNCTION NUMVAL(ws-salario-base-in)
           IF ws-func-id = 0 THEN
               DISPLAY "ERRO: funcionario obrigatorio" STOP RUN END-IF
           IF ws-comp-competencia = SPACES THEN
               DISPLAY "ERRO: competencia obrigatoria" STOP RUN END-IF
           IF ws-comp-competencia-ref = SPACES THEN
               DISPLAY "ERRO: competencia de referencia obrigatoria"
               STOP RUN END-IF.

       validar-motivo-comp.
      *>   RFC-013 Decisão 1: motivo obrigatório ao abrir (rastreabilidade).
      *>   Decisão 2: valores negativos exigem motivo específico e validado
      *>   (erro comprovado, devolução, decisão judicial) e respeitam o
      *>   limite legal de desconto de 70% do salário.
           IF ws-comp-motivo = SPACES THEN
               DISPLAY "ERRO: motivo obrigatorio" STOP RUN END-IF
           IF ws-comp-valor = 0 THEN
               DISPLAY "ERRO: valor da diferenca obrigatorio" STOP RUN END-IF
           IF ws-comp-valor < 0 THEN
               IF ws-comp-motivo NOT = "erro comprovado"
                   AND ws-comp-motivo NOT = "devolucao"
                   AND ws-comp-motivo NOT = "decisao judicial" THEN
                   DISPLAY "ERRO: valor negativo exige motivo especifico "
                       "(erro comprovado, devolucao ou decisao judicial)"
                       STOP RUN END-IF
               COMPUTE ws-limite-desc ROUNDED = ws-salario-base * 70 / 100
               IF FUNCTION ABS(ws-comp-valor) > ws-limite-desc THEN
                   DISPLAY "ERRO: desconto excede o limite legal de 70% "
                       "do salario" STOP RUN END-IF
           END-IF.

       calcular-comp.
      *>   Diferença a favor (positiva): tributa INSS/IRRF sobre a diferença.
      *>   Diferença contra (negativa): devolução — não tributa (o valor já
      *>   foi tributado na competência original).
           IF ws-comp-valor > 0 THEN
               PERFORM folha-carregar-config
               MOVE ws-comp-valor TO ws-base-inss
               PERFORM calcular-inss
               MOVE ws-inss TO ws-comp-inss
               COMPUTE ws-base-irrf = ws-base-inss - ws-inss
               IF ws-base-irrf < 0 THEN MOVE 0 TO ws-base-irrf END-IF
               PERFORM calcular-irrf
               MOVE ws-irrf TO ws-comp-irrf
               COMPUTE ws-comp-liquido = ws-comp-valor
                   - ws-comp-inss - ws-comp-irrf
           ELSE
               MOVE 0 TO ws-comp-inss ws-comp-irrf
               MOVE ws-comp-valor TO ws-comp-liquido
           END-IF.

       gravar-comp.
           MOVE 0 TO ws-prox-id
           OPEN INPUT cp-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT cp-file CLOSE cp-file
               OPEN INPUT cp-file END-IF
           PERFORM UNTIL 1 = 2
               READ cp-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF cp-id > ws-prox-id THEN MOVE cp-id TO ws-prox-id END-IF
           END-PERFORM
           CLOSE cp-file
           ADD 1 TO ws-prox-id
           OPEN EXTEND cp-file
           MOVE ws-prox-id TO cp-id
           MOVE ws-func-id TO cp-funcionario-id
           MOVE ws-nome-in TO cp-nome
           MOVE ws-comp-competencia TO cp-competencia
           MOVE ws-comp-competencia-ref TO cp-competencia-ref
           MOVE ws-comp-motivo TO cp-motivo
           MOVE ws-comp-valor TO cp-valor
           MOVE ws-comp-inss TO cp-inss
           MOVE ws-comp-irrf TO cp-irrf
           MOVE ws-comp-liquido TO cp-liquido
           MOVE "C" TO cp-situacao
           MOVE SPACES TO cp-data-pag
           WRITE cp-reg
           CLOSE cp-file.

       mostrar-comp-calculo.
           MOVE SPACES TO ws-json-linha
           MOVE ws-prox-id TO ws-id-ed
           MOVE ws-func-id TO ws-func-id-ed
           STRING '{"id":' FUNCTION TRIM(ws-id-ed)
               ',"funcionario_id":' FUNCTION TRIM(ws-func-id-ed)
               ',"nome":"' FUNCTION TRIM(ws-nome-in) '"'
               ',"competencia":"' FUNCTION TRIM(ws-comp-competencia) '"'
               ',"competencia_ref":"' FUNCTION TRIM(ws-comp-competencia-ref) '"'
               ',"motivo":"' FUNCTION TRIM(ws-comp-motivo) '"'
               INTO ws-json-linha
           MOVE ws-comp-valor TO ws-ed
           STRING FUNCTION TRIM(ws-json-linha)
               ',"valor":' FUNCTION TRIM(ws-ed)
               INTO ws-json-linha
           MOVE ws-comp-inss TO ws-ne
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss":' FUNCTION TRIM(ws-ne)
               INTO ws-json-linha
           MOVE ws-comp-irrf TO ws-ne
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf":' FUNCTION TRIM(ws-ne)
               INTO ws-json-linha
           MOVE ws-comp-liquido TO ws-ed
           STRING FUNCTION TRIM(ws-json-linha)
               ',"liquido":' FUNCTION TRIM(ws-ed)
               ',"situacao":"C"}'
               INTO ws-json-linha
           DISPLAY FUNCTION TRIM(ws-json-linha).

       comp-listar.
           OPEN INPUT cp-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"complementares":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"complementares":['
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ cp-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-encontrou = "S" THEN MOVE "N" TO ws-encontrou
               ELSE DISPLAY "," END-IF
               MOVE SPACES TO ws-json-linha
               MOVE cp-id TO ws-id-ed
               MOVE cp-funcionario-id TO ws-func-id-ed
               STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                   ',"funcionario_id":' FUNCTION TRIM(ws-func-id-ed)
                   ',"nome":"' FUNCTION TRIM(cp-nome) '"'
                   ',"competencia":"' FUNCTION TRIM(cp-competencia) '"'
                   ',"competencia_ref":"' FUNCTION TRIM(cp-competencia-ref) '"'
                   ',"motivo":"' FUNCTION TRIM(cp-motivo) '"'
                   INTO ws-json-linha
               MOVE cp-valor TO ws-ed
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"valor":' FUNCTION TRIM(ws-ed) INTO ws-json-linha
               MOVE cp-inss TO ws-ne
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"inss":' FUNCTION TRIM(ws-ne) INTO ws-json-linha
               MOVE cp-irrf TO ws-ne
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"irrf":' FUNCTION TRIM(ws-ne) INTO ws-json-linha
               MOVE cp-liquido TO ws-ed
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"liquido":' FUNCTION TRIM(ws-ed)
                   ',"situacao":"' cp-situacao '"'
                   ',"data_pagamento":"' FUNCTION TRIM(cp-data-pag) '"}'
                   INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
           END-PERFORM
           DISPLAY ']}'
           CLOSE cp-file.

       comp-validar.
           MOVE "C" TO ws-sit-origem
           MOVE "V" TO ws-sit-destino
           PERFORM comp-transicao.

       comp-fechar.
           MOVE "V" TO ws-sit-origem
           MOVE "F" TO ws-sit-destino
           PERFORM comp-transicao.

       comp-pagar.
           MOVE "F" TO ws-sit-origem
           MOVE "P" TO ws-sit-destino
           ACCEPT ws-data-in FROM ENVIRONMENT "DATA_PAGAMENTO"
           PERFORM comp-transicao.

       comp-transicao.
      *>   Fluxo de estados RFC-006 na complementar: C (calculada) →
      *>   V (validada) → F (fechada) → P (paga). Reescreve o arquivo
      *>   mantendo os demais registros.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           MOVE "N" TO ws-encontrou
           OPEN INPUT cp-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO" STOP RUN END-IF
           OPEN OUTPUT cp-temp
           PERFORM UNTIL 1 = 2
               READ cp-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               MOVE cp-reg TO cp-temp-reg
               IF cp-id = ws-id THEN
                   IF cp-situacao NOT = ws-sit-origem THEN
                       DISPLAY "ERRO: transicao invalida" STOP RUN END-IF
                   MOVE ws-sit-destino TO qt-situacao
                   IF ws-sit-destino = "P" THEN
                       MOVE ws-data-in TO qt-data-pag
                   END-IF
                   MOVE "S" TO ws-encontrou
               END-IF
               WRITE cp-temp-reg
           END-PERFORM
           CLOSE cp-file CLOSE cp-temp
           CALL "system" USING "mv dados/complementar.tmp dados/complementar.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO".

       comp-excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           MOVE "N" TO ws-encontrou
           OPEN INPUT cp-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO" STOP RUN END-IF
           OPEN OUTPUT cp-temp
           PERFORM UNTIL 1 = 2
               READ cp-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF cp-id NOT = ws-id THEN
                   MOVE cp-reg TO cp-temp-reg
                   WRITE cp-temp-reg
               ELSE MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE cp-file CLOSE cp-temp
           CALL "system" USING "mv dados/complementar.tmp dados/complementar.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO".

       comp-encargos.
      *>   RFC-013 Decisão 4: encargos e recolhimentos são recalculados
      *>   APENAS sobre a diferença das complementares da competência
      *>   (não sobre a folha original). Base = soma das diferenças a favor
      *>   (positivas) das complementares fechadas/pagas; FGTS sobre a base
      *>   e INSS patronal/RAT/terceiros conforme regime (igual RFC-014).
      *>   Não grava em encargos.dat (a folha mensal já tem o seu) — apenas
      *>   retorna o JSON para o server gerar lançamentos/recolhimentos.
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           ACCEPT ws-regime-in FROM ENVIRONMENT "REGIME"
           PERFORM folha-carregar-config
           MOVE 0 TO ws-enc-base ws-enc-fgts ws-enc-inss-patronal
           MOVE 0 TO ws-enc-rat ws-enc-terceiros
           OPEN INPUT cp-file
           IF ws-file-status NOT = "35" THEN
               PERFORM UNTIL 1 = 2
                   READ cp-file NEXT RECORD
                       AT END EXIT PERFORM
                   END-READ
                   IF cp-competencia = ws-comp-in
                       AND (cp-situacao = "F" OR cp-situacao = "P")
                       AND cp-valor > 0 THEN
                       ADD cp-valor TO ws-enc-base
                   END-IF
               END-PERFORM
           END-IF
           CLOSE cp-file
           COMPUTE ws-enc-fgts ROUNDED = ws-enc-base * cf-fgts-aliquota / 100
           IF ws-regime-in = "simples" THEN
               MOVE 0 TO ws-enc-inss-patronal ws-enc-rat ws-enc-terceiros
           ELSE
               COMPUTE ws-enc-inss-patronal ROUNDED =
                   ws-enc-base * cf-inss-patronal-aliq / 100
               COMPUTE ws-enc-rat ROUNDED =
                   ws-enc-base * cf-rat-aliq / 100
               COMPUTE ws-enc-terceiros ROUNDED =
                   ws-enc-base * cf-terceiros-aliq / 100
           END-IF
           COMPUTE ws-enc-total = ws-enc-fgts + ws-enc-inss-patronal
               + ws-enc-rat + ws-enc-terceiros
           MOVE ws-enc-base TO ws-jx
           STRING '{"competencia":"' FUNCTION TRIM(ws-comp-in) '",'
               '"regime":"' FUNCTION TRIM(ws-regime-in) '",'
               '"base":' FUNCTION TRIM(ws-jx)
               INTO ws-json-linha
           MOVE ws-enc-fgts TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"fgts":' FUNCTION TRIM(ws-jx) INTO ws-json-linha
           MOVE ws-enc-inss-patronal TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss_patronal":' FUNCTION TRIM(ws-jx) INTO ws-json-linha
           MOVE ws-enc-rat TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"rat":' FUNCTION TRIM(ws-jx) INTO ws-json-linha
           MOVE ws-enc-terceiros TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"terceiros":' FUNCTION TRIM(ws-jx) INTO ws-json-linha
           MOVE ws-enc-total TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"total":' FUNCTION TRIM(ws-jx) '}'
               INTO ws-json-linha
           DISPLAY FUNCTION TRIM(ws-json-linha).

       rescisao-incluir.
           PERFORM ler-dados-rescisao
           PERFORM validar-motivo
           PERFORM calcular-rescisao
           PERFORM gravar-rescisao.
       rescisao-calcular.
           PERFORM ler-dados-rescisao
           PERFORM validar-motivo
           PERFORM calcular-rescisao
           PERFORM mostrar-rescisao.

       ler-dados-rescisao.
           ACCEPT ws-func-id-in FROM ENVIRONMENT "FUNCIONARIO_ID"
           COMPUTE ws-func-id = FUNCTION NUMVAL(ws-func-id-in)
           ACCEPT ws-nome-in FROM ENVIRONMENT "NOME"
           ACCEPT ws-motivo-in FROM ENVIRONMENT "MOTIVO"
           ACCEPT ws-data-in FROM ENVIRONMENT "DATA_DESLIG"
           ACCEPT ws-tipo-aviso-in FROM ENVIRONMENT "TIPO_AVISO"
           ACCEPT ws-dias-in FROM ENVIRONMENT "DIAS_AVISO"
           ACCEPT ws-saldo-dias-in FROM ENVIRONMENT "SALDO_DIAS"
           ACCEPT ws-ferias-venc-dias-in FROM ENVIRONMENT "FERIAS_VENC_DIAS"
           ACCEPT ws-ferias-prop-meses-in FROM ENVIRONMENT "FERIAS_PROP_MESES"
           ACCEPT ws-13-prop-meses-in FROM ENVIRONMENT "13_PROP_MESES"
           ACCEPT ws-salario-base-in FROM ENVIRONMENT "SALARIO_BASE"
           IF ws-func-id = 0 THEN
               DISPLAY "ERRO: funcionario obrigatorio" STOP RUN END-IF
           IF ws-data-in = SPACES THEN
               DISPLAY "ERRO: data de desligamento obrigatoria"
               STOP RUN END-IF
           IF ws-motivo-in = SPACES THEN
               DISPLAY "ERRO: motivo de desligamento obrigatorio"
               STOP RUN END-IF
           COMPUTE re-dias-aviso = FUNCTION NUMVAL(ws-dias-in)
           COMPUTE ws-saldo-dias = FUNCTION NUMVAL(ws-saldo-dias-in)
           COMPUTE ws-ferias-venc-dias =
               FUNCTION NUMVAL(ws-ferias-venc-dias-in)
           COMPUTE ws-ferias-prop-meses =
               FUNCTION NUMVAL(ws-ferias-prop-meses-in)
           COMPUTE ws-13-prop-meses =
               FUNCTION NUMVAL(ws-13-prop-meses-in)
           COMPUTE ws-salario-base = FUNCTION NUMVAL(ws-salario-base-in).

       validar-motivo.
           EVALUATE ws-motivo-in
               WHEN "sem-justa-causa"  CONTINUE
               WHEN "com-justa-causa"  CONTINUE
               WHEN "pedido-demissao"  CONTINUE
               WHEN "acordo"           CONTINUE
               WHEN "termino-contrato" CONTINUE
               WHEN OTHER
                   DISPLAY "ERRO: motivo de desligamento invalido"
                   STOP RUN
           END-EVALUATE.

       calcular-rescisao.
           MOVE "C" TO re-situacao
           MOVE ws-motivo-in TO re-motivo
           MOVE ws-data-in TO re-data-deslig
           MOVE ws-tipo-aviso-in TO re-tipo-aviso
           MOVE ws-nome-in TO re-nome
           MOVE ws-func-id TO re-funcionario-id
           COMPUTE ws-salario-dia = ws-salario-base / 30
           COMPUTE re-saldo-salario ROUNDED =
               ws-salario-dia * ws-saldo-dias
           IF ws-tipo-aviso-in = "indenizado" THEN
               COMPUTE ws-aviso-previo ROUNDED =
                   ws-salario-dia * re-dias-aviso
               MOVE ws-aviso-previo TO re-aviso-previo
           ELSE
               MOVE 0 TO ws-aviso-previo
               MOVE 0 TO re-aviso-previo END-IF
      *>   RFC-010 Decisao 4 na rescisao: ferias vencidas sao pagas em dobro
      *>   (so o salario dobra — 1/3 constitucional permanece na base normal,
      *>   mesma decisao de produto do gozo). RFC-010 §6: vencidas pagas no acerto.
           COMPUTE ws-ferias-venc-normal ROUNDED =
               ws-salario-dia * ws-ferias-venc-dias
           COMPUTE re-ferias-venc ROUNDED =
               ws-ferias-venc-normal * 2
           COMPUTE re-ferias-prop ROUNDED =
               ws-salario-base / 12 * ws-ferias-prop-meses
           COMPUTE ws-ferias-1-3-base =
               ws-ferias-venc-normal + re-ferias-prop
           COMPUTE ws-ferias-total = re-ferias-venc + re-ferias-prop
           COMPUTE re-1-3-ferias ROUNDED = ws-ferias-1-3-base / 3
           COMPUTE re-13-prop ROUNDED =
               ws-salario-base / 12 * ws-13-prop-meses
           COMPUTE ws-total-verbas = re-saldo-salario
               + ws-aviso-previo + re-ferias-venc + re-ferias-prop
               + re-1-3-ferias + re-13-prop
           COMPUTE re-fgts ROUNDED = ws-total-verbas * 0.08
           IF ws-motivo-in = "sem-justa-causa" THEN
               COMPUTE re-multa-fgts ROUNDED = re-fgts * 0.40
           ELSE IF ws-motivo-in = "acordo" THEN
               COMPUTE re-multa-fgts ROUNDED = re-fgts * 0.20
           ELSE MOVE 0 TO re-multa-fgts END-IF END-IF
           MOVE 0 TO re-inss re-irrf
           COMPUTE ws-total-verbas =
               ws-total-verbas + re-fgts + re-multa-fgts
           COMPUTE re-liquido =
               ws-total-verbas - re-inss - re-irrf
           PERFORM calcula-prazo
      *>   preserva o registro calculado (o READ do gravar-rescisao apaga)
           MOVE re-reg TO ws-re-backup.

       calcula-prazo.
           MOVE SPACES TO ws-prazo-pag
           IF ws-data-in = SPACES THEN EXIT PARAGRAPH END-IF
           UNSTRING ws-data-in DELIMITED BY "-"
               INTO ws-ano-x ws-mes-x ws-dia-x
           END-UNSTRING
           MOVE ws-ano-x TO ws-ano-n
           MOVE ws-mes-x TO ws-mes-n
           MOVE ws-dia-x TO ws-dia-n
           COMPUTE ws-data-num =
               ws-ano-n * 10000 + ws-mes-n * 100 + ws-dia-n
           COMPUTE ws-data-int = FUNCTION INTEGER-OF-DATE(ws-data-num)
           ADD 10 TO ws-data-int
           COMPUTE ws-data-num = FUNCTION DATE-OF-INTEGER(ws-data-int)
           MOVE ws-data-num TO ws-data-edit
           STRING ws-dt-ano "-" ws-dt-mes "-" ws-dt-dia
               DELIMITED BY SIZE INTO ws-prazo-pag.

       gravar-rescisao.
           MOVE 0 TO ws-prox-id
           OPEN INPUT re-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT re-file CLOSE re-file
               OPEN INPUT re-file END-IF
           PERFORM UNTIL 1 = 2
               READ re-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF re-funcionario-id = ws-func-id
                  AND re-situacao = "C" THEN
                   DISPLAY "ERRO: funcionario ja possui rescisao pendente"
                   STOP RUN END-IF
               IF re-id > ws-prox-id THEN MOVE re-id TO ws-prox-id END-IF
           END-PERFORM
           CLOSE re-file
           ADD 1 TO ws-prox-id
      *>   restaura o registro calculado sobrescrito pelo loop de READ acima
           MOVE ws-re-backup TO re-reg
           OPEN EXTEND re-file
           MOVE ws-prox-id TO re-id
           MOVE ws-func-id TO re-funcionario-id
           MOVE ws-nome-in TO re-nome
           MOVE ws-motivo-in TO re-motivo
           MOVE ws-data-in TO re-data-deslig
           MOVE ws-tipo-aviso-in TO re-tipo-aviso
           MOVE ws-aviso-previo TO re-aviso-previo
           MOVE ws-prazo-pag TO re-prazo-pag
           MOVE "C" TO re-situacao
           MOVE SPACES TO re-data-pagamento
           WRITE re-reg
           CLOSE re-file
           PERFORM mostrar-rescisao.

       mostrar-rescisao.
           MOVE SPACES TO ws-json-linha
           MOVE ws-prox-id TO ws-id-ed
           MOVE ws-func-id TO ws-func-id-ed
           MOVE re-dias-aviso TO ws-dias-ed
           STRING '{"id":' FUNCTION TRIM(ws-id-ed)
               ',"funcionario_id":' FUNCTION TRIM(ws-func-id-ed)
               ',"motivo":"' FUNCTION TRIM(re-motivo) '"'
               ',"data_deslig":"' FUNCTION TRIM(re-data-deslig) '"'
               ',"tipo_aviso":"' FUNCTION TRIM(re-tipo-aviso) '"'
               ',"dias_aviso":' FUNCTION TRIM(ws-dias-ed)
               INTO ws-json-linha
           MOVE re-aviso-previo TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"aviso_previo":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
           MOVE re-saldo-salario TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"saldo_salario":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
           MOVE re-ferias-venc TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"ferias_venc":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
           IF ws-ferias-venc-dias > 0 THEN MOVE "true" TO ws-bool-ed
           ELSE MOVE "false" TO ws-bool-ed END-IF
           STRING FUNCTION TRIM(ws-json-linha)
               ',"ferias_venc_dobro":' FUNCTION TRIM(ws-bool-ed)
               INTO ws-json-linha
           MOVE re-ferias-prop TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"ferias_prop":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
           MOVE re-1-3-ferias TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"1_3_ferias":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
           MOVE ws-ferias-total TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"ferias":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
           MOVE re-13-prop TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"decimo_proporcional":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
           MOVE re-fgts TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"fgts":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
           MOVE re-multa-fgts TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"multa_fgts":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
           MOVE re-inss TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
           MOVE re-irrf TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
           MOVE re-liquido TO ws-jl
           STRING FUNCTION TRIM(ws-json-linha)
               ',"liquido":' FUNCTION TRIM(ws-jl)
               ',"prazo_pagamento":"' FUNCTION TRIM(ws-prazo-pag) '"'
               ',"situacao":"' re-situacao '"}'
               INTO ws-json-linha
           DISPLAY FUNCTION TRIM(ws-json-linha).

       rescisao-listar.
           OPEN INPUT re-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"rescisoes":[],"total":0}'
               STOP RUN END-IF
           DISPLAY '{"rescisoes":['
           MOVE "S" TO ws-encontrou
           MOVE 0 TO ws-total
           PERFORM UNTIL 1 = 2
               READ re-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               ADD 1 TO ws-total
               IF ws-encontrou = "S" THEN MOVE "N" TO ws-encontrou
               ELSE DISPLAY "," END-IF
               MOVE SPACES TO ws-json-linha
               MOVE re-id TO ws-id-ed
               MOVE re-funcionario-id TO ws-func-id-ed
               MOVE re-dias-aviso TO ws-dias-ed
               STRING '{"id":' FUNCTION TRIM(ws-id-ed)
                   ',"funcionario_id":' FUNCTION TRIM(ws-func-id-ed)
                   ',"nome":"' FUNCTION TRIM(re-nome) '"'
                   ',"motivo":"' FUNCTION TRIM(re-motivo) '"'
                   ',"data_deslig":"' FUNCTION TRIM(re-data-deslig) '"'
                   ',"tipo_aviso":"' FUNCTION TRIM(re-tipo-aviso) '"'
                   ',"dias_aviso":' FUNCTION TRIM(ws-dias-ed)
                   INTO ws-json-linha
               MOVE re-aviso-previo TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"aviso_previo":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
               MOVE re-saldo-salario TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"saldo_salario":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
               MOVE re-ferias-venc TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"ferias_venc":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
               IF re-ferias-venc > 0 THEN MOVE "true" TO ws-bool-ed
               ELSE MOVE "false" TO ws-bool-ed END-IF
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"ferias_venc_dobro":' FUNCTION TRIM(ws-bool-ed)
                   INTO ws-json-linha
               MOVE re-ferias-prop TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"ferias_prop":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
               MOVE re-1-3-ferias TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"1_3_ferias":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
               COMPUTE ws-ferias-total =
                   re-ferias-venc + re-ferias-prop + re-1-3-ferias
               MOVE ws-ferias-total TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"ferias":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
               MOVE re-13-prop TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"decimo_proporcional":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
               MOVE re-fgts TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"fgts":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
               MOVE re-multa-fgts TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"multa_fgts":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
               MOVE re-inss TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"inss":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
               MOVE re-irrf TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"irrf":' FUNCTION TRIM(ws-jl) INTO ws-json-linha
               MOVE re-liquido TO ws-jl
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"liquido":' FUNCTION TRIM(ws-jl)
                   ',"prazo_pagamento":"' FUNCTION TRIM(re-prazo-pag) '"'
                   ',"situacao":"' re-situacao '"'
                   ',"data_pagamento":"' FUNCTION TRIM(re-data-pagamento) '"}'
                   INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
           END-PERFORM
           MOVE ws-total TO ws-total-ed
           DISPLAY '],"total":' FUNCTION TRIM(ws-total-ed) '}'
           CLOSE re-file.

       rescisao-pagar.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           ACCEPT ws-data-in FROM ENVIRONMENT "DATA_PAGAMENTO"
           IF ws-data-in = SPACES THEN
               MOVE FUNCTION CURRENT-DATE(1:8) TO ws-data-edit
               STRING ws-dt-ano "-" ws-dt-mes "-" ws-dt-dia
                   DELIMITED BY SIZE INTO ws-data-in
           END-IF
           MOVE "N" TO ws-encontrou
           OPEN INPUT re-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO" STOP RUN END-IF
           OPEN OUTPUT re-temp
           PERFORM UNTIL 1 = 2
               READ re-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF re-id = ws-id THEN
                   MOVE "S" TO ws-encontrou
                   IF re-situacao = "P" THEN
                       DISPLAY "ERRO: rescisao ja paga" STOP RUN END-IF
                   MOVE "P" TO re-situacao
                   MOVE ws-data-in TO re-data-pagamento
               END-IF
               MOVE re-id TO se-id
               MOVE re-funcionario-id TO se-funcionario-id
               MOVE re-nome TO se-nome
               MOVE re-motivo TO se-motivo
               MOVE re-data-deslig TO se-data-deslig
               MOVE re-tipo-aviso TO se-tipo-aviso
               MOVE re-dias-aviso TO se-dias-aviso
               MOVE re-aviso-previo TO se-aviso-previo
               MOVE re-saldo-salario TO se-saldo-salario
               MOVE re-ferias-venc TO se-ferias-venc
               MOVE re-ferias-prop TO se-ferias-prop
               MOVE re-1-3-ferias TO se-1-3-ferias
               MOVE re-13-prop TO se-13-prop
               MOVE re-fgts TO se-fgts
               MOVE re-multa-fgts TO se-multa-fgts
               MOVE re-inss TO se-inss
               MOVE re-irrf TO se-irrf
               MOVE re-liquido TO se-liquido
               MOVE re-situacao TO se-situacao
               MOVE re-data-pagamento TO se-data-pagamento
               MOVE re-prazo-pag TO se-prazo-pag
               WRITE re-temp-reg
           END-PERFORM
           CLOSE re-file CLOSE re-temp
           CALL "system" USING "mv dados/rescisoes.tmp dados/rescisoes.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO".

       rescisao-excluir.
           ACCEPT ws-id-in FROM ENVIRONMENT "ID"
           COMPUTE ws-id = FUNCTION NUMVAL(ws-id-in)
           MOVE "N" TO ws-encontrou
           OPEN INPUT re-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO" STOP RUN END-IF
           OPEN OUTPUT re-temp
           PERFORM UNTIL 1 = 2
               READ re-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF re-id NOT = ws-id THEN
                   MOVE re-id TO se-id
                   MOVE re-funcionario-id TO se-funcionario-id
                   MOVE re-nome TO se-nome
                   MOVE re-motivo TO se-motivo
                   MOVE re-data-deslig TO se-data-deslig
                   MOVE re-tipo-aviso TO se-tipo-aviso
                   MOVE re-dias-aviso TO se-dias-aviso
                   MOVE re-aviso-previo TO se-aviso-previo
                   MOVE re-saldo-salario TO se-saldo-salario
                   MOVE re-ferias-venc TO se-ferias-venc
                   MOVE re-ferias-prop TO se-ferias-prop
                   MOVE re-1-3-ferias TO se-1-3-ferias
                   MOVE re-13-prop TO se-13-prop
                   MOVE re-fgts TO se-fgts
                   MOVE re-multa-fgts TO se-multa-fgts
                   MOVE re-inss TO se-inss
                   MOVE re-irrf TO se-irrf
                   MOVE re-liquido TO se-liquido
                   MOVE re-situacao TO se-situacao
                   MOVE re-data-pagamento TO se-data-pagamento
                   MOVE re-prazo-pag TO se-prazo-pag
                   WRITE re-temp-reg
               ELSE
                   IF re-situacao = "P" THEN
                       DISPLAY "ERRO: rescisao ja paga, nao pode ser excluida"
                       STOP RUN END-IF
                   MOVE "S" TO ws-encontrou
               END-IF
           END-PERFORM
           CLOSE re-file CLOSE re-temp
           CALL "system" USING "mv dados/rescisoes.tmp dados/rescisoes.dat"
           END-CALL
           IF ws-encontrou = "S" THEN DISPLAY "OK"
           ELSE DISPLAY "ERRO".

      *> ============ RFC-006 — Processamento da Folha ============
      *> Competência única (decisão 2): header (func_id=0) guarda o
      *> estado; registros por funcionário guardam o resultado calculado.
      *> Estados: A=aberta C=calculada V=validada F=fechada P=paga.

       folha-carregar-config.
      *>   RFC-005 Regra 1: o cálculo usa a tabela vigente NA COMPETÊNCIA.
      *>   ws-comp-in traz a competência sendo processada; sem filtro (férias,
      *>   13º, rescisão), usa a versão mais recente (última linha).
           PERFORM config-defaults
           MOVE SPACES TO ws-cf-sel
           OPEN INPUT cf-file
           IF ws-file-status NOT = "35" THEN           PERFORM UNTIL 1 = 2
               READ cf-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
                   IF cf-competencia NOT = SPACES THEN
                       IF ws-comp-in = SPACES THEN
                           MOVE cf-reg TO ws-cf-sel
                       ELSE
                           IF cf-competencia <= ws-comp-in THEN
                               MOVE cf-reg TO ws-cf-sel
                           END-IF
                       END-IF
                   END-IF
               END-PERFORM
           END-IF
           CLOSE cf-file
           IF ws-cf-sel NOT = SPACES THEN
               MOVE ws-cf-sel TO cf-reg
           END-IF.

       config-defaults.
           MOVE 1518.00 TO cf-salario-minimo
           MOVE 1518.00 TO cf-inss-f1-teto
           MOVE 7.50     TO cf-inss-f1-aliq
           MOVE 2793.88  TO cf-inss-f2-teto
           MOVE 9.00     TO cf-inss-f2-aliq
           MOVE 4190.83  TO cf-inss-f3-teto
           MOVE 12.00    TO cf-inss-f3-aliq
           MOVE 8157.41  TO cf-inss-f4-teto
           MOVE 14.00    TO cf-inss-f4-aliq
           MOVE 189.59   TO cf-irrf-ded-dep
           MOVE 2259.20  TO cf-irrf-f1-teto
           MOVE 0.00     TO cf-irrf-f1-aliq
           MOVE 2826.65  TO cf-irrf-f2-teto
           MOVE 7.50     TO cf-irrf-f2-aliq
           MOVE 3751.05  TO cf-irrf-f3-teto
           MOVE 15.00    TO cf-irrf-f3-aliq
           MOVE 4664.68  TO cf-irrf-f4-teto
           MOVE 22.50    TO cf-irrf-f4-aliq
           MOVE 0.00     TO cf-irrf-f1-ded
           MOVE 169.44   TO cf-irrf-f2-ded
           MOVE 381.44   TO cf-irrf-f3-ded
           MOVE 662.77   TO cf-irrf-f4-ded
           MOVE 0.00     TO cf-irrf-f5-teto
           MOVE 27.50    TO cf-irrf-f5-aliq
           MOVE 896.00   TO cf-irrf-f5-ded
           MOVE 8.00     TO cf-fgts-aliquota
           MOVE 50.00    TO cf-hora-extra-aliq
           MOVE 1905.52  TO cf-sf-f1-teto
           MOVE 62.04    TO cf-sf-f1-valor
           MOVE 3047.00  TO cf-sf-f2-teto
           MOVE 43.17    TO cf-sf-f2-valor
      *> Encargos patronais (RFC-014): INSS patronal 20%, RAT/SAT 2%
      *> (risco médio — ajustável por CNAE) e terceiros configurável
           MOVE 20.00    TO cf-inss-patronal-aliq
           MOVE 2.00     TO cf-rat-aliq
           MOVE 0.00     TO cf-terceiros-aliq
           MOVE SPACES   TO cf-competencia.

       calcular-inss.
      *>   INSS progressivo por faixa (RFC-005 §2 — soma das faixas)
           IF ws-base-inss <= cf-inss-f1-teto THEN
               COMPUTE ws-p1 = ws-base-inss * cf-inss-f1-aliq / 100
               MOVE 0 TO ws-p2 ws-p3 ws-p4
           ELSE
               COMPUTE ws-p1 = cf-inss-f1-teto * cf-inss-f1-aliq / 100
               COMPUTE ws-resto = ws-base-inss - cf-inss-f1-teto
               COMPUTE ws-teto2 = cf-inss-f2-teto - cf-inss-f1-teto
               IF ws-resto <= ws-teto2 THEN
                   COMPUTE ws-p2 = ws-resto * cf-inss-f2-aliq / 100
                   MOVE 0 TO ws-p3 ws-p4
               ELSE
                   COMPUTE ws-p2 = ws-teto2 * cf-inss-f2-aliq / 100
                   COMPUTE ws-resto = ws-base-inss - cf-inss-f2-teto
                   COMPUTE ws-teto3 = cf-inss-f3-teto - cf-inss-f2-teto
                   IF ws-resto <= ws-teto3 THEN
                       COMPUTE ws-p3 = ws-resto * cf-inss-f3-aliq / 100
                       MOVE 0 TO ws-p4
                   ELSE
                       COMPUTE ws-p3 = ws-teto3 * cf-inss-f3-aliq / 100
                       COMPUTE ws-resto = ws-base-inss - cf-inss-f3-teto
                       COMPUTE ws-teto1 = cf-inss-f4-teto - cf-inss-f3-teto
                       IF ws-resto <= ws-teto1 THEN
                           COMPUTE ws-p4 = ws-resto * cf-inss-f4-aliq / 100
                       ELSE
                           COMPUTE ws-p4 = ws-teto1 * cf-inss-f4-aliq / 100
                       END-IF
                   END-IF
               END-IF
           END-IF
           COMPUTE ws-inss ROUNDED = ws-p1 + ws-p2 + ws-p3 + ws-p4.

       calcular-irrf.
      *>   IRRF (RFC-005 §3): recebe a base pronta em ws-base-irrf
           IF ws-base-irrf <= cf-irrf-f1-teto THEN
               MOVE 0 TO ws-irrf
           ELSE
               IF ws-base-irrf <= cf-irrf-f2-teto THEN
                   COMPUTE ws-irrf ROUNDED = ws-base-irrf
                       * cf-irrf-f2-aliq / 100 - cf-irrf-f2-ded
               ELSE
                   IF ws-base-irrf <= cf-irrf-f3-teto THEN
                       COMPUTE ws-irrf ROUNDED = ws-base-irrf
                           * cf-irrf-f3-aliq / 100 - cf-irrf-f3-ded
                   ELSE
                       IF ws-base-irrf <= cf-irrf-f4-teto THEN
                           COMPUTE ws-irrf ROUNDED = ws-base-irrf
                               * cf-irrf-f4-aliq / 100 - cf-irrf-f4-ded
                       ELSE
                           COMPUTE ws-irrf ROUNDED = ws-base-irrf
                               * cf-irrf-f5-aliq / 100 - cf-irrf-f5-ded
                       END-IF
                   END-IF
               END-IF
               IF ws-irrf < 0 THEN MOVE 0 TO ws-irrf END-IF
           END-IF.

       calcular-sal-familia.
      *>   Salário-família (RFC-005 §4): direito por cota (dependente
      *>   elegível) conforme a faixa de salário. Duas faixas com teto e
      *>   valor por cota; acima do 2º teto não há direito.
           MOVE 0 TO ws-sal-familia
           IF ws-cotas-sf > 0 THEN
               IF ws-salario-base <= cf-sf-f1-teto THEN
                   COMPUTE ws-sal-familia ROUNDED =
                       ws-cotas-sf * cf-sf-f1-valor
               ELSE
                   IF ws-salario-base <= cf-sf-f2-teto THEN
                       COMPUTE ws-sal-familia ROUNDED =
                           ws-cotas-sf * cf-sf-f2-valor
                   END-IF
               END-IF
           END-IF.

       folha-abrir.
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           IF ws-comp-in = SPACES THEN
               DISPLAY "ERRO: competencia obrigatoria" STOP RUN END-IF
           OPEN INPUT fo-file
           IF ws-file-status = "35" THEN
               OPEN OUTPUT fo-file CLOSE fo-file
               OPEN INPUT fo-file END-IF
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fo-func-id = 0 AND fo-competencia = ws-comp-in THEN
                   DISPLAY "ERRO: competencia ja existe"
                   STOP RUN END-IF
           END-PERFORM
           CLOSE fo-file
      *>   Monta o header DEPOIS do loop (o READ sobrescreve fo-reg)
           MOVE ws-comp-in TO fo-competencia
           MOVE 0 TO fo-func-id
           MOVE "__COMPETENCIA__" TO fo-nome
           MOVE 0 TO fo-salario-base fo-horas-extras fo-dsr
           MOVE 0 TO fo-faltas-dias fo-dependentes
           MOVE 0 TO fo-outros-prov fo-outros-desc
           MOVE 0 TO fo-fgts
           MOVE 0 TO fo-proventos fo-base-inss
           MOVE 0 TO fo-inss
           MOVE 0 TO fo-base-irrf
           MOVE 0 TO fo-irrf fo-total-desc fo-liquido
           MOVE "A" TO fo-situacao
           MOVE SPACES TO fo-data-pag
           OPEN EXTEND fo-file
           WRITE fo-reg
           CLOSE fo-file
           DISPLAY "OK".

       folha-calcular.
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           ACCEPT ws-func-id-in FROM ENVIRONMENT "FUNCIONARIO_ID"
           COMPUTE ws-func-id = FUNCTION NUMVAL(ws-func-id-in)
           ACCEPT ws-nome-in FROM ENVIRONMENT "NOME"
           ACCEPT ws-salario-base-in FROM ENVIRONMENT "SALARIO_BASE"
           MOVE FUNCTION NUMVAL(ws-salario-base-in) TO ws-salario-base
           ACCEPT ws-valor-in FROM ENVIRONMENT "HORAS_EXTRAS"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO ws-he-extra
           ACCEPT ws-valor-in FROM ENVIRONMENT "DSR"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO ws-dsr
           ACCEPT ws-faltas-in FROM ENVIRONMENT "FALTAS"
           MOVE FUNCTION NUMVAL(ws-faltas-in) TO ws-faltas
           ACCEPT ws-dep-in FROM ENVIRONMENT "DEPENDENTES"
           COMPUTE ws-dependentes = FUNCTION NUMVAL(ws-dep-in)
           ACCEPT ws-cotas-sf-in FROM ENVIRONMENT "COTAS_SF"
           IF ws-cotas-sf-in = SPACES THEN
               MOVE 0 TO ws-cotas-sf
           ELSE
               COMPUTE ws-cotas-sf = FUNCTION NUMVAL(ws-cotas-sf-in)
           END-IF
           ACCEPT ws-valor-in FROM ENVIRONMENT "OUTROS_PROV"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO ws-outros-prov
           ACCEPT ws-valor-in FROM ENVIRONMENT "OUTROS_DESC"
           MOVE FUNCTION NUMVAL(ws-valor-in) TO ws-outros-desc
           IF ws-comp-in = SPACES OR ws-func-id = 0 THEN
               DISPLAY "ERRO: competencia e funcionario obrigatorios"
               STOP RUN END-IF
           MOVE "N" TO ws-achou-comp
           OPEN INPUT fo-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: competencia nao existe" STOP RUN END-IF
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fo-func-id = 0 AND fo-competencia = ws-comp-in THEN
                   MOVE "S" TO ws-achou-comp
                   IF fo-situacao = "V" OR fo-situacao = "F"
                       OR fo-situacao = "P" THEN
                       DISPLAY "ERRO: competencia '" fo-situacao "' nao aceita recalculo"
                       STOP RUN END-IF
               END-IF
           END-PERFORM
           CLOSE fo-file
           IF ws-achou-comp NOT = "S" THEN
               DISPLAY "ERRO: competencia nao existe" STOP RUN END-IF

           PERFORM folha-carregar-config
      *>   Proventos e bases (RFC-006 §3.2)
           COMPUTE ws-total-prov = ws-salario-base + ws-he-extra
               + ws-dsr + ws-outros-prov
           MOVE ws-total-prov TO ws-base-inss
           PERFORM calcular-inss
      *>   IRRF (RFC-005 §3): base = base INSS - INSS - dependentes
           COMPUTE ws-base-irrf = ws-base-inss - ws-inss
               - (ws-dependentes * cf-irrf-ded-dep)
           IF ws-base-irrf < 0 THEN MOVE 0 TO ws-base-irrf END-IF
           PERFORM calcular-irrf
      *>   Salário-família (RFC-005 §4): provento que NÃO incide INSS/IRRF;
      *>   entra nos proventos e no líquido, fora da base INSS.
           PERFORM calcular-sal-familia
           ADD ws-sal-familia TO ws-total-prov
      *>   Descontos: faltas (salario/30 por dia) + outros + INSS + IRRF
           COMPUTE ws-desc-faltas ROUNDED =
               (ws-salario-base / 30) * ws-faltas
           COMPUTE ws-total-desc ROUNDED = ws-desc-faltas
               + ws-outros-desc + ws-inss + ws-irrf
           COMPUTE ws-liquido = ws-total-prov - ws-total-desc
      *>   FGTS (RFC-005 §4): 8% do salário base, gravado no processamento
           COMPUTE ws-fgts ROUNDED = ws-salario-base
               * cf-fgts-aliquota / 100

      *>   Grava/substitui o registro do funcionário na competência
           OPEN INPUT fo-file
           OPEN OUTPUT fo-temp-file
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fo-competencia = ws-comp-in
                   AND fo-func-id = ws-func-id THEN
                   CONTINUE
               ELSE
                   MOVE fo-competencia TO ft-competencia
                   MOVE fo-func-id TO ft-func-id
                   MOVE fo-nome TO ft-nome
                   MOVE fo-salario-base TO ft-salario-base
                   MOVE fo-horas-extras TO ft-horas-extras
                   MOVE fo-dsr TO ft-dsr
                   MOVE fo-faltas-dias TO ft-faltas-dias
                   MOVE fo-dependentes TO ft-dependentes
                   MOVE fo-outros-prov TO ft-outros-prov
                   MOVE fo-outros-desc TO ft-outros-desc
               MOVE fo-sal-familia TO ft-sal-familia
                   MOVE fo-sal-familia TO ft-sal-familia
                   MOVE fo-fgts TO ft-fgts
                   MOVE fo-proventos TO ft-proventos
                   MOVE fo-base-inss TO ft-base-inss
                   MOVE fo-inss TO ft-inss
                   MOVE fo-base-irrf TO ft-base-irrf
                   MOVE fo-irrf TO ft-irrf
                   MOVE fo-total-desc TO ft-total-desc
                   MOVE fo-liquido TO ft-liquido
                   MOVE fo-situacao TO ft-situacao
                   MOVE fo-data-pag TO ft-data-pag
                   WRITE fo-temp-reg
               END-IF
           END-PERFORM
           MOVE ws-comp-in TO ft-competencia
           MOVE ws-func-id TO ft-func-id
           MOVE ws-nome-in TO ft-nome
           MOVE ws-salario-base TO ft-salario-base
           MOVE ws-he-extra TO ft-horas-extras
           MOVE ws-dsr TO ft-dsr
           MOVE ws-faltas TO ft-faltas-dias
           MOVE ws-dependentes TO ft-dependentes
           MOVE ws-outros-prov TO ft-outros-prov
           MOVE ws-outros-desc TO ft-outros-desc
           MOVE ws-sal-familia TO ft-sal-familia
           MOVE ws-fgts TO ft-fgts
           MOVE ws-total-prov TO ft-proventos
           MOVE ws-base-inss TO ft-base-inss
           MOVE ws-inss TO ft-inss
           MOVE ws-base-irrf TO ft-base-irrf
           MOVE ws-irrf TO ft-irrf
           MOVE ws-total-desc TO ft-total-desc
           MOVE ws-liquido TO ft-liquido
           MOVE "C" TO ft-situacao
           MOVE SPACES TO ft-data-pag
           WRITE fo-temp-reg
           CLOSE fo-file CLOSE fo-temp-file
           CALL "system" USING "mv dados/folhas.tmp dados/folhas.dat"
           END-CALL

           MOVE ws-total-prov TO ws-jx
           STRING '{"proventos":' FUNCTION TRIM(ws-jx)
               INTO ws-json-linha
           MOVE ws-base-inss TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"base_inss":' FUNCTION TRIM(ws-jx)
               INTO ws-json-linha
           MOVE ws-inss TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss":' FUNCTION TRIM(ws-jx)
               INTO ws-json-linha
           MOVE ws-base-irrf TO ws-ne
           STRING FUNCTION TRIM(ws-json-linha)
               ',"base_irrf":' FUNCTION TRIM(ws-ne)
               INTO ws-json-linha
           MOVE ws-irrf TO ws-ne
           STRING FUNCTION TRIM(ws-json-linha)
               ',"irrf":' FUNCTION TRIM(ws-ne)
               INTO ws-json-linha
           MOVE ws-sal-familia TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"salario_familia":' FUNCTION TRIM(ws-jx)
               INTO ws-json-linha
           MOVE ws-total-desc TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"total_descontos":' FUNCTION TRIM(ws-jx)
               INTO ws-json-linha
           MOVE ws-liquido TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"liquido":' FUNCTION TRIM(ws-jx) '}'
               INTO ws-json-linha
           DISPLAY FUNCTION TRIM(ws-json-linha).

       folha-concluir.
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           PERFORM folha-transicao-interna
           OPEN INPUT fo-file
           OPEN OUTPUT fo-temp-file
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fo-func-id = 0 AND fo-competencia = ws-comp-in THEN
                   IF fo-situacao NOT = "A" THEN
                       DISPLAY "ERRO: concluir exige competencia aberta"
                       STOP RUN END-IF
                   MOVE "C" TO ft-situacao
               ELSE
                   MOVE fo-situacao TO ft-situacao
               END-IF
               MOVE fo-competencia TO ft-competencia
               MOVE fo-func-id TO ft-func-id
               MOVE fo-nome TO ft-nome
               MOVE fo-salario-base TO ft-salario-base
               MOVE fo-horas-extras TO ft-horas-extras
               MOVE fo-dsr TO ft-dsr
               MOVE fo-faltas-dias TO ft-faltas-dias
               MOVE fo-dependentes TO ft-dependentes
               MOVE fo-outros-prov TO ft-outros-prov
               MOVE fo-outros-desc TO ft-outros-desc
               MOVE fo-sal-familia TO ft-sal-familia
               MOVE fo-fgts TO ft-fgts
               MOVE fo-proventos TO ft-proventos
               MOVE fo-base-inss TO ft-base-inss
               MOVE fo-inss TO ft-inss
               MOVE fo-base-irrf TO ft-base-irrf
               MOVE fo-irrf TO ft-irrf
               MOVE fo-total-desc TO ft-total-desc
               MOVE fo-liquido TO ft-liquido
               MOVE fo-data-pag TO ft-data-pag
               WRITE fo-temp-reg
           END-PERFORM
           CLOSE fo-file CLOSE fo-temp-file
           CALL "system" USING "mv dados/folhas.tmp dados/folhas.dat"
           END-CALL
           DISPLAY "OK".

       folha-transicao-interna.
           MOVE "N" TO ws-achou-comp
           MOVE 0 TO ws-qtde-func
           OPEN INPUT fo-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: competencia nao existe" STOP RUN END-IF
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fo-func-id = 0 AND fo-competencia = ws-comp-in THEN
                   MOVE "S" TO ws-achou-comp
               END-IF
               IF fo-func-id > 0 AND fo-competencia = ws-comp-in THEN
                   ADD 1 TO ws-qtde-func
               END-IF
           END-PERFORM
           CLOSE fo-file
           IF ws-achou-comp NOT = "S" THEN
               DISPLAY "ERRO: competencia nao existe" STOP RUN END-IF
           IF ws-qtde-func = 0 THEN
               DISPLAY "ERRO: nenhum funcionario processado" STOP RUN END-IF.

       folha-validar.
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           PERFORM folha-transicao-interna
           PERFORM folha-muda-estado
           DISPLAY "OK".

       folha-fechar.
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           ACCEPT ws-regime-in FROM ENVIRONMENT "REGIME"
           PERFORM folha-transicao-interna
           PERFORM folha-muda-estado
      *> RFC-014 §4.4/Decisão 4: encargos calculados no fechamento e
      *> consolidados no relatório próprio (nunca no holerite — RFC-007)
           PERFORM encargos-calcular
           DISPLAY "OK".

       encargos-calcular.
      *> RFC-014 §4: base de encargos = soma dos proventos que incidem FGTS
      *> (base FGTS do processamento); INSS patronal, RAT e terceiros usam a
      *> tabela vigente da competência. Regime "simples" zera INSS patronal,
      *> RAT e terceiros (recolhimento unificado DAS — RFC-014 §3/Decisão 2).
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           ACCEPT ws-regime-in FROM ENVIRONMENT "REGIME"
           PERFORM folha-carregar-config
           MOVE 0 TO ws-enc-base ws-enc-fgts ws-enc-inss-patronal
           MOVE 0 TO ws-enc-rat ws-enc-terceiros
           OPEN INPUT fo-file
           IF ws-file-status NOT = "35" THEN
               PERFORM UNTIL 1 = 2
                   READ fo-file NEXT RECORD
                       AT END EXIT PERFORM
                   END-READ
                   IF fo-func-id > 0 AND fo-competencia = ws-comp-in THEN
                       ADD fo-salario-base TO ws-enc-base
                       ADD fo-fgts TO ws-enc-fgts
                   END-IF
               END-PERFORM
           END-IF
           CLOSE fo-file
           IF ws-regime-in = "simples" THEN
               MOVE 0 TO ws-enc-inss-patronal ws-enc-rat ws-enc-terceiros
           ELSE
               COMPUTE ws-enc-inss-patronal ROUNDED =
                   ws-enc-base * cf-inss-patronal-aliq / 100
               COMPUTE ws-enc-rat ROUNDED =
                   ws-enc-base * cf-rat-aliq / 100
               COMPUTE ws-enc-terceiros ROUNDED =
                   ws-enc-base * cf-terceiros-aliq / 100
           END-IF
           COMPUTE ws-enc-total = ws-enc-fgts + ws-enc-inss-patronal
               + ws-enc-rat + ws-enc-terceiros
      *>   Grava o registro de encargos da competência (substitui versão)
           MOVE ws-comp-in TO en-competencia
           MOVE ws-regime-in TO en-regime
           MOVE ws-enc-base TO en-base
           MOVE ws-enc-fgts TO en-fgts
           MOVE ws-enc-inss-patronal TO en-inss-patronal
           MOVE ws-enc-rat TO en-rat
           MOVE ws-enc-terceiros TO en-terceiros
           MOVE ws-enc-total TO en-total
           MOVE en-reg TO ws-en-sel
           PERFORM encargos-grava
      *>   O READ dentro do grava sobrescreve en-reg; restaura a cópia
           MOVE ws-en-sel TO en-reg
           PERFORM encargos-display-json.

       encargos-mostrar.
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           MOVE SPACES TO ws-en-sel
           OPEN INPUT en-file
           IF ws-file-status = "35" THEN
               MOVE SPACES TO en-reg
               MOVE ws-comp-in TO en-competencia
               MOVE SPACES TO en-regime
               MOVE 0 TO en-base en-fgts en-inss-patronal
               MOVE 0 TO en-rat en-terceiros en-total
               PERFORM encargos-display-json
               STOP RUN END-IF
           MOVE "N" TO ws-achou-comp
           PERFORM UNTIL 1 = 2
               READ en-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF en-competencia = ws-comp-in THEN
                   MOVE "S" TO ws-achou-comp
                   MOVE en-reg TO ws-en-sel
               END-IF
           END-PERFORM
           CLOSE en-file
           IF ws-en-sel = SPACES THEN
               MOVE ws-comp-in TO en-competencia
               MOVE SPACES TO en-regime
               MOVE 0 TO en-base en-fgts en-inss-patronal
               MOVE 0 TO en-rat en-terceiros en-total
           ELSE
               MOVE ws-en-sel TO en-reg
           END-IF
           PERFORM encargos-display-json.

       encargos-grava.
      *>   Reescreve o arquivo mantendo as outras competências e a nova
      *>   (ou atualizada) por último. Usa ws-en-sel porque o READ sobrescreve
      *>   en-reg (mesmo padrão do config-salvar com ws-cf-sel)
           OPEN INPUT en-file
           OPEN OUTPUT en-temp
           IF ws-file-status NOT = "35" THEN
               PERFORM UNTIL 1 = 2
                   READ en-file NEXT RECORD
                       AT END EXIT PERFORM
                   END-READ
                   IF en-competencia NOT = ws-comp-in THEN
                       MOVE en-reg TO en-temp-reg
                       WRITE en-temp-reg
                   END-IF
               END-PERFORM
           END-IF
           MOVE ws-en-sel TO en-temp-reg
           WRITE en-temp-reg
           CLOSE en-file CLOSE en-temp
           CALL "system" USING
               "mv dados/encargos.tmp dados/encargos.dat"
           END-CALL.

       encargos-display-json.
      *>   Emite o JSON de encargos (uma linha) para o server persistir o
      *>   relatório e gerar os lançamentos contábeis
           MOVE en-base TO ws-jx
           STRING '{"competencia":"' FUNCTION TRIM(en-competencia) '",'
               '"regime":"' FUNCTION TRIM(en-regime) '",'
               '"base":' FUNCTION TRIM(ws-jx)
               INTO ws-json-linha
           MOVE en-fgts TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"fgts":' FUNCTION TRIM(ws-jx) INTO ws-json-linha
           MOVE en-inss-patronal TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"inss_patronal":' FUNCTION TRIM(ws-jx) INTO ws-json-linha
           MOVE en-rat TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"rat":' FUNCTION TRIM(ws-jx) INTO ws-json-linha
           MOVE en-terceiros TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"terceiros":' FUNCTION TRIM(ws-jx) INTO ws-json-linha
           MOVE en-total TO ws-jx
           STRING FUNCTION TRIM(ws-json-linha)
               ',"total":' FUNCTION TRIM(ws-jx) '}'
               INTO ws-json-linha
           DISPLAY FUNCTION TRIM(ws-json-linha).

       folha-pagar.
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           ACCEPT ws-data-in FROM ENVIRONMENT "DATA_PAGAMENTO"
           MOVE "N" TO ws-achou-comp
           OPEN INPUT fo-file
           IF ws-file-status = "35" THEN
               DISPLAY "ERRO: competencia nao existe" STOP RUN END-IF
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fo-func-id = 0 AND fo-competencia = ws-comp-in THEN
                   MOVE "S" TO ws-achou-comp
               END-IF
           END-PERFORM
           CLOSE fo-file
           IF ws-achou-comp NOT = "S" THEN
               DISPLAY "ERRO: competencia nao existe" STOP RUN END-IF
           PERFORM folha-muda-estado
           DISPLAY "OK".

       folha-muda-estado.
           OPEN INPUT fo-file
           OPEN OUTPUT fo-temp-file
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               MOVE fo-competencia TO ft-competencia
               MOVE fo-func-id TO ft-func-id
               MOVE fo-nome TO ft-nome
               MOVE fo-salario-base TO ft-salario-base
               MOVE fo-horas-extras TO ft-horas-extras
               MOVE fo-dsr TO ft-dsr
               MOVE fo-faltas-dias TO ft-faltas-dias
               MOVE fo-dependentes TO ft-dependentes
               MOVE fo-outros-prov TO ft-outros-prov
               MOVE fo-outros-desc TO ft-outros-desc
               MOVE fo-sal-familia TO ft-sal-familia
               MOVE fo-fgts TO ft-fgts
               MOVE fo-proventos TO ft-proventos
               MOVE fo-base-inss TO ft-base-inss
               MOVE fo-inss TO ft-inss
               MOVE fo-base-irrf TO ft-base-irrf
               MOVE fo-irrf TO ft-irrf
               MOVE fo-total-desc TO ft-total-desc
               MOVE fo-liquido TO ft-liquido
               MOVE fo-data-pag TO ft-data-pag
               IF fo-func-id = 0 AND fo-competencia = ws-comp-in THEN
                   EVALUATE ws-acao
                       WHEN "folha-validar"
                           IF fo-situacao NOT = "C" THEN
                               DISPLAY "ERRO: validar exige competencia calculada"
                               STOP RUN END-IF
                           MOVE "V" TO ft-situacao
                       WHEN "folha-fechar"
                           IF fo-situacao NOT = "V" THEN
                               DISPLAY "ERRO: fechar exige competencia validada"
                               STOP RUN END-IF
                           MOVE "F" TO ft-situacao
                       WHEN "folha-pagar"
                           IF fo-situacao NOT = "F" THEN
                               DISPLAY "ERRO: pagar exige competencia fechada"
                               STOP RUN END-IF
                           MOVE "P" TO ft-situacao
                           MOVE ws-data-in TO ft-data-pag
                       WHEN OTHER
                           DISPLAY "ERRO: transicao invalida" STOP RUN
                   END-EVALUATE
               ELSE
                   MOVE fo-situacao TO ft-situacao
                   IF ws-acao = "folha-pagar"
                       AND fo-func-id > 0
                       AND fo-competencia = ws-comp-in THEN
                       MOVE ws-data-in TO ft-data-pag
                   END-IF
               END-IF
               WRITE fo-temp-reg
           END-PERFORM
           CLOSE fo-file CLOSE fo-temp-file
           CALL "system" USING "mv dados/folhas.tmp dados/folhas.dat"
           END-CALL.

       folha-listar.
           OPEN INPUT fo-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"competencias":[]}'
               STOP RUN END-IF
           DISPLAY '{"competencias":['
           MOVE SPACES TO ws-comp-ant
           MOVE "N" TO ws-emitiu
           MOVE "S" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fo-func-id = 0 THEN
      *>           Novo header: emite a competência anterior (se houver)
                   IF ws-emitiu = "S" THEN
                       MOVE SPACES TO ws-json-linha
                       IF ws-encontrou = "S" THEN MOVE "N" TO ws-encontrou
                       ELSE DISPLAY "," END-IF
                       MOVE ws-qtde-func TO ws-qtde-ed
                       STRING '{"competencia":"' FUNCTION TRIM(ws-comp-ant) '"'
                           ',"situacao":"' ws-sit-ant '"'
                           ',"qtde_funcionarios":' FUNCTION TRIM(ws-qtde-ed)
                           INTO ws-json-linha
                       MOVE ws-total-prov TO ws-total-prov-ed
                       STRING FUNCTION TRIM(ws-json-linha)
                           ',"total_proventos":' FUNCTION TRIM(ws-total-prov-ed)
                           INTO ws-json-linha
                       MOVE ws-total-desc TO ws-total-desc-ed
                       STRING FUNCTION TRIM(ws-json-linha)
                           ',"total_descontos":' FUNCTION TRIM(ws-total-desc-ed)
                           INTO ws-json-linha
                       MOVE ws-liquido TO ws-liquido-ed
                       STRING FUNCTION TRIM(ws-json-linha)
                           ',"liquido":' FUNCTION TRIM(ws-liquido-ed) '}'
                           INTO ws-json-linha
                       DISPLAY FUNCTION TRIM(ws-json-linha)
                   END-IF
                   MOVE fo-competencia TO ws-comp-ant
                   MOVE fo-situacao TO ws-sit-ant
                   MOVE 0 TO ws-qtde-func ws-total-prov
                   MOVE 0 TO ws-total-desc ws-liquido
                   MOVE "S" TO ws-emitiu
               END-IF
               IF fo-func-id > 0 AND fo-competencia = ws-comp-ant THEN
                   ADD 1 TO ws-qtde-func
                   ADD fo-proventos TO ws-total-prov
                   ADD fo-total-desc TO ws-total-desc
                   ADD fo-liquido TO ws-liquido
               END-IF
           END-PERFORM
      *>   Emite a última competência
           IF ws-emitiu = "S" THEN
               MOVE SPACES TO ws-json-linha
               IF ws-encontrou = "S" THEN MOVE "N" TO ws-encontrou
               ELSE DISPLAY "," END-IF
               MOVE ws-qtde-func TO ws-qtde-ed
               STRING '{"competencia":"' FUNCTION TRIM(ws-comp-ant) '"'
                   ',"situacao":"' ws-sit-ant '"'
                   ',"qtde_funcionarios":' FUNCTION TRIM(ws-qtde-ed)
                   INTO ws-json-linha
               MOVE ws-total-prov TO ws-total-prov-ed
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"total_proventos":' FUNCTION TRIM(ws-total-prov-ed)
                   INTO ws-json-linha
               MOVE ws-total-desc TO ws-total-desc-ed
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"total_descontos":' FUNCTION TRIM(ws-total-desc-ed)
                   INTO ws-json-linha
               MOVE ws-liquido TO ws-liquido-ed
               STRING FUNCTION TRIM(ws-json-linha)
                   ',"liquido":' FUNCTION TRIM(ws-liquido-ed) '}'
                   INTO ws-json-linha
               DISPLAY FUNCTION TRIM(ws-json-linha)
           END-IF
           DISPLAY ']}'
           CLOSE fo-file.

       folha-mostrar.
           ACCEPT ws-comp-in FROM ENVIRONMENT "COMPETENCIA"
           OPEN INPUT fo-file
           IF ws-file-status = "35" THEN
               DISPLAY '{"funcionarios":[]}'
               STOP RUN END-IF
           DISPLAY '{"competencia":"' FUNCTION TRIM(ws-comp-in) '","funcionarios":['
           MOVE "S" TO ws-encontrou
           PERFORM UNTIL 1 = 2
               READ fo-file NEXT RECORD
                   AT END EXIT PERFORM
               END-READ
               IF fo-func-id > 0 AND fo-competencia = ws-comp-in THEN
                   MOVE SPACES TO ws-json-linha
                   IF ws-encontrou = "S" THEN MOVE "N" TO ws-encontrou
                   ELSE DISPLAY "," END-IF
                   MOVE fo-func-id TO ws-func-id-ed
                   MOVE fo-salario-base TO ws-jx
                   STRING '{"funcionario_id":' FUNCTION TRIM(ws-func-id-ed)
                       ',"nome":"' FUNCTION TRIM(fo-nome) '"'
                       ',"salario_base":' FUNCTION TRIM(ws-jx)
                       INTO ws-json-linha
                   MOVE fo-proventos TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"proventos":' FUNCTION TRIM(ws-jx)
                       INTO ws-json-linha
                   MOVE fo-base-inss TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"base_inss":' FUNCTION TRIM(ws-jx)
                       INTO ws-json-linha
                   MOVE fo-inss TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"inss":' FUNCTION TRIM(ws-jx)
                       INTO ws-json-linha
                   MOVE fo-base-irrf TO ws-ne
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"base_irrf":' FUNCTION TRIM(ws-ne)
                       INTO ws-json-linha
                   MOVE fo-irrf TO ws-ne
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"irrf":' FUNCTION TRIM(ws-ne)
                       INTO ws-json-linha
                   MOVE fo-sal-familia TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"salario_familia":' FUNCTION TRIM(ws-jx)
                       INTO ws-json-linha
                   MOVE fo-total-desc TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"total_descontos":' FUNCTION TRIM(ws-jx)
                       INTO ws-json-linha
                   MOVE fo-liquido TO ws-jx
                   STRING FUNCTION TRIM(ws-json-linha)
                       ',"liquido":' FUNCTION TRIM(ws-jx)
                       ',"situacao":"' fo-situacao '"'
                       ',"data_pagamento":"' FUNCTION TRIM(fo-data-pag) '"}'
                       INTO ws-json-linha
                   DISPLAY FUNCTION TRIM(ws-json-linha)
               END-IF
           END-PERFORM
           DISPLAY ']}'
           CLOSE fo-file.
