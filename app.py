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
        vne = float(data.get('vne', 1000.00))
        spread = float(data['spread'])
        interest_freq = data['interest_frequency']
        amort_type = data['amort_type']
        grace_months = int(data.get('grace_period_months', 0))
        use_curve = data.get('use_curve', False)
        cdi_rate = float(data.get('cdi_rate', 0))

        # Valida datas
        if maturity_date <= emission_date:
            return jsonify({'error': 'Data de vencimento deve ser posterior à emissão'}), 400

        # Cria calculadora
        calc = DebentureCalculator()

        # Carrega curva DI se solicitado
        curve_loaded = False
        curve_info = None
        if use_curve:
            curve_loaded = calc.load_di_curve(emission_date)
            if curve_loaded and calc.di_curve is not None:
                curve_info = {
                    'loaded': True,
                    'vertices_count': len(calc.di_curve),
                    'min_days': int(calc.di_curve['dias_uteis'].min()),
                    'max_days': int(calc.di_curve['dias_uteis'].max())
                }

        # Gera fluxo de caixa
        cash_flow = calc.generate_cash_flow(
            emission_date=emission_date,
            maturity_date=maturity_date,
            vne=vne,
            cdi_rate_annual=cdi_rate,
            spread_annual=spread,
            interest_frequency=interest_freq,
            amort_type=amort_type,
            grace_period_months=grace_months,
            custom_amort_percentages=None
        )

        # Calcula métricas
        metrics = calc.calculate_metrics(cash_flow, emission_date, vne, cdi_rate, spread)

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
                'vne': vne,
                'cdi_rate': cdi_rate if not use_curve else 'Curva ANBIMA',
                'spread': spread,
                'interest_frequency': interest_freq,
                'amort_type': amort_type,
                'grace_period_months': grace_months,
                'use_curve': use_curve
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
