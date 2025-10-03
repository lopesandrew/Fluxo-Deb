# 📊 Calculadora de Debêntures CDI+

Calculadora interativa de fluxo de caixa para debêntures indexadas ao CDI, seguindo os padrões B3 e ANBIMA (base 252 dias úteis).

## 📋 Funcionalidades

- **Cálculo de Fluxo de Caixa**: Gera cronograma completo de pagamentos de juros e amortização
- **Padrão B3/ANBIMA**: Cálculos baseados em 252 dias úteis, com feriados nacionais do Brasil
- **Múltiplas Periodicidades**: Suporte para pagamentos mensais, trimestrais, semestrais, anuais ou bullet
- **Sistemas de Amortização**: Bullet, SAC, Price ou customizado
- **Carência Configurável**: Período de carência do principal
- **Métricas Financeiras**:
  - Taxa Interna de Retorno (TIR)
  - Payback Simples e Descontado
  - Duration de Macaulay
  - Modified Duration
  - Prazo Médio Ponderado
- **Exportação HTML**: Tabela editável com dashboard interativo e gráficos

## 🚀 Instalação

### Requisitos

- Python 3.7+
- Biblioteca `holidays`

### Instalando Dependências

```bash
pip install holidays
```

## 💻 Uso

### Modo Interativo

Execute o script diretamente para usar o modo interativo:

```bash
python debenture_calculator.py
```

O programa irá solicitar:
1. **Datas**: Emissão e vencimento
2. **Valor Nominal**: VNE (padrão R$ 1.000,00)
3. **Taxas**: CDI projetado e spread
4. **Periodicidade**: Frequência dos pagamentos de juros
5. **Amortização**: Sistema de amortização
6. **Carência**: Período de carência do principal
7. **Arquivo**: Nome do arquivo HTML de saída

### Uso Programático

```python
from datetime import datetime
from debenture_calculator import DebentureCalculator

# Cria calculadora
calc = DebentureCalculator()

# Define parâmetros
emission_date = datetime(2024, 1, 15)
maturity_date = datetime(2027, 1, 15)
vne = 1000.00
cdi_rate = 10.65  # % a.a.
spread = 2.50     # % a.a.

# Gera fluxo de caixa
cash_flow = calc.generate_cash_flow(
    emission_date=emission_date,
    maturity_date=maturity_date,
    vne=vne,
    cdi_rate_annual=cdi_rate,
    spread_annual=spread,
    interest_frequency='semestral',
    amort_type='sac',
    grace_period_months=6
)

# Calcula métricas
metrics = calc.calculate_metrics(cash_flow, emission_date, vne, cdi_rate, spread)

# Exporta para HTML
calc.export_to_html(cash_flow, emission_date, vne, cdi_rate, spread, "minha_debenture.html")
```

## 📊 Saída HTML

O arquivo HTML gerado inclui:

- ✅ **Tabela Completa**: Todos os eventos de pagamento com detalhes
- ✏️ **Células Editáveis**: Juros e amortização podem ser editados (células em amarelo)
- 📈 **Dashboard de Métricas**: Cards com todas as métricas financeiras
- 📊 **Gráfico Interativo**: Visualização do fluxo de caixa ao longo do tempo
- 📚 **Glossário**: Explicação das métricas calculadas

## 🔢 Fórmulas Utilizadas

### Fator CDI
```
FatorDI = (1 + CDI/100)^(du/252)
```

### Fator Spread
```
FatorSpread = (1 + Spread/100)^(du/252)
```

### Juros do Período
```
J = VNA × (FatorDI × FatorSpread - 1)
```

Onde:
- `du` = dias úteis entre os pagamentos
- `VNA` = Valor Nominal Atualizado
- Base de cálculo: 252 dias úteis (padrão ANBIMA)

## 📖 Exemplos

### Exemplo 1: Debênture Simples Semestral

```python
# Debênture de 3 anos com pagamento semestral e amortização bullet
cash_flow = calc.generate_cash_flow(
    emission_date=datetime(2024, 1, 15),
    maturity_date=datetime(2027, 1, 15),
    vne=1000.00,
    cdi_rate_annual=10.65,
    spread_annual=2.50,
    interest_frequency='semestral',
    amort_type='bullet'
)
```

### Exemplo 2: Debênture com Carência SAC

```python
# Debênture de 5 anos, carência de 12 meses, amortização SAC trimestral
cash_flow = calc.generate_cash_flow(
    emission_date=datetime(2024, 1, 15),
    maturity_date=datetime(2029, 1, 15),
    vne=10000.00,
    cdi_rate_annual=11.00,
    spread_annual=3.00,
    interest_frequency='trimestral',
    amort_type='sac',
    grace_period_months=12
)
```

## 📚 Glossário de Métricas

- **TIR (Taxa Interna de Retorno)**: Taxa que iguala o valor presente dos fluxos futuros ao investimento inicial
- **Payback Simples**: Tempo para recuperar o investimento sem considerar o valor do dinheiro no tempo
- **Payback Descontado**: Tempo para recuperar o investimento considerando o valor presente dos fluxos
- **Duration de Macaulay**: Prazo médio ponderado dos fluxos de caixa
- **Modified Duration**: Sensibilidade do preço da debênture à variação de 1% na taxa de juros

## 🏦 Conformidade

Este calculador segue os padrões:
- ✅ **B3**: Base 252 dias úteis
- ✅ **ANBIMA**: Feriados nacionais brasileiros
- ✅ **Convenção**: Dias úteis para cálculo de juros

## 🛠️ Estrutura do Código

### Classe `DebentureCalculator`

**Métodos principais:**

- `generate_payment_dates()`: Gera datas de pagamento de juros e amortização
- `calculate_cdi_factor()`: Calcula fator CDI acumulado
- `calculate_spread_factor()`: Calcula fator de spread
- `calculate_interest()`: Calcula juros do período
- `calculate_amortization_schedule()`: Gera cronograma de amortização
- `generate_cash_flow()`: Gera fluxo de caixa completo
- `calculate_metrics()`: Calcula todas as métricas financeiras
- `export_to_html()`: Exporta para HTML com dashboard

## 📝 Licença

Este projeto é de código aberto e está disponível para uso educacional e comercial.

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para:
- Reportar bugs
- Sugerir novas funcionalidades
- Enviar pull requests

## 📧 Contato

Para dúvidas ou sugestões, entre em contato através do repositório.

---

**Desenvolvido com ❤️ para o mercado de renda fixa brasileiro**