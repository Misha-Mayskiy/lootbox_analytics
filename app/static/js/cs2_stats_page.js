document.addEventListener('DOMContentLoaded', function () {
    const syncBtn = document.getElementById('syncCs2InventoryBtn');
    const syncStatusDiv = document.getElementById('syncStatus');
    const investmentForm = document.getElementById('investmentForm');
    const investmentInput = document.getElementById('cs2InvestmentInput');
    const investmentStatusDiv = document.getElementById('investmentStatus');
    const csrfTokenElement = document.getElementById('csrf_token_value');
    const csrfToken = csrfTokenElement ? csrfTokenElement.value : null;

    function showSyncStatus(message, type) {
        if (syncStatusDiv) {
            syncStatusDiv.style.display = 'block';
            syncStatusDiv.className = `alert alert-${type} mt-2`;
            syncStatusDiv.innerText = message;
        }
    }

    function showInvestmentStatus(message, type) {
        if (investmentStatusDiv) {
            investmentStatusDiv.innerText = message;
            investmentStatusDiv.className = `small mt-1 text-${type}`;
        }
    }

    if (syncBtn) {
        syncBtn.addEventListener('click', function () {
            showSyncStatus('Синхронизация инвентаря CS2... Пожалуйста, подождите.', 'info');
            syncBtn.disabled = true;
            syncBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Загрузка...';

            const headers = {'Content-Type': 'application/json'};
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            fetch(window.cs2SyncUrl, {method: 'POST', headers: headers})
                .then(response => {
                    const contentType = response.headers.get("content-type");
                    if (contentType && contentType.indexOf("application/json") !== -1) {
                        return response.json().then(data => ({ok: response.ok, status: response.status, body: data}));
                    }
                    return response.text().then(text => {
                        throw new Error(`Ответ сервера не JSON (статус ${response.status}): ${text.substring(0, 200)}`);
                    });
                })
                .then(dataObj => {
                    showSyncStatus((dataObj.body && dataObj.body.message) ? dataObj.body.message : 'Статус неизвестен', dataObj.ok ? 'success' : 'danger');
                    if (dataObj.ok) {
                        setTimeout(() => {
                            window.location.reload();
                        }, 2500);
                    }
                })
                .catch(error => {
                    showSyncStatus('Ошибка синхронизации: ' + error.message, 'danger');
                    console.error('Ошибка синхронизации CS2:', error);
                })
                .finally(() => {
                    syncBtn.disabled = false;
                    syncBtn.innerHTML = '<svg width="1em" height="1em" viewBox="0 0 16 16" class="bi bi-arrow-clockwise" fill="currentColor" xmlns="http://www.w3.org/2000/svg" style="margin-right: 5px; vertical-align: text-bottom;"><path fill-rule="evenodd" d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/><path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/></svg> Синхронизировать инвентарь Steam';
                });
        });
    }

    if (investmentForm && investmentInput) {
        investmentForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const amount = parseFloat(investmentInput.value);
            if (isNaN(amount) || amount < 0) {
                showInvestmentStatus('Пожалуйста, введите корректную сумму (неотрицательное число).', 'danger');
                return;
            }
            showInvestmentStatus('Сохранение...', 'info');

            const headers = {'Content-Type': 'application/json'};
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            fetch(window.cs2UpdateInvestmentUrl, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({amount: amount})
            })
                .then(response => {
                    const contentType = response.headers.get("content-type");
                    if (contentType && contentType.indexOf("application/json") !== -1) {
                        return response.json().then(data => ({ok: response.ok, status: response.status, body: data}));
                    }
                    return response.text().then(text => {
                        throw new Error(`Ответ сервера не JSON (статус ${response.status}): ${text.substring(0, 200)}`);
                    });
                })
                .then(dataObj => {
                    showInvestmentStatus((dataObj.body && dataObj.body.message) ? dataObj.body.message : 'Ошибка', dataObj.ok ? 'success' : 'danger');
                    if (dataObj.ok && dataObj.body.new_roi !== undefined) {
                        const roiElement = document.getElementById('cs2RoiValue');
                        if (roiElement) {
                            roiElement.innerText = dataObj.body.new_roi + '%';
                            roiElement.className = 'font-weight-bold ';
                            if (dataObj.body.new_roi > 0) roiElement.classList.add('text-success');
                            else if (dataObj.body.new_roi < 0) roiElement.classList.add('text-danger');
                            else roiElement.classList.add('text-muted');
                        }
                    }
                })
                .catch(error => {
                    showInvestmentStatus('Ошибка сохранения: ' + error.message, 'danger');
                    console.error('Ошибка сохранения затрат CS2:', error);
                });
        });
    }

    if (window.chartDataCS2 && window.chartDataCS2.rarityChartData) {
        const cs2RarityCtx = document.getElementById('cs2RarityPieChart');
        const cs2RarityData = window.chartDataCS2.rarityChartData;
        if (cs2RarityCtx && cs2RarityData.labels && cs2RarityData.labels.length > 0) {
            new Chart(cs2RarityCtx, {
                type: 'doughnut',
                data: cs2RarityData,
                options: {responsive: true, maintainAspectRatio: false, plugins: {legend: {position: 'right'}}}
            });
        } else if (cs2RarityCtx) {
            cs2RarityCtx.style.display = 'none';
        }
    }

    if (window.chartDataCS2 && window.chartDataCS2.typeChartData) {
        const cs2TypeCtx = document.getElementById('cs2TypePieChart');
        const cs2TypeData = window.chartDataCS2.typeChartData;
        if (cs2TypeCtx && cs2TypeData.labels && cs2TypeData.labels.length > 0) {
            new Chart(cs2TypeCtx, {
                type: 'pie',
                data: cs2TypeData,
                options: {responsive: true, maintainAspectRatio: false, plugins: {legend: {position: 'right'}}}
            });
        } else if (cs2TypeCtx) {
            cs2TypeCtx.style.display = 'none';
        }
    }
});