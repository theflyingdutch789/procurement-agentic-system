/**
 * Data Visualization Module using Apache ECharts
 * Intelligently detects data types and renders appropriate visualizations
 */

export const DataVisualizer = {
    /**
     * Analyze data structure and determine best visualization type
     */
    analyzeData(results, pipeline) {
        if (!results || results.length === 0) {
            return { type: 'none' };
        }

        const firstItem = results[0];
        const keys = Object.keys(firstItem);

        // Check for aggregated data (has _id and aggregation fields like total, count, avg)
        const hasId = keys.includes('_id');
        const hasAggregation = keys.some(k =>
            ['total', 'count', 'sum', 'avg', 'average', 'min', 'max'].includes(k.toLowerCase())
        );

        // Check for time-based data
        const hasTimeDimension = keys.some(k =>
            ['year', 'month', 'date', 'quarter', 'fiscal_year', 'timestamp'].includes(k.toLowerCase())
        ) || (hasId && (
            String(firstItem._id).match(/^\d{4}/) || // Starts with year
            String(firstItem._id).includes('-20') || // Contains year pattern
            ['fiscal_year', 'year', 'quarter'].some(t => String(firstItem._id).toLowerCase().includes(t))
        ));

        // Determine chart type based on data characteristics
        if (hasId && hasAggregation) {
            if (results.length <= 8 && !hasTimeDimension) {
                // Pie chart for small categorical data
                return {
                    type: 'multi',
                    primary: 'pie',
                    alternate: ['bar', 'table'],
                    label: this._extractLabel(firstItem),
                    value: this._extractValue(firstItem)
                };
            } else if (hasTimeDimension) {
                // Line chart for time series
                return {
                    type: 'multi',
                    primary: 'line',
                    alternate: ['bar', 'table'],
                    label: this._extractLabel(firstItem),
                    value: this._extractValue(firstItem),
                    isTimeSeries: true
                };
            } else {
                // Bar chart for aggregated data
                return {
                    type: 'multi',
                    primary: 'bar',
                    alternate: ['pie', 'table'],
                    label: this._extractLabel(firstItem),
                    value: this._extractValue(firstItem)
                };
            }
        }

        // Default to table for detailed/non-aggregated data
        // But still make it a multi-view with table as primary
        return {
            type: 'multi',
            primary: 'table',
            alternate: [],  // Table-only, but still uses multi-view container
            columns: keys
        };
    },

    /**
     * Extract label field from data item
     */
    _extractLabel(item) {
        if (item._id !== null && item._id !== undefined) {
            return '_id';
        }
        const keys = Object.keys(item);
        return keys.find(k => typeof item[k] === 'string') || keys[0];
    },

    /**
     * Extract value field from data item
     */
    _extractValue(item) {
        const keys = Object.keys(item);
        const valueKey = keys.find(k =>
            ['total', 'count', 'sum', 'avg', 'average', 'value', 'amount'].includes(k.toLowerCase())
        );
        return valueKey || keys.find(k => typeof item[k] === 'number') || keys[1];
    },

    /**
     * Create visualization container with view toggles
     */
    createVisualizationContainer(containerId, analysisResult) {
        if (analysisResult.type === 'none') {
            return null;
        }

        const container = document.createElement('div');
        container.className = 'visualization-container';
        container.id = containerId;

        // Create view toggle buttons (only if there are multiple views)
        if (analysisResult.type === 'multi' && analysisResult.alternate && analysisResult.alternate.length > 0) {
            const toolbar = document.createElement('div');
            toolbar.className = 'viz-toolbar';

            const views = [analysisResult.primary, ...analysisResult.alternate];
            views.forEach(viewType => {
                const btn = document.createElement('button');
                btn.className = `viz-toggle-btn ${viewType === analysisResult.primary ? 'active' : ''}`;
                btn.dataset.view = viewType;
                btn.innerHTML = this._getViewIcon(viewType);
                btn.title = `Show ${viewType} view`;
                btn.onclick = () => this.switchView(containerId, viewType);
                toolbar.appendChild(btn);
            });

            container.appendChild(toolbar);
        }

        // Create chart container
        const chartDiv = document.createElement('div');
        chartDiv.className = 'viz-chart';
        chartDiv.id = `${containerId}-chart`;
        chartDiv.style.width = '100%';
        chartDiv.style.height = '400px';
        container.appendChild(chartDiv);

        return container;
    },

    /**
     * Get icon HTML for view type
     */
    _getViewIcon(viewType) {
        const icons = {
            bar: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="20" x2="12" y2="4"></line><line x1="18" y1="20" x2="18" y2="10"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>',
            pie: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>',
            line: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>',
            table: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>'
        };
        return icons[viewType] || icons.table;
    },

    /**
     * Switch visualization view
     */
    switchView(containerId, viewType) {
        const container = document.getElementById(containerId);
        if (!container) return;

        // Update active button
        container.querySelectorAll('.viz-toggle-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === viewType);
        });

        // Get stored data and render new view
        const data = container._visualizationData;
        if (data) {
            this.renderVisualization(containerId, data.results, data.analysis, viewType);
        }
    },

    /**
     * Render appropriate visualization based on analysis
     */
    renderVisualization(containerId, results, analysis, forceView = null) {
        try {
            const container = document.getElementById(containerId);
            if (!container) {
                console.error('[Viz] Container not found:', containerId);
                return;
            }

            // Store data for view switching
            container._visualizationData = { results, analysis };

            const chartId = `${containerId}-chart`;
            const viewType = forceView || (analysis.type === 'multi' ? analysis.primary : analysis.type);

            // Get chart container
            const chartDiv = document.getElementById(chartId);
            if (!chartDiv) {
                console.error('[Viz] Chart div not found:', chartId);
                return;
            }

            // Dispose existing ECharts instance if it exists
            const existingInstance = echarts.getInstanceByDom(chartDiv);
            if (existingInstance) {
                existingInstance.dispose();
            }

            // Clear container content
            chartDiv.innerHTML = '';

            if (viewType === 'table') {
                this.renderTable(chartDiv, results, analysis);
            } else {
                // Initialize new ECharts instance
                const chart = echarts.init(chartDiv);

            switch (viewType) {
                case 'bar':
                    this.renderBarChart(chart, results, analysis);
                    break;
                case 'pie':
                    this.renderPieChart(chart, results, analysis);
                    break;
                case 'line':
                    this.renderLineChart(chart, results, analysis);
                    break;
            }

            // Store chart instance for future cleanup
            chartDiv._chartInstance = chart;

            // Make chart responsive
            const resizeHandler = () => {
                if (chart && !chart.isDisposed()) {
                    chart.resize();
                }
            };

            // Remove old resize listener if exists
            if (chartDiv._resizeHandler) {
                window.removeEventListener('resize', chartDiv._resizeHandler);
            }

            chartDiv._resizeHandler = resizeHandler;
            window.addEventListener('resize', resizeHandler);
            }
        } catch (error) {
            console.error('[Viz] Error rendering visualization:', error);
            console.error('[Viz] Error details:', error.message);
            console.error('[Viz] Data:', { results, analysis });
            const chartDiv = document.getElementById(`${containerId}-chart`);
            if (chartDiv) {
                chartDiv.innerHTML = `<div style="padding: 20px; color: #e74c3c; text-align: center;">
                    <strong>Visualization Error:</strong><br>${error.message}
                </div>`;
            }
        }
    },

    /**
     * Render bar chart
     */
    renderBarChart(chart, results, analysis) {
        // Limit chart data to 20 items for readability
        const maxChartItems = 20;
        const chartData = results.slice(0, maxChartItems);
        const isTruncated = results.length > maxChartItems;

        const labels = chartData.map(item => {
            const label = item[analysis.label];
            if (typeof label === 'string' && label.length > 50) {
                return label.substring(0, 47) + '...';
            }
            return String(label || 'Unknown');
        });

        const values = chartData.map(item => {
            const val = item[analysis.value];
            return typeof val === 'number' ? val : 0;
        });

        const option = {
            title: {
                text: isTruncated ? `Data Analysis (Top ${maxChartItems} of ${results.length})` : 'Data Analysis',
                subtext: isTruncated ? 'Switch to table view to see all results' : '',
                left: 'center',
                textStyle: { fontSize: 16, fontWeight: 'normal' },
                subtextStyle: { fontSize: 12, color: '#666' }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: (params) => {
                    const param = params[0];
                    const fullLabel = chartData[param.dataIndex][analysis.label];
                    return `${fullLabel}<br/>${param.marker} ${this._formatNumber(param.value)}`;
                }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: labels,
                axisLabel: {
                    interval: 0,
                    rotate: labels.length > 5 ? 45 : 0,
                    fontSize: 11
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    formatter: (value) => this._formatNumber(value, true)
                }
            },
            series: [{
                type: 'bar',
                data: values,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#6366f1' },
                        { offset: 1, color: '#8b5cf6' }
                    ])
                },
                label: {
                    show: chartData.length <= 10,
                    position: 'top',
                    formatter: (params) => this._formatNumber(params.value, true)
                }
            }]
        };

        chart.setOption(option);
    },

    /**
     * Render pie chart
     */
    renderPieChart(chart, results, analysis) {
        // Limit pie chart to 15 items for readability
        const maxChartItems = 15;
        const chartData = results.slice(0, maxChartItems);
        const isTruncated = results.length > maxChartItems;

        const data = chartData.map(item => ({
            name: String(item[analysis.label] || 'Unknown'),
            value: typeof item[analysis.value] === 'number' ? item[analysis.value] : 0
        }));

        const option = {
            title: {
                text: isTruncated ? `Distribution (Top ${maxChartItems} of ${results.length})` : 'Distribution',
                subtext: isTruncated ? 'Switch to table view to see all results' : '',
                left: 'center',
                textStyle: { fontSize: 16, fontWeight: 'normal' },
                subtextStyle: { fontSize: 12, color: '#666' }
            },
            tooltip: {
                trigger: 'item',
                formatter: (params) => {
                    return `${params.name}<br/>${params.marker} ${this._formatNumber(params.value)} (${params.percent}%)`;
                }
            },
            legend: {
                orient: 'vertical',
                right: 10,
                top: 'center',
                formatter: (name) => {
                    if (name.length > 30) {
                        return name.substring(0, 27) + '...';
                    }
                    return name;
                }
            },
            series: [{
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: true,
                itemStyle: {
                    borderRadius: 10,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: chartData.length <= 6,
                    formatter: (params) => {
                        return `${params.name}\n${params.percent}%`;
                    }
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 14,
                        fontWeight: 'bold'
                    }
                },
                data: data
            }]
        };

        chart.setOption(option);
    },

    /**
     * Render line chart (for time series)
     */
    renderLineChart(chart, results, analysis) {
        // Limit line chart to 20 items for readability
        const maxChartItems = 20;
        const chartData = results.slice(0, maxChartItems);
        const isTruncated = results.length > maxChartItems;

        const labels = chartData.map(item => String(item[analysis.label] || 'Unknown'));
        const values = chartData.map(item => {
            const val = item[analysis.value];
            return typeof val === 'number' ? val : 0;
        });

        const option = {
            title: {
                text: isTruncated ? `Trend Analysis (Top ${maxChartItems} of ${results.length})` : 'Trend Analysis',
                subtext: isTruncated ? 'Switch to table view to see all results' : '',
                left: 'center',
                textStyle: { fontSize: 16, fontWeight: 'normal' },
                subtextStyle: { fontSize: 12, color: '#666' }
            },
            tooltip: {
                trigger: 'axis',
                formatter: (params) => {
                    const param = params[0];
                    return `${param.name}<br/>${param.marker} ${this._formatNumber(param.value)}`;
                }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: labels,
                boundaryGap: false
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    formatter: (value) => this._formatNumber(value, true)
                }
            },
            series: [{
                type: 'line',
                data: values,
                smooth: true,
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(99, 102, 241, 0.3)' },
                        { offset: 1, color: 'rgba(99, 102, 241, 0.05)' }
                    ])
                },
                lineStyle: {
                    color: '#6366f1',
                    width: 2
                },
                itemStyle: {
                    color: '#6366f1'
                },
                label: {
                    show: chartData.length <= 12,
                    position: 'top',
                    formatter: (params) => this._formatNumber(params.value, true)
                }
            }]
        };

        chart.setOption(option);
    },

    /**
     * Render table view
     */
    renderTable(container, results, analysis) {
        // Clear container
        container.innerHTML = '';

        // Create scrollable wrapper for table
        const tableWrapper = document.createElement('div');
        tableWrapper.className = 'viz-table-wrapper';
        tableWrapper.style.maxHeight = '400px';
        tableWrapper.style.overflowY = 'auto';
        tableWrapper.style.overflowX = 'auto';

        const table = document.createElement('table');
        table.className = 'viz-table';

        // Create header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');

        const columns = analysis.columns || Object.keys(results[0]);

        columns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = this._inferColumnName(col, results);
            th.style.textAlign = 'left';  // Consistent left alignment for all headers
            headerRow.appendChild(th);
        });

        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Create body
        const tbody = document.createElement('tbody');
        results.slice(0, 100).forEach((row, idx) => {
            const tr = document.createElement('tr');
            tr.className = idx % 2 === 0 ? 'even' : 'odd';

            columns.forEach(col => {
                const td = document.createElement('td');
                const value = row[col];

                if (typeof value === 'number') {
                    td.textContent = this._formatNumber(value);
                    td.style.textAlign = 'left';  // Consistent left alignment
                } else if (value === null || value === undefined) {
                    td.textContent = '-';
                    td.style.color = '#999';
                    td.style.textAlign = 'left';
                } else if (Array.isArray(value)) {
                    // Handle arrays (especially arrays of objects)
                    td.innerHTML = this._formatArrayValue(value);
                    td.style.verticalAlign = 'top';
                    td.style.textAlign = 'left';
                } else if (typeof value === 'object') {
                    // Handle nested objects
                    td.innerHTML = this._formatObjectValue(value);
                    td.style.verticalAlign = 'top';
                    td.style.textAlign = 'left';
                } else {
                    // Truncate long text values
                    const strValue = String(value);
                    if (strValue.length > 100) {
                        td.textContent = strValue.substring(0, 97) + '...';
                        td.title = strValue;  // Show full text on hover
                    } else {
                        td.textContent = strValue;
                    }
                    td.style.textAlign = 'left';
                }

                tr.appendChild(td);
            });

            tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        tableWrapper.appendChild(table);

        // Show count if truncated
        if (results.length > 100) {
            const note = document.createElement('div');
            note.className = 'viz-table-note';
            note.textContent = `Showing 100 of ${results.length} results`;
            container.appendChild(note);
        }

        container.appendChild(tableWrapper);
    },

    /**
     * Infer a better column name based on the data
     */
    _inferColumnName(columnName, results) {
        // If not _id, use default formatting
        if (columnName !== '_id') {
            return columnName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }

        // For _id column, try to infer based on the actual data
        if (results && results.length > 0) {
            const sampleValue = results[0][columnName];
            const strValue = String(sampleValue);

            // Check for fiscal year patterns (e.g., "2012-2013", "FY2012", "2012")
            if (/^\d{4}[-/]\d{4}$/.test(strValue)) {
                return 'Fiscal Year';
            }
            if (/^FY\s*\d{4}/i.test(strValue)) {
                return 'Fiscal Year';
            }
            if (/^\d{4}$/.test(strValue)) {
                // Could be year, fiscal year, or just a number - check if it looks like a year
                const year = parseInt(strValue);
                if (year >= 1900 && year <= 2100) {
                    return 'Year';
                }
            }

            // Check for date patterns
            if (/^\d{4}-\d{2}-\d{2}/.test(strValue)) {
                return 'Date';
            }

            // Check for month patterns
            if (/^(january|february|march|april|may|june|july|august|september|october|november|december)/i.test(strValue)) {
                return 'Month';
            }

            // Check for quarter patterns
            if (/^Q[1-4]|quarter\s*[1-4]/i.test(strValue)) {
                return 'Quarter';
            }

            // Check if all values look like department/category names (longer strings)
            if (strValue.length > 15 && /[a-z]/i.test(strValue)) {
                return 'Category';
            }

            // Check if it looks like a name or title
            if (strValue.length > 5 && strValue.includes(' ') && /^[A-Z]/.test(strValue)) {
                return 'Name';
            }
        }

        // Default fallback for _id
        return 'Category';
    },

    /**
     * Format number with commas and optional abbreviation
     */
    _formatNumber(num, abbreviate = false) {
        if (typeof num !== 'number') return String(num);

        if (abbreviate) {
            let value, suffix;
            if (Math.abs(num) >= 1e12) {
                value = num / 1e12;
                suffix = 'T';
            } else if (Math.abs(num) >= 1e9) {
                value = num / 1e9;
                suffix = 'B';
            } else if (Math.abs(num) >= 1e6) {
                value = num / 1e6;
                suffix = 'M';
            } else if (Math.abs(num) >= 1e3) {
                value = num / 1e3;
                suffix = 'K';
            } else {
                // No abbreviation needed
                return num % 1 === 0 ? num.toString() : num.toFixed(1);
            }

            // Only show decimal if it's not a whole number
            if (value % 1 === 0) {
                return value.toFixed(0) + suffix;
            } else {
                return value.toFixed(1) + suffix;
            }
        }

        if (Math.abs(num) >= 100) {
            return num.toLocaleString('en-US', { maximumFractionDigits: 0 });
        }

        return num.toLocaleString('en-US', { maximumFractionDigits: 2 });
    },

    /**
     * Format array values for table display
     */
    _formatArrayValue(arr) {
        if (!arr || arr.length === 0) return '-';

        // If array contains objects, format each as a bullet point
        if (typeof arr[0] === 'object' && arr[0] !== null) {
            const items = arr.map(obj => {
                // Format each object's key-value pairs
                const parts = [];
                for (const [key, val] of Object.entries(obj)) {
                    if (val !== null && val !== undefined) {
                        let formattedVal = val;
                        if (typeof val === 'number') {
                            formattedVal = this._formatNumber(val);
                        }
                        parts.push(`<strong>${key}:</strong> ${formattedVal}`);
                    }
                }
                return `<li style="margin-bottom: 8px;">${parts.join(', ')}</li>`;
            }).join('');

            return `<ul style="margin: 0; padding-left: 20px; list-style-type: disc;">${items}</ul>`;
        } else {
            // Simple array of primitives
            return arr.map(item => {
                if (typeof item === 'number') {
                    return this._formatNumber(item);
                }
                return String(item);
            }).join(', ');
        }
    },

    /**
     * Format object values for table display
     */
    _formatObjectValue(obj) {
        if (!obj) return '-';

        const parts = [];
        for (const [key, val] of Object.entries(obj)) {
            if (val !== null && val !== undefined) {
                let formattedVal = val;
                if (typeof val === 'number') {
                    formattedVal = this._formatNumber(val);
                } else if (Array.isArray(val)) {
                    formattedVal = this._formatArrayValue(val);
                } else if (typeof val === 'object') {
                    // Nested object - just show JSON
                    formattedVal = JSON.stringify(val);
                }
                parts.push(`<div><strong>${key}:</strong> ${formattedVal}</div>`);
            }
        }

        return parts.join('');
    }
};

// Export to window for global access

console.log('[Visualizations] Module loaded successfully');
