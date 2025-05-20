function applyFilters() {
    const activity = document.getElementById('activityFilter').value;
    const date = document.getElementById('dateFilter').value;
    const url = new URL(window.location.href);
    url.searchParams.set('activity', activity);
    url.searchParams.set('date', date);
    window.location.href = url.toString();
}

document.addEventListener('DOMContentLoaded', () => {
    // tab switching
    const tabs = document.querySelectorAll('.analytics-tab');
    const sections = document.querySelectorAll('.analytics-section');

    function setActiveTab(tabId) {
        tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabId);
        });
        sections.forEach(section => {
            section.classList.toggle('active', section.id === tabId);
            section.classList.toggle('hidden', section.id !== tabId);
        });
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.set('tab', tabId.replace('-section', ''));
        window.history.pushState({}, document.title, `${window.location.pathname}?${urlParams}`);
    }

    const urlParams = new URLSearchParams(window.location.search);
    const initialTab = urlParams.get('tab') === 'charts' ? 'charts-section' :
        urlParams.get('tab') === 'goals' ? 'goals-section' : 'history-section';
    setActiveTab(initialTab);

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            setActiveTab(tab.dataset.tab);
        });
    });
    // goals
    const goalsDialog = document.getElementById('goalsDialog');
    const configureButton = document.querySelector('.configure-goals-button');
    const cancelButton = goalsDialog.querySelector('.cancel-button');
    const goalsForm = document.getElementById('goalsForm');

    configureButton.addEventListener('click', () => {
        goalsDialog.showModal();
    });

    cancelButton.addEventListener('click', () => {
        goalsDialog.close();
    });

    goalsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const weeklyWorkouts = parseInt(document.getElementById('weeklyWorkouts').value);
        const weeklyDistance = parseFloat(document.getElementById('weeklyDistance').value);

        if (isNaN(weeklyWorkouts) || weeklyWorkouts < 1 || weeklyWorkouts > 14) {
            alert('Please enter a valid number of workouts (1–14).');
            return;
        }
        if (isNaN(weeklyDistance) || weeklyDistance < 1 || weeklyDistance > 100) {
            alert('Please enter a valid distance (1–100 km).');
            return;
        }

        const csrfTokenElement = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (!csrfTokenElement || !csrfTokenElement.value) {
            console.error('CSRF token not found or empty');
            alert('Failed to save goals: CSRF token missing');
            return;
        }
        const csrfToken = csrfTokenElement.value;
        console.debug('CSRF token:', csrfToken);

        const payload = { weeklyWorkouts, weeklyDistance };
        console.debug('Sending update_goals payload:', payload);

        try {
            const response = await fetch('/home/update-goals/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const text = await response.text();
                console.error('Non-OK response:', response.status, text);
                throw new Error(`HTTP ${response.status}: ${text}`);
            }

            const result = await response.json();
            console.debug('Update_goals response:', result);

            if (result.status === 'success') {
                document.getElementById('targetWorkouts').textContent = result.weekly_workouts;
                document.getElementById('targetDistance').textContent = result.weekly_distance;
                const completedWorkouts = parseInt(document.getElementById('completedWorkouts').textContent) || 0;
                const completedDistance = parseFloat(document.getElementById('completedDistance').textContent) || 0;
                const workoutsProgress = Math.round(result.weekly_workouts > 0 ? (completedWorkouts / result.weekly_workouts) * 100 : 0);
                const distanceProgress = Math.round(result.weekly_distance > 0 ? (completedDistance / result.weekly_distance) * 100 : 0);
                document.querySelectorAll('.goal-progress')[0].textContent = workoutsProgress + '%';
                document.querySelectorAll('.goal-progress')[1].textContent = distanceProgress + '%';
                window.goalWorkouts = result.weekly_workouts;
                window.goalDistance = result.weekly_distance;
                updateFrequencyChart();
                updateDistanceChart();
                goalsDialog.close();
            } else {
                console.error('Update failed:', result.message);
                alert(`Failed to save goals: ${result.message || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('AJAX error:', error.message);
            alert(`Failed to save goals: ${error.message}`);
        }
    });

    // sorting
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', () => {
            const table = document.getElementById('historyTable');
            const rows = Array.from(table.querySelectorAll('.history-row'));
            const sortKey = header.dataset.sort;
            const isAscending = header.classList.toggle('asc');
            rows.sort((a, b) => {
                let aValue, bValue;
                if (sortKey === 'date') {
                    aValue = a.children[0].dataset.date || '0';
                    bValue = b.children[0].dataset.date || '0';
                    return isAscending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
                } else if (sortKey === 'workout') {
                    aValue = a.children[1].textContent.trim().toLowerCase();
                    bValue = b.children[1].textContent.trim().toLowerCase();
                    return isAscending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
                } else if (sortKey === 'details') {
                    aValue = parseFloat(a.children[2].querySelector('.detail-value').dataset.details) || 0;
                    bValue = parseFloat(a.children[2].querySelector('.detail-value').dataset.details) || 0;
                    return isAscending ? aValue - bValue : bValue - aValue;
                } else if (sortKey === 'duration') {
                    aValue = parseInt(a.children[3].querySelector('.detail-value').dataset.duration) || 0;
                    bValue = parseInt(a.children[3].querySelector('.detail-value').dataset.duration) || 0;
                    return isAscending ? aValue - bValue : bValue - aValue;
                }
                return 0;
            });
            rows.forEach(row => table.appendChild(row));
        });
    });

    // Time Range Toggle Buttons
    document.querySelectorAll('.time-range-toggle').forEach(button => {
        button.addEventListener('click', () => {
            const chart = button.dataset.chart; // e.g., "freq", "dist", "pace", etc.
            const url = new URL(window.location.href);
            const currentTimeRange = url.searchParams.get(`${chart}_time_range`) || 'recent';
            const newTimeRange = currentTimeRange === 'all' ? 'recent' : 'all';
            url.searchParams.set(`${chart}_time_range`, newTimeRange);
            window.location.href = url.toString();
        });
    });

    // Chart setup
    const frequencyData = window.frequencyData || {};
    const distanceData = window.distanceData || {};
    const paceData = window.paceData || {};
    const strengthData = window.strengthData || {};
    const volumeData = window.volumeData || {};
    const freqCtx = document.getElementById('frequencyChart').getContext('2d');
    const distCtx = document.getElementById('distanceChart').getContext('2d');
    const paceCtx = document.getElementById('paceChart').getContext('2d');
    const strengthCtx = document.getElementById('strengthChart').getContext('2d');
    const volumeCtx = document.getElementById('volumeChart').getContext('2d');

    let freqChart, distChart, paceChart, strengthChart, volumeChart;

    function getPeriodData(data, period, activityType) {
        if (activityType !== undefined) {
            return data[period][activityType] || [];
        }
        return data[period] || [];
    }

    function renderChart(ctx, data, period, label, yAxisTitle, valueKey, chartType = 'bar', activityType = undefined) {
        const periodData = getPeriodData(data, period, activityType);
        if (!periodData.length) {
            console.warn(`No ${period} data available for ${label}, using fallback`);
            periodData.push({ label: 'No Data', [valueKey]: 0 });
        }

        if (ctx === freqCtx && freqChart) freqChart.destroy();
        if (ctx === distCtx && distChart) distChart.destroy();
        if (ctx === paceCtx && paceChart) paceChart.destroy();
        if (ctx === strengthCtx && strengthChart) strengthChart.destroy();
        if (ctx === volumeCtx && volumeChart) volumeChart.destroy();

        const datasets = [{
            label: label,
            data: periodData.map(item => item[valueKey]),
            backgroundColor: chartType === 'bar' ? 'rgba(37, 99, 235, 0.6)' : 'rgba(37, 99, 235, 0.2)',
            borderColor: 'rgba(37, 99, 235, 1)',
            borderWidth: 1,
            fill: chartType === 'line',
            tension: 0.1
        }];

        // Add goal line for Workout Frequency
        if (ctx === freqCtx && window.goalWorkouts) {
            datasets.push({
                label: 'Goal',
                data: Array(periodData.length).fill(window.goalWorkouts),
                type: 'line',
                borderColor: 'rgba(255, 99, 132, 1)', // Red for visibility
                borderWidth: 2,
                pointRadius: 0, // No points
                fill: false,
                tension: 0
            });
        }

        // goal line for Running Distance
        if (ctx === distCtx && window.goalDistance) {
            datasets.push({
                label: 'Goal',
                data: Array(periodData.length).fill(window.goalDistance),
                type: 'line',
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                tension: 0
            });
        }

        const chart = new Chart(ctx, {
            type: chartType,
            data: {
                labels: periodData.map(item => item.label),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: yAxisTitle },
                        ticks: { stepSize: valueKey === 'pace' ? 0.5 : valueKey === 'weight' ? 10 : 1 }
                    },
                    x: {
                        title: { display: true, text: period.charAt(0).toUpperCase() + period.slice(1) },
                        offset: (ctx === freqCtx || ctx === distCtx) ? false : undefined,
                        grid: {
                            offset: (ctx === freqCtx || ctx === distCtx) ? false : undefined
                        },
                        ticks: {
                            padding: (ctx === freqCtx || ctx === distCtx) ? 0 : undefined
                        }
                    }
                },
                plugins: {
                    legend: { display: ctx === freqCtx || ctx === distCtx ? true : false },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                const index = context[0].dataIndex;
                                return periodData[index].date_range || periodData[index].label;
                            },
                            label: function(context) {
                                const value = context.parsed.y;
                                if (context.dataset.label === 'Goal') {
                                    return `Goal: ${value.toFixed(context.datasetIndex === 1 ? 1 : 0)} ${ctx === distCtx ? 'km' : 'workouts'}`;
                                }
                                if (valueKey === 'count') return `${value} workout${value !== 1 ? 's' : ''}`;
                                if (valueKey === 'distance') return `${value.toFixed(2)} km`;
                                if (valueKey === 'pace') {
                                    const minutes = Math.floor(value);
                                    const seconds = Math.round((value - minutes) * 60);
                                    return `${minutes}:${seconds < 10 ? '0' : ''}${seconds} min/km`;
                                }
                                if (valueKey === 'weight') {
                                    const reps = periodData[context.dataIndex].reps || 0;
                                    return `${value.toFixed(1)}kg x ${reps} reps`;
                                }
                            }
                        }
                    }
                }
            }
        });

        if (ctx === freqCtx) freqChart = chart;
        if (ctx === distCtx) distChart = chart;
        if (ctx === paceCtx) paceChart = chart;
        if (ctx === strengthCtx) strengthChart = chart;
        if (ctx === volumeCtx) volumeChart = chart;
    }

    function renderStrengthChart(ctx, data, period, label, yAxisTitle, valueKey, chartType = 'line', exercise = 'all') {
        let datasets = [];
        let showLegend = false;
        const allDates = getPeriodData(data, period, 'all').map(item => item.label);

        if (exercise === 'all') {
            const exercises = Object.keys(data[period]).filter(key => key !== 'all');
            const colors = [
                'rgba(37, 99, 235, 1)',   // Blue
                'rgba(255, 99, 132, 1)',  // Red
                'rgba(75, 192, 192, 1)',  // Teal
                'rgba(255, 159, 64, 1)',  // Orange
                'rgba(153, 102, 255, 1)', // Purple
                'rgba(255, 205, 86, 1)'   // Yellow
            ];
            datasets = exercises.map((ex, index) => {
                const exData = getPeriodData(data, period, ex);
                const dataMap = {};
                exData.forEach(item => dataMap[item.label] = item[valueKey]);
                const alignedData = allDates.map(date => dataMap[date] !== undefined ? dataMap[date] : null);
                return {
                    label: ex,
                    data: alignedData,
                    borderColor: colors[index % colors.length],
                    backgroundColor: colors[index % colors.length].replace('1)', '0.2)'),
                    borderWidth: 1,
                    fill: true,
                    tension: 0.1,
                    spanGaps: true
                };
            });
            showLegend = true;
        } else {
            const periodData = getPeriodData(data, period, exercise);
            if (!periodData.length) {
                console.warn(`No ${period} data available for ${label}, using fallback`);
                periodData.push({ label: 'No Data', [valueKey]: 0 });
            }
            datasets = [{
                label: exercise,
                data: periodData.map(item => item[valueKey]),
                backgroundColor: 'rgba(37, 99, 235, 0.2)',
                borderColor: 'rgba(37, 99, 235, 1)',
                borderWidth: 1,
                fill: true,
                tension: 0.1
            }];
        }

        if (ctx === strengthCtx && strengthChart) strengthChart.destroy();

        const chart = new Chart(ctx, {
            type: chartType,
            data: {
                labels: allDates,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: yAxisTitle },
                        ticks: { stepSize: 10 }
                    },
                    x: { title: { display: true, text: period.charAt(0).toUpperCase() + period.slice(1) } }
                },
                plugins: {
                    legend: { display: showLegend },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                const index = context[0].dataIndex;
                                const periodData = getPeriodData(data, period, exercise === 'all' ? context[0].dataset.label : exercise);
                                const date = allDates[index];
                                const item = periodData.find(d => d.label === date) || {};
                                return item.date_range || date;
                            },
                            label: function(context) {
                                const value = context.parsed.y;
                                if (!value && value !== 0) return 'No Data';
                                const periodData = getPeriodData(data, period, exercise === 'all' ? context.dataset.label : exercise);
                                const date = allDates[context.dataIndex];
                                const item = periodData.find(d => d.label === date) || {};
                                const reps = item.reps || 0;
                                return `${value.toFixed(1)}kg x ${reps} reps`;
                            }
                        }
                    }
                }
            }
        });

        strengthChart = chart;
    }

    function renderVolumeChart(ctx, data, period, exercise = 'all') {
        const periodData = getPeriodData(data, period, exercise);
        if (!periodData.length) {
            console.warn(`No ${period} volume data available for ${exercise}, using fallback`);
            periodData.push({ label: 'No Data', volume: 0, by_exercise: {} });
        }

        if (ctx === volumeCtx && volumeChart) volumeChart.destroy();

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: periodData.map(item => item.label),
                datasets: [{
                    label: exercise === 'all' ? 'Volume Lifted' : `Volume Lifted (${exercise})`,
                    data: periodData.map(item => item.volume),
                    backgroundColor: 'rgba(34, 197, 94, 0.6)',
                    borderColor: 'rgba(34, 197, 94, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Volume (kg)' },
                        ticks: { stepSize: 100 }
                    },
                    x: { title: { display: true, text: period.charAt(0).toUpperCase() + period.slice(1) } }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                const index = context[0].dataIndex;
                                return periodData[index].date_range || periodData[index].label;
                            },
                            label: function(context) {
                                const value = context.parsed.y;
                                if (exercise === 'all') {
                                    const byExercise = periodData[context.dataIndex].by_exercise || {};
                                    let tooltip = [`Total: ${value.toFixed(0)} kg`];
                                    for (const [ex, vol] of Object.entries(byExercise)) {
                                        tooltip.push(`${ex}: ${vol.toFixed(0)} kg`);
                                    }
                                    return tooltip;
                                } else {
                                    return `${value.toFixed(0)} kg`;
                                }
                            }
                        }
                    }
                }
            }
        });

        volumeChart = chart;
    }

    // Initial render
    const initialFreqPeriod = document.getElementById('freqPeriodFilter').value;
    const initialFreqActivity = document.getElementById('freqActivityFilter').value;
    const initialDistPeriod = document.getElementById('distancePeriodFilter').value;
    const initialPacePeriod = document.getElementById('pacePeriodFilter').value;
    const initialStrengthPeriod = document.getElementById('strengthPeriodFilter').value;
    const initialStrengthExercise = document.getElementById('strengthExerciseFilter').value;
    const initialVolumePeriod = document.getElementById('volumePeriodFilter').value;
    const initialVolumeExercise = document.getElementById('volumeExerciseFilter').value;
    renderChart(freqCtx, frequencyData, initialFreqPeriod, 'Workouts', 'Number of Workouts', 'count', 'bar', initialFreqActivity);
    renderChart(distCtx, distanceData, initialDistPeriod, 'Distance', 'Distance (km)', 'distance', 'bar');
    renderChart(paceCtx, paceData, initialPacePeriod, 'Pace', 'Pace (min/km)', 'pace', 'line');
    renderStrengthChart(strengthCtx, strengthData, initialStrengthPeriod, 'Strength', 'Weight (kg)', 'weight', 'line', initialStrengthExercise);
    renderVolumeChart(volumeCtx, volumeData, initialVolumePeriod, initialVolumeExercise);

    // Chart updates
    window.updateFrequencyChart = function() {
        const period = document.getElementById('freqPeriodFilter').value;
        const activityType = document.getElementById('freqActivityFilter').value;
        renderChart(freqCtx, frequencyData, period, 'Workouts', 'Number of Workouts', 'count', 'bar', activityType);
        const url = new URL(window.location.href);
        url.searchParams.set('freq_period', period);
        url.searchParams.set('freq_activity_type', activityType);
        window.history.pushState({}, document.title, url);
    };

    window.updateDistanceChart = function() {
        const period = document.getElementById('distancePeriodFilter').value;
        renderChart(distCtx, distanceData, period, 'Distance', 'Distance (km)', 'distance', 'bar');
        const url = new URL(window.location.href);
        url.searchParams.set('dist_period', period);
        window.history.pushState({}, document.title, url);
    };

    window.updatePaceChart = function() {
        const period = document.getElementById('pacePeriodFilter').value;
        renderChart(paceCtx, paceData, period, 'Pace', 'Pace (min/km)', 'pace', 'line');
        const url = new URL(window.location.href);
        url.searchParams.set('pace_period', period);
        window.history.pushState({}, document.title, url);
    };

    window.updateStrengthChart = function() {
        const period = document.getElementById('strengthPeriodFilter').value;
        const exercise = document.getElementById('strengthExerciseFilter').value;
        renderStrengthChart(strengthCtx, strengthData, period, 'Strength', 'Weight (kg)', 'weight', 'line', exercise);
        const url = new URL(window.location.href);
        url.searchParams.set('strength_period', period);
        url.searchParams.set('strength_exercise', exercise);
        window.history.pushState({}, document.title, url);
    };

    window.updateVolumeChart = function() {
        const period = document.getElementById('volumePeriodFilter').value;
        const exercise = document.getElementById('volumeExerciseFilter').value;
        renderVolumeChart(volumeCtx, volumeData, period, exercise);
        const url = new URL(window.location.href);
        url.searchParams.set('volume_period', period);
        url.searchParams.set('volume_exercise', exercise);
        window.history.pushState({}, document.title, url);
    };
});