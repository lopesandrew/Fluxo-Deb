"""
Teste simples para verificar se a coluna de taxa e vértice está funcionando
"""
from datetime import datetime
from debenture_calculator import DebentureCalculator

# Configuração
calc = DebentureCalculator()

emission_date = datetime(2024, 1, 15)
maturity_date = datetime(2025, 1, 15)
vne = 1000.00
cdi_rate = 10.65
spread = 2.50
interest_freq = 'semestral'
amort_type = 'bullet'
grace_months = 0

# Tenta carregar curva DI
print("Tentando carregar curva DI da ANBIMA...")
curve_loaded = calc.load_di_curve(emission_date)

if curve_loaded:
    print("Curva DI carregada com sucesso!")
else:
    print("Usando taxa CDI fixa fornecida")

# Gera fluxo de caixa
print("\nGerando fluxo de caixa...")
cash_flow = calc.generate_cash_flow(
    emission_date=emission_date,
    maturity_date=maturity_date,
    vne=vne,
    cdi_rate_annual=cdi_rate,
    spread_annual=spread,
    interest_frequency=interest_freq,
    amort_type=amort_type,
    grace_period_months=grace_months
)

# Exibe resultado
print("\n" + "=" * 120)
print(f"{'Ev':<4} {'Data':<12} {'DU':<5} {'DC':<5} {'Taxa CDI':<10} {'Vertice':<10} {'Saldo Dev.':<16} {'Juros':<16} {'Amort.':<16} {'PMT':<16}")
print("=" * 120)

for row in cash_flow:
    taxa_display = f"{row['taxa_cdi_efetiva']:.2f}%" if row['taxa_cdi_efetiva'] is not None else "-"
    vertice_display = f"{row['vertice_dias_uteis']}" if row['vertice_dias_uteis'] is not None else "-"

    print(f"{row['evento']:<4} "
          f"{row['data'].strftime('%d/%m/%Y'):<12} "
          f"{row['dias_uteis']:<5} "
          f"{row['dias_corridos']:<5} "
          f"{taxa_display:<10} "
          f"{vertice_display:<10} "
          f"R$ {row['saldo_devedor']:>12,.2f}  "
          f"R$ {row['juros']:>12,.2f}  "
          f"R$ {row['amortizacao']:>12,.2f}  "
          f"R$ {row['pmt']:>12,.2f}")

# Gera HTML
print("\nGerando arquivo HTML...")
calc.export_to_html(
    cash_flow,
    emission_date,
    vne,
    cdi_rate,
    spread,
    "teste_taxa_vertice.html",
    maturity_date=maturity_date,
    interest_frequency=interest_freq,
    amort_type=amort_type,
    grace_period_months=grace_months
)

print("\nTeste concluido! Arquivo gerado: teste_taxa_vertice.html")
