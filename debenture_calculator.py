"""
Calculadora de Fluxo de Pagamento de Debêntures CDI+
Padrão: B3 e ANBIMA - Base 252 dias úteis
Versão Interativa
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import holidays
from pyettj import get_ettj_anbima
import pandas as pd
import numpy as np
import json

class DebentureCalculator:
    """
    Calculadora de fluxo de debêntures seguindo padrões B3/ANBIMA
    """
    
    def __init__(self):
        # Feriados nacionais do Brasil (ANBIMA)
        self.br_holidays = holidays.Brazil(years=range(2020, 2050))
        # Curva DI futura (será carregada quando necessário)
        self.di_curve = None
        
    def is_business_day(self, date: datetime) -> bool:
        """Verifica se é dia útil (exclui sábados, domingos e feriados nacionais)"""
        return date.weekday() < 5 and date not in self.br_holidays
    
    def next_business_day(self, date: datetime) -> datetime:
        """Retorna o próximo dia útil"""
        next_day = date
        while not self.is_business_day(next_day):
            next_day += timedelta(days=1)
        return next_day
    
    def count_business_days(self, start_date: datetime, end_date: datetime) -> int:
        """Conta dias úteis entre duas datas (exclusive end_date)"""
        count = 0
        current = start_date
        while current < end_date:
            if self.is_business_day(current):
                count += 1
            current += timedelta(days=1)
        return count
    
    def count_calendar_days(self, start_date: datetime, end_date: datetime) -> int:
        """Conta dias corridos entre duas datas (exclusive end_date)"""
        return (end_date - start_date).days

    def load_di_curve(self, reference_date: datetime = None):
        """
        Carrega a curva de juros prefixada (PRE) da ANBIMA como proxy para DI

        reference_date: Data de referência para a curva (default: dia útil anterior)
        """
        try:
            if reference_date is None:
                reference_date = datetime.now()

            # Tenta carregar dados da ANBIMA
            # ANBIMA atualiza dados com 1 dia de atraso
            date_to_try = reference_date
            max_attempts = 5

            for attempt in range(max_attempts):
                try:
                    date_str = date_to_try.strftime('%d/%m/%Y')
                    _, ettj, _, _ = get_ettj_anbima(date_str)

                    # Remove linhas vazias e converte valores
                    ettj = ettj.dropna(subset=['Vertice', 'Prefixados'])
                    ettj['Vertice'] = ettj['Vertice'].str.replace('.', '').str.strip()
                    ettj['Prefixados'] = ettj['Prefixados'].str.replace(',', '.').str.strip()

                    # Remove linhas com valores vazios
                    ettj = ettj[(ettj['Vertice'] != '') & (ettj['Prefixados'] != '')]

                    ettj['Vertice'] = ettj['Vertice'].astype(int)
                    ettj['Prefixados'] = ettj['Prefixados'].astype(float)

                    self.di_curve = ettj[['Vertice', 'Prefixados']].copy()
                    self.di_curve.columns = ['dias_uteis', 'taxa']

                    print(f"[OK] Curva PRE/DI ANBIMA carregada para {date_str}")
                    print(f"     Vertices disponiveis: {len(self.di_curve)} pontos")
                    return True

                except ValueError:
                    # Tenta dia anterior
                    date_to_try = date_to_try - timedelta(days=1)
                    if attempt < max_attempts - 1:
                        continue
                    else:
                        raise

        except Exception as e:
            print(f"[AVISO] Erro ao carregar curva ANBIMA: {str(e)}")
            print("        Continuando com taxa CDI fixa fornecida pelo usuario")
            self.di_curve = None
            return False

    def get_cdi_rate_from_curve(self, payment_date: datetime, emission_date: datetime) -> float:
        """
        Obtém taxa da curva PRE para uma data específica usando interpolação linear

        Retorna taxa anual em percentual (ex: 10.65 para 10,65% a.a.)
        """
        if self.di_curve is None:
            return None

        try:
            # Calcula dias úteis até o pagamento
            business_days = self.count_business_days(emission_date, payment_date)

            # Interpola taxa usando os vértices da curva
            vertices = self.di_curve['dias_uteis'].values
            taxas = self.di_curve['taxa'].values

            # Interpolação linear
            if business_days <= vertices[0]:
                # Se prazo menor que primeiro vértice, usa a taxa do primeiro vértice
                rate = taxas[0]
            elif business_days >= vertices[-1]:
                # Se prazo maior que último vértice, usa a taxa do último vértice
                rate = taxas[-1]
            else:
                # Interpolação linear entre vértices
                rate = np.interp(business_days, vertices, taxas)

            return float(rate)

        except Exception as e:
            print(f"[AVISO] Erro ao interpolar taxa da curva: {str(e)}")
            return None
    
    def generate_payment_dates(self, 
                              emission_date: datetime,
                              maturity_date: datetime,
                              frequency: str,
                              grace_period_months: int = 0) -> Tuple[List[datetime], List[datetime]]:
        """
        Gera datas de pagamento de juros e amortização
        
        frequency: 'mensal', 'trimestral', 'semestral', 'anual', 'bullet'
        grace_period_months: meses de carência do principal
        """
        
        freq_months = {
            'mensal': 1,
            'trimestral': 3,
            'semestral': 6,
            'anual': 12,
            'bullet': None
        }
        
        if frequency not in freq_months:
            raise ValueError(f"Frequência inválida: {frequency}")
        
        # Datas de pagamento de juros
        interest_dates = []
        
        if frequency == 'bullet':
            interest_dates = [maturity_date]
        else:
            months = freq_months[frequency]
            current_date = emission_date
            
            while True:
                # Adiciona meses
                month = current_date.month + months
                year = current_date.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                
                try:
                    next_date = datetime(year, month, current_date.day)
                except ValueError:
                    # Dia não existe no mês (ex: 31 de fev), usa último dia do mês
                    if month == 12:
                        next_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                    else:
                        next_date = datetime(year, month + 1, 1) - timedelta(days=1)
                
                if next_date > maturity_date:
                    break
                    
                interest_dates.append(next_date)
                current_date = next_date
            
            # Garante que vencimento está incluído
            if interest_dates[-1] != maturity_date:
                interest_dates.append(maturity_date)
        
        # Ajusta para dias úteis
        interest_dates = [self.next_business_day(d) for d in interest_dates]
        
        # Datas de amortização (após carência)
        grace_date = emission_date
        if grace_period_months > 0:
            month = emission_date.month + grace_period_months
            year = emission_date.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            try:
                grace_date = datetime(year, month, emission_date.day)
            except ValueError:
                if month == 12:
                    grace_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    grace_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Amortizações: apenas após carência
        amort_dates = [d for d in interest_dates if d > grace_date]
        
        return interest_dates, amort_dates
    
    def calculate_cdi_factor(self, 
                            cdi_rate_annual: float,
                            business_days: int) -> float:
        """
        Calcula fator CDI acumulado
        
        cdi_rate_annual: Taxa CDI anual (ex: 10.65 para 10,65% a.a.)
        business_days: Número de dias úteis
        """
        # Fórmula B3: FatorDI = (1 + CDI/100)^(du/252)
        return ((1 + cdi_rate_annual / 100) ** (business_days / 252))
    
    def calculate_spread_factor(self,
                               spread_annual: float,
                               business_days: int) -> float:
        """
        Calcula fator de spread
        
        spread_annual: Taxa de spread anual (ex: 2.50 para 2,50% a.a.)
        business_days: Número de dias úteis
        """
        # Fórmula B3: FatorSpread = (1 + spread/100)^(du/252)
        return ((1 + spread_annual / 100) ** (business_days / 252))
    
    def calculate_interest(self,
                          vna: float,
                          cdi_rate_annual: float,
                          spread_annual: float,
                          business_days: int,
                          payment_date: datetime = None,
                          emission_date: datetime = None) -> float:
        """
        Calcula juros do período (CDI + Spread)

        Fórmula: J = VNA × (FatorDI × FatorSpread - 1)

        Se curva DI estiver disponível e datas forem fornecidas, usa taxa da curva
        """
        # Tenta obter taxa da curva DI futura
        curve_cdi_rate = None
        if payment_date and emission_date:
            curve_cdi_rate = self.get_cdi_rate_from_curve(payment_date, emission_date)

        # Usa taxa da curva se disponível, senão usa a taxa fixa fornecida
        effective_cdi_rate = curve_cdi_rate if curve_cdi_rate is not None else cdi_rate_annual

        fator_di = self.calculate_cdi_factor(effective_cdi_rate, business_days)
        fator_spread = self.calculate_spread_factor(spread_annual, business_days)
        fator_juros = fator_di * fator_spread

        return vna * (fator_juros - 1)
    
    def calculate_amortization_schedule(self,
                                       vne: float,
                                       amort_dates: List[datetime],
                                       amort_type: str,
                                       custom_percentages: List[float] = None) -> Dict[datetime, float]:
        """
        Calcula cronograma de amortização
        
        amort_type: 'bullet', 'sac', 'price', 'custom'
        custom_percentages: Lista de percentuais para amortização customizada
        """
        
        amort_schedule = {}
        
        if amort_type == 'bullet':
            # Tudo no vencimento
            amort_schedule[amort_dates[-1]] = 100.0
            
        elif amort_type == 'sac':
            # Sistema SAC: parcelas iguais
            n_payments = len(amort_dates)
            amort_percent = 100.0 / n_payments
            for date in amort_dates:
                amort_schedule[date] = amort_percent
                
        elif amort_type == 'price':
            # Sistema Price: percentuais crescentes (simplificado - usa SAC como base)
            # Para Price real precisaria da taxa de juros
            n_payments = len(amort_dates)
            amort_percent = 100.0 / n_payments
            for date in amort_dates:
                amort_schedule[date] = amort_percent
                
        elif amort_type == 'custom':
            if not custom_percentages or len(custom_percentages) != len(amort_dates):
                raise ValueError("Percentuais customizados devem ter mesmo tamanho que datas de amortização")
            
            if abs(sum(custom_percentages) - 100.0) > 0.01:
                raise ValueError(f"Percentuais devem somar 100%, soma atual: {sum(custom_percentages):.2f}%")
            
            for date, pct in zip(amort_dates, custom_percentages):
                amort_schedule[date] = pct
        
        else:
            raise ValueError(f"Tipo de amortização inválido: {amort_type}")
        
        return amort_schedule
    
    def generate_cash_flow(self,
                          emission_date: datetime,
                          maturity_date: datetime,
                          vne: float,
                          cdi_rate_annual: float,
                          spread_annual: float,
                          interest_frequency: str,
                          amort_type: str,
                          grace_period_months: int = 0,
                          custom_amort_percentages: List[float] = None) -> List[Dict]:
        """
        Gera fluxo de caixa completo da debênture
        """
        
        # Gera datas de pagamento
        interest_dates, amort_dates = self.generate_payment_dates(
            emission_date, maturity_date, interest_frequency, grace_period_months
        )
        
        # Cronograma de amortização
        amort_schedule = self.calculate_amortization_schedule(
            vne, amort_dates, amort_type, custom_amort_percentages
        )
        
        # Constrói fluxo de caixa
        cash_flow = []
        vna_current = vne  # Valor Nominal Atualizado
        previous_date = emission_date
        
        for idx, payment_date in enumerate(interest_dates):
            # Calcula dias
            business_days = self.count_business_days(previous_date, payment_date)
            calendar_days = self.count_calendar_days(previous_date, payment_date)
            
            # Calcula juros (passa as datas para usar curva DI se disponível)
            interest = self.calculate_interest(
                vna_current, cdi_rate_annual, spread_annual, business_days,
                payment_date=payment_date, emission_date=emission_date
            )
            
            # Calcula amortização
            amortization = 0.0
            if payment_date in amort_schedule:
                amort_percent = amort_schedule[payment_date]
                amortization = vne * (amort_percent / 100)
            
            # PMT = Juros + Amortização
            pmt = interest + amortization
            
            # Adiciona ao fluxo
            cash_flow.append({
                'evento': idx + 1,
                'data': payment_date,
                'dias_uteis': business_days,
                'dias_corridos': calendar_days,
                'saldo_devedor': vna_current,
                'juros': interest,
                'amortizacao': amortization,
                'pmt': pmt
            })
            
            # Atualiza saldo devedor
            vna_current -= amortization
            previous_date = payment_date
        
        return cash_flow

    def cash_flow_to_json(self, cash_flow: List[Dict]) -> List[Dict]:
        """
        Converte cash flow para formato JSON serializable
        """
        json_flow = []
        for row in cash_flow:
            json_row = row.copy()
            # Converte datetime para string
            json_row['data'] = row['data'].strftime('%Y-%m-%d')
            json_flow.append(json_row)
        return json_flow

    def calculate_irr(self, cash_flow: List[Dict], vne: float, emission_date: datetime) -> float:
        """
        Calcula a TIR (Taxa Interna de Retorno) usando método de Newton-Raphson
        """
        # Fluxo de caixa: investimento inicial negativo + pagamentos positivos
        flows = [-vne]  # Investimento inicial
        
        for row in cash_flow:
            flows.append(row['pmt'])
        
        # Método de Newton-Raphson para encontrar TIR
        irr = 0.1  # Chute inicial: 10% a.a.
        max_iterations = 100
        tolerance = 0.0001
        
        for _ in range(max_iterations):
            npv = 0
            derivative = 0
            
            for i, flow in enumerate(flows):
                npv += flow / ((1 + irr) ** i)
                if i > 0:
                    derivative -= i * flow / ((1 + irr) ** (i + 1))
            
            if abs(npv) < tolerance:
                break
            
            if derivative == 0:
                break
                
            irr = irr - npv / derivative
        
        return irr * 100  # Retorna em percentual
    
    def calculate_payback(self, cash_flow: List[Dict], vne: float, emission_date: datetime, discount_rate: float) -> Dict:
        """
        Calcula o período de payback simples e descontado
        discount_rate: taxa de desconto em decimal (ex: 0.1 para 10%)
        """
        accumulated_simple = 0
        accumulated_discounted = 0
        payback_simple_years = None
        payback_discounted_years = None
        
        for i, row in enumerate(cash_flow):
            # Payback simples
            accumulated_simple += row['pmt']
            if payback_simple_years is None and accumulated_simple >= vne:
                days_from_emission = (row['data'] - emission_date).days
                payback_simple_years = days_from_emission / 365.25
            
            # Payback descontado
            years_from_emission = (row['data'] - emission_date).days / 365.25
            pv_flow = row['pmt'] / ((1 + discount_rate) ** years_from_emission)
            accumulated_discounted += pv_flow
            
            if payback_discounted_years is None and accumulated_discounted >= vne:
                payback_discounted_years = years_from_emission
        
        return {
            'payback_simple_years': payback_simple_years,
            'payback_simple_months': payback_simple_years * 12 if payback_simple_years else None,
            'payback_discounted_years': payback_discounted_years,
            'payback_discounted_months': payback_discounted_years * 12 if payback_discounted_years else None
        }
    
    def calculate_metrics(self, cash_flow: List[Dict], emission_date: datetime, 
                         vne: float, cdi_rate: float, spread: float) -> Dict:
        """
        Calcula métricas financeiras: duration, prazo médio, etc.
        """
        total_pv = 0
        weighted_time = 0
        weighted_pmt = 0
        total_juros = 0
        total_amort = 0
        total_pmt = 0
        
        # Taxa de desconto (CDI + Spread)
        discount_rate = (cdi_rate + spread) / 100
        
        for row in cash_flow:
            # Tempo em anos desde emissão
            days_from_emission = (row['data'] - emission_date).days
            years_from_emission = days_from_emission / 365.25
            
            # Valor presente do fluxo
            pv_flow = row['pmt'] / ((1 + discount_rate) ** years_from_emission)
            
            # Acumula para cálculo de duration
            total_pv += pv_flow
            weighted_time += pv_flow * years_from_emission
            
            # Acumula para prazo médio (ponderado pelo valor nominal)
            weighted_pmt += row['pmt'] * years_from_emission
            
            # Totais
            total_juros += row['juros']
            total_amort += row['amortizacao']
            total_pmt += row['pmt']
        
        # Duration de Macaulay (em anos)
        duration_years = weighted_time / total_pv if total_pv > 0 else 0
        
        # Prazo médio ponderado (em anos)
        avg_maturity_years = weighted_pmt / total_pmt if total_pmt > 0 else 0
        
        # Modified Duration
        modified_duration = duration_years / (1 + discount_rate)
        
        # Calcula TIR
        irr = self.calculate_irr(cash_flow, vne, emission_date)
        
        # Calcula Payback
        payback = self.calculate_payback(cash_flow, vne, emission_date, discount_rate)
        
        return {
            'total_juros': total_juros,
            'total_amortizacao': total_amort,
            'total_pmt': total_pmt,
            'duration_years': duration_years,
            'duration_months': duration_years * 12,
            'modified_duration': modified_duration,
            'avg_maturity_years': avg_maturity_years,
            'avg_maturity_months': avg_maturity_years * 12,
            'num_payments': len(cash_flow),
            'avg_pmt': total_pmt / len(cash_flow) if len(cash_flow) > 0 else 0,
            'irr': irr,
            'payback_simple_years': payback['payback_simple_years'],
            'payback_simple_months': payback['payback_simple_months'],
            'payback_discounted_years': payback['payback_discounted_years'],
            'payback_discounted_months': payback['payback_discounted_months']
        }
    
    def export_to_html(self, cash_flow: List[Dict], emission_date: datetime,
                      vne: float, cdi_rate: float, spread: float, filename: str = "fluxo_debenture.html",
                      maturity_date: datetime = None, interest_frequency: str = None,
                      amort_type: str = None, grace_period_months: int = 0):
        """
        Exporta fluxo de caixa para HTML editável com métricas financeiras
        """

        # Calcula métricas
        metrics = self.calculate_metrics(cash_flow, emission_date, vne, cdi_rate, spread)

        # Determina data de vencimento se não fornecida
        if maturity_date is None:
            maturity_date = cash_flow[-1]['data'] if cash_flow else emission_date

        # Formata informações de input
        freq_display = {
            'mensal': 'Mensal',
            'trimestral': 'Trimestral',
            'semestral': 'Semestral',
            'anual': 'Anual',
            'bullet': 'Bullet (no vencimento)'
        }

        amort_display = {
            'bullet': 'Bullet (tudo no vencimento)',
            'sac': 'SAC (Sistema de Amortização Constante)',
            'price': 'PRICE (Sistema Francês)',
            'custom': 'Customizado'
        }

        html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fluxo de Pagamento - Debênture CDI+</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .input-summary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .input-summary h2 {
            margin: 0 0 20px 0;
            font-size: 1.5em;
            border-bottom: 2px solid rgba(255,255,255,0.3);
            padding-bottom: 10px;
        }
        .input-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .input-item {
            background-color: rgba(255,255,255,0.1);
            padding: 12px;
            border-radius: 5px;
            border-left: 4px solid rgba(255,255,255,0.5);
        }
        .input-item label {
            display: block;
            font-size: 0.85em;
            opacity: 0.9;
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .input-item .value {
            font-size: 1.3em;
            font-weight: bold;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background-color: #34495e;
            color: white;
            padding: 12px;
            text-align: right;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        th:first-child {
            text-align: center;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
            text-align: right;
        }
        td:first-child {
            text-align: center;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .total-row {
            font-weight: bold;
            background-color: #ecf0f1;
        }
        .editable {
            background-color: #fff9e6;
            cursor: pointer;
        }
        .editable:hover {
            background-color: #fff3cd;
        }
        .summary {
            margin-top: 30px;
            padding: 20px;
            background-color: #e8f4f8;
            border-radius: 5px;
        }
        .summary h3 {
            margin-top: 0;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .metric-card {
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .metric-card h4 {
            margin: 0 0 10px 0;
            color: #34495e;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #2980b9;
        }
        .metric-subtitle {
            font-size: 0.85em;
            color: #7f8c8d;
            margin-top: 5px;
        }
        canvas {
            background-color: white;
            border-radius: 5px;
            padding: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Fluxo de Pagamento - Debênture CDI+</h1>

        <div class="input-summary">
            <h2>📋 Dados da Debênture</h2>
            <div class="input-grid">
                <div class="input-item">
                    <label>📅 Data de Emissão</label>
                    <div class="value">""" + emission_date.strftime('%d/%m/%Y') + """</div>
                </div>
                <div class="input-item">
                    <label>📅 Data de Vencimento</label>
                    <div class="value">""" + maturity_date.strftime('%d/%m/%Y') + """</div>
                </div>
                <div class="input-item">
                    <label>💰 Valor Nominal (VNE)</label>
                    <div class="value">R$ """ + f"{vne:,.2f}" + """</div>
                </div>
                <div class="input-item">
                    <label>📊 Taxa CDI</label>
                    <div class="value">""" + (f"Curva PRE ANBIMA" if self.di_curve is not None else f"{cdi_rate:.2f}% a.a. (fixa)") + """</div>
                </div>
                <div class="input-item">
                    <label>➕ Spread sobre CDI</label>
                    <div class="value">""" + f"{spread:.2f}% a.a." + """</div>
                </div>
                <div class="input-item">
                    <label>📈 Taxa Total (Projetada)</label>
                    <div class="value">""" + f"{cdi_rate + spread:.2f}% a.a." + """</div>
                </div>
                <div class="input-item">
                    <label>💵 Periodicidade dos Juros</label>
                    <div class="value">""" + (freq_display.get(interest_frequency, 'N/A') if interest_frequency else 'N/A') + """</div>
                </div>
                <div class="input-item">
                    <label>📉 Sistema de Amortização</label>
                    <div class="value">""" + (amort_display.get(amort_type, 'N/A') if amort_type else 'N/A') + """</div>
                </div>
                <div class="input-item">
                    <label>⏳ Carência do Principal</label>
                    <div class="value">""" + f"{grace_period_months} meses" + """</div>
                </div>
                <div class="input-item">
                    <label>📆 Prazo Total</label>
                    <div class="value">""" + f"{(maturity_date - emission_date).days} dias" + """</div>
                </div>
            </div>
        </div>

        <table id="cashFlowTable">
            <thead>
                <tr>
                    <th>Evento</th>
                    <th>Data</th>
                    <th>Dias Úteis</th>
                    <th>Dias Corridos</th>
                    <th>Saldo Devedor (R$)</th>
                    <th>Juros (R$)</th>
                    <th>Amortização (R$)</th>
                    <th>PMT (R$)</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Adiciona linhas de dados
        total_juros = 0
        total_amort = 0
        total_pmt = 0
        
        for row in cash_flow:
            total_juros += row['juros']
            total_amort += row['amortizacao']
            total_pmt += row['pmt']
            
            html += f"""
                <tr>
                    <td>{row['evento']}</td>
                    <td>{row['data'].strftime('%d/%m/%Y')}</td>
                    <td>{row['dias_uteis']}</td>
                    <td>{row['dias_corridos']}</td>
                    <td>R$ {row['saldo_devedor']:,.2f}</td>
                    <td class="editable">R$ {row['juros']:,.2f}</td>
                    <td class="editable">R$ {row['amortizacao']:,.2f}</td>
                    <td><strong>R$ {row['pmt']:,.2f}</strong></td>
                </tr>
"""
        
        # Linha de totais
        html += f"""
                <tr class="total-row">
                    <td colspan="5">TOTAIS</td>
                    <td>R$ {total_juros:,.2f}</td>
                    <td>R$ {total_amort:,.2f}</td>
                    <td><strong>R$ {total_pmt:,.2f}</strong></td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
        
        <div class="summary">
            <h3>📊 Resumo e Métricas Financeiras</h3>
            
            <div class="summary-grid">
                <div class="metric-card">
                    <h4>💰 Total de Juros Pagos</h4>
                    <div class="metric-value" id="totalJuros">R$ """ + f"{metrics['total_juros']:,.2f}" + """</div>
                    <div class="metric-subtitle">Remuneração CDI + Spread</div>
                </div>
                
                <div class="metric-card">
                    <h4>💵 Total de Amortização</h4>
                    <div class="metric-value" id="totalAmort">R$ """ + f"{metrics['total_amortizacao']:,.2f}" + """</div>
                    <div class="metric-subtitle">Principal devolvido</div>
                </div>
                
                <div class="metric-card">
                    <h4>💳 Total Pago (PMT)</h4>
                    <div class="metric-value" id="totalPmt">R$ """ + f"{metrics['total_pmt']:,.2f}" + """</div>
                    <div class="metric-subtitle">Juros + Amortização</div>
                </div>
                
                <div class="metric-card">
                    <h4>📅 Número de Pagamentos</h4>
                    <div class="metric-value">""" + f"{metrics['num_payments']}" + """</div>
                    <div class="metric-subtitle">Total de eventos</div>
                </div>
                
                <div class="metric-card">
                    <h4>💸 PMT Médio</h4>
                    <div class="metric-value">R$ """ + f"{metrics['avg_pmt']:,.2f}" + """</div>
                    <div class="metric-subtitle">Média dos pagamentos</div>
                </div>
                
                <div class="metric-card">
                    <h4>⏱️ Prazo Médio</h4>
                    <div class="metric-value">""" + f"{metrics['avg_maturity_years']:.2f}" + """ anos</div>
                    <div class="metric-subtitle">""" + f"{metrics['avg_maturity_months']:.1f}" + """ meses ponderados</div>
                </div>
                
                <div class="metric-card">
                    <h4>📐 Duration (Macaulay)</h4>
                    <div class="metric-value">""" + f"{metrics['duration_years']:.2f}" + """ anos</div>
                    <div class="metric-subtitle">""" + f"{metrics['duration_months']:.1f}" + """ meses | Sensibilidade ao tempo</div>
                </div>
                
                <div class="metric-card">
                    <h4>📉 Modified Duration</h4>
                    <div class="metric-value">""" + f"{metrics['modified_duration']:.2f}" + """</div>
                    <div class="metric-subtitle">Sensibilidade à taxa de juros</div>
                </div>
                
                <div class="metric-card">
                    <h4>📈 TIR (Taxa Interna de Retorno)</h4>
                    <div class="metric-value">""" + f"{metrics['irr']:.2f}%" + """</div>
                    <div class="metric-subtitle">Retorno anual equivalente</div>
                </div>
                
                <div class="metric-card">
                    <h4>⏳ Payback Simples</h4>
                    <div class="metric-value">""" + (f"{metrics['payback_simple_years']:.2f} anos" if metrics['payback_simple_years'] else "N/A") + """</div>
                    <div class="metric-subtitle">""" + (f"{metrics['payback_simple_months']:.1f} meses" if metrics['payback_simple_months'] else "Não recuperável") + """</div>
                </div>
                
                <div class="metric-card">
                    <h4>💹 Payback Descontado</h4>
                    <div class="metric-value">""" + (f"{metrics['payback_discounted_years']:.2f} anos" if metrics['payback_discounted_years'] else "N/A") + """</div>
                    <div class="metric-subtitle">""" + (f"{metrics['payback_discounted_months']:.1f} meses (VP)" if metrics['payback_discounted_months'] else "Não recuperável") + """</div>
                </div>
            </div>
        </div>
        
        <div class="summary">
            <h3>📊 Visualização do Fluxo de Caixa</h3>
            <canvas id="cashFlowChart" style="max-height: 400px;"></canvas>
        </div>
        
        <p style="margin-top: 30px; text-align: center; color: #7f8c8d; font-size: 0.9em;">
            Calculado conforme padrões B3/ANBIMA - Base 252 dias úteis<br>
            Células em amarelo são editáveis (clique para editar)<br>""" + (
            f"<strong>Curva de Juros:</strong> Curva PRE ANBIMA (taxas interpoladas por vencimento)<br>" if self.di_curve is not None else ""
        ) + """<br>
            <strong>📚 Glossário:</strong><br>
            <strong>TIR:</strong> Taxa que iguala o valor presente dos fluxos futuros ao investimento inicial<br>
            <strong>Payback Simples:</strong> Tempo para recuperar o investimento (sem considerar valor do dinheiro no tempo)<br>
            <strong>Payback Descontado:</strong> Tempo para recuperar o investimento considerando o valor presente dos fluxos<br>
            <strong>Duration:</strong> Prazo médio ponderado dos fluxos de caixa<br>
            <strong>Modified Duration:</strong> Sensibilidade do preço à variação de 1% na taxa de juros
        </p>
    </div>
    
    <script>
        // Torna células editáveis
        document.querySelectorAll('.editable').forEach(cell => {
            cell.addEventListener('click', function() {
                const currentValue = this.textContent.replace('R$ ', '').replace(/\\./g, '').replace(',', '.');
                const input = document.createElement('input');
                input.type = 'text';
                input.value = currentValue;
                input.style.width = '100%';
                input.style.textAlign = 'right';
                
                this.textContent = '';
                this.appendChild(input);
                input.focus();
                
                input.addEventListener('blur', function() {
                    const newValue = parseFloat(this.value);
                    if (!isNaN(newValue)) {
                        cell.textContent = 'R$ ' + newValue.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        updateTotals();
                    } else {
                        cell.textContent = 'R$ ' + currentValue;
                    }
                });
                
                input.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        this.blur();
                    }
                });
            });
        });
        
        function updateTotals() {
            const rows = document.querySelectorAll('#cashFlowTable tbody tr:not(.total-row)');
            let totalJuros = 0;
            let totalAmort = 0;
            let totalPmt = 0;
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                const juros = parseFloat(cells[5].textContent.replace('R$ ', '').replace(/\\./g, '').replace(',', '.'));
                const amort = parseFloat(cells[6].textContent.replace('R$ ', '').replace(/\\./g, '').replace(',', '.'));
                const pmt = juros + amort;
                
                totalJuros += juros;
                totalAmort += amort;
                totalPmt += pmt;
                
                cells[7].innerHTML = '<strong>R$ ' + pmt.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '</strong>';
            });
            
            const numPayments = rows.length;
            const avgPmt = totalPmt / numPayments;
            
            // Atualiza linha de totais
            const totalRow = document.querySelector('.total-row');
            totalRow.cells[1].textContent = 'R$ ' + totalJuros.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            totalRow.cells[2].textContent = 'R$ ' + totalAmort.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            totalRow.cells[3].innerHTML = '<strong>R$ ' + totalPmt.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '</strong>';
            
            // Atualiza cards de resumo
            document.getElementById('totalJuros').textContent = 'R$ ' + totalJuros.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            document.getElementById('totalAmort').textContent = 'R$ ' + totalAmort.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            document.getElementById('totalPmt').textContent = 'R$ ' + totalPmt.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            
            // Atualiza PMT médio
            const avgPmtElements = document.querySelectorAll('.metric-value');
            avgPmtElements[4].textContent = 'R$ ' + avgPmt.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        
        // Cria gráfico do fluxo de caixa
        const ctx = document.getElementById('cashFlowChart').getContext('2d');
        const chartData = {
            labels: [""" + ", ".join([f"'{row['data'].strftime('%d/%m/%Y')}'" for row in cash_flow]) + """],
            datasets: [
                {
                    label: 'Juros (R$)',
                    data: [""" + ", ".join([f"{row['juros']:.2f}" for row in cash_flow]) + """],
                    backgroundColor: 'rgba(52, 152, 219, 0.6)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Amortização (R$)',
                    data: [""" + ", ".join([f"{row['amortizacao']:.2f}" for row in cash_flow]) + """],
                    backgroundColor: 'rgba(46, 204, 113, 0.6)',
                    borderColor: 'rgba(46, 204, 113, 1)',
                    borderWidth: 1
                },
                {
                    label: 'PMT Total (R$)',
                    data: [""" + ", ".join([f"{row['pmt']:.2f}" for row in cash_flow]) + """],
                    type: 'line',
                    backgroundColor: 'rgba(231, 76, 60, 0.2)',
                    borderColor: 'rgba(231, 76, 60, 1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        };
        
        const config = {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Fluxo de Pagamentos ao Longo do Tempo',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += 'R$ ' + context.parsed.y.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Data de Pagamento'
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45,
                            autoSkip: true,
                            maxTicksLimit: 20
                        }
                    },
                    y: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Valor (R$)'
                        },
                        ticks: {
                            callback: function(value) {
                                return 'R$ ' + value.toLocaleString('pt-BR', {minimumFractionDigits: 0, maximumFractionDigits: 0});
                            }
                        }
                    }
                }
            }
        };
        
        const cashFlowChart = new Chart(ctx, config);
    </script>
</body>
</html>
"""
        
        # Salva arquivo
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"\n[OK] Arquivo HTML gerado: {filename}")


def get_date_input(prompt: str) -> datetime:
    """Solicita entrada de data do usuário"""
    while True:
        try:
            date_str = input(prompt)
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            print("❌ Formato inválido! Use DD/MM/AAAA (ex: 15/01/2024)")


def get_float_input(prompt: str, min_value: float = None, max_value: float = None) -> float:
    """Solicita entrada numérica do usuário"""
    while True:
        try:
            value = float(input(prompt).replace(',', '.'))
            if min_value is not None and value < min_value:
                print(f"❌ Valor deve ser maior ou igual a {min_value}")
                continue
            if max_value is not None and value > max_value:
                print(f"❌ Valor deve ser menor ou igual a {max_value}")
                continue
            return value
        except ValueError:
            print("❌ Valor inválido! Digite um número.")


def get_int_input(prompt: str, min_value: int = None, max_value: int = None) -> int:
    """Solicita entrada inteira do usuário"""
    while True:
        try:
            value = int(input(prompt))
            if min_value is not None and value < min_value:
                print(f"❌ Valor deve ser maior ou igual a {min_value}")
                continue
            if max_value is not None and value > max_value:
                print(f"❌ Valor deve ser menor ou igual a {max_value}")
                continue
            return value
        except ValueError:
            print("❌ Valor inválido! Digite um número inteiro.")


def get_choice_input(prompt: str, options: list) -> str:
    """Solicita escolha do usuário de uma lista"""
    print(prompt)
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    
    while True:
        try:
            choice = int(input("\nEscolha (número): "))
            if 1 <= choice <= len(options):
                return options[choice - 1].lower().split()[0]
            else:
                print(f"❌ Escolha um número entre 1 e {len(options)}")
        except ValueError:
            print("❌ Digite um número válido!")


def main():
    """Função principal interativa"""
    
    print("=" * 70)
    print("  CALCULADORA DE DEBÊNTURES CDI+ - Padrão B3/ANBIMA")
    print("=" * 70)
    print("\n🔢 Vamos configurar sua debênture passo a passo!\n")
    
    # 1. Data de emissão
    print("📅 DATAS DA OPERAÇÃO")
    print("-" * 70)
    emission_date = get_date_input("Data de emissão (DD/MM/AAAA): ")
    maturity_date = get_date_input("Data de vencimento (DD/MM/AAAA): ")
    
    while maturity_date <= emission_date:
        print("❌ Data de vencimento deve ser posterior à emissão!")
        maturity_date = get_date_input("Data de vencimento (DD/MM/AAAA): ")
    
    # 2. Valor nominal
    print("\n💰 VALOR DA DEBÊNTURE")
    print("-" * 70)
    print("Padrão ANBIMA: R$ 1.000,00")
    use_default = input("Usar valor padrão? (S/n): ").strip().lower()
    
    if use_default == 'n':
        vne = get_float_input("Valor Nominal de Emissão (R$): ", min_value=0.01)
    else:
        vne = 1000.00
        print(f"✅ Usando VNE = R$ {vne:,.2f}")
    
    # 3. Taxas
    print("\n📊 REMUNERAÇÃO (CDI+)")
    print("-" * 70)

    # Pergunta se quer usar curva DI futura
    use_curve = input("Deseja usar a curva DI futura da B3? (S/n): ").strip().lower()

    cdi_rate = 0  # Default
    if use_curve == 's' or use_curve == '':
        print("🔄 Buscando curva DI futura da B3...")
        # A curva será carregada na calculadora depois
        print("✅ Curva DI será utilizada nos cálculos")
        cdi_rate = 0  # Será substituído pela curva
    else:
        cdi_rate = get_float_input("Taxa CDI projetada (% a.a., ex: 10.65): ", min_value=0)

    spread = get_float_input("Spread sobre CDI (% a.a., ex: 2.50): ", min_value=0)

    if use_curve == 's' or use_curve == '':
        print(f"\n✅ Taxa total: Curva DI + {spread:.2f}% a.a.")
    else:
        print(f"\n✅ Taxa total: CDI + {spread:.2f}% a.a.")
        print(f"   Projeção: {cdi_rate:.2f}% + {spread:.2f}% = {cdi_rate + spread:.2f}% a.a.")
    
    # 4. Frequência de juros
    print("\n💵 PAGAMENTO DE JUROS")
    print("-" * 70)
    interest_freq = get_choice_input(
        "Escolha a periodicidade:",
        ["Mensal", "Trimestral", "Semestral", "Anual", "Bullet (no vencimento)"]
    )
    
    # 5. Tipo de amortização
    print("\n📉 AMORTIZAÇÃO DO PRINCIPAL")
    print("-" * 70)
    amort_type = get_choice_input(
        "Escolha o sistema de amortização:",
        ["Bullet (tudo no vencimento)", "SAC (parcelas constantes)", 
         "Price (PMT constante)", "Custom (personalizado)"]
    )
    
    custom_percentages = None
    if amort_type == 'bullet':
        amort_type_display = 'Bullet'
    elif amort_type == 'sac':
        amort_type_display = 'SAC'
    elif amort_type == 'price':
        amort_type_display = 'Price'
    else:
        amort_type_display = 'Customizado'
        print("\n⚠️  Modo customizado - você precisará definir os percentuais manualmente")
        print("    (por enquanto vamos usar SAC como padrão)")
        amort_type = 'sac'
    
    # 6. Carência
    print("\n⏳ CARÊNCIA DO PRINCIPAL")
    print("-" * 70)
    has_grace = input("Há período de carência do principal? (S/n): ").strip().lower()
    
    if has_grace == 's' or has_grace == '':
        grace_months = get_int_input("Carência em meses: ", min_value=0)
    else:
        grace_months = 0
    
    # 7. Nome do arquivo
    print("\n💾 EXPORTAÇÃO")
    print("-" * 70)
    default_filename = "fluxo_debenture_cdi.html"
    custom_name = input(f"Nome do arquivo HTML (Enter para '{default_filename}'): ").strip()
    filename = custom_name if custom_name else default_filename
    
    if not filename.endswith('.html'):
        filename += '.html'
    
    # Resumo
    print("\n" + "=" * 70)
    print("📋 RESUMO DA CONFIGURAÇÃO")
    print("=" * 70)
    print(f"Data de Emissão:      {emission_date.strftime('%d/%m/%Y')}")
    print(f"Data de Vencimento:   {maturity_date.strftime('%d/%m/%Y')}")
    print(f"Valor Nominal:        R$ {vne:,.2f}")
    if use_curve == 's' or use_curve == '':
        print(f"CDI:                  Curva PRE ANBIMA (variável por vencimento)")
    else:
        print(f"CDI Projetado:        {cdi_rate:.2f}% a.a. (fixo)")
    print(f"Spread:               +{spread:.2f}% a.a.")
    if use_curve == 's' or use_curve == '':
        print(f"Taxa Total:           Curva PRE + {spread:.2f}% a.a.")
    else:
        print(f"Taxa Total:           CDI + {spread:.2f}% a.a. = {cdi_rate + spread:.2f}% a.a.")
    print(f"Periodicidade Juros:  {interest_freq.capitalize()}")
    print(f"Sistema Amortização:  {amort_type_display}")
    print(f"Carência Principal:   {grace_months} meses")
    print(f"Arquivo de saída:     {filename}")
    print("=" * 70)
    
    confirm = input("\nConfirmar e calcular? (S/n): ").strip().lower()
    
    if confirm == 'n':
        print("\n❌ Operação cancelada.")
        return
    
    # Cria calculadora e gera fluxo
    print("\n🔄 Calculando fluxo de caixa...")
    calc = DebentureCalculator()

    # Carrega curva DI se solicitado
    if use_curve == 's' or use_curve == '':
        calc.load_di_curve(emission_date)

    try:
        cash_flow = calc.generate_cash_flow(
            emission_date=emission_date,
            maturity_date=maturity_date,
            vne=vne,
            cdi_rate_annual=cdi_rate,
            spread_annual=spread,
            interest_frequency=interest_freq,
            amort_type=amort_type,
            grace_period_months=grace_months,
            custom_amort_percentages=custom_percentages
        )
        
        # Exibe resumo no console
        print("\n" + "=" * 70)
        print("📋 FLUXO DE PAGAMENTO GERADO")
        print("=" * 70)
        print(f"\n{'Ev':<4} {'Data':<12} {'DU':<5} {'DC':<5} {'Saldo Dev.':<16} {'Juros':<16} {'Amort.':<16} {'PMT':<16}")
        print("-" * 110)
        
        total_juros = 0
        total_amort = 0
        total_pmt = 0
        
        for row in cash_flow[:10]:  # Mostra primeiros 10 eventos
            total_juros += row['juros']
            total_amort += row['amortizacao']
            total_pmt += row['pmt']
            
            print(f"{row['evento']:<4} "
                  f"{row['data'].strftime('%d/%m/%Y'):<12} "
                  f"{row['dias_uteis']:<5} "
                  f"{row['dias_corridos']:<5} "
                  f"R$ {row['saldo_devedor']:>12,.2f}  "
                  f"R$ {row['juros']:>12,.2f}  "
                  f"R$ {row['amortizacao']:>12,.2f}  "
                  f"R$ {row['pmt']:>12,.2f}")
        
        if len(cash_flow) > 10:
            print(f"... (mais {len(cash_flow) - 10} eventos)")
        
        # Calcula totais finais
        total_juros = sum(row['juros'] for row in cash_flow)
        total_amort = sum(row['amortizacao'] for row in cash_flow)
        total_pmt = sum(row['pmt'] for row in cash_flow)
        
        print("-" * 110)
        print(f"{'TOTAIS':<26} "
              f"{'':16} "
              f"R$ {total_juros:>12,.2f}  "
              f"R$ {total_amort:>12,.2f}  "
              f"R$ {total_pmt:>12,.2f}")
        
        # Exporta para HTML
        calc.export_to_html(cash_flow, emission_date, vne, cdi_rate, spread, filename,
                           maturity_date=maturity_date, interest_frequency=interest_freq,
                           amort_type=amort_type, grace_period_months=grace_months)
        
        print("\n" + "=" * 70)
        print("✅ CÁLCULO CONCLUÍDO COM SUCESSO!")
        print("=" * 70)
        
        # Calcula métricas para exibir
        metrics = calc.calculate_metrics(cash_flow, emission_date, vne, cdi_rate, spread)
        
        print(f"\n📊 MÉTRICAS FINANCEIRAS:")
        print(f"   💰 Total Pago (PMT):         R$ {metrics['total_pmt']:,.2f}")
        print(f"   📈 TIR:                      {metrics['irr']:.2f}% a.a.")
        if metrics['payback_simple_years']:
            print(f"   ⏳ Payback Simples:          {metrics['payback_simple_years']:.2f} anos ({metrics['payback_simple_months']:.1f} meses)")
        else:
            print(f"   ⏳ Payback Simples:          Não recuperável no período")
        if metrics['payback_discounted_years']:
            print(f"   💹 Payback Descontado:       {metrics['payback_discounted_years']:.2f} anos ({metrics['payback_discounted_months']:.1f} meses)")
        else:
            print(f"   💹 Payback Descontado:       Não recuperável no período")
        print(f"   📐 Duration:                 {metrics['duration_years']:.2f} anos ({metrics['duration_months']:.1f} meses)")
        print(f"   📉 Modified Duration:        {metrics['modified_duration']:.2f}")
        
        print(f"\n📄 Arquivo HTML gerado: {filename}")
        print(f"📊 Total de eventos: {len(cash_flow)}")
        print("\n💡 Abra o arquivo HTML em seu navegador para visualizar:")
        print("   • Tabela completa editável")
        print("   • Dashboard com todas as métricas")
        print("   • Gráfico interativo do fluxo de caixa")
        
    except Exception as e:
        print(f"\n❌ Erro ao calcular: {str(e)}")


if __name__ == "__main__":
    main()