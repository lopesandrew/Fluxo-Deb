"""
Teste da calculadora com curva DI futura
"""
from datetime import datetime
from debenture_calculator import DebentureCalculator

# Cria calculadora
calc = DebentureCalculator()

# Carrega curva DI
print("Carregando curva DI futura da ANBIMA...")
calc.load_di_curve()

# Parâmetros da debênture
emission_date = datetime(2025, 1, 15)
maturity_date = datetime(2026, 1, 15)  # 1 ano
vne = 1000.00
spread = 2.50  # 2.50% a.a. sobre CDI
interest_freq = 'semestral'
amort_type = 'bullet'

print("\nGerando fluxo de caixa...")
cash_flow = calc.generate_cash_flow(
    emission_date=emission_date,
    maturity_date=maturity_date,
    vne=vne,
    cdi_rate_annual=0,  # Será ignorado pois usaremos a curva
    spread_annual=spread,
    interest_frequency=interest_freq,
    amort_type=amort_type,
    grace_period_months=0
)

# Exibe fluxo
print("\n" + "="*80)
print("FLUXO DE CAIXA COM CURVA DI FUTURA")
print("="*80)
print(f"\n{'Evento':<8} {'Data':<12} {'DU':<6} {'Saldo Dev.':<16} {'Juros':<16} {'Amort.':<16} {'PMT':<16}")
print("-"*100)

for row in cash_flow:
    print(f"{row['evento']:<8} "
          f"{row['data'].strftime('%d/%m/%Y'):<12} "
          f"{row['dias_uteis']:<6} "
          f"R$ {row['saldo_devedor']:>12,.2f}  "
          f"R$ {row['juros']:>12,.2f}  "
          f"R$ {row['amortizacao']:>12,.2f}  "
          f"R$ {row['pmt']:>12,.2f}")

# Calcula métricas
metrics = calc.calculate_metrics(cash_flow, emission_date, vne, 0, spread)

print("\n" + "="*80)
print("MÉTRICAS FINANCEIRAS")
print("="*80)
print(f"Total Pago (PMT):     R$ {metrics['total_pmt']:,.2f}")
print(f"TIR:                  {metrics['irr']:.2f}% a.a.")
print(f"Duration:             {metrics['duration_years']:.2f} anos ({metrics['duration_months']:.1f} meses)")

# Exporta para HTML
print("\nExportando para HTML...")
calc.export_to_html(
    cash_flow, emission_date, vne, 0, spread,
    filename="teste_curva_di.html",
    maturity_date=maturity_date,
    interest_frequency=interest_freq,
    amort_type=amort_type,
    grace_period_months=0
)

print("\nArquivo 'teste_curva_di.html' gerado com sucesso!")
