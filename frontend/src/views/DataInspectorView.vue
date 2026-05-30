<script setup>
import { onMounted, watch } from 'vue';
import {
  dbActiveTab,
  dbActiveEngine,
  dbData,
  dbLoading,
  dbFilters,
  viewCurrency,
  loadDBData,
  formatNumber,
  formatCurrency,
  exchangeRate,
  fetchExchangeRate,
  formatDateTime,
  activeTicker,
  watchlist,
  ordersLog
} from '../store/tradingStore.js';

onMounted(() => {
  fetchExchangeRate();
});

// Filter Actions
function applyFilters() {
  dbFilters.page = 1;
  loadDBData();
}

function prevPage() {
  if (dbFilters.page > 1) {
    dbFilters.page--;
    loadDBData();
  }
}

function nextPage() {
  if (dbData.bars.length === dbFilters.limit) {
    dbFilters.page++;
    loadDBData();
  }
}

// Load descriptions dynamically
function getDBTitle() {
  if (dbActiveTab.value === 'clickhouse') return 'ClickHouse Columnar OLAP Engine (Time-Series Pricing)';
  if (dbActiveTab.value === 'mongodb') return 'MongoDB Document-Store Engine (Economics News)';
  if (dbActiveTab.value === 'duckdb') return 'DuckDB Embedded In-process Analytics (Computed indicators)';
  return 'PostgreSQL ACID Relational Database (Watchlist & Transactions)';
}

function getDBDescription() {
  if (dbActiveTab.value === 'clickhouse') {
    return '최대 초당 수만 개의 실시간 주가 틱 거래량 데이터를 대량 적재하기 위해 컬럼 지향형(OLAP) 시계열 DB에 저장합니다. 뛰어난 분석 쿼리 압축성으로 초고속 집계(Aggregation) 성능을 가집니다.';
  }
  if (dbActiveTab.value === 'mongodb') {
    return 'Naver RSS, Google RSS, Alpha Vantage에서 수집된 비정형 거시경제 금융 뉴스 아티팩트의 스키마 제약 없는 JSON 포맷을 대용량 저장하기 위해 도큐먼트 지향형 NoSQL을 사용합니다.';
  }
  if (dbActiveTab.value === 'duckdb') {
    return '메모리 락 병목 없이 수집된 시계열 원천 데이터를 분석하여 로컬에서 가장 빠르게 기술적 분석 지표(SMA, RSI, 모멘텀) 연산을 보장하기 위해 고속 임베디드 DuckDB 파일 데이터베이스를 채택하여 피처 엔지니어링을 처리합니다.';
  }
  return '자산 데이터, 승인 대기열 및 거래 이력 등 데이터 정합성(Consistency)과 ACID 트랜잭션 보장이 최우선인 관계형 모델들은 엔터프라이즈급 PostgreSQL을 클라이언트로 연동하여 세션을 보장받습니다.';
}

function getDBBorderClass() {
  if (dbActiveTab.value === 'clickhouse') return 'border-brandIndigo';
  if (dbActiveTab.value === 'mongodb') return 'border-brandGreen';
  if (dbActiveTab.value === 'duckdb') return 'border-brandGold';
  return 'border-brandPurple';
}

function getStatusBadgeClass(status) {
  if (status === 'FILLED') return 'bg-emerald-950/60 text-brandGreen border border-brandGreen/20';
  if (status === 'REJECTED' || status === 'CANCELLED') return 'bg-rose-950/60 text-brandRed border border-brandRed/20';
  if (status === 'SUBMITTED') return 'bg-indigo-950/60 text-brandIndigo border border-brandIndigo/20';
  return 'bg-amber-950/60 text-brandGold border border-brandGold/20';
}

onMounted(() => {
  loadDBData();
});

watch(dbActiveTab, () => {
  loadDBData();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- DB Segmented Tabs Selector -->
    <div class="glass-card p-4 flex flex-wrap gap-2 select-none">
      <button
        @click="dbActiveTab = 'clickhouse'"
        :class="[
          'flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold uppercase font-outfit tracking-wide transition-all border cursor-pointer',
          dbActiveTab === 'clickhouse' ? 'border-brandIndigo text-brandIndigo bg-brandIndigo/5' : 'border-slate-800 text-slate-400 hover:text-white'
        ]"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
        <span>ClickHouse (OHLCV Pricing)</span>
      </button>
      <button
        @click="dbActiveTab = 'mongodb'"
        :class="[
          'flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold uppercase font-outfit tracking-wide transition-all border cursor-pointer',
          dbActiveTab === 'mongodb' ? 'border-brandGreen text-brandGreen bg-brandGreen/5' : 'border-slate-800 text-slate-400 hover:text-white'
        ]"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 4a2 2 0 00-2 2v3a2 2 0 002 2h2a2 2 0 002-2v-3a2 2 0 00-2-2h-2z" />
        </svg>
        <span>MongoDB (Economic News)</span>
      </button>
      <button
        @click="dbActiveTab = 'duckdb'"
        :class="[
          'flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold uppercase font-outfit tracking-wide transition-all border cursor-pointer',
          dbActiveTab === 'duckdb' ? 'border-brandGold text-brandGold bg-brandGold/5' : 'border-slate-800 text-slate-400 hover:text-white'
        ]"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
        <span>DuckDB (Computed Features)</span>
      </button>
      <button
        @click="dbActiveTab = 'postgres'"
        :class="[
          'flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold uppercase font-outfit tracking-wide transition-all border cursor-pointer',
          dbActiveTab === 'postgres' ? 'border-brandPurple text-brandPurple bg-brandPurple/5' : 'border-slate-800 text-slate-400 hover:text-white'
        ]"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
        </svg>
        <span>PostgreSQL (Relational States)</span>
      </button>
    </div>

    <!-- DB Description banner -->
    <div class="glass-card p-6 border-l-4" :class="getDBBorderClass()">
      <h3 class="font-outfit font-extrabold text-sm text-white uppercase tracking-wider mb-2">
        {{ getDBTitle() }}
      </h3>
      <p class="text-xs text-slate-400 leading-relaxed font-light">
        {{ getDBDescription() }}
      </p>
    </div>

    <!-- Real raw data tables -->
    <div class="glass-card p-5 overflow-hidden">
      <div class="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-4">
        <h4 class="font-outfit font-extrabold text-xs text-white uppercase tracking-wider">
          Real-world Database Records
        </h4>
        <div class="flex items-center gap-2">
          <span class="text-[9px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded uppercase font-bold font-mono">
            Connection: {{ dbActiveEngine }}
          </span>
          <button @click="loadDBData" class="text-slate-500 hover:text-white text-[9px] uppercase font-bold flex items-center gap-1 cursor-pointer">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 animate-spin-hover" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89H18" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      <!-- Loader -->
      <div v-if="dbLoading" class="text-center py-20 text-slate-500 text-xs flex flex-col items-center gap-3">
        <div class="w-8 h-8 rounded-full border-2 border-brandIndigo border-t-transparent animate-spin"></div>
        <span>Fetching data from target database...</span>
      </div>

      <!-- ClickHouse Filter Toolbar -->
      <div v-if="dbActiveTab === 'clickhouse' && !dbLoading" class="flex flex-wrap items-end gap-3 mb-4 bg-slate-900/40 p-3 rounded-lg border border-slate-800/50">
        <div class="flex flex-col gap-1">
          <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">Ticker</label>
          <input v-model="dbFilters.ticker" type="text" placeholder="All Tickers" class="bg-slate-800 text-xs text-white px-2 py-1.5 rounded border border-slate-700 w-28 focus:outline-none focus:border-brandIndigo" />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">Start Date</label>
          <input v-model="dbFilters.startDate" type="date" class="bg-slate-800 text-xs text-slate-300 px-2 py-1.5 rounded border border-slate-700 focus:outline-none focus:border-brandIndigo" />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">End Date</label>
          <input v-model="dbFilters.endDate" type="date" class="bg-slate-800 text-xs text-slate-300 px-2 py-1.5 rounded border border-slate-700 focus:outline-none focus:border-brandIndigo" />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">Limit</label>
          <select v-model.number="dbFilters.limit" class="bg-slate-800 text-xs text-slate-300 px-2 py-1.5 rounded border border-slate-700 focus:outline-none focus:border-brandIndigo">
            <option value="50">50 rows</option>
            <option value="100">100 rows</option>
            <option value="500">500 rows</option>
            <option value="1000">1000 rows</option>
          </select>
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">Sort</label>
          <select v-model="dbFilters.sort" class="bg-slate-800 text-xs text-slate-300 px-2 py-1.5 rounded border border-slate-700 focus:outline-none focus:border-brandIndigo">
            <option value="desc">Newest First</option>
            <option value="asc">Oldest First</option>
          </select>
        </div>
        
        <div class="flex flex-col gap-1 ml-2 border-l border-slate-700/50 pl-3">
          <div class="flex items-center gap-2">
            <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">Currency</label>
            <span v-if="exchangeRate" class="text-[9px] font-mono text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
              USD/KRW: {{ formatNumber(exchangeRate) }}
            </span>
          </div>
          <div class="flex items-center bg-slate-800 rounded p-0.5 border border-slate-700 h-[30px]">
            <button 
              @click="viewCurrency = 'NATIVE'"
              :class="{'bg-slate-600 text-white': viewCurrency === 'NATIVE', 'text-slate-400 hover:text-white': viewCurrency !== 'NATIVE'}"
              class="px-2 py-0.5 text-[10px] font-bold rounded transition-colors"
            >NATIVE</button>
            <button 
              @click="viewCurrency = 'KRW'"
              :class="{'bg-slate-600 text-white': viewCurrency === 'KRW', 'text-slate-400 hover:text-white': viewCurrency !== 'KRW'}"
              class="px-2 py-0.5 text-[10px] font-bold rounded transition-colors"
            >KRW</button>
            <button 
              @click="viewCurrency = 'USD'"
              :class="{'bg-slate-600 text-white': viewCurrency === 'USD', 'text-slate-400 hover:text-white': viewCurrency !== 'USD'}"
              class="px-2 py-0.5 text-[10px] font-bold rounded transition-colors"
            >USD</button>
          </div>
        </div>

        <button @click="applyFilters" class="bg-brandIndigo/20 hover:bg-brandIndigo/40 text-brandIndigo font-bold text-xs px-4 py-1.5 rounded transition-colors border border-brandIndigo/30 ml-auto h-[30px]">
          Apply Filter
        </button>
      </div>

      <!-- MongoDB News Filter Toolbar -->
      <div v-if="dbActiveTab === 'mongodb' && !dbLoading" class="flex flex-wrap items-end gap-3 mb-4 bg-slate-900/40 p-3 rounded-lg border border-slate-800/50">
        <div class="flex flex-col gap-1">
          <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">뉴스 분류</label>
          <div class="flex items-center bg-slate-800 rounded p-0.5 border border-slate-700 h-[30px]">
            <button 
              @click="dbFilters.categoryFilter = 'all'; applyFilters();"
              :class="dbFilters.categoryFilter === 'all' ? 'bg-brandGreen text-slate-950 font-extrabold' : 'text-slate-400 hover:text-white font-medium'"
              class="px-3 py-0.5 text-[10px] rounded transition-all cursor-pointer h-full flex items-center"
            >전체 보기</button>
            <button 
              @click="dbFilters.categoryFilter = 'watchlist'; applyFilters();"
              :class="dbFilters.categoryFilter === 'watchlist' ? 'bg-brandGreen text-slate-950 font-extrabold' : 'text-slate-400 hover:text-white font-medium'"
              class="px-3 py-0.5 text-[10px] rounded transition-all cursor-pointer h-full flex items-center"
            >관심종목</button>
            <button 
              @click="dbFilters.categoryFilter = 'general'; applyFilters();"
              :class="dbFilters.categoryFilter === 'general' ? 'bg-brandGreen text-slate-950 font-extrabold' : 'text-slate-400 hover:text-white font-medium'"
              class="px-3 py-0.5 text-[10px] rounded transition-all cursor-pointer h-full flex items-center"
            >경제/증권 일반</button>
          </div>
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">검색 (기사 제목)</label>
          <input v-model="dbFilters.query" type="text" placeholder="기사 제목 검색..." class="bg-slate-800 text-xs text-white px-2.5 py-1.5 rounded border border-slate-700 w-44 focus:outline-none focus:border-brandGreen" />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">관련 종목/암호화폐</label>
          <input v-model="dbFilters.ticker" type="text" placeholder="All Tickers" class="bg-slate-800 text-xs text-white px-2 py-1.5 rounded border border-slate-700 w-28 focus:outline-none focus:border-brandGreen" />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">시작 일자</label>
          <input v-model="dbFilters.startDate" type="date" class="bg-slate-800 text-xs text-slate-300 px-2 py-1.5 rounded border border-slate-700 focus:outline-none focus:border-brandGreen" />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">종료 일자</label>
          <input v-model="dbFilters.endDate" type="date" class="bg-slate-800 text-xs text-slate-300 px-2 py-1.5 rounded border border-slate-700 focus:outline-none focus:border-brandGreen" />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-[9px] font-bold text-slate-500 uppercase tracking-wide">Limit</label>
          <select v-model.number="dbFilters.limit" class="bg-slate-800 text-xs text-slate-300 px-2 py-1.5 rounded border border-slate-700 focus:outline-none focus:border-brandGreen">
            <option value="30">30 rows</option>
            <option value="50">50 rows</option>
            <option value="100">100 rows</option>
            <option value="200">200 rows</option>
          </select>
        </div>
        
        <button @click="applyFilters" class="bg-brandGreen/20 hover:bg-brandGreen/40 text-brandGreen font-bold text-xs px-4 py-1.5 rounded transition-colors border border-brandGreen/30 ml-auto h-[30px] cursor-pointer">
          Apply Filter
        </button>
      </div>

      <!-- Data lists tables -->
      <div v-if="!dbLoading" class="overflow-x-auto">
        <!-- ClickHouse OHLCV table -->
        <table v-if="dbActiveTab === 'clickhouse'" class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-slate-800/80 text-slate-500 font-semibold">
              <th class="py-3 px-4">종목 코드</th>
              <th class="py-3 px-4">수집 시간</th>
              <th class="py-3 px-4">시가 (Open)</th>
              <th class="py-3 px-4">고가 (High)</th>
              <th class="py-3 px-4">저가 (Low)</th>
              <th class="py-3 px-4">종가 (Close)</th>
              <th class="py-3 px-4 text-right">거래량 (Volume)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(b, idx) in dbData.bars" :key="idx" class="border-b border-slate-800/30 hover:bg-slate-900/30 text-white font-sans">
              <td class="py-3 px-4 font-bold text-brandIndigo">{{ b.ticker }}</td>
              <td class="py-3 px-4 text-slate-400">{{ formatDateTime(b.timestamp) }}</td>
              <td class="py-3 px-4 font-mono">{{ formatCurrency(b.open, b.ticker, viewCurrency) }}</td>
              <td class="py-3 px-4 text-brandGreen font-mono">{{ formatCurrency(b.high, b.ticker, viewCurrency) }}</td>
              <td class="py-3 px-4 text-brandRed font-mono">{{ formatCurrency(b.low, b.ticker, viewCurrency) }}</td>
              <td class="py-3 px-4 font-bold font-mono">{{ formatCurrency(b.close, b.ticker, viewCurrency) }}</td>
              <td class="py-3 px-4 text-right text-slate-400 font-mono">{{ formatNumber(b.volume) }}</td>
            </tr>
            <tr v-if="dbData.bars.length === 0" class="text-slate-500 text-center">
              <td colspan="7" class="py-10">최근 적재된 캔들 가격 데이터가 없습니다.</td>
            </tr>
          </tbody>
        </table>
        
        <!-- Pagination Controls -->
        <div v-if="dbActiveTab === 'clickhouse'" class="flex items-center justify-between mt-4">
          <span class="text-xs text-slate-500">Page {{ dbFilters.page }}</span>
          <div class="flex gap-2">
            <button @click="prevPage" :disabled="dbFilters.page <= 1" class="bg-slate-800 text-xs px-3 py-1 rounded text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700 border border-slate-700">Previous</button>
            <button @click="nextPage" :disabled="dbData.bars.length < dbFilters.limit" class="bg-slate-800 text-xs px-3 py-1 rounded text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700 border border-slate-700">Next</button>
          </div>
        </div>

        <!-- MongoDB news list cards -->
        <div v-if="dbActiveTab === 'mongodb'" class="flex flex-col gap-4">
          <div v-for="(n, idx) in dbData.news" :key="idx" class="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-col gap-2">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-[10px] bg-brandGreen/10 text-brandGreen px-2 py-0.5 rounded font-extrabold uppercase font-mono tracking-wider">{{ n.source }}</span>
                <span v-if="n.ticker" class="text-[10px] bg-brandIndigo/10 text-brandIndigo px-2 py-0.5 rounded font-extrabold uppercase font-mono tracking-wider">{{ n.ticker }}</span>
              </div>
              <span class="text-[10px] text-slate-500 font-medium">{{ formatDateTime(n.published_at) }}</span>
            </div>
            <h5 class="text-xs font-bold text-white leading-snug">{{ n.title }}</h5>
            <p class="text-[11px] text-slate-400 font-light mt-1">{{ n.summary }}</p>
            <a :href="n.url" target="_blank" class="text-[10px] text-brandGreen hover:underline self-end font-semibold font-outfit uppercase mt-2">원문보기 &rarr;</a>
          </div>
          <div v-if="dbData.news.length === 0" class="text-slate-500 text-center py-10">최근 적재된 거시 뉴스 기사 데이터가 없습니다.</div>
        </div>

        <!-- DuckDB technical indicators table -->
        <table v-if="dbActiveTab === 'duckdb'" class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-slate-800/80 text-slate-500 font-semibold">
              <th class="py-3 px-4">종목 코드</th>
              <th class="py-3 px-4">연산 시간</th>
              <th class="py-3 px-4">이동평균 SMA 5</th>
              <th class="py-3 px-4">이동평균 SMA 20</th>
              <th class="py-3 px-4">RSI (지표 수치)</th>
              <th class="py-3 px-4 text-right font-mono">가중치 모멘텀</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(f, idx) in dbData.features" :key="idx" class="border-b border-slate-800/30 hover:bg-slate-900/30 text-white font-sans">
              <td class="py-3 px-4 font-bold text-brandGold">{{ f.ticker }}</td>
              <td class="py-3 px-4 text-slate-400">{{ formatDateTime(f.timestamp) }}</td>
              <td class="py-3 px-4 font-mono">{{ formatCurrency(f.features.sma_5, f.ticker, viewCurrency) }}</td>
              <td class="py-3 px-4 font-mono">{{ formatCurrency(f.features.sma_20, f.ticker, viewCurrency) }}</td>
              <td class="py-3 px-4 font-bold" :class="f.features.rsi > 70 ? 'text-brandRed' : (f.features.rsi < 30 ? 'text-brandGreen' : 'text-slate-300')">
                {{ f.features.rsi ? f.features.rsi.toFixed(2) : '0.00' }}
              </td>
              <td class="py-3 px-4 text-right text-slate-400 font-mono">{{ f.features.momentum ? f.features.momentum.toFixed(4) : '0.0000' }}</td>
            </tr>
            <tr v-if="dbData.features.length === 0" class="text-slate-500 text-center">
              <td colspan="6" class="py-10">최근 연산된 오프라인 기술 지표 피처 데이터가 없습니다.</td>
            </tr>
          </tbody>
        </table>

        <!-- PostgreSQL relational tables -->
        <div v-if="dbActiveTab === 'postgres'" class="flex flex-col gap-6">
          <div>
            <h5 class="text-xs font-bold text-brandPurple uppercase tracking-wider mb-3">Watchlist Persistent Table</h5>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div v-for="t in watchlist" :key="t" class="bg-slate-900/40 border border-slate-800/60 rounded-xl p-3 flex justify-between items-center text-xs text-white">
                <span class="font-outfit font-extrabold text-brandPurple">{{ t }}</span>
                <span class="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-bold font-sans">SQL Row</span>
              </div>
            </div>
          </div>
          <div class="border-t border-slate-800/60 pt-6">
            <h5 class="text-xs font-bold text-brandPurple uppercase tracking-wider mb-3">Orders Transaction Log</h5>
            <table class="w-full text-left border-collapse text-xs">
              <thead>
                <tr class="border-b border-slate-800/80 text-slate-500 font-semibold">
                  <th class="py-3 px-4">주문 ID</th>
                  <th class="py-3 px-4">종목 코드</th>
                  <th class="py-3 px-4">거래 유형</th>
                  <th class="py-3 px-4">체결 수량</th>
                  <th class="py-3 px-4">평균 체결가</th>
                  <th class="py-3 px-4 text-right">체결 상태</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="o in ordersLog" :key="o.order_id" class="border-b border-slate-800/30 hover:bg-slate-900/30 text-white font-sans">
                  <td class="py-3 px-4 text-slate-500 font-mono">{{ o.order_id }}</td>
                  <td class="py-3 px-4 font-bold">{{ o.ticker }}</td>
                  <td class="py-3 px-4" :class="o.action === 'BUY' ? 'text-brandGreen' : 'text-brandRed'">{{ o.action }}</td>
                  <td class="py-3 px-4">{{ o.quantity }} 주</td>
                  <td class="py-3 px-4 font-mono">{{ formatCurrency(o.price, o.ticker, viewCurrency) }}</td>
                  <td class="py-3 px-4 text-right">
                    <span :class="['px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', getStatusBadgeClass(o.status)]">
                      {{ o.status }}
                    </span>
                  </td>
                </tr>
                <tr v-if="ordersLog.length === 0" class="text-slate-500 text-center">
                  <td colspan="6" class="py-10">최근 실행된 ACID 트랜잭션 매매 이력이 없습니다.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
