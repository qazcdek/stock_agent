<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue';
import Chart from 'chart.js/auto';
import {
  activeTicker,
  newTickerInput,
  tickerCorrection,
  watchlist,
  systemLogs,
  blackboard,
  addWatchlistTicker,
  removeWatchlistTicker,
  onTickerInput,
  applyTickerCorrection,
  clearLogs,
  fetchWatchlist,
  dbData,
  simReport,
  automatedMode,
  formatNumber,
  formatCurrency,
  viewCurrency,
  formatDateTime,
  fetchPrediction,
  chartCallbacks,
  apiBase
} from '../store/tradingStore.js';

// Chart instances
let priceChart = null;
let volumeChart = null;

// Trend lines for technical analysis
const trendLines = ref([]);
let activeLine = null;

// Context menu for trend line options
const showContextMenu = ref(false);
const contextMenuPos = ref({ x: 0, y: 0 });
const magnetMode = ref(true); // 추세선 자석모드 (기본 ON)
const showSma5 = ref(true);  // SMA 5선 보이기 여부
const showSma20 = ref(true); // SMA 20선 보이기 여부

function toggleSma5() {
  showSma5.value = !showSma5.value;
  if (priceChart) {
    priceChart.setDatasetVisibility(1, showSma5.value);
    priceChart.update();
  }
}

function toggleSma20() {
  showSma20.value = !showSma20.value;
  if (priceChart) {
    priceChart.setDatasetVisibility(2, showSma20.value);
    priceChart.update();
  }
}

// Slicing states for mouse zoom and scroll
let rawChartData = [];
const zoomRange = ref(50);
const scrollOffset = ref(0);
const totalCandles = ref(0);

function removeLastTrendLine() {
  if (trendLines.value.length > 0) {
    trendLines.value.pop();
    if (priceChart) {
      priceChart.update('none');
    }
  }
  showContextMenu.value = false;
}

function removeAllTrendLines() {
  trendLines.value = [];
  activeLine = null;
  if (priceChart) {
    priceChart.options.plugins.tooltip.enabled = true;
    priceChart.update('none');
  }
  showContextMenu.value = false;
}

function handleGlobalMouseUp(e) {
  if (!priceChart) return;
  if (e.button === 0 && activeLine) {
    trendLines.value.push(activeLine);
    activeLine = null;
    priceChart.options.plugins.tooltip.enabled = true;
    priceChart.update('none');
  }
}

function handleGlobalClick() {
  showContextMenu.value = false;
}

// Cold Start State
const coldStartStatus = ref(null);
const isSeeding = ref(false);
let pollInterval = null;

async function checkColdStartHealth() {
  try {
    const res = await fetch(`${apiBase}/api/health/cold-start`);
    if (res.ok) {
      coldStartStatus.value = await res.json();
      isSeeding.value = coldStartStatus.value.is_seeding;
      
      if (isSeeding.value && !pollInterval) {
        pollInterval = setInterval(checkColdStartHealth, 2000);
      } else if (!isSeeding.value && pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
    }
  } catch (e) {
    console.error('Failed to check cold start health', e);
  }
}

async function triggerBulkSeeding() {
  if (isSeeding.value) return;
  isSeeding.value = true;
  if (!pollInterval) {
    pollInterval = setInterval(checkColdStartHealth, 2000);
  }
  try {
    const res = await fetch(`${apiBase}/api/health/cold-start/trigger`, { method: 'POST' });
    if (!res.ok) {
      console.error('Failed to trigger bulk seeding');
      isSeeding.value = false;
    }
  } catch (e) {
    console.error('Failed to trigger bulk seeding', e);
    isSeeding.value = false;
  }
}

// Select ticker action
function selectTicker(ticker) {
  activeTicker.value = ticker;
  fetchChartData(ticker);
  fetchPrediction(ticker);
}

// Fetch historical chart data
async function fetchChartData(ticker) {
  try {
    // Reset any temporary lines on ticker change
    trendLines.value = [];
    activeLine = null;
    const res = await fetch(`${apiBase}/api/charts/${encodeURIComponent(ticker)}`);
    const chartData = await res.json();
    
    if (!chartData || chartData.length === 0) {
      rawChartData = [];
      totalCandles.value = 0;
      if (priceChart) {
        priceChart.destroy();
        priceChart = null;
      }
      if (volumeChart) {
        volumeChart.destroy();
        volumeChart = null;
      }
      return;
    }
    
    // Store master arrays
    rawChartData = chartData;
    totalCandles.value = rawChartData.length;
    
    // Default to show full chart window initially
    zoomRange.value = rawChartData.length;
    scrollOffset.value = 0;

    // Build the initial chart panels
    const sliced = rawChartData;
    const labels = sliced.map(d => {
      const barDate = new Date(d.timestamp);
      const month = String(barDate.getMonth() + 1).padStart(2, '0');
      const day = String(barDate.getDate()).padStart(2, '0');
      return d.timestamp.includes('T00:00:00') 
        ? `${month}/${day}` 
        : `${month}/${day} ${barDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    });
    
    const openPrices = sliced.map(d => d.open);
    const highPrices = sliced.map(d => d.high);
    const lowPrices = sliced.map(d => d.low);
    const closePrices = sliced.map(d => d.close);
    const volumes = sliced.map(d => d.volume);
    const sma5 = sliced.map(d => d.sma_5);
    const sma20 = sliced.map(d => d.sma_20);

    renderPriceChart(labels, openPrices, highPrices, lowPrices, closePrices, volumes, sma5, sma20);
  } catch (e) {
    console.error('Failed to load chart data', e);
  }
}

// Local plugin to draw candlestick wicks (High / Low vertical lines)
const candlestickWicksPlugin = {
  id: 'candlestickWicks',
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    chart.data.datasets.forEach((dataset, datasetIndex) => {
      if (dataset.label === 'Candlestick' && dataset.candlesticks) {
        const meta = chart.getDatasetMeta(datasetIndex);
        meta.data.forEach((barElement, index) => {
          const candle = dataset.candlesticks[index];
          if (!candle) return;
          
          const x = barElement.x;
          const yScale = chart.scales.y;
          const yHigh = yScale.getPixelForValue(candle.h);
          const yLow = yScale.getPixelForValue(candle.l);
          const yTop = Math.min(yScale.getPixelForValue(candle.o), yScale.getPixelForValue(candle.c));
          const yBottom = Math.max(yScale.getPixelForValue(candle.o), yScale.getPixelForValue(candle.c));
          
          ctx.save();
          // 상승캔들은 빨간색 (#EF4444), 하락캔들은 파란색 (#3B82F6)
          ctx.strokeStyle = candle.c >= candle.o ? '#EF4444' : '#3B82F6';
          ctx.lineWidth = 0.75;
          
          // Draw high wick (from High to top of the candle body)
          ctx.beginPath();
          ctx.moveTo(x, yHigh);
          ctx.lineTo(x, yTop);
          ctx.stroke();
          
          // Draw low wick (from Low to bottom of the candle body)
          ctx.beginPath();
          ctx.moveTo(x, yLow);
          ctx.lineTo(x, yBottom);
          ctx.stroke();
          
          ctx.restore();
        });
      }
    });
  }
};

// Nice scale calculation helper:
// Lock axis min to largest multiple of step size smaller than 80% of minVal
function getNiceScale(minVal, maxVal) {
  const targetMin = minVal * 0.98;
  const targetMax = maxVal * 1.02;
  const range = targetMax - targetMin;
  const tempStep = range / 6;
  const magnitude = Math.pow(10, Math.floor(Math.log10(tempStep)));
  const normalizedStep = tempStep / magnitude;
  
  let stepSize;
  if (normalizedStep < 1.5) stepSize = 1 * magnitude;
  else if (normalizedStep < 3) stepSize = 2 * magnitude;
  else if (normalizedStep < 7.5) stepSize = 5 * magnitude;
  else stepSize = 10 * magnitude;
  
  const scaleMin = Math.floor(targetMin / stepSize) * stepSize;
  const scaleMax = Math.ceil(targetMax / stepSize) * stepSize;
  
  return {
    min: scaleMin,
    max: scaleMax,
    stepSize: stepSize
  };
}

const trendLinesPlugin = {
  id: 'trendLines',
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    const xAxis = chart.scales.x;
    const yAxis = chart.scales.y;
    if (!xAxis || !yAxis) return;
    
    ctx.save();
    ctx.strokeStyle = '#FFFFFF'; // Pure white
    ctx.lineWidth = 1;
    ctx.setLineDash([]);
    
    // High-precision sub-pixel coordinate interpolator to bypass CategoryScale snapping
    const p0 = xAxis.getPixelForValue(0);
    const p1 = xAxis.getPixelForValue(1);
    const spacing = p1 - p0;
    const getXPixel = (val) => p0 + (val - scrollOffset.value) * spacing;
    
    // 1. Draw completed trend lines (with viewport scroll offset calculations)
    trendLines.value.forEach(line => {
      const startX = getXPixel(line.startX);
      const startY = yAxis.getPixelForValue(line.startY);
      const endX = getXPixel(line.endX);
      const endY = yAxis.getPixelForValue(line.endY);
      
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();
    });
    
    // 2. Draw active line in progress
    if (activeLine) {
      const startX = getXPixel(activeLine.startX);
      const startY = yAxis.getPixelForValue(activeLine.startY);
      const endX = getXPixel(activeLine.endX);
      const endY = yAxis.getPixelForValue(activeLine.endY);
      
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.65)'; // Semi-transparent white
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();
    }
    
    ctx.restore();
  }
};

// High-performance data slice and redraw coordinator
function redrawSlicing() {
  if (!priceChart || !volumeChart || rawChartData.length === 0) return;

  const sliced = rawChartData.slice(scrollOffset.value, scrollOffset.value + zoomRange.value);

  const labels = sliced.map(d => {
    const barDate = new Date(d.timestamp);
    const month = String(barDate.getMonth() + 1).padStart(2, '0');
    const day = String(barDate.getDate()).padStart(2, '0');
    return d.timestamp.includes('T00:00:00') 
      ? `${month}/${day}` 
      : `${month}/${day} ${barDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  });

  const openPrices = sliced.map(d => d.open);
  const highPrices = sliced.map(d => d.high);
  const lowPrices = sliced.map(d => d.low);
  const closePrices = sliced.map(d => d.close);
  const volumes = sliced.map(d => d.volume);
  const sma5 = sliced.map(d => d.sma_5);
  const sma20 = sliced.map(d => d.sma_20);

  // Update Price Candlestick datasets in-place
  priceChart.data.labels = labels;
  priceChart.data.datasets[0].data = closePrices.map((cp, idx) => [openPrices[idx], cp]);
  priceChart.data.datasets[0].candlesticks = closePrices.map((cp, idx) => ({
    o: openPrices[idx],
    h: highPrices[idx],
    l: lowPrices[idx],
    c: cp
  }));
  
  const candleColors = closePrices.map((cp, idx) => cp >= openPrices[idx] ? '#EF4444' : '#3B82F6');
  priceChart.data.datasets[0].backgroundColor = candleColors;
  priceChart.data.datasets[0].borderColor = candleColors;

  priceChart.data.datasets[1].data = sma5;
  priceChart.data.datasets[2].data = sma20;

  // Recalculate dynamic Nice scale bounds for the active sliced window
  const minLow = Math.min(...lowPrices);
  const maxHigh = Math.max(...highPrices);
  const niceScale = getNiceScale(minLow, maxHigh);
  
  priceChart.options.scales.y.min = niceScale.min;
  priceChart.options.scales.y.max = niceScale.max;
  priceChart.options.scales.y.ticks.stepSize = niceScale.stepSize;

  if (priceChart.scales && priceChart.scales.y) {
    priceChart.scales.y.options.min = niceScale.min;
    priceChart.scales.y.options.max = niceScale.max;
    if (priceChart.scales.y.options.ticks) {
      priceChart.scales.y.options.ticks.stepSize = niceScale.stepSize;
    }
  }

  // Update Volume dataset in-place
  volumeChart.data.labels = labels;
  volumeChart.data.datasets[0].data = volumes;
  
  const volumeColors = closePrices.map((cp, idx) => cp >= openPrices[idx] ? 'rgba(239, 68, 68, 0.35)' : 'rgba(59, 130, 246, 0.35)');
  const volumeBorderColors = closePrices.map((cp, idx) => cp >= openPrices[idx] ? '#EF4444' : '#3B82F6');
  volumeChart.data.datasets[0].backgroundColor = volumeColors;
  volumeChart.data.datasets[0].borderColor = volumeBorderColors;

  priceChart.setDatasetVisibility(1, showSma5.value);
  priceChart.setDatasetVisibility(2, showSma20.value);
  priceChart.update('none');
  volumeChart.update('none');
}

// Render chart on canvas
function renderPriceChart(labels, openPrices, highPrices, lowPrices, closePrices, volumes, sma5, sma20) {
  const priceCtx = document.getElementById('dashboard-price-chart');
  const volumeCtx = document.getElementById('dashboard-volume-chart');
  if (!priceCtx || !volumeCtx) return;
  
  if (priceChart) {
    priceChart.destroy();
  }
  if (volumeChart) {
    volumeChart.destroy();
  }

  // Pre-calculate visual styling color schemes: 상승 빨간색 (#EF4444), 하락 파란색 (#3B82F6)
  const candleColors = closePrices.map((cp, idx) => cp >= openPrices[idx] ? '#EF4444' : '#3B82F6');
  const volumeColors = closePrices.map((cp, idx) => cp >= openPrices[idx] ? 'rgba(239, 68, 68, 0.35)' : 'rgba(59, 130, 246, 0.35)');
  const volumeBorderColors = closePrices.map((cp, idx) => cp >= openPrices[idx] ? '#EF4444' : '#3B82F6');

  // Lock left Y-axis width on both charts to 80px to align vertical grid lines
  const fixedYAxisWidth = 80;

  // Calculate dynamic nice scales for the Price chart Y-axis
  const minLow = Math.min(...lowPrices);
  const maxHigh = Math.max(...highPrices);
  const niceScale = getNiceScale(minLow, maxHigh);

  // 1. Price Chart Instantiation
  priceChart = new Chart(priceCtx.getContext('2d'), {
    plugins: [candlestickWicksPlugin, trendLinesPlugin],
    data: {
      labels: labels,
      datasets: [
        {
          type: 'bar',
          label: 'Candlestick',
          data: closePrices.map((cp, idx) => [openPrices[idx], cp]),
          candlesticks: closePrices.map((cp, idx) => ({
            o: openPrices[idx],
            h: highPrices[idx],
            l: lowPrices[idx],
            c: cp
          })),
          backgroundColor: candleColors,
          borderColor: candleColors,
          borderWidth: 1,
          borderRadius: 0,
          barPercentage: 0.7,
          grouped: false,
          yAxisID: 'y'
        },
        {
          type: 'line',
          label: 'SMA 5',
          data: sma5,
          borderColor: '#34D399',
          fill: false,
          tension: 0.1,
          borderWidth: 1.5,
          pointRadius: 0,
          yAxisID: 'y',
          hidden: !showSma5.value
        },
        {
          type: 'line',
          label: 'SMA 20',
          data: sma20,
          borderColor: '#F59E0B',
          fill: false,
          tension: 0.1,
          borderWidth: 1.5,
          pointRadius: 0,
          yAxisID: 'y',
          hidden: !showSma20.value
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      layout: {
        padding: { left: 0, right: 10, top: 5, bottom: 5 }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.03)' },
          ticks: { display: false } // Date labels are shown on the volume chart underneath
        },
        y: {
          position: 'left',
          min: niceScale.min,
          max: niceScale.max,
          grid: { color: 'rgba(255, 255, 255, 0.03)' },
          ticks: { 
            color: '#64748B', 
            font: { size: 10 },
            stepSize: niceScale.stepSize,
            callback: function(value) {
              return formatCurrency(value, activeTicker.value);
            }
          },
          afterFit: (scale) => {
            scale.width = fixedYAxisWidth;
          }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.65)',
          titleColor: '#F8FAFC',
          bodyColor: '#E2E8F0',
          borderColor: 'rgba(255, 255, 255, 0.08)',
          borderWidth: 1,
          callbacks: {
            label: function(context) {
              const dataset = context.dataset;
              const index = context.dataIndex;
              if (dataset.label === 'Candlestick' && dataset.candlesticks) {
                const candle = dataset.candlesticks[index];
                if (candle) {
                  return [
                    `Open:  ${formatCurrency(candle.o, activeTicker.value)}`,
                    `High:  ${formatCurrency(candle.h, activeTicker.value)}`,
                    `Low:   ${formatCurrency(candle.l, activeTicker.value)}`,
                    `Close: ${formatCurrency(candle.c, activeTicker.value)}`
                  ];
                }
              }
              return `${dataset.label}: ${formatCurrency(context.raw, activeTicker.value)}`;
            }
          }
        }
      }
    }
  });

  // 2. Volume Chart Instantiation
  volumeChart = new Chart(volumeCtx.getContext('2d'), {
    data: {
      labels: labels,
      datasets: [
        {
          type: 'bar',
          label: 'Volume',
          data: volumes,
          backgroundColor: volumeColors,
          borderColor: volumeBorderColors,
          borderWidth: 1,
          borderRadius: 1,
          barPercentage: 0.5,
          grouped: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      layout: {
        padding: { left: 0, right: 10, top: 0, bottom: 5 }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.03)' },
          ticks: { color: '#64748B', font: { size: 10 } }
        },
        y: {
          position: 'left',
          grid: { color: 'rgba(255, 255, 255, 0.03)' },
          ticks: { 
            color: '#64748B', 
            font: { size: 9 },
            callback: function(value) {
              return formatNumber(value);
            }
          },
          afterFit: (scale) => {
            scale.width = fixedYAxisWidth;
          }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.65)',
          titleColor: '#F8FAFC',
          bodyColor: '#E2E8F0',
          borderColor: 'rgba(255, 255, 255, 0.08)',
          borderWidth: 1,
          callbacks: {
            label: function(context) {
              return `Volume: ${formatNumber(context.raw)}`;
            }
          }
        }
      }
    }
  });
}

// Live WebSocket chart updater
function updateLiveChart(bar) {
  if (rawChartData.length === 0) return;
  
  const barDate = new Date(bar.timestamp);
  const month = String(barDate.getMonth() + 1).padStart(2, '0');
  const day = String(barDate.getDate()).padStart(2, '0');
  const dateStr = bar.timestamp.includes('T00:00:00') 
    ? `${month}/${day}` 
    : `${month}/${day} ${barDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  
  const lastIndex = rawChartData.length - 1;
  const lastBar = rawChartData[lastIndex];
  
  const barDateLast = new Date(lastBar.timestamp);
  const monthLast = String(barDateLast.getMonth() + 1).padStart(2, '0');
  const dayLast = String(barDateLast.getDate()).padStart(2, '0');
  const lastLabel = lastBar.timestamp.includes('T00:00:00')
    ? `${monthLast}/${dayLast}`
    : `${monthLast}/${dayLast} ${barDateLast.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

  const isSameDay = lastLabel === dateStr || lastLabel.includes(dateStr) ||
    (lastLabel.split(' ')[0] === dateStr.split(' ')[0] && lastLabel.includes(':') && dateStr.includes(':'));

  // Detect if user is scrolled fully to the latest data
  const wasAtEnd = (scrollOffset.value + zoomRange.value) >= rawChartData.length;

  if (isSameDay) {
    // Update the last candle in master array
    rawChartData[lastIndex] = {
      ...rawChartData[lastIndex],
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
      volume: bar.volume
    };

    // Recalculate SMAs
    const closePrices = rawChartData.map(c => c.close);
    const start5 = Math.max(0, lastIndex - 4);
    const sub5 = closePrices.slice(start5, lastIndex + 1);
    rawChartData[lastIndex].sma_5 = sub5.reduce((a, b) => a + b, 0) / sub5.length;
    
    const start20 = Math.max(0, lastIndex - 19);
    const sub20 = closePrices.slice(start20, lastIndex + 1);
    rawChartData[lastIndex].sma_20 = sub20.reduce((a, b) => a + b, 0) / sub20.length;
  } else {
    // Compute next SMAs
    const closePrices = rawChartData.map(c => c.close);
    closePrices.push(bar.close);
    const nextIdx = rawChartData.length;

    const start5 = Math.max(0, nextIdx - 4);
    const sub5 = closePrices.slice(start5, nextIdx + 1);
    const nextSma5 = sub5.reduce((a, b) => a + b, 0) / sub5.length;
    
    const start20 = Math.max(0, nextIdx - 19);
    const sub20 = closePrices.slice(start20, nextIdx + 1);
    const nextSma20 = sub20.reduce((a, b) => a + b, 0) / sub20.length;

    // Append to master list
    rawChartData.push({
      timestamp: bar.timestamp,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
      volume: bar.volume,
      sma_5: nextSma5,
      sma_20: nextSma20
    });

    // Roll master list to keep max 50 items
    if (rawChartData.length > 50) {
      rawChartData.shift();
      
      // Shift absolute trend lines indices back by 1 to match the rolling data
      trendLines.value = trendLines.value.map(line => ({
        ...line,
        startX: line.startX - 1,
        endX: line.endX - 1
      })).filter(line => line.startX >= 0 || line.endX >= 0);
    }

    totalCandles.value = rawChartData.length;

    // Dynamic viewport scrolling behavior snappings
    if (wasAtEnd) {
      scrollOffset.value = Math.max(0, rawChartData.length - zoomRange.value);
    } else {
      if (rawChartData.length > 50) {
        scrollOffset.value = Math.max(0, scrollOffset.value - 1);
      }
    }
  }

  redrawSlicing();
}

// Event receiver registration
function onRawDataCollected(data) {
  if (data.ticker === activeTicker.value) {
    updateLiveChart(data.bar);
  }
}

// Opinion coloring
function getActionBadgeClass(action) {
  if (action === 'BUY') return 'bg-brandGreen/15 text-brandGreen border border-brandGreen/25';
  if (action === 'SELL') return 'bg-brandRed/15 text-brandRed border border-brandRed/25';
  return 'bg-slate-800 text-slate-400 border border-slate-700/50';
}

onMounted(async () => {
  chartCallbacks.push(onRawDataCollected);
  await checkColdStartHealth();
  await fetchWatchlist();
  if (watchlist.value.length > 0) {
    if (!watchlist.value.includes(activeTicker.value)) {
      activeTicker.value = watchlist.value[0];
    }
    fetchChartData(activeTicker.value);
    fetchPrediction(activeTicker.value);
  }

  // Setup interactive drag-and-drop trend line listeners on Price Canvas
  const priceCtx = document.getElementById('dashboard-price-chart');
  if (priceCtx) {
    priceCtx.addEventListener('mousedown', (e) => {
      if (!priceChart) return;
      if (e.button === 0) { // Left-click down
        const xAxis = priceChart.scales.x;
        const yAxis = priceChart.scales.y;
        if (!xAxis || !yAxis) return;
        const area = priceChart.chartArea;
        
        // Ensure starting point is inside the plotting bounds
        if (e.offsetX >= area.left && e.offsetX <= area.right && e.offsetY >= area.top && e.offsetY <= area.bottom) {
          const rawIdx = xAxis.getValueForPixel(e.offsetX);
          const activeIndex = magnetMode.value
            ? Math.max(0, Math.min(zoomRange.value - 1, Math.round(rawIdx)))
            : Math.max(0, Math.min(zoomRange.value - 1, rawIdx));
          const startXVal = activeIndex + scrollOffset.value; // Absolute index!
          const startYVal = yAxis.getValueForPixel(e.offsetY);
          
          activeLine = {
            startX: startXVal,
            startY: startYVal,
            endX: startXVal,
            endY: startYVal
          };

          // Temporarily disable the tooltip box during drag-and-drop drawing
          priceChart.options.plugins.tooltip.enabled = false;
          priceChart.setActiveElements([]);
          priceChart.update('none');
        }
      }
    });

    priceCtx.addEventListener('mousemove', (e) => {
      if (!priceChart || !activeLine) return;
      const xAxis = priceChart.scales.x;
      const yAxis = priceChart.scales.y;
      if (!xAxis || !yAxis) return;
      
      const rawIdx = xAxis.getValueForPixel(e.offsetX);
      const activeIndex = magnetMode.value
        ? Math.max(0, Math.min(zoomRange.value - 1, Math.round(rawIdx)))
        : Math.max(0, Math.min(zoomRange.value - 1, rawIdx));
      activeLine.endX = activeIndex + scrollOffset.value; // Absolute index!
      activeLine.endY = yAxis.getValueForPixel(e.offsetY); // Allow free horizontal and vertical drawing
      
      priceChart.update('none');
    });

    priceCtx.addEventListener('contextmenu', (e) => {
      e.preventDefault(); // Prevent native right-click popup
      
      // If we are actively drawing a trend line, right-click cancels the action
      if (activeLine) {
        activeLine = null;
        priceChart.options.plugins.tooltip.enabled = true;
        priceChart.update('none');
        return;
      }
      
      if (!priceChart || trendLines.value.length === 0) return;
      
      // Position the custom context menu at viewport coordinates
      contextMenuPos.value = {
        x: e.clientX,
        y: e.clientY
      };
      showContextMenu.value = true;
    });

    // Setup interactive wheel zoom centered under mouse cursor
    priceCtx.addEventListener('wheel', (e) => {
      e.preventDefault();
      if (!priceChart || rawChartData.length === 0) return;

      const xAxis = priceChart.scales.x;
      if (!xAxis) return;
      const area = priceChart.chartArea;

      // Only zoom if cursor is inside chart area bounds
      if (e.offsetX < area.left || e.offsetX > area.right || e.offsetY < area.top || e.offsetY > area.bottom) {
        return;
      }

      const activeIndex = xAxis.getValueForPixel(e.offsetX); // Sliced index (0 to zoomRange-1)
      const absoluteIndex = activeIndex + scrollOffset.value; // Absolute index in master rawChartData

      const zoomIn = e.deltaY < 0;
      const minRange = 10;
      const maxRange = rawChartData.length;

      let newRange = zoomRange.value;
      if (zoomIn) {
        newRange = Math.max(minRange, zoomRange.value - 4);
      } else {
        newRange = Math.min(maxRange, zoomRange.value + 4);
      }

      if (newRange === zoomRange.value) return;

      // Anchored scroll offset calculations to lock cursor focus
      const fraction = activeIndex / zoomRange.value;
      let newOffset = Math.round(absoluteIndex - fraction * newRange);

      newOffset = Math.max(0, Math.min(rawChartData.length - newRange, newOffset));

      zoomRange.value = newRange;
      scrollOffset.value = newOffset;

      redrawSlicing();
    });

    // Register global window event listeners cleanly
    window.addEventListener('mouseup', handleGlobalMouseUp);
    window.addEventListener('click', handleGlobalClick);
  }
});

onUnmounted(() => {
  const index = chartCallbacks.indexOf(onRawDataCollected);
  if (index > -1) {
    chartCallbacks.splice(index, 1);
  }
  if (priceChart) {
    priceChart.destroy();
    priceChart = null;
  }
  if (volumeChart) {
    volumeChart.destroy();
    volumeChart = null;
  }
  if (pollInterval) {
    clearInterval(pollInterval);
  }
  // Remove global window event listeners to prevent memory leaks
  window.removeEventListener('mouseup', handleGlobalMouseUp);
  window.removeEventListener('click', handleGlobalClick);
});

// Watch active ticker to redraw
watch(activeTicker, (newTicker) => {
  fetchChartData(newTicker);
  fetchPrediction(newTicker);
});
</script>

<template>
  <div class="flex flex-col gap-6 relative">

    <!-- Custom Trend Line Context Menu -->
    <div
      v-if="showContextMenu"
      :style="{ top: contextMenuPos.y + 'px', left: contextMenuPos.x + 'px' }"
      class="fixed z-50 bg-slate-950/95 border border-slate-800/80 rounded-xl shadow-2xl p-1.5 flex flex-col min-w-[180px] backdrop-blur-md font-sans text-xs"
    >
      <button
        @click="removeLastTrendLine"
        class="flex items-center gap-2 px-3 py-2 text-left rounded-lg text-slate-200 hover:bg-slate-900 hover:text-white transition-all cursor-pointer font-medium"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 text-brandGold" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M3 12l6.414 6.414a2 2 0 001.414.586H19a2 2 0 002-2V7a2 2 0 00-2-2h-8.172a2 2 0 00-1.414.586L3 12z" />
        </svg>
        <span>최근 선 지우기 (Undo)</span>
      </button>
      <button
        @click="removeAllTrendLines"
        class="flex items-center gap-2 px-3 py-2 text-left rounded-lg text-brandRed hover:bg-red-950/20 transition-all cursor-pointer font-medium"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 text-brandRed" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
        <span>모든 선 지우기 (Clear All)</span>
      </button>
    </div>

    <!-- Cold Start Banner -->
    <div v-if="coldStartStatus?.requires_bulk_update || isSeeding" class="bg-brandGold/10 border border-brandGold/30 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-brandGold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <h4 class="text-brandGold font-bold font-outfit">
            <span v-if="isSeeding">데이터 수집 중... ({{ coldStartStatus?.seeding_progress?.completed || 0 }} / {{ coldStartStatus?.seeding_progress?.total || coldStartStatus?.deficient_count }})</span>
            <span v-else>초기 데이터가 부족합니다 (Cold Start 감지)</span>
          </h4>
          <p class="text-sm text-brandGold/80 mt-1">
            <span v-if="isSeeding">현재 <strong>{{ coldStartStatus?.seeding_progress?.current_ticker || '대기중' }}</strong> 데이터 수집 진행 중입니다. 백그라운드에서 자동 처리됩니다.</span>
            <span v-else>시스템 초기화 혹은 유니버스 변경으로 인해 총 {{ coldStartStatus.deficient_count }} 종목에 대한 과거 주가 데이터 수집이 필요합니다.</span>
          </p>
        </div>
      </div>
      <button 
        @click="triggerBulkSeeding" 
        :disabled="isSeeding"
        class="shrink-0 bg-brandGold text-slate-900 hover:bg-yellow-400 font-bold px-5 py-2.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      >
        <svg v-if="isSeeding" class="animate-spin h-4 w-4 text-slate-900" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>{{ isSeeding ? '업데이트 진행중' : '벌크 데이터 업데이트' }}</span>
      </button>
    </div>

    <!-- Dashboard Cards Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      
      <!-- Watchlist Selector Card -->
      <div class="glass-card lg:col-span-1 p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <!-- Lucide Icons as SVG to prevent layout flicker -->
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandGold" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.907c.961 0 1.367 1.243.583 1.83l-3.978 2.89a1 1 0 00-.364 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.583-1.83h4.907a1 1 0 00.95-.69l1.519-4.674z" />
            </svg>
            관심 종목
          </h3>
          <span class="text-[10px] bg-brandIndigo/20 text-brandIndigo px-2 py-0.5 rounded-full font-bold font-outfit">
            {{ watchlist.length }} Assets
          </span>
        </div>

        <!-- Watchlist items list -->
        <div class="flex flex-col gap-2 max-h-[360px] overflow-y-auto pr-1">
          <div
            v-for="ticker in watchlist"
            :key="ticker"
            @click="selectTicker(ticker)"
            :class="[
              'flex items-center justify-between p-3 border rounded-xl cursor-pointer transition-all',
              activeTicker === ticker ? 'border-brandIndigo bg-brandIndigo/5' : 'border-slate-800/80 hover:bg-slate-800/30'
            ]"
          >
            <div class="flex items-center gap-2">
              <span class="font-outfit font-extrabold text-xs" :class="activeTicker === ticker ? 'text-brandIndigo' : 'text-white'">
                {{ ticker }}
              </span>
              <span class="text-[8px] bg-emerald-950/60 text-brandGreen border border-brandGreen/20 px-1.5 py-0.2 rounded font-semibold font-sans">
                Collecting
              </span>
            </div>
            <button
              @click.stop="removeWatchlistTicker(ticker)"
              class="text-slate-500 hover:text-brandRed text-[9px] font-outfit uppercase font-semibold transition-colors"
            >
              Delete
            </button>
          </div>
        </div>

        <!-- Add Ticker Form -->
        <div class="flex flex-col gap-2 mt-2">
          <div class="flex gap-2">
            <input
              type="text"
              v-model="newTickerInput"
              @input="onTickerInput"
              placeholder="예: KOSPI:005930, AAPL"
              class="flex-1 bg-slate-900/60 border border-slate-800/80 text-xs px-3 py-2.5 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-brandIndigo"
            />
            <button
              @click="addWatchlistTicker"
              class="bg-gradient-to-tr from-brandIndigo to-brandGreen hover:opacity-90 text-white font-extrabold text-xs px-4 py-2.5 rounded-xl shadow-md font-outfit cursor-pointer"
            >
              ADD
            </button>
          </div>
          <!-- Ticker AI Correction Suggestion -->
          <div v-if="tickerCorrection" class="bg-indigo-950/40 border border-brandIndigo/25 rounded-xl p-3 text-[11px] flex items-center justify-between">
            <span class="text-slate-300">💡 Did you mean: <strong class="text-white font-bold">{{ tickerCorrection.corrected }}</strong>?</span>
            <button @click="applyTickerCorrection" class="text-brandIndigo hover:text-indigo-400 font-extrabold text-[9px] uppercase font-outfit cursor-pointer">
              Apply
            </button>
          </div>
        </div>
      </div>

      <!-- Real-time Chart.js Price Panel -->
      <div class="glass-card lg:col-span-3 p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div class="flex items-center gap-3">
            <span class="text-xs bg-brandIndigo/10 text-brandIndigo px-2 py-0.5 rounded font-extrabold font-outfit uppercase">
              Chart Feed
            </span>
            <h3 class="font-outfit font-extrabold text-sm text-white uppercase tracking-wider">
              {{ activeTicker }} 실시간 일별 차트
            </h3>
          </div>
          <div class="flex items-center gap-3 text-[10px] font-semibold">
            <!-- Magnet Mode Toggle Button -->
            <button
              @click="magnetMode = !magnetMode"
              :class="[
                'flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[9px] font-extrabold tracking-wider font-outfit transition-all uppercase cursor-pointer mr-2',
                magnetMode ? 'border-brandGold/40 bg-brandGold/10 text-brandGold' : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700'
              ]"
              title="추세선 그리기 시 가장 가까운 캔들 고점/저점에 자석처럼 붙는 모드를 설정합니다."
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18a6 6 0 0112 0v-3a3 3 0 00-6 0v3z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M18 15h3v3h-3zM3 15h3v3H3z" />
              </svg>
              <span>자석 {{ magnetMode ? 'ON' : 'OFF' }}</span>
            </button>
            <span class="flex items-center gap-1.5 text-red-500"><span class="w-2 h-2 rounded-full bg-red-500"></span>상승 캔들</span>
            <span class="flex items-center gap-1.5 text-blue-500"><span class="w-2 h-2 rounded-full bg-blue-500"></span>하락 캔들</span>
            <!-- Interactive SMA 5 Toggle Button -->
            <button
              @click="toggleSma5"
              :class="[
                'flex items-center gap-1.5 px-2 py-0.5 rounded border transition-all cursor-pointer font-extrabold text-[9px] uppercase tracking-wider font-outfit',
                showSma5 
                  ? 'border-[#34D399]/40 bg-[#34D399]/10 text-[#34D399]' 
                  : 'border-slate-800 bg-slate-900/60 text-slate-500 hover:border-slate-700'
              ]"
              title="차트에서 5일 이동평균선(SMA 5)을 켜거나 끕니다."
            >
              <span class="w-2.5 h-1 bg-[#34D399] rounded-full"></span>
              SMA 5 {{ showSma5 ? 'ON' : 'OFF' }}
            </button>

            <!-- Interactive SMA 20 Toggle Button -->
            <button
              @click="toggleSma20"
              :class="[
                'flex items-center gap-1.5 px-2 py-0.5 rounded border transition-all cursor-pointer font-extrabold text-[9px] uppercase tracking-wider font-outfit',
                showSma20 
                  ? 'border-[#F59E0B]/40 bg-[#F59E0B]/10 text-[#F59E0B]' 
                  : 'border-slate-800 bg-slate-900/60 text-slate-500 hover:border-slate-700'
              ]"
              title="차트에서 20일 이동평균선(SMA 20)을 켜거나 끕니다."
            >
              <span class="w-2.5 h-1 bg-[#F59E0B] rounded-full"></span>
              SMA 20 {{ showSma20 ? 'ON' : 'OFF' }}
            </button>
            <span class="flex items-center gap-1.5 text-slate-400/80"><span class="w-2 h-2 bg-slate-400/50 border border-slate-400 rounded-sm"></span>거래량</span>
          </div>
        </div>
        <!-- Split Vertically Stacked Canvas Containers -->
        <div class="flex flex-col gap-1 w-full">
          <!-- Price Chart (top, height 280px) -->
          <div class="h-[280px] relative w-full">
            <canvas id="dashboard-price-chart" class="cursor-pencil"></canvas>
          </div>
          <!-- Volume Chart (bottom, height 120px) -->
          <div class="h-[120px] relative w-full">
            <canvas id="dashboard-volume-chart"></canvas>
          </div>
          <!-- Synchronized Scroll Bar Range Input Slider (Visible when zoomed in) -->
          <div v-if="zoomRange < totalCandles" class="px-2 pt-1 flex items-center w-full">
            <input
              type="range"
              min="0"
              :max="totalCandles - zoomRange"
              v-model.number="scrollOffset"
              @input="redrawSlicing"
              class="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-brandIndigo focus:outline-none"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Blackboard Candidate Analysts Section -->
      <div class="glass-card lg:col-span-2 p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandIndigo" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            블랙보드 의견 (Candidate Analysts)
          </h3>
          <span class="text-[9px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-bold uppercase tracking-wider">
            Workspace Live Ticks
          </span>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- Technical Candidate Card -->
          <div class="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">기술적 분석가</span>
              <span :class="['text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wide', getActionBadgeClass(blackboard.technical.action)]">
                {{ blackboard.technical.action }}
              </span>
            </div>
            <div class="text-xs font-semibold text-white">가중치 신뢰도: {{ (blackboard.technical.weight * 100).toFixed(0) }}%</div>
            <p class="text-[11px] text-slate-400 leading-relaxed font-light mt-1">{{ blackboard.technical.reason }}</p>
          </div>

          <!-- Fundamental Candidate Card -->
          <div class="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">기본적 가치 분석가</span>
              <span :class="['text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wide', getActionBadgeClass(blackboard.fundamental.action)]">
                {{ blackboard.fundamental.action }}
              </span>
            </div>
            <div class="text-xs font-semibold text-white">가중치 신뢰도: {{ (blackboard.fundamental.weight * 100).toFixed(0) }}%</div>
            <p class="text-[11px] text-slate-400 leading-relaxed font-light mt-1">{{ blackboard.fundamental.reason }}</p>
          </div>

          <!-- ML Predictor Candidate Card -->
          <div class="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">ML 예측 모델</span>
              <span :class="['text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wide', getActionBadgeClass(blackboard.ml.action)]">
                {{ blackboard.ml.action }}
              </span>
            </div>
            <div class="text-xs font-semibold text-white">예측가: {{ formatCurrency(blackboard.ml.predictedPrice, blackboard.ml.ticker || '', viewCurrency) }}</div>
            <div class="text-[10px] text-slate-400">신뢰지수: {{ (blackboard.ml.confidence * 100).toFixed(0) }}%</div>
            <p class="text-[11px] text-slate-400 leading-relaxed font-light mt-1">
              실시간 가격 추세를 OLS 선형 회귀 모형으로 예측하여 즉시 판별을 결정합니다.
            </p>
          </div>
        </div>
      </div>

      <!-- Dynamic Event Terminal Log -->
      <div class="glass-card lg:col-span-1 p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandGreen" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            시스템 실시간 로그
          </h3>
          <button @click="clearLogs" class="text-slate-500 hover:text-white text-[9px] uppercase font-bold tracking-wider cursor-pointer">
            Clear
          </button>
        </div>
        <div class="h-[155px] bg-slate-950/80 border border-slate-900 rounded-xl p-4 overflow-y-auto flex flex-col gap-2 font-mono text-[10px]">
          <div v-for="(log, idx) in systemLogs" :key="idx" class="flex gap-2">
            <span class="text-slate-600 select-none">[{{ log.time }}]</span>
            <span :class="'text-' + log.color">{{ log.text }}</span>
          </div>
          <div v-if="systemLogs.length === 0" class="text-slate-600 text-center py-10 font-sans italic">
            대기 중... 실시간 가격 틱 수집 시 로그가 자동 롤링됩니다.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cursor-pencil {
  cursor: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23FBBF24' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z'/><path d='m15 5 4 4'/></svg>") 2 22, crosshair;
}
</style>
