"""
Aplicação Web Flask - Calculadora de Debêntures CDI+
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
from debenture_calculator import DebentureCalculator
import traceback

app = Flask(__name__)
CORS(app)

def parse_ipca_indices(raw_text: str):
    """
    Converte texto em formato YYYY-MM=indice em dicionário {YYYY-MM: float}.
    Retorna tupla (dict, texto_normalizado).
    """
    if not raw_text:
        return {}, ''

    indices = {}
    normalized_lines = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        sanitized = line.replace(';', '=').replace(':', '=').replace('	', '=').replace(',', '.')
        if '=' not in sanitized:
            continue
        key_part, value_part = sanitized.split('=', 1)
        key = key_part.strip().replace('/', '-').replace(' ', '')
        value_str = value_part.strip()

        if len(key) == 6 and key.isdigit():
            key = f"{key[:4]}-{key[4:]}"
        elif len(key) == 7 and key[4] == '-':
            key = f"{key[:4]}-{key[5:].zfill(2)}"
        else:
            parts = key.split('-')
            if len(parts) == 2 and len(parts[0]) == 4 and parts[1].isdigit():
                key = f"{parts[0]}-{parts[1].zfill(2)}"

        try:
            value = float(value_str)
        except ValueError:
            continue

        indices[key] = value
        normalized_lines.append(f"{key}={value:.6f}")

    normalized_text = '\n'.join(normalized_lines)
    return indices, normalized_text

@app.route('/')
def index():
    """Página principal com formulário"""
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    """Endpoint para calcular fluxo de caixa"""
    try:
        # Recebe dados do formulário
        data = request.json

        # Parse das datas
        emission_date = datetime.strptime(data['emission_date'], '%Y-%m-%d')
        maturity_date = datetime.strptime(data['maturity_date'], '%Y-%m-%d')

        # Parse dos valores
        vne_unitario = float(data.get('vne', 1000.00) or 1000.00)
        quantity = int(data.get('quantity', 1) or 1)
        if quantity < 1:
            quantity = 1
        vne_total = vne_unitario * quantity
        spread = float(data['spread'])
        interest_freq = data['interest_frequency']
        amort_type = data['amort_type']
        grace_months = int(data.get('grace_period_months', 0))
        use_curve = data.get('use_curve', False)
        cdi_rate = float(data.get('cdi_rate', 0))

        # Novos parâmetros para IPCA+
        indexador = data.get('indexador', 'CDI')
        anniversary_day_ipca = int(data.get('anniversary_day_ipca', 15))
        ipca_projected_annual = float(data.get('ipca_projected_annual', 4.5))

        ipca_indices_raw = data.get('ipca_indices', '')
        ipca_indices, ipca_indices_text = parse_ipca_indices(ipca_indices_raw)

        # Valida datas
        if maturity_date <= emission_date:
            return jsonify({'error': 'Data de vencimento deve ser posterior à emissão'}), 400

        # Cria calculadora
        calc = DebentureCalculator()

        # Carrega curva conforme indexador
        curve_loaded = False
        curve_info = None

        if indexador == 'CDI' and use_curve:
            curve_loaded = calc.load_di_curve(emission_date)
            if curve_loaded and calc.di_curve is not None:
                curve_info = {
                    'loaded': True,
                    'type': 'PRE',
                    'vertices_count': len(calc.di_curve),
                    'min_days': int(calc.di_curve['dias_uteis'].min()),
                    'max_days': int(calc.di_curve['dias_uteis'].max())
                }

        elif indexador == 'IPCA' and use_curve:
            # Para IPCA implícito, precisa carregar AMBAS as curvas (PRE e NTN-B)
            di_loaded = calc.load_di_curve(emission_date)
            ipca_loaded = calc.load_ipca_curve(emission_date)

            if di_loaded and ipca_loaded and calc.di_curve is not None and calc.ipca_curve is not None:
                curve_info = {
                    'loaded': True,
                    'type': 'NTN-B + PRE (IPCA implícito)',
                    'vertices_count': len(calc.ipca_curve),
                    'min_days': int(calc.ipca_curve['dias_uteis'].min()),
                    'max_days': int(calc.ipca_curve['dias_uteis'].max())
                }
                curve_loaded = True
            elif ipca_loaded and calc.ipca_curve is not None:
                # Fallback: só NTN-B carregada (usa IPCA projetado manual)
                curve_info = {
                    'loaded': True,
                    'type': 'NTN-B (taxa real)',
                    'vertices_count': len(calc.ipca_curve),
                    'min_days': int(calc.ipca_curve['dias_uteis'].min()),
                    'max_days': int(calc.ipca_curve['dias_uteis'].max())
                }
                curve_loaded = True
                # Carrega projeções IPCA manual como fallback
                calc.load_ipca_projections(ipca_projected_annual)
            else:
                # Nenhuma curva carregada, usa IPCA projetado manual
                calc.load_ipca_projections(ipca_projected_annual)

        # Gera fluxo de caixa
        cash_flow = calc.generate_cash_flow(
            emission_date=emission_date,
            maturity_date=maturity_date,
            vne=vne_total,
            cdi_rate_annual=cdi_rate,
            spread_annual=spread,
            interest_frequency=interest_freq,
            amort_type=amort_type,
            grace_period_months=grace_months,
            custom_amort_percentages=None,
            indexador=indexador,
            anniversary_day_ipca=anniversary_day_ipca,
            ipca_projected_annual=ipca_projected_annual,
            ipca_custom_indices=ipca_indices if indexador == 'IPCA' else None
        )

        # Calcula métricas
        metrics = calc.calculate_metrics(cash_flow, emission_date, vne_total, cdi_rate, spread)

        # Converte para JSON
        cash_flow_json = calc.cash_flow_to_json(cash_flow)

        # Prepara resposta
        response = {
            'success': True,
            'cash_flow': cash_flow_json,
            'metrics': metrics,
            'inputs': {
                'emission_date': emission_date.strftime('%d/%m/%Y'),
                'maturity_date': maturity_date.strftime('%d/%m/%Y'),
                'vne': vne_total,
                'vne_unitario': vne_unitario,
                'quantity': quantity,
                'vne_total': vne_total,
                'cdi_rate': cdi_rate if not use_curve else 'Curva ANBIMA',
                'spread': spread,
                'interest_frequency': interest_freq,
                'amort_type': amort_type,
                'grace_period_months': grace_months,
                'use_curve': use_curve,
                'indexador': indexador,
                'anniversary_day_ipca': anniversary_day_ipca if indexador == 'IPCA' else None,
                'ipca_projected_annual': ipca_projected_annual if indexador == 'IPCA' else None,
                'ipca_indices_text': ipca_indices_text if indexador == 'IPCA' else None,
                'ipca_indices_count': len(ipca_indices) if indexador == 'IPCA' else 0
            },
            'curve_info': curve_info
        }

        return jsonify(response)

    except Exception as e:
        print(f"Erro no cálculo: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Erro ao calcular: {str(e)}'
        }), 500

@app.route('/get_di_curve', methods=['GET'])
def get_di_curve():
    """Endpoint para carregar curva DI"""
    try:
        # Data de referência (pode vir como parâmetro)
        date_str = request.args.get('date', None)
        if date_str:
            reference_date = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            reference_date = None

        # Carrega curva
        calc = DebentureCalculator()
        success = calc.load_di_curve(reference_date)

        if success and calc.di_curve is not None:
            # Converte para JSON
            curve_data = {
                'vertices': calc.di_curve['dias_uteis'].tolist(),
                'rates': calc.di_curve['taxa'].tolist()
            }
            return jsonify({
                'success': True,
                'curve': curve_data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Não foi possível carregar a curva DI'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao carregar curva: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("  Calculadora de Debêntures CDI+ - Servidor Web")
    print("=" * 60)
    print("\nServidor rodando em: http://127.0.0.1:5000")
    print("\nPressione Ctrl+C para parar o servidor\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
