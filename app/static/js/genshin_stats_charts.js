document.addEventListener('DOMContentLoaded', function () {
    const overallRarityData = window.chartData.overallRarityData;
    const bannerStatesData = window.chartData.bannerStatesData;

    const overallRarityCtx = document.getElementById('overallRarityPieChart');
    if (overallRarityCtx && Object.keys(overallRarityData).length > 0 && (overallRarityData['3'] || overallRarityData['4'] || overallRarityData['5'])) {
        new Chart(overallRarityCtx, {
            type: 'doughnut',
            data: {
                labels: ['5★ (' + (overallRarityData['5'] || 0) + ')', '4★ (' + (overallRarityData['4'] || 0) + ')', '3★ (' + (overallRarityData['3'] || 0) + ')'],
                datasets: [{
                    label: 'Распределение по редкости',
                    data: [overallRarityData['5'] || 0, overallRarityData['4'] || 0, overallRarityData['3'] || 0],
                    backgroundColor: ['gold', 'purple', 'dodgerblue'],
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                plugins: {legend: {position: 'bottom'}}
            }
        });
    } else if (overallRarityCtx) {
        overallRarityCtx.style.display = 'none';
        let p = document.createElement('p');
        p.textContent = 'Нет данных для графика редкости.';
        if (overallRarityCtx.parentNode) {
            overallRarityCtx.parentNode.appendChild(p);
        }
    }

    // Итерация по группам баннеров для остальных графиков
    for (const banner_group_name in bannerStatesData) {
        if (bannerStatesData.hasOwnProperty(banner_group_name)) {
            const state = bannerStatesData[banner_group_name];
            let groupTitle = banner_group_name.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());

            // График Истории Pity для 5★
            const pityHistoryForGroup = state.history_5_star;
            if (pityHistoryForGroup && pityHistoryForGroup.length > 0) {
                const pityHistoryCanvasId = `pityHistoryLineChart_${banner_group_name}`;
                const pityHistoryCtx = document.getElementById(pityHistoryCanvasId);
                if (pityHistoryCtx) {
                    pityHistoryCtx.style.display = 'block';
                    const pityValues = pityHistoryForGroup.map(h => h.pity_at);
                    const labels = pityHistoryForGroup.map((h, index) => `5★ #${index + 1}`);
                    new Chart(pityHistoryCtx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: `История Pity 5★ (${groupTitle})`,
                                data: pityValues,
                                borderColor: getRandomColor(),
                                tension: 0.1,
                                fill: false
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: {beginAtZero: true, title: {display: true, text: 'Pity (кол-во круток)'}},
                                x: {title: {display: true, text: 'Номер 5★ дропа'}}
                            },
                            plugins: {legend: {display: false}}
                        }
                    });
                }
            }

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
                                    label: 'Статистика 50/50',
                                    data: [state.wins_50_50, state.losses_50_50],
                                    backgroundColor: ['rgba(75, 192, 192, 0.7)', 'rgba(255, 99, 132, 0.7)'],
                                    borderColor: ['rgba(75, 192, 192, 1)', 'rgba(255, 99, 132, 1)'],
                                    borderWidth: 1,
                                    hoverOffset: 4
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {legend: {position: 'bottom'}}
                            }
                        });
                    }
                }
            }

            // График Распределения 5* по зонам Pity
            const pityLuckData = state.pity_luck_5_star;
            if (pityLuckData && pityLuckData.total > 0) {
                const pityZoneCanvasId = `pityZoneChart_${banner_group_name}`;
                const pityZoneCtx = document.getElementById(pityZoneCanvasId);
                if (pityZoneCtx) {
                    let earlyLabel = 'Рано';
                    if (pityLuckData.soft_pity_start_val) {
                        earlyLabel = `Рано (<${pityLuckData.soft_pity_start_val})`;
                    } else {
                        earlyLabel = `Рано (<${(banner_group_name === 'character_event' || banner_group_name === 'standard' ? 74 : (banner_group_name === 'weapon_event' ? 62 : 'N/A'))})`;
                    }

                    new Chart(pityZoneCtx, {
                        type: 'bar',
                        data: {
                            labels: [earlyLabel, 'Soft Pity', 'Hard Pity/Позже'],
                            datasets: [{
                                label: 'Кол-во 5★ дропов',
                                data: [pityLuckData.early, pityLuckData.soft_pity_zone, pityLuckData.hard_pity],
                                backgroundColor: ['rgba(75, 192, 192, 0.7)', 'rgba(54, 162, 235, 0.7)', 'rgba(255, 159, 64, 0.7)'],
                                borderColor: ['rgba(75, 192, 192, 1)', 'rgba(54, 162, 235, 1)', 'rgba(255, 159, 64, 1)'],
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            indexAxis: 'y',
                            scales: {
                                x: {
                                    beginAtZero: true,
                                    ticks: {stepSize: 1}
                                }
                            },
                            plugins: {legend: {display: false}}
                        }
                    });
                }
            }
        }
    }
});

function getRandomColor() {
    var letters = '0123456789ABCDEF';
    var color = '#';
    for (var i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}