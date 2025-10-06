// Calculadora de Debêntures - Frontend JavaScript

// Controla visibilidade do campo CDI Rate
document.getElementById('use_curve').addEventListener('change', function() {
    const cdiRateRow = document.getElementById('cdi-rate-row');
    const cdiRateInput = document.getElementById('cdi_rate');

    if (this.checked) {
        cdiRateRow.style.display = 'none';
        cdiRateInput.required = false;
    } else {
        cdiRateRow.style.display = 'block';
        cdiRateInput.required = true;
    }
});

// Submissão do formulário
document.getElementById('debenture-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    // Coleta dados do formulário
    const formData = {
        emission_date: document.getElementById('emission_date').value,
        maturity_date: document.getElementById('maturity_date').value,
        vne: parseFloat(document.getElementById('vne').value),
        use_curve: document.getElementById('use_curve').checked,
        cdi_rate: parseFloat(document.getElementById('cdi_rate').value) || 0,
        spread: parseFloat(document.getElementById('spread').value),
        interest_frequency: document.getElementById('interest_frequency').value,
        amort_type: document.getElementById('amort_type').value,
        grace_period_months: parseInt(document.getElementById('grace_period_months').value) || 0
    };

    // Mostra loading
    document.getElementById('loading').style.display = 'block';
    document.getElementById('error-message').style.display = 'none';
    document.getElementById('results').style.display = 'none';
    document.getElementById('calc-btn').disabled = true;

    try {
        // Envia requisição
        const response = await fetch('/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.success) {
            // Exibe resultados
            displayResults(data);
        } else {
            // Exibe erro
            showError(data.error || 'Erro ao calcular');
        }

    } catch (error) {
        showError('Erro ao conectar com o servidor: ' + error.message);
    } finally {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('calc-btn').disabled = false;
    }
});

// Exibe erro
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

// Exibe resultados
function displayResults(data) {
    // Resumo dos inputs
    displayInputSummary(data.inputs, data.curve_info);

    // Métricas
    displayMetrics(data.metrics);

    // Fluxo de caixa
    displayCashFlow(data.cash_flow);

    // Gráfico
    displayChart(data.cash_flow);

    // Mostra seção de resultados
    document.getElementById('results').style.display = 'block';
    document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}

// Exibe resumo dos inputs
function displayInputSummary(inputs, curveInfo) {
    const summaryDiv = document.getElementById('input-summary');

    const cdiDisplay = inputs.use_curve ?
        'Curva PRE ANBIMA' + (curveInfo ? ` (${curveInfo.vertices_count} vértices)` : '') :
        inputs.cdi_rate.toFixed(2) + '% a.a.';

    const frequencyMap = {
        'mensal': 'Mensal',
        'trimestral': 'Trimestral',
        'semestral': 'Semestral',
        'anual': 'Anual',
        'bullet': 'Bullet'
    };

    const amortMap = {
        'bullet': 'Bullet',
        'sac': 'SAC',
        'price': 'PRICE'
    };

    summaryDiv.innerHTML = `
        <div class="input-item">
            <strong>Data de Emissão</strong>
            <span>${inputs.emission_date}</span>
        </div>
        <div class="input-item">
            <strong>Data de Vencimento</strong>
            <span>${inputs.maturity_date}</span>
        </div>
        <div class="input-item">
            <strong>Valor Nominal</strong>
            <span>R$ ${inputs.vne.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</span>
        </div>
        <div class="input-item">
            <strong>CDI</strong>
            <span>${cdiDisplay}</span>
        </div>
        <div class="input-item">
            <strong>Spread</strong>
            <span>+${inputs.spread.toFixed(2)}% a.a.</span>
        </div>
        <div class="input-item">
            <strong>Periodicidade</strong>
            <span>${frequencyMap[inputs.interest_frequency]}</span>
        </div>
        <div class="input-item">
            <strong>Amortização</strong>
            <span>${amortMap[inputs.amort_type]}</span>
        </div>
        <div class="input-item">
            <strong>Carência</strong>
            <span>${inputs.grace_period_months} meses</span>
        </div>
    `;
}

// Exibe métricas
function displayMetrics(metrics) {
    const metricsDiv = document.getElementById('metrics-grid');

    metricsDiv.innerHTML = `
        <div class="metric-card">
            <h4>Total de Juros</h4>
            <div class="metric-value">R$ ${metrics.total_juros.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div>
            <div class="metric-subtitle">Remuneração CDI + Spread</div>
        </div>
        <div class="metric-card">
            <h4>Total de Amortização</h4>
            <div class="metric-value">R$ ${metrics.total_amortizacao.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div>
            <div class="metric-subtitle">Principal devolvido</div>
        </div>
        <div class="metric-card">
            <h4>Total Pago (PMT)</h4>
            <div class="metric-value">R$ ${metrics.total_pmt.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div>
            <div class="metric-subtitle">Juros + Amortização</div>
        </div>
        <div class="metric-card">
            <h4>TIR</h4>
            <div class="metric-value">${metrics.irr.toFixed(2)}%</div>
            <div class="metric-subtitle">Taxa Interna de Retorno</div>
        </div>
        <div class="metric-card">
            <h4>Duration (Macaulay)</h4>
            <div class="metric-value">${metrics.duration_years.toFixed(2)} anos</div>
            <div class="metric-subtitle">${metrics.duration_months.toFixed(1)} meses</div>
        </div>
        <div class="metric-card">
            <h4>Modified Duration</h4>
            <div class="metric-value">${metrics.modified_duration.toFixed(2)}</div>
            <div class="metric-subtitle">Sensibilidade à taxa</div>
        </div>
        <div class="metric-card">
            <h4>Payback Simples</h4>
            <div class="metric-value">${metrics.payback_simple_years ? metrics.payback_simple_years.toFixed(2) + ' anos' : 'N/A'}</div>
            <div class="metric-subtitle">${metrics.payback_simple_months ? metrics.payback_simple_months.toFixed(1) + ' meses' : 'Não recuperável'}</div>
        </div>
        <div class="metric-card">
            <h4>Número de Pagamentos</h4>
            <div class="metric-value">${metrics.num_payments}</div>
            <div class="metric-subtitle">Total de eventos</div>
        </div>
    `;
}

// Exibe fluxo de caixa
function displayCashFlow(cashFlow) {
    const tbody = document.getElementById('cash-flow-body');
    const tfoot = document.getElementById('cash-flow-footer');

    let totalJuros = 0;
    let totalAmort = 0;
    let totalPmt = 0;

    // Linhas
    let html = '';
    cashFlow.forEach(row => {
        totalJuros += row.juros;
        totalAmort += row.amortizacao;
        totalPmt += row.pmt;

        const dataFormatada = new Date(row.data + 'T00:00:00').toLocaleDateString('pt-BR');

        html += `
            <tr>
                <td>${row.evento}</td>
                <td>${dataFormatada}</td>
                <td>${row.dias_uteis}</td>
                <td>${row.dias_corridos}</td>
                <td>R$ ${row.saldo_devedor.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                <td>R$ ${row.juros.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                <td>R$ ${row.amortizacao.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                <td><strong>R$ ${row.pmt.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</strong></td>
            </tr>
        `;
    });

    tbody.innerHTML = html;

    // Total
    tfoot.innerHTML = `
        <tr>
            <td colspan="5">TOTAIS</td>
            <td>R$ ${totalJuros.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
            <td>R$ ${totalAmort.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
            <td><strong>R$ ${totalPmt.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</strong></td>
        </tr>
    `;
}

// Exibe gráfico
let chartInstance = null;
function displayChart(cashFlow) {
    const ctx = document.getElementById('cash-flow-chart').getContext('2d');

    // Destroi gráfico anterior se existir
    if (chartInstance) {
        chartInstance.destroy();
    }

    const labels = cashFlow.map(row => new Date(row.data + 'T00:00:00').toLocaleDateString('pt-BR'));
    const jurosData = cashFlow.map(row => row.juros);
    const amortData = cashFlow.map(row => row.amortizacao);
    const pmtData = cashFlow.map(row => row.pmt);

    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Juros (R$)',
                    data: jurosData,
                    backgroundColor: 'rgba(66, 77, 165, 0.7)',
                    borderColor: 'rgba(66, 77, 165, 1)',
                    borderWidth: 2
                },
                {
                    label: 'Amortização (R$)',
                    data: amortData,
                    backgroundColor: 'rgba(66, 77, 165, 0.4)',
                    borderColor: 'rgba(66, 77, 165, 0.8)',
                    borderWidth: 2
                },
                {
                    label: 'PMT Total (R$)',
                    data: pmtData,
                    type: 'line',
                    backgroundColor: 'rgba(231, 76, 60, 0.2)',
                    borderColor: 'rgba(231, 76, 60, 1)',
                    borderWidth: 3,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Fluxo de Pagamentos ao Longo do Tempo',
                    font: {
                        size: 18,
                        weight: 'bold'
                    }
                },
                legend: {
                    display: true,
                    position: 'top'
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
                            label += 'R$ ' + context.parsed.y.toLocaleString('pt-BR', {minimumFractionDigits: 2});
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
                        minRotation: 45
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
                            return 'R$ ' + value.toLocaleString('pt-BR', {minimumFractionDigits: 0});
                        }
                    }
                }
            }
        }
    });
}

// Define datas padrão
window.addEventListener('load', function() {
    const today = new Date();
    const nextYear = new Date(today);
    nextYear.setFullYear(today.getFullYear() + 1);

    document.getElementById('emission_date').valueAsDate = today;
    document.getElementById('maturity_date').valueAsDate = nextYear;
});
