// Calculadora de DebÃªntures - Frontend JavaScript

// Controla alternÃ¢ncia entre CDI e IPCA
document.getElementById('indexador').addEventListener('change', function() {
    const indexador = this.value;
    const cdiFields = document.getElementById('cdi-fields');
    const ipcaFields = document.getElementById('ipca-fields');

    if (indexador === 'CDI') {
        cdiFields.style.display = 'block';
        ipcaFields.style.display = 'none';
    } else if (indexador === 'IPCA') {
        cdiFields.style.display = 'none';
        ipcaFields.style.display = 'block';
    }
});

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

// Controla visibilidade do campo Taxa Real (IPCA)
document.getElementById('use_ipca_curve').addEventListener('change', function() {
    const realRateRow = document.getElementById('real-rate-row');
    const realRateInput = document.getElementById('real_rate');

    if (this.checked) {
        realRateRow.style.display = 'none';
        realRateInput.required = false;
    } else {
        realRateRow.style.display = 'block';
        realRateInput.required = true;
    }
});

// SubmissÃ£o do formulÃ¡rio
document.getElementById('debenture-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    // Coleta dados do formulÃ¡rio
    const indexador = document.getElementById('indexador').value;

    const formData = {
        emission_date: document.getElementById('emission_date').value,
        maturity_date: document.getElementById('maturity_date').value,
        vne: parseFloat(document.getElementById('vne').value),
        quantity: parseInt(document.getElementById('quantity').value, 10) || 1,
        interest_frequency: document.getElementById('interest_frequency').value,
        amort_type: document.getElementById('amort_type').value,
        grace_period_months: parseInt(document.getElementById('grace_period_months').value) || 0,
        indexador: indexador,
        ipca_indices: document.getElementById('ipca_indices') ? document.getElementById('ipca_indices').value : ''
    };

    // Dados especÃ­ficos para CDI
    if (indexador === 'CDI') {
        formData.use_curve = document.getElementById('use_curve').checked;
        formData.cdi_rate = parseFloat(document.getElementById('cdi_rate').value) || 0;
        formData.spread = parseFloat(document.getElementById('spread').value);
    }
    // Dados especÃ­ficos para IPCA
    else if (indexador === 'IPCA') {
        formData.use_curve = document.getElementById('use_ipca_curve').checked;
        formData.spread = parseFloat(document.getElementById('real_rate').value);  // Taxa real
        formData.cdi_rate = 0;  // NÃ£o usa CDI no IPCA+
        formData.ipca_projected_annual = parseFloat(document.getElementById('ipca_projected_annual').value) || 4.5;
        formData.anniversary_day_ipca = parseInt(document.getElementById('anniversary_day_ipca').value) || 15;
    }

    // Mostra loading
    document.getElementById('loading').style.display = 'block';
    document.getElementById('error-message').style.display = 'none';
    document.getElementById('results').style.display = 'none';
    document.getElementById('calc-btn').disabled = true;

    try {
        // Envia requisiÃ§Ã£o
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

    // MÃ©tricas
    displayMetrics(data.metrics);

    // Fluxo de caixa
    displayCashFlow(data.cash_flow);

    // GrÃ¡fico
    displayChart(data.cash_flow);

    // Mostra seÃ§Ã£o de resultados
    document.getElementById('results').style.display = 'block';
    document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}

// Exibe resumo dos inputs
function displayInputSummary(inputs, curveInfo) {
    const summaryDiv = document.getElementById('input-summary');

    const indexador = inputs.indexador || 'CDI';
    const quantityRaw = typeof inputs.quantity === 'number' ? inputs.quantity : parseInt(inputs.quantity || 1, 10);
    const quantity = Number.isFinite(quantityRaw) && quantityRaw > 0 ? quantityRaw : 1;

    const totalNominalRaw = inputs.vne_total ?? inputs.vne ?? (inputs.vne_unitario ? inputs.vne_unitario * quantity : 0);
    const totalNominal = Number(totalNominalRaw) || 0;
    const unitNominalSource = inputs.vne_unitario ?? (quantity ? totalNominal / quantity : totalNominal);
    const unitNominal = Number(unitNominalSource) || 0;

    const indexadorDisplay = indexador === 'IPCA' ? 'IPCA (Inflacao)' : 'CDI (DI+)';

    const cdiRateNumber = Number(inputs.cdi_rate);
    const cdiDisplay = inputs.use_curve ?
        'Curva PRE ANBIMA' + (curveInfo && curveInfo.vertices_count ? ` (${curveInfo.vertices_count} pontos)` : '') :
        (Number.isFinite(cdiRateNumber) ? `${cdiRateNumber.toFixed(2)}% a.a.` : (inputs.cdi_rate || '-'));

    let baseLabel = indexador === 'IPCA' ? 'Atualizacao IPCA' : 'CDI';
    let baseDisplay;
    if (indexador === 'IPCA') {
        if (inputs.use_curve && curveInfo && curveInfo.type) {
            baseDisplay = curveInfo.vertices_count ? `${curveInfo.type} (${curveInfo.vertices_count} pontos)` : curveInfo.type;
        } else if (typeof inputs.ipca_projected_annual === 'number' && !Number.isNaN(inputs.ipca_projected_annual)) {
            baseDisplay = `${inputs.ipca_projected_annual.toFixed(2)}% a.a.`;
        } else if (inputs.ipca_projected_annual) {
            baseDisplay = `${inputs.ipca_projected_annual}% a.a.`;
        } else {
            baseDisplay = 'IPCA projetado';
        }
    } else {
        baseDisplay = cdiDisplay;
    }

    const indicesSource = indexador === 'IPCA'
        ? (inputs.ipca_indices_count && inputs.ipca_indices_count > 0
            ? `${inputs.ipca_indices_count} índices NI`
            : (inputs.use_curve ? 'Curva ANBIMA' : 'Projeção anual'))
        : '-';
    const indicesTooltipRaw = indexador === 'IPCA' && inputs.ipca_indices_text ? inputs.ipca_indices_text : '';
    const indicesTooltip = indicesTooltipRaw ? indicesTooltipRaw.replace(/\"/g, '').replace(/\r?\n/g, ' | ').trim() : '';
    const indicesAttr = indicesTooltip ? ` title=\"${indicesTooltip}\"` : '';

    const spreadLabel = indexador === 'IPCA' ? 'Taxa Real' : 'Spread';
    const spreadNumber = Number(inputs.spread);
    let spreadDisplay;
    if (Number.isFinite(spreadNumber)) {
        spreadDisplay = indexador === 'IPCA'
            ? `${spreadNumber.toFixed(2)}% a.a.`
            : `+${spreadNumber.toFixed(2)}% a.a.`;
    } else {
        spreadDisplay = inputs.spread || '-';
    }

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
            <strong>Data de Emissao</strong>
            <span>${inputs.emission_date}</span>
        </div>
        <div class="input-item">
            <strong>Data de Vencimento</strong>
            <span>${inputs.maturity_date}</span>
        </div>
        <div class="input-item">
            <strong>Valor Nominal Unitario</strong>
            <span>R$ ${unitNominal.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
        </div>
        <div class="input-item">
            <strong>Quantidade</strong>
            <span>${quantity.toLocaleString('pt-BR')}</span>
        </div>
        <div class="input-item">
            <strong>Valor Nominal Total</strong>
            <span>R$ ${totalNominal.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
        </div>
        <div class="input-item">
            <strong>Indexador</strong>
            <span>${indexadorDisplay}</span>
        </div>
        <div class="input-item">
            <strong>${baseLabel}</strong>
            <span>${baseDisplay}</span>
        </div>
        <div class="input-item">
            <strong>Índices NI</strong>
            <span${indicesAttr}>${indicesSource}</span>
        </div>
        <div class="input-item">
            <strong>${spreadLabel}</strong>
            <span>${spreadDisplay}</span>
        </div>
        <div class="input-item">
            <strong>Periodicidade</strong>
            <span>${frequencyMap[inputs.interest_frequency] || inputs.interest_frequency}</span>
        </div>
        <div class="input-item">
            <strong>Amortizacao</strong>
            <span>${amortMap[inputs.amort_type] || inputs.amort_type}</span>
        </div>
        <div class="input-item">
            <strong>Carencia</strong>
            <span>${inputs.grace_period_months} meses</span>
        </div>
    `;
}


// Exibe mÃ©tricas
function displayMetrics(metrics) {
    const metricsDiv = document.getElementById('metrics-grid');

    metricsDiv.innerHTML = `
        <div class="metric-card">
            <h4>Total de Juros</h4>
            <div class="metric-value">R$ ${metrics.total_juros.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div>
            <div class="metric-subtitle">RemuneraÃ§Ã£o CDI + Spread</div>
        </div>
        <div class="metric-card">
            <h4>Total de AmortizaÃ§Ã£o</h4>
            <div class="metric-value">R$ ${metrics.total_amortizacao.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div>
            <div class="metric-subtitle">Principal devolvido</div>
        </div>
        <div class="metric-card">
            <h4>Total Pago (PMT)</h4>
            <div class="metric-value">R$ ${metrics.total_pmt.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div>
            <div class="metric-subtitle">Juros + AmortizaÃ§Ã£o</div>
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
            <div class="metric-subtitle">Sensibilidade Ã  taxa</div>
        </div>
        <div class="metric-card">
            <h4>Payback Simples</h4>
            <div class="metric-value">${metrics.payback_simple_years ? metrics.payback_simple_years.toFixed(2) + ' anos' : 'N/A'}</div>
            <div class="metric-subtitle">${metrics.payback_simple_months ? metrics.payback_simple_months.toFixed(1) + ' meses' : 'NÃ£o recuperÃ¡vel'}</div>
        </div>
        <div class="metric-card">
            <h4>NÃºmero de Pagamentos</h4>
            <div class="metric-value">${metrics.num_payments}</div>
            <div class="metric-subtitle">Total de eventos</div>
        </div>
    `;
}

// Exibe fluxo de caixa
function displayCashFlow(cashFlow) {
    const tbody = document.getElementById('cash-flow-body');
    const tfoot = document.getElementById('cash-flow-footer');
    const thead = document.querySelector('#cash-flow-table thead tr');

    if (cashFlow.length === 0) return;

    // Detecta indexador
    const indexador = cashFlow[0].indexador || 'CDI';

    // Atualiza cabeÃ§alhos conforme indexador
    if (indexador === 'IPCA') {
        thead.innerHTML = `
            <th>Evento</th>
            <th>Data</th>
            <th>DU</th>
            <th>DC</th>
            <th>VNA Atualizado (R$)</th>
            <th>IPCA Acum (%)</th>
            <th>Taxa Real (%)</th>
            <th>VÃ©rtice (DU)</th>
            <th>Juros (R$)</th>
            <th>AmortizaÃ§Ã£o (R$)</th>
            <th>PMT (R$)</th>
        `;
    } else {
        thead.innerHTML = `
            <th>Evento</th>
            <th>Data</th>
            <th>DU</th>
            <th>DC</th>
            <th>Taxa CDI (%)</th>
            <th>VÃ©rtice (DU)</th>
            <th>Saldo Devedor (R$)</th>
            <th>Juros (R$)</th>
            <th>AmortizaÃ§Ã£o (R$)</th>
            <th>PMT (R$)</th>
        `;
    }

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

        if (indexador === 'IPCA') {
            const vnaDisplay = row.vna_atualizado ? row.vna_atualizado.toLocaleString('pt-BR', {minimumFractionDigits: 2}) : '-';
            const ipcaDisplay = row.ipca_acumulado != null ? row.ipca_acumulado.toFixed(2) : '-';
            const taxaRealDisplay = row.taxa_real_efetiva != null ? row.taxa_real_efetiva.toFixed(2) : '-';
            const verticeDisplay = row.vertice_dias_uteis != null ? row.vertice_dias_uteis : '-';

            html += `
                <tr>
                    <td>${row.evento}</td>
                    <td>${dataFormatada}</td>
                    <td>${row.dias_uteis}</td>
                    <td>${row.dias_corridos}</td>
                    <td>R$ ${vnaDisplay}</td>
                    <td>${ipcaDisplay}</td>
                    <td>${taxaRealDisplay}</td>
                    <td>${verticeDisplay}</td>
                    <td>R$ ${row.juros.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                    <td>R$ ${row.amortizacao.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                    <td><strong>R$ ${row.pmt.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</strong></td>
                </tr>
            `;
        } else {
            const taxaCdiDisplay = row.taxa_cdi_efetiva != null ? row.taxa_cdi_efetiva.toFixed(2) : '-';
            const verticeDisplay = row.vertice_dias_uteis != null ? row.vertice_dias_uteis : '-';

            html += `
                <tr>
                    <td>${row.evento}</td>
                    <td>${dataFormatada}</td>
                    <td>${row.dias_uteis}</td>
                    <td>${row.dias_corridos}</td>
                    <td>${taxaCdiDisplay}</td>
                    <td>${verticeDisplay}</td>
                    <td>R$ ${row.saldo_devedor.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                    <td>R$ ${row.juros.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                    <td>R$ ${row.amortizacao.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                    <td><strong>R$ ${row.pmt.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</strong></td>
                </tr>
            `;
        }
    });

    tbody.innerHTML = html;

    // Total
    const colspanTotal = indexador === 'IPCA' ? 8 : 7;
    tfoot.innerHTML = `
        <tr>
            <td colspan="${colspanTotal}">TOTAIS</td>
            <td>R$ ${totalJuros.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
            <td>R$ ${totalAmort.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
            <td><strong>R$ ${totalPmt.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</strong></td>
        </tr>
    `;
}

// Exibe grÃ¡fico
let chartInstance = null;
function displayChart(cashFlow) {
    const ctx = document.getElementById('cash-flow-chart').getContext('2d');

    // Destroi grÃ¡fico anterior se existir
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
                    label: 'AmortizaÃ§Ã£o (R$)',
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

// Define datas padrÃ£o
window.addEventListener('load', function() {
    const today = new Date();
    const nextYear = new Date(today);
    nextYear.setFullYear(today.getFullYear() + 1);

    document.getElementById('emission_date').valueAsDate = today;
    document.getElementById('maturity_date').valueAsDate = nextYear;
});

