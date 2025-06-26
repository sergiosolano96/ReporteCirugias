document.addEventListener('DOMContentLoaded', function() {
    console.log("Dashboard JS cargado");
    
    try {
        // 1. Verificar elementos del DOM
        const elements = {
            mensual: document.getElementById('mensual-data'),
            cirujanos: document.getElementById('top-cirujanos-data'),
            clinicas: document.getElementById('top-clinicas-data'),
            total: document.getElementById('total-general'),
            displayTotal: document.getElementById('total-general-display')
        };

        // 2. Validar que existen todos los elementos
        if (!elements.mensual || !elements.cirujanos || !elements.clinicas || !elements.total) {
            throw new Error("Elementos de datos no encontrados en el DOM");
        }

        // 3. Cargar y validar datos
        const data = {
            mensual: JSON.parse(elements.mensual.textContent || '[]'),
            cirujanos: JSON.parse(elements.cirujanos.textContent || '[]'),
            clinicas: JSON.parse(elements.clinicas.textContent || '[]'),
            total: parseFloat(elements.total.textContent || '0')
        };
        
        console.log("Datos recibidos:", data);

        // 4. Formateador de moneda
        const formatCOP = (value) => new Intl.NumberFormat('es-CO', {
            style: 'currency',
            currency: 'COP',
            maximumFractionDigits: 0
        }).format(value);

        // 5. Actualizar total general
        if (elements.displayTotal) {
            elements.displayTotal.textContent = formatCOP(data.total);
        }

        // 6. Configuración común para gráficos
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false
        };

        // 7. Gráfico Mensual
        if (data.mensual.length > 0 && document.getElementById('chartMensual')) {
            new Chart(document.getElementById('chartMensual').getContext('2d'), {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'Ingresos Mensuales',
                        data: data.mensual.map(item => ({
                            x: item.Mes,
                            y: item.Valor
                        })),
                        borderColor: '#3B82F6',
                        backgroundColor: '#93C5FD80',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: {
                    ...chartOptions,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'month',
                                tooltipFormat: 'MMM YYYY'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: formatCOP
                            }
                        }
                    }
                }
            });
        }

        // 8. Gráfico Cirujanos
        if (data.cirujanos.length > 0 && document.getElementById('chartCirujanos')) {
            new Chart(document.getElementById('chartCirujanos').getContext('2d'), {
                type: 'bar',
                data: {
                    labels: data.cirujanos.map(item => item.Cirujano),
                    datasets: [{
                        label: 'Ingresos',
                        data: data.cirujanos.map(item => item.Valor),
                        backgroundColor: '#10B981'
                    }]
                },
                options: {
                    ...chartOptions,
                    indexAxis: 'y',
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: {
                                callback: formatCOP
                            }
                        }
                    }
                }
            });
        }

        // 9. Gráfico Clínicas
        if (data.clinicas.length > 0 && document.getElementById('chartClinicas')) {
            new Chart(document.getElementById('chartClinicas').getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: data.clinicas.map(item => item.Clínica),
                    datasets: [{
                        data: data.clinicas.map(item => item.Valor),
                        backgroundColor: [
                            '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'
                        ]
                    }]
                },
                options: {
                    ...chartOptions,
                    cutout: '70%'
                }
            });
        }

    } catch (error) {
        console.error("Error en dashboard:", error);
        const errorContainer = document.createElement('div');
        errorContainer.className = 'alert alert-danger m-4';
        errorContainer.innerHTML = `
            <h4>Error al cargar el dashboard</h4>
            <p>${error.message}</p>
        `;
        document.querySelector('.container-fluid').prepend(errorContainer);
    }
});