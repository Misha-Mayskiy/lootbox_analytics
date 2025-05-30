document.addEventListener('DOMContentLoaded', function () {
    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    const legendTextColor = isDarkMode ? 'rgba(166,166,166,0.85)' : 'rgba(0, 0, 0, 0.85)';

    // Проверяем, существуют ли данные, перед тем как пытаться их использовать
    if (!window.genshinChartData || !window.genshinChartData.overallRarityData || !window.genshinChartData.bannerStatesData) {
        console.warn("Данные для графиков Genshin (window.genshinChartData) не найдены или неполны.");
        return;
    }

    const overallRarityData = window.genshinChartData.overallRarityData;
    const bannerStatesData = window.genshinChartData.bannerStatesData;
    // const pityLimits = window.genshinChartData.pityLimits || {}; // Если передаем лимиты

    // 1. Общий график распределения редкости
    const overallRarityCtx = document.getElementById('overallRarityPieChart');
    if (overallRarityCtx && Object.keys(overallRarityData).length > 0 && (overallRarityData['3'] || overallRarityData['4'] || overallRarityData['5'])) {
        new Chart(overallRarityCtx, {
            type: 'doughnut',
            data: {
                labels: [
                    `5★ Предметы (${overallRarityData['5'] || 0})`,
                    `4★ Предметы (${overallRarityData['4'] || 0})`,
                    `3★ Оружие (${overallRarityData['3'] || 0})`
                ],
                datasets: [{
                    label: 'Распределение по редкости',
                    data: [overallRarityData['5'] || 0, overallRarityData['4'] || 0, overallRarityData['3'] || 0],
                    backgroundColor: [
                        'rgba(255, 205, 86, 0.8)', // Gold
                        'rgba(172, 107, 248, 0.8)', // Purple
                        'rgba(54, 162, 235, 0.8)'  // Blue
                    ],
                    borderColor: [ // Добавим рамки для лучшей видимости на разных фонах
                        'rgba(255, 205, 86, 1)',
                        'rgba(172, 107, 248, 1)',
                        'rgba(54, 162, 235, 1)'
                    ],
                    borderWidth: 1,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {font: {size: 10}, color: legendTextColor}
                    },
                    title: {display: false}
                }
            }
        });
    } else if (overallRarityCtx && overallRarityCtx.parentNode) { // Проверка parentNode
        overallRarityCtx.style.display = 'none';
        const p = document.createElement('p');
        p.className = 'text-muted small text-center py-5';
        p.textContent = 'Нет данных для графика общей редкости.';
        overallRarityCtx.parentNode.appendChild(p);
    }

    // Итерация по группам баннеров для остальных графиков
    for (const banner_group_name in bannerStatesData) {
        if (bannerStatesData.hasOwnProperty(banner_group_name)) {
            const state = bannerStatesData[banner_group_name];
            if (!state || state.total_pulls === 0) continue; // Пропускаем, если нет данных по группе

            let groupTitle = banner_group_name.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());

            // 2. График Статистики 50/50 (только для character_event)
            if (banner_group_name === 'character_event') {
                if (state.wins_50_50 + state.losses_50_50 > 0) {
                    const fiftyFiftyCanvasId = `fiftyFiftyChart_${banner_group_name}`;
                    const fiftyFiftyCtx = document.getElementById(fiftyFiftyCanvasId);
                    if (fiftyFiftyCtx) {
                        new Chart(fiftyFiftyCtx, {
                            type: 'pie',
                            data: {
                                labels: [
                                    `Выиграно 50/50 (${state.wins_50_50})`,
                                    `Проиграно 50/50 (${state.losses_50_50})`
                                ],
                                datasets: [{
                                    data: [state.wins_50_50, state.losses_50_50],
                                    backgroundColor: ['rgba(75, 192, 192, 0.7)', 'rgba(255, 99, 132, 0.7)'],
                                    borderColor: ['rgba(75, 192, 192, 1)', 'rgba(255, 99, 132, 1)'],
                                    borderWidth: 1,
                                    hoverOffset: 4
                                }]
                            },
                            options: {
                                responsive: true, maintainAspectRatio: false,
                                plugins: {
                                    legend: {
                                        position: 'bottom',
                                        labels: {font: {size: 10}, color: legendTextColor}
                                    }
                                }
                            }
                        });
                    }
                }
            }

            // 3. График Распределения 5* по зонам Pity
            const pityLuckData = state.pity_luck_5_star;
            if (pityLuckData && pityLuckData.total > 0) {
                const pityZoneCanvasId = `pityZoneChart_${banner_group_name}`;
                const pityZoneCtx = document.getElementById(pityZoneCanvasId);
                if (pityZoneCtx) {
                    let earlyLabel = `Рано (<${pityLuckData.soft_pity_start_val || 'N/A'})`;
                    new Chart(pityZoneCtx, {
                        type: 'bar',
                        data: {
                            labels: [earlyLabel, 'Soft Pity', 'Hard Pity/Позже'],
                            datasets: [{
                                label: 'Кол-во 5★',
                                data: [pityLuckData.early, pityLuckData.soft_pity_zone, pityLuckData.hard_pity],
                                backgroundColor: ['rgba(75, 192, 192, 0.7)', 'rgba(54, 162, 235, 0.7)', 'rgba(255, 159, 64, 0.7)'],
                                borderColor: ['rgba(75, 192, 192, 1)', 'rgba(54, 162, 235, 1)', 'rgba(255, 159, 64, 1)'],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true, maintainAspectRatio: false, indexAxis: 'y',
                            scales: {x: {beginAtZero: true, ticks: {stepSize: 1}}},
                            plugins: {legend: {display: false, labels: {color: legendTextColor}}}
                        }
                    });
                }
            }

            // 4. График Истории Pity для 5★
            const pityHistoryForGroup = state.history_5_star;
            if (pityHistoryForGroup && pityHistoryForGroup.length > 1) { // Нужны хотя бы 2 точки для линии
                const pityHistoryCanvasId = `pityHistoryLineChart_${banner_group_name}`;
                const pityHistoryCtx = document.getElementById(pityHistoryCanvasId);
                if (pityHistoryCtx) {
                    pityHistoryCtx.style.display = 'block';
                    const pityValues = pityHistoryForGroup.map(h => h.pity_at);
                    const labels = pityHistoryForGroup.map((h, index) => `5★ #${index + 1} (${h.item_name.substring(0, 15)}${h.item_name.length > 15 ? '...' : ''})`);
                    new Chart(pityHistoryCtx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: `Pity 5★`,
                                data: pityValues,
                                borderColor: getRandomColor(),
                                tension: 0.1,
                                fill: false
                            }]
                        },
                        options: {
                            responsive: true, maintainAspectRatio: false,
                            scales: {
                                y: {beginAtZero: true, title: {display: true, text: 'Pity (кол-во молитв)'}},
                                x: {title: {display: false}} // Метки уже информативны
                            },
                            plugins: {legend: {display: false, labels: {color: legendTextColor}}}
                        }
                    });
                }
            } else if (pityHistoryForGroup && pityHistoryForGroup.length === 1 && document.getElementById(`pityHistoryLineChart_${banner_group_name}`)) {
                // Если только один 5* дроп, график линии не нужен, можно скрыть канвас или показать сообщение
                const canvas = document.getElementById(`pityHistoryLineChart_${banner_group_name}`);
                if (canvas && canvas.parentNode) {
                    canvas.style.display = 'none';
                    const p = document.createElement('p');
                    p.className = 'text-muted small text-center';
                    p.textContent = 'Нужен хотя бы второй 5★ дроп для построения графика истории Pity.';
                    canvas.parentNode.appendChild(p);
                }
            }
        }
    }
});

function getRandomColor() {
    const r = Math.floor(Math.random() * 200 + 55); // Яркие, но не слишком светлые
    const g = Math.floor(Math.random() * 200 + 55);
    const b = Math.floor(Math.random() * 200 + 55);
    return `rgb(${r},${g},${b})`;
}