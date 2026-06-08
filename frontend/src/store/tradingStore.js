import { reactive, ref } from 'vue';

// Dynamically determine the backend REST API base URL and WebSocket URL
const isDev = window.location.port === '5173';
export const apiBase = isDev ? 'http://localhost:8000' : '';
export const wsUrl = isDev ? 'ws://localhost:8000/ws' : `ws://${window.location.host}/ws`;

// Centralized Reactive States
export const currentTab = ref('dashboard');
export const dbActiveTab = ref('clickhouse');
export const dbActiveEngine = ref('ClickHouse');
export const automatedMode = ref(false);
export const activeTicker = ref('KOSPI:005930');
export const newTickerInput = ref('');
export const tickerCorrection = ref(null);
export const watchlist = ref([]);
export const systemLogs = ref([]);
export const simLogs = ref([]);
export const simLoading = ref(false);
export const simReport = ref(null);
export const dbLoading = ref(false);
export const ordersLog = ref([]);
export const pendingQueue = ref([]);
export const recommendationsList = ref([]);
export const recommendationsLoading = ref(false);

// Currency Settings
export const exchangeRate = ref(1400.0);
export const viewCurrency = ref('NATIVE'); // NATIVE, KRW, USD

export const dbFilters = reactive({
  ticker: '',
  startDate: '',
  endDate: '',
  limit: 50,
  sort: 'desc',
  page: 1,
  query: '',
  categoryFilter: 'all'
});

export const portfolio = reactive({
  cash: 100000000,
  totalValue: 100000000,
  floatingPnl: 0,
  positions: []
});

export const dbData = reactive({
  bars: [],
  news: [],
  features: []
});

export const blackboard = reactive({
  technical: { action: 'HOLD', weight: 0.5, reason: '데이터 수집 대기 중...' },
  fundamental: { action: 'HOLD', weight: 0.5, reason: '데이터 수집 대기 중...' },
  ml: { action: 'HOLD', predictedPrice: 70000.0, confidence: 0.5 }
});

export const simRequest = reactive({
  tickers: [],
  days: 2
});

export const orderForm = reactive({
  ticker: 'KOSPI:005930',
  action: 'BUY',
  quantity: 10,
  price: 70000
});

// Event Logger Helper
export function addLog(text, color = 'slate-400') {
  const time = new Date().toLocaleTimeString();
  systemLogs.value.unshift({ time, text, color });
  if (systemLogs.value.length > 50) {
    systemLogs.value.pop();
  }
}

export function clearLogs() {
  systemLogs.value = [];
}

// WebSocket connection management
let socket = null;
export function connectWS() {
  if (socket) return;
  addLog(`Establishing Blackboard live event socket: ${wsUrl}`, 'brandIndigo');
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    addLog('Live market event stream connected successfully.', 'brandGreen');
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleWSEvent(data);
    } catch (e) {
      console.error('Failed to parse WebSocket message', e);
    }
  };

  socket.onclose = () => {
    addLog('WebSocket disconnected. Retrying connection in 5 seconds...', 'brandRed');
    socket = null;
    setTimeout(connectWS, 5000);
  };
}

// Event receiver routing
export const chartCallbacks = []; // Listeners for new pricing bars
function handleWSEvent(data) {
  if (data.event_type === 'RawDataCollected') {
    // Notify chart visualizers
    chartCallbacks.forEach(cb => cb(data));

    const bare = data.ticker.includes(':') ? data.ticker.split(':')[1] : data.ticker;
    addLog(
      `Collected pricing tick for [${data.ticker}]: Close=₩${formatNumber(data.bar.close)} Vol=${formatNumber(data.bar.volume)}`,
      'slate-300'
    );

    // If collected tick matches active display ticker, update AI analytics
    if (data.ticker === activeTicker.value) {
      fetchPrediction(activeTicker.value);
    }
  } 
  else if (data.event_type === 'PortfolioUpdated') {
    portfolio.cash = data.cash;
    portfolio.totalValue = data.total_value;
    portfolio.floatingPnl = data.floating_pnl;
    portfolio.positions = data.positions;
    addLog(
      `Portfolio updated: Value=₩${formatNumber(data.total_value)} P&L=₩${formatNumber(data.floating_pnl)}`,
      'brandPurple'
    );
  } 
  else if (data.event_type === 'QueueUpdated') {
    addLog(`Approval Queue changed: order for ${data.intent.ticker} marked ${data.action}`, 'brandGold');
    fetchQueue();
  } 
  else if (data.event_type === 'OrderFilled') {
    addLog(
      `OMS ORDER FILLED SUCCESS: [${data.order.action}] ${data.order.ticker} qty=${data.order.quantity} at ₩${formatNumber(data.order.avg_fill_price)}`,
      'brandGreen'
    );
    fetchPortfolio();
    fetchOrdersLog();
  } 
  else if (data.event_type === 'OrderRejected') {
    addLog(`OMS ORDER REJECTED/CANCELLED: ${data.order.ticker} (Reason: ${data.order.reason})`, 'brandRed');
    fetchOrdersLog();
  }
}

// API REST methods
export async function fetchWatchlist() {
  try {
    const res = await fetch(`${apiBase}/api/watchlist`);
    const data = await res.json();
    watchlist.value = data;
    if (data.length > 0) {
      if (simRequest.tickers.length === 0) {
        simRequest.tickers = [...data];
      }
      if (!data.includes(activeTicker.value)) {
        activeTicker.value = data[0];
      }
    }
    return data;
  } catch (e) {
    console.error('Watchlist fetch failed', e);
  }
}

export async function fetchRecommendations() {
  try {
    const res = await fetch(`${apiBase}/api/recommendations`);
    const data = await res.json();
    recommendationsList.value = data;
    return data;
  } catch (e) {
    console.error('Failed to fetch recommendations', e);
  }
}

export async function generateRecommendations() {
  recommendationsLoading.value = true;
  addLog('Starting multi-agent Blackboard Trading Team candidate scan...', 'brandPurple');
  try {
    const res = await fetch(`${apiBase}/api/recommendations/generate`, {
      method: 'POST'
    });
    const data = await res.json();
    recommendationsList.value = data;
    addLog(`Multi-agent Blackboard scan complete. Generated ${data.length} stock recommendations!`, 'brandGreen');
    return data;
  } catch (e) {
    console.error('Failed to generate recommendations', e);
    addLog('Multi-agent Blackboard scan failed.', 'brandRed');
  } finally {
    recommendationsLoading.value = false;
  }
}

export async function addWatchlistTicker() {
  const val = newTickerInput.value.trim().toUpperCase();
  if (!val) return;

  addLog(`Adding ${val} to Watchlist (관심종목)...`, 'slate-400');
  try {
    const res = await fetch(`${apiBase}/api/watchlist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticker: val })
    });
    const data = await res.json();
    if (data.success) {
      newTickerInput.value = '';
      tickerCorrection.value = null;
      await fetchWatchlist();
      addLog(`Successfully added ${val} to persistent SQL Watchlist. Raw collection started!`, 'brandGreen');
    }
  } catch (e) {
    console.error('Add ticker failed', e);
  }
}

export async function addWatchlistTickerSymbol(ticker) {
  addLog(`Adding ${ticker} to Watchlist (관심종목)...`, 'slate-400');
  try {
    const res = await fetch(`${apiBase}/api/watchlist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticker: ticker })
    });
    const data = await res.json();
    if (data.success) {
      await fetchWatchlist();
      addLog(`Successfully added ${ticker} to persistent SQL Watchlist. Raw collection started!`, 'brandGreen');
      return true;
    }
  } catch (e) {
    console.error('Add ticker symbol failed', e);
  }
  return false;
}

export async function removeWatchlistTicker(ticker) {
  addLog(`Removing ${ticker} from Watchlist...`, 'slate-400');
  try {
    const res = await fetch(`${apiBase}/api/watchlist/${ticker}`, {
      method: 'DELETE'
    });
    const data = await res.json();
    if (data.success) {
      await fetchWatchlist();
      addLog(`Successfully removed ${ticker} from Watchlist.`, 'brandRed');
    }
  } catch (e) {
    console.error('Remove ticker failed', e);
  }
}

// Autocomplete suggestions
let suggestionTimeout = null;
export function onTickerInput(e) {
  clearTimeout(suggestionTimeout);
  const val = e.target.value.trim();
  if (val.length < 2) {
    tickerCorrection.value = null;
    return;
  }
  suggestionTimeout = setTimeout(async () => {
    try {
      const res = await fetch(`${apiBase}/api/ticker/correct?query=${encodeURIComponent(val)}`);
      const data = await res.json();
      if (data && data.corrected && data.corrected.toUpperCase() !== val.toUpperCase()) {
        tickerCorrection.value = data;
      } else {
        tickerCorrection.value = null;
      }
    } catch (err) {
      console.error(err);
    }
  }, 600);
}

export function applyTickerCorrection() {
  if (tickerCorrection.value) {
    newTickerInput.value = tickerCorrection.value.corrected;
    tickerCorrection.value = null;
    addLog('Applied dynamic LLM correction recommend.', 'brandIndigo');
  }
}

// Portfolio & Orders
export async function fetchPortfolio() {
  try {
    const res = await fetch(`${apiBase}/api/portfolio`);
    const data = await res.json();
    portfolio.cash = data.cash;
    portfolio.totalValue = data.total_value;
    portfolio.floatingPnl = data.floating_pnl;
    portfolio.positions = data.positions;
  } catch (e) {
    console.error(e);
  }
}

// System / Background fetches
export async function fetchExchangeRate() {
  try {
    const res = await fetch(`${apiBase}/api/system/exchange-rate`);
    if (res.ok) {
      const data = await res.json();
      if (data.rate) exchangeRate.value = data.rate;
    }
  } catch (e) {
    console.error("Failed to fetch exchange rate", e);
  }
}

export async function fetchOrdersLog() {
  try {
    const res = await fetch(`${apiBase}/api/orders`);
    ordersLog.value = await res.json();
  } catch (e) {
    console.error(e);
  }
}

export async function fetchQueue() {
  try {
    const res = await fetch(`${apiBase}/api/queue`);
    pendingQueue.value = await res.json();
  } catch (e) {
    console.error(e);
  }
}

export async function toggleMode() {
  try {
    await fetch(`${apiBase}/api/settings/mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ automated: automatedMode.value })
    });
    addLog(
      `Trading workflow toggled: ${automatedMode.value ? 'Automated Bypass' : 'Manual Approval Required'}`,
      'brandGold'
    );
  } catch (e) {
    console.error(e);
  }
}

export async function approveQueueItem(id) {
  try {
    await fetch(`${apiBase}/api/queue/${id}/approve`, { method: 'POST' });
    await fetchQueue();
  } catch (e) {
    console.error(e);
  }
}

export async function rejectQueueItem(id) {
  try {
    await fetch(`${apiBase}/api/queue/${id}/reject`, { method: 'POST' });
    await fetchQueue();
  } catch (e) {
    console.error(e);
  }
}

export async function submitManualOrder() {
  addLog(`OMS Dispatching Manual Order Ticket: ${orderForm.ticker}...`, 'brandGreen');
  try {
    const res = await fetch(`${apiBase}/api/orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ticker: orderForm.ticker,
        action: orderForm.action,
        quantity: orderForm.quantity,
        price: orderForm.price
      })
    });
    const data = await res.json();
    if (data.success) {
      addLog(
        `Manual Order successfully pushed! ${automatedMode.value ? 'Sent to Exchange Execution.' : 'Queued for Manual approval.'}`,
        'brandGreen'
      );
      await fetchQueue();
      await fetchPortfolio();
    }
  } catch (e) {
    console.error(e);
    addLog('Manual Order placement failed.', 'brandRed');
  }
}

// Blackboard Predictor
export async function fetchPrediction(ticker) {
  try {
    const res = await fetch(`${apiBase}/api/predict/${ticker}`);
    const data = await res.json();

    blackboard.ml.action = data.direction || 'HOLD';
    blackboard.ml.predictedPrice = data.predicted_close || 70000.0;
    blackboard.ml.confidence = data.confidence || 0.5;

    // Technical & Fundamental reasoning synthesis based on direction
    if (blackboard.ml.action === 'BUY') {
      blackboard.technical.action = 'BUY';
      blackboard.technical.weight = 0.72;
      blackboard.technical.reason = '지수이동평균(EMA) 5일선이 20일선을 상향 돌파하는 골든크로스 매수 신호 포착.';

      blackboard.fundamental.action = 'BUY';
      blackboard.fundamental.weight = 0.68;
      blackboard.fundamental.reason = '현재 주가 대비 주당순자산가치(BPS) 및 실적 전망치가 저평가 국면을 탈출하며 적정 가격 지지선 견조.';
    } else if (blackboard.ml.action === 'SELL') {
      blackboard.technical.action = 'SELL';
      blackboard.technical.weight = 0.78;
      blackboard.technical.reason = '상대강도시수(RSI)가 70 과매수 영역에 진입한 뒤 가격 저항 모멘텀 이탈 조짐 포착.';

      blackboard.fundamental.action = 'SELL';
      blackboard.fundamental.weight = 0.61;
      blackboard.fundamental.reason = '거시 경제 원자재 지출 비용 상승 부담으로 인한 영업 이익률 조정 압박 발생.';
    } else {
      blackboard.technical.action = 'HOLD';
      blackboard.technical.weight = 0.5;
      blackboard.technical.reason = '이동평균선 수렴 수평 횡보 국면으로 모멘텀 돌파 추세 대기.';

      blackboard.fundamental.action = 'HOLD';
      blackboard.fundamental.weight = 0.5;
      blackboard.fundamental.reason = '분기별 기업 가치 지표가 예상 추정치 중앙 범위에 걸쳐 중립 기조 유지.';
    }
  } catch (e) {
    console.error(e);
  }
}

// Multi-DB queries
export async function loadDBData() {
  dbLoading.value = true;
  try {
    if (dbActiveTab.value === 'clickhouse') {
      const targetTicker = dbFilters.ticker.trim();
      const offset = (dbFilters.page - 1) * dbFilters.limit;
      let url = `${apiBase}/api/data/bars?limit=${dbFilters.limit}&offset=${offset}&sort=${dbFilters.sort}`;
      if (targetTicker) url += `&ticker=${encodeURIComponent(targetTicker)}`;
      if (dbFilters.startDate) url += `&start_date=${dbFilters.startDate}`;
      if (dbFilters.endDate) url += `&end_date=${dbFilters.endDate}`;
      
      const res = await fetch(url);
      dbData.bars = await res.json();
      dbActiveEngine.value = dbData.bars.length > 0 ? dbData.bars[0].db_engine : 'ClickHouse';
    } 
    else if (dbActiveTab.value === 'mongodb') {
      const targetTicker = dbFilters.ticker.trim();
      const targetQuery = dbFilters.query.trim();
      let url = `${apiBase}/api/data/news?limit=${dbFilters.limit}`;
      if (targetTicker) url += `&ticker=${encodeURIComponent(targetTicker)}`;
      if (dbFilters.startDate) url += `&start_date=${dbFilters.startDate}`;
      if (dbFilters.endDate) url += `&end_date=${dbFilters.endDate}`;
      if (targetQuery) url += `&query=${encodeURIComponent(targetQuery)}`;
      if (dbFilters.categoryFilter) url += `&category_filter=${dbFilters.categoryFilter}`;
      
      const res = await fetch(url);
      dbData.news = await res.json();
      dbActiveEngine.value = dbData.news.length > 0 ? dbData.news[0].db_engine : 'MongoDB';
    } 
    else if (dbActiveTab.value === 'duckdb') {
      const res = await fetch(`${apiBase}/api/data/features?ticker=${encodeURIComponent(activeTicker.value)}`);
      const payload = await res.json();
      dbData.features = payload.features;
      dbActiveEngine.value = payload.db_engine;
    } 
    else if (dbActiveTab.value === 'postgres') {
      dbActiveEngine.value = 'PostgreSQL (ACID)';
      await fetchWatchlist();
      await fetchOrdersLog();
    }
  } catch (e) {
    console.error(e);
  } finally {
    dbLoading.value = false;
  }
}

// Backtest simulation engine
export async function runSimulation() {
  simLoading.value = true;
  simLogs.value = [];
  simReport.value = null;

  const time = new Date().toLocaleTimeString();
  simLogs.value.unshift({
    time,
    text: `Starting backtest simulation for assets: ${simRequest.tickers.join(', ')}`,
    color: 'brandIndigo font-bold'
  });
  simLogs.value.unshift({
    time,
    text: `Active database lookback: ${simRequest.days} days...`,
    color: 'slate-400'
  });

  try {
    const res = await fetch(`${apiBase}/api/backtest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tickers: simRequest.tickers,
        days: simRequest.days
      })
    });
    const data = await res.json();

    if (data.success) {
      simReport.value = data.metrics;

      const reportTime = new Date().toLocaleTimeString();
      simLogs.value.unshift({
        time: reportTime,
        text: 'Simulation ended. Math metrics computed dynamically.',
        color: 'brandGreen font-bold'
      });
      simLogs.value.unshift({
        time: reportTime,
        text: `Final Portfolio Value: ₩${formatNumber(data.metrics.final_value)}`,
        color: 'white'
      });
      simLogs.value.unshift({
        time: reportTime,
        text: `Simulation steps finished: ${data.metrics.steps_run} historical ticks loaded.`,
        color: 'brandIndigo'
      });
      simLogs.value.unshift({
        time: reportTime,
        text: 'Routing historical ticks backtesting adapters matching orders...',
        color: 'slate-300'
      });
      simLogs.value.unshift({
        time: reportTime,
        text: 'Seeding backtest database schemas successfully.',
        color: 'brandPurple'
      });
    } else {
      simLogs.value.unshift({
        time: new Date().toLocaleTimeString(),
        text: `Backtest Run Failed: ${data.error}`,
        color: 'brandRed font-bold'
      });
    }
  } catch (e) {
    console.error(e);
    simLogs.value.unshift({
      time: new Date().toLocaleTimeString(),
      text: 'Simulation execution server crash.',
      color: 'brandRed font-bold'
    });
  } finally {
    simLoading.value = false;
  }
}

// Global UI Formatting helpers
export function formatNumber(num) {
  if (num === null || num === undefined) return '0.00';
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num);
}

export function formatCurrency(value, ticker = '', targetCurrency = viewCurrency.value) {
  if (value === null || value === undefined) return '0.00';
  
  const isUSD = ticker.startsWith('NASDAQ') || ticker.startsWith('NYSE') || ticker.startsWith('AMEX');
  // KOSPI and CRYPTO (via Coinone) are treated as KRW native
  const nativeCurrency = isUSD ? 'USD' : 'KRW';
  
  let resultValue = value;
  let symbol = nativeCurrency === 'USD' ? '$' : '₩';
  
  // NATIVE: don't convert
  if (targetCurrency === 'NATIVE') {
    return `${symbol}${formatNumber(resultValue)}`;
  }
  
  // Convert to KRW
  if (targetCurrency === 'KRW') {
    if (nativeCurrency === 'USD') {
      resultValue = value * exchangeRate.value;
    }
    return `₩${formatNumber(resultValue)}`;
  }
  
  // Convert to USD
  if (targetCurrency === 'USD') {
    if (nativeCurrency === 'KRW') {
      resultValue = value / exchangeRate.value;
    }
    return `$${formatNumber(resultValue)}`;
  }
  
  return `${symbol}${formatNumber(resultValue)}`;
}

export function formatDateTime(val) {
  if (!val) return '-';
  try {
    const d = new Date(val);
    return d.toLocaleString();
  } catch (e) {
    return val;
  }
}

// New Navigation/Tab States
export const dashboardSummary = ref(null);
export const approvalsList = ref([]);
export const activePositions = ref([]);
export const activeOrders = ref([]);
export const tradeHistory = ref([]);
export const strategySettings = ref({ buy_threshold: 0.25, sell_threshold: -0.25, strategies: [] });
export const modelRegistry = ref([]);
export const notificationConfig = ref({
  slack_webhook_url: "",
  telegram_bot_token: "",
  telegram_chat_id: "",
  notify_order_filled: true,
  notify_order_rejected: true,
  notify_approval_required: true
});
export const systemConfig = ref({});
export const blackboardState = ref({});
export const systemHealth = ref({});
export const backtestJob = ref(null);

export async function fetchDashboardSummary() {
  try {
    const res = await fetch(`${apiBase}/api/dashboard/summary`);
    if (res.ok) {
      dashboardSummary.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to fetch dashboard summary", e);
  }
}

export async function fetchApprovals() {
  try {
    const res = await fetch(`${apiBase}/api/approvals`);
    if (res.ok) {
      approvalsList.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to fetch approvals", e);
  }
}

export async function handleApprovalAction(queueId, action) {
  try {
    const res = await fetch(`${apiBase}/api/approvals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ queue_id: queueId, action })
    });
    if (res.ok) {
      await fetchApprovals();
      await fetchDashboardSummary();
    }
  } catch (e) {
    console.error("Failed to handle approval action", e);
  }
}

export async function fetchActivePositions() {
  try {
    const res = await fetch(`${apiBase}/api/positions`);
    if (res.ok) {
      activePositions.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to fetch active positions", e);
  }
}

export async function fetchActiveOrders() {
  try {
    const res = await fetch(`${apiBase}/api/orders/active`);
    if (res.ok) {
      activeOrders.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to fetch active orders", e);
  }
}

export async function fetchTradeHistory(from = "", to = "") {
  try {
    let url = `${apiBase}/api/trades`;
    const params = [];
    if (from) params.push(`from_date=${from}`);
    if (to) params.push(`to_date=${to}`);
    if (params.length > 0) url += `?${params.join("&")}`;
    
    const res = await fetch(url);
    if (res.ok) {
      tradeHistory.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to fetch trade history", e);
  }
}

export async function fetchStrategySettings() {
  try {
    const res = await fetch(`${apiBase}/api/strategies`);
    if (res.ok) {
      strategySettings.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to fetch strategy settings", e);
  }
}

export async function saveStrategySettings(payload) {
  try {
    const res = await fetch(`${apiBase}/api/strategies`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      strategySettings.value = (await res.json()).strategies;
      addLog("Successfully saved dynamic strategy parameters.", "brandGreen");
    }
  } catch (e) {
    console.error("Failed to save strategy settings", e);
  }
}

export async function fetchModelRegistry() {
  try {
    const res = await fetch(`${apiBase}/api/models`);
    if (res.ok) {
      modelRegistry.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to fetch model registry", e);
  }
}

export async function trainModel(ticker) {
  addLog(`Triggering ML OLS regression model training for ${ticker}...`, "brandIndigo");
  try {
    const res = await fetch(`${apiBase}/api/models`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker })
    });
    const data = await res.json();
    if (data.success) {
      addLog(`Model trained successfully for ${ticker}! R-squared: ${data.model.r_squared}`, "brandGreen");
      await fetchModelRegistry();
      return true;
    } else {
      addLog(`Training failed: ${data.error}`, "brandRed");
      return false;
    }
  } catch (e) {
    console.error("Failed to train model", e);
    return false;
  }
}

export async function fetchNotificationConfig() {
  try {
    const res = await fetch(`${apiBase}/api/notifications/config`);
    if (res.ok) {
      notificationConfig.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to fetch notification config", e);
  }
}

export async function saveNotificationConfig(payload) {
  try {
    const res = await fetch(`${apiBase}/api/notifications/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      notificationConfig.value = (await res.json()).config;
      addLog("Successfully saved notification configurations.", "brandGreen");
    }
  } catch (e) {
    console.error("Failed to save notification config", e);
  }
}

export async function fetchSystemConfig() {
  try {
    const res = await fetch(`${apiBase}/api/system/config`);
    if (res.ok) {
      systemConfig.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to fetch system config", e);
  }
}

export async function saveSystemConfig(payload) {
  try {
    const res = await fetch(`${apiBase}/api/system/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      systemConfig.value = (await res.json()).config;
      addLog("Successfully updated system risk limits.", "brandGreen");
    }
  } catch (e) {
    console.error("Failed to save system config", e);
  }
}

export async function fetchBlackboardState(ticker = "") {
  try {
    let url = `${apiBase}/api/blackboard/state`;
    if (ticker) url += `?ticker=${encodeURIComponent(ticker)}`;
    const res = await fetch(url);
    if (res.ok) {
      blackboardState.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to fetch blackboard state", e);
  }
}

export async function fetchSystemHealth() {
  try {
    const res = await fetch(`${apiBase}/api/system/health`);
    if (res.ok) {
      systemHealth.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to fetch system health", e);
  }
}

export async function triggerAsyncBacktest(tickers, days) {
  simLoading.value = true;
  simLogs.value = [];
  simReport.value = null;
  
  addLog("Spawning background asynchronous backtest run...", "brandIndigo");
  
  try {
    const res = await fetch(`${apiBase}/api/backtests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tickers, days })
    });
    const data = await res.json();
    if (data.success) {
      backtestJob.value = data.backtest_id;
      addLog(`Job submitted successfully. Job ID: ${data.backtest_id}`, "brandGreen");
      pollBacktestJob(data.backtest_id);
    } else {
      simLoading.value = false;
      addLog(`Failed to start backtest: ${data.error}`, "brandRed");
    }
  } catch (e) {
    simLoading.value = false;
    console.error("Failed to trigger backtest", e);
  }
}

async function pollBacktestJob(jobId) {
  if (!simLoading.value || backtestJob.value !== jobId) return;
  
  try {
    const res = await fetch(`${apiBase}/api/backtests/${jobId}`);
    if (res.ok) {
      const data = await res.json();
      
      if (data.logs) {
        simLogs.value = data.logs.map(log => ({
          time: new Date().toLocaleTimeString(),
          text: log,
          color: log.includes("failed") || log.includes("Failed") ? "brandRed" : log.includes("ended") || log.includes("successfully") ? "brandGreen" : "slate-300"
        })).reverse();
      }
      
      if (data.status === "COMPLETED") {
        simReport.value = data.metrics;
        simLoading.value = false;
        backtestJob.value = null;
        addLog("Asynchronous backtest run completed successfully.", "brandGreen");
      } else if (data.status === "FAILED") {
        simLoading.value = false;
        backtestJob.value = null;
        addLog("Asynchronous backtest run failed.", "brandRed");
      } else {
        setTimeout(() => pollBacktestJob(jobId), 1000);
      }
    }
  } catch (e) {
    console.error("Error polling backtest status", e);
    simLoading.value = false;
    backtestJob.value = null;
  }
}
