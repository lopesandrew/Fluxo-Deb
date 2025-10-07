import unittest
from datetime import datetime

from debenture_calculator import DebentureCalculator


class IpcaResetTest(unittest.TestCase):
    def test_ipca_reset_each_payment(self):
        calc = DebentureCalculator()

        emission_date = datetime(2025, 1, 15)
        maturity_date = datetime(2025, 4, 15)
        vne = 1000.0
        spread_real = 4.0
        ipca_annual = 6.0

        cash_flow = calc.generate_cash_flow(
            emission_date=emission_date,
            maturity_date=maturity_date,
            vne=vne,
            cdi_rate_annual=0.0,
            spread_annual=spread_real,
            interest_frequency='mensal',
            amort_type='sac',
            grace_period_months=0,
            custom_amort_percentages=None,
            indexador='IPCA',
            anniversary_day_ipca=15,
            ipca_projected_annual=ipca_annual
        )

        ipca_monthly_expected = ((1 + ipca_annual / 100) ** (1 / 12) - 1) * 100
        tolerance = 0.05  # permite pequenas diferenças de pró-rata em dias úteis

        ipca_values = [row['ipca_acumulado'] for row in cash_flow]
        self.assertGreater(len(ipca_values), 1)

        for value in ipca_values:
            self.assertAlmostEqual(value, ipca_monthly_expected, delta=tolerance)

        amort_nominal = vne / len(cash_flow)
        saldo_nominal = vne

        for row in cash_flow:
            saldo_devedor_pre_pagamento = row['saldo_devedor']
            ratio_cash = row['amortizacao'] / saldo_devedor_pre_pagamento if saldo_devedor_pre_pagamento else 0.0
            ratio_nominal = amort_nominal / saldo_nominal if saldo_nominal else 0.0
            self.assertAlmostEqual(ratio_cash, ratio_nominal, places=6)
            saldo_nominal -= amort_nominal

    def test_quantity_scaling(self):
        calc = DebentureCalculator()

        params = dict(
            emission_date=datetime(2025, 1, 15),
            maturity_date=datetime(2025, 4, 15),
            cdi_rate_annual=0.0,
            spread_annual=4.0,
            interest_frequency='mensal',
            amort_type='sac',
            grace_period_months=0,
            custom_amort_percentages=None,
            indexador='IPCA',
            anniversary_day_ipca=15,
            ipca_projected_annual=6.0
        )

        base_flow = calc.generate_cash_flow(vne=1000.0, **params)
        multi_flow = calc.generate_cash_flow(vne=3000.0, **params)

        for base_row, multi_row in zip(base_flow, multi_flow):
            self.assertAlmostEqual(multi_row['saldo_devedor'], base_row['saldo_devedor'] * 3, places=6)
            self.assertAlmostEqual(multi_row['juros'], base_row['juros'] * 3, places=6)
            self.assertAlmostEqual(multi_row['amortizacao'], base_row['amortizacao'] * 3, places=6)
            self.assertAlmostEqual(multi_row['pmt'], base_row['pmt'] * 3, places=6)

    def test_ipca_custom_indices_vna(self):
        calc = DebentureCalculator()
        calc.ipca_custom_indices = {'2025-01': 100.0, '2025-02': 102.0}

        base_vna = 1000.0
        base_date = datetime(2025, 1, 15)
        current_date = datetime(2025, 2, 17)  # próximo dia útil após o aniversário

        vna, accumulated = calc.calculate_vna(
            base_vna,
            base_date,
            current_date,
            anniversary_day=15,
            ipca_monthly_rate=0.0
        )

        self.assertAlmostEqual(vna, 1020.0, places=6)
        self.assertAlmostEqual(accumulated, 2.0, places=6)

if __name__ == '__main__':
    unittest.main()



