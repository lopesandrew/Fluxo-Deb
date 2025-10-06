# Calculadora de Debêntures CDI+
## BCP Securities

Aplicação web para cálculo de fluxo de caixa de debêntures indexadas ao CDI, seguindo padrões B3/ANBIMA.

---

## 🚀 Como Usar

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Iniciar o Servidor

```bash
python app.py
```

O servidor estará disponível em: **http://127.0.0.1:5000**

### 3. Acessar a Aplicação

Abra o navegador e acesse `http://127.0.0.1:5000`

---

## 📋 Funcionalidades

### Inputs Disponíveis:
- **Datas**: Emissão e Vencimento
- **Valor Nominal**: Padrão R$ 1.000,00 (ANBIMA)
- **Remuneração**:
  - Curva DI Futura ANBIMA (automática)
  - Taxa CDI fixa (manual)
- **Spread**: % sobre CDI
- **Periodicidade**: Mensal, Trimestral, Semestral, Anual, Bullet
- **Amortização**: Bullet, SAC, PRICE
- **Carência**: Período sem amortização do principal

### Resultados Calculados:
- **Fluxo de Caixa Completo**
  - Datas de pagamento
  - Dias úteis e corridos
  - Saldo devedor
  - Juros e amortização por período
  - PMT total

- **Métricas Financeiras**
  - TIR (Taxa Interna de Retorno)
  - Duration (Macaulay e Modified)
  - Payback (Simples e Descontado)
  - Prazo médio ponderado
  - Totais consolidados

- **Visualizações**
  - Tabela detalhada editável
  - Gráfico interativo (barras + linha)
  - Dashboard de métricas

---

## 🎨 Design

O layout segue a identidade visual da **BCP Securities**:
- **Cor principal**: #424da5 (azul BCP)
- **Tipografia**: Roboto Condensed / Roboto
- **Estilo**: Corporativo, clean e profissional

---

## 🔧 Tecnologias

**Backend:**
- Flask 3.1+
- Python 3.13
- pyettj (curva DI ANBIMA)

**Frontend:**
- HTML5 / CSS3
- JavaScript (Vanilla)
- Chart.js (gráficos)

**Cálculos:**
- Base 252 dias úteis (padrão B3)
- Curva PRE ANBIMA como proxy DI
- Interpolação linear para vencimentos

---

## 📁 Estrutura do Projeto

```
Fluxo-Deb/
├── app.py                      # Servidor Flask
├── debenture_calculator.py     # Engine de cálculo
├── requirements.txt            # Dependências
├── templates/
│   └── index.html             # Interface web
└── static/
    ├── css/
    │   └── style.css          # Estilos BCP
    └── js/
        └── app.js             # Lógica frontend
```

---

## 📊 Padrões Utilizados

- **B3/ANBIMA**: Base 252 dias úteis
- **Curva DI**: ETTJ PRE ANBIMA (dados públicos)
- **Interpolação**: Linear entre vértices
- **TIR**: Método Newton-Raphson
- **Duration**: Macaulay e Modified

---

## 📌 Notas Importantes

1. **Curva DI**: Atualizada diariamente pela ANBIMA (D-1)
2. **Feriados**: Calendário ANBIMA oficial
3. **Precisão**: Cálculos seguem metodologia B3
4. **Uso Interno**: Ferramenta desenvolvida para BCP Securities

---

## 👨‍💻 Desenvolvimento

Desenvolvido para uso interno da **BCP Securities**
Mercados de Capitais - Renda Fixa

---

## 🔐 Segurança

- Aplicação local (não exposta publicamente)
- Sem armazenamento de dados sensíveis
- Cálculos realizados server-side

---

**BCP Securities** | Calculadora de Debêntures CDI+
