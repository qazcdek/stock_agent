<script setup>
import { onMounted, ref, watch } from 'vue';
import {
  watchlist,
  fetchWatchlist,
  apiBase,
  formatCurrency,
  viewCurrency,
  formatNumber
} from '../store/tradingStore.js';

const activeDb = ref("clickhouse");
const selectedTicker = ref("");
const queryLimit = ref(25);
const queryResult = ref([]);
const queryLoading = ref(false);

async function executeQuery() {
  queryLoading.value = true;
  try {
    let url = `${apiBase}/api/data/query?db=${activeDb.value}&limit=${queryLimit.value}`;
    if (selectedTicker.value) {
      url += `&ticker=${encodeURIComponent(selectedTicker.value)}`;
    }
    const res = await fetch(url);
    if (res.ok) {
      queryResult.value = await res.json();
    }
  } catch (e) {
    console.error("Failed to run DB query", e);
  } finally {
    queryLoading.value = false;
  }
}

watch(activeDb, () => {
  queryResult.value = [];
  executeQuery();
});

onMounted(async () => {
  await fetchWatchlist();
  if (watchlist.value.length > 0) {
    selectedTicker.value = watchlist.value[0];
  }
  executeQuery();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- DB Tab selector buttons -->
    <div class="glass-card p-4 flex flex-wrap gap-2 select-none">
      <button
        @click="activeDb = 'clickhouse'"
        :class="[
          'flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold uppercase font-outfit tracking-wide transition-all border cursor-pointer',
          activeDb === 'clickhouse' ? 'border-brandIndigo text-brandIndigo bg-brandIndigo/5' : 'border-slate-800 text-slate-400 hover:text-white'
        ]"
      >
        <span>ClickHouse (시계열 종가 데이터)</span>
      </button>
      <button
        @click="activeDb = 'mongodb'"
        :class="[
          'flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold uppercase font-outfit tracking-wide transition-all border cursor-pointer',
          activeDb === 'mongodb' ? 'border-brandGreen text-brandGreen bg-brandGreen/5' : 'border-slate-800 text-slate-400 hover:text-white'
        ]"
      >
        <span>MongoDB (비정형 경제 뉴스)</span>
      </button>
      <button
        @click="activeDb = 'duckdb'"
        :class="[
          'flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold uppercase font-outfit tracking-wide transition-all border cursor-pointer',
          activeDb === 'duckdb' ? 'border-brandGold text-brandGold bg-brandGold/5' : 'border-slate-800 text-slate-400 hover:text-white'
        ]"
      >
        <span>DuckDB (계산된 테크니컬 피처)</span>
      </button>
      <button
        @click="activeDb = 'postgres'"
        :class="[
          'flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold uppercase font-outfit tracking-wide transition-all border cursor-pointer',
          activeDb === 'postgres' ? 'border-brandPurple text-brandPurple bg-brandPurple/5' : 'border-slate-800 text-slate-400 hover:text-white'
        ]"
      >
        <span>PostgreSQL ( watchlist & 트랜잭션 )</span>
      </button>
    </div>

    <!-- Filters row -->
    <div class="glass-card p-4 flex flex-wrap items-end gap-3 text-xs">
      <div class="flex flex-col gap-1">
        <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">대상 종목</span>
        <select
          v-model="selectedTicker"
          class="bg-slate-900 border border-slate-800 p-2.5 rounded-xl text-white focus:outline-none focus:border-brandIndigo cursor-pointer"
        >
          <option v-for="t in watchlist" :key="t" :value="t">{{ t }}</option>
          <option value="">전체 (All Tickers)</option>
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">조회 로우 제한</span>
        <select
          v-model.number="queryLimit"
          class="bg-slate-900 border border-slate-800 p-2.5 rounded-xl text-white focus:outline-none focus:border-brandIndigo cursor-pointer"
        >
          <option :value="10">10 rows</option>
          <option :value="25">25 rows</option>
          <option :value="50">50 rows</option>
          <option :value="100">100 rows</option>
        </select>
      </div>

      <button
        @click="executeQuery"
        class="bg-brandIndigo hover:bg-indigo-600 text-white font-bold px-5 py-2.5 rounded-xl cursor-pointer self-end transition-colors"
      >
        쿼리 실행
      </button>
    </div>

    <!-- Results Box -->
    <div class="glass-card p-5">
      <div class="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-4">
        <h4 class="font-outfit font-extrabold text-xs text-white uppercase tracking-wider">
          Query Results Grid (API: GET /api/data/query)
        </h4>
        <span v-if="queryLoading" class="text-[9px] bg-brandIndigo/20 text-brandIndigo px-2 py-0.5 rounded-full font-bold animate-pulse font-mono">
          Querying Database...
        </span>
      </div>

      <!-- Loading State -->
      <div v-if="queryLoading" class="text-center py-20 text-slate-500 text-xs">
        데이터베이스 레코드를 로드하고 있습니다...
      </div>

      <!-- Query tables content -->
      <div v-else class="overflow-x-auto">
        <!-- ClickHouse Bars -->
        <table v-if="activeDb === 'clickhouse'" class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-slate-800/80 text-slate-500 font-semibold">
              <th class="py-2.5 px-3">종목 코드</th>
              <th class="py-2.5 px-3">날짜/시간</th>
              <th class="py-2.5 px-3">시가</th>
              <th class="py-2.5 px-3">고가</th>
              <th class="py-2.5 px-3">저가</th>
              <th class="py-2.5 px-3">종가</th>
              <th class="py-2.5 px-3 text-right">거래량</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(b, idx) in queryResult" :key="idx" class="border-b border-slate-800/30 hover:bg-slate-900/10 text-white font-sans">
              <td class="py-3 px-3 font-bold text-brandIndigo">{{ b.ticker }}</td>
              <td class="py-3 px-3 text-slate-400 font-mono">{{ b.timestamp.replace('T', ' ').substring(0, 16) }}</td>
              <td class="py-3 px-3 font-mono">{{ formatCurrency(b.open, b.ticker, viewCurrency) }}</td>
              <td class="py-3 px-3 text-brandGreen font-mono">{{ formatCurrency(b.high, b.ticker, viewCurrency) }}</td>
              <td class="py-3 px-3 text-brandRed font-mono">{{ formatCurrency(b.low, b.ticker, viewCurrency) }}</td>
              <td class="py-3 px-3 font-bold font-mono">{{ formatCurrency(b.close, b.ticker, viewCurrency) }}</td>
              <td class="py-3 px-3 text-right text-slate-400 font-mono">{{ formatNumber(b.volume) }}</td>
            </tr>
            <tr v-if="queryResult.length === 0" class="text-slate-500 text-center py-10">
              <td colspan="7">조회된 가격 시계열 데이터가 없습니다.</td>
            </tr>
          </tbody>
        </table>

        <!-- MongoDB News articles -->
        <div v-else-if="activeDb === 'mongodb'" class="flex flex-col gap-4">
          <div v-for="(n, idx) in queryResult" :key="idx" class="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-col gap-2">
            <div class="flex justify-between items-center text-[10px] text-slate-500">
              <span class="bg-brandGreen/10 text-brandGreen px-2 py-0.5 rounded font-extrabold uppercase font-mono tracking-wider">{{ n.source }}</span>
              <span>{{ n.published_at.replace('T', ' ').substring(0, 16) }}</span>
            </div>
            <h5 class="text-xs font-bold text-white leading-snug">{{ n.title }}</h5>
            <p class="text-[11px] text-slate-400 font-light mt-1">{{ n.summary }}</p>
          </div>
          <div v-if="queryResult.length === 0" class="text-slate-500 text-center py-10">조회된 비정형 거시 뉴스 데이터가 없습니다.</div>
        </div>

        <!-- DuckDB indicators -->
        <table v-else-if="activeDb === 'duckdb'" class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-slate-800/80 text-slate-500 font-semibold">
              <th class="py-2.5 px-3">종목 코드</th>
              <th class="py-2.5 px-3">연산 시간</th>
              <th class="py-2.5 px-3">SMA 5일선</th>
              <th class="py-2.5 px-3">SMA 20일선</th>
              <th class="py-2.5 px-3">RSI 지표</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(f, idx) in queryResult.features" :key="idx" class="border-b border-slate-800/30 hover:bg-slate-900/10 text-white font-sans">
              <td class="py-3 px-3 font-bold text-brandGold">{{ f.ticker }}</td>
              <td class="py-3 px-3 text-slate-400 font-mono">{{ f.timestamp.replace('T', ' ').substring(0, 16) }}</td>
              <td class="py-3 px-3 font-mono">{{ formatCurrency(f.features.sma_5, f.ticker, viewCurrency) }}</td>
              <td class="py-3 px-3 font-mono">{{ formatCurrency(f.features.sma_20, f.ticker, viewCurrency) }}</td>
              <td class="py-3 px-3 font-bold" :class="f.features.rsi > 70 ? 'text-brandRed' : (f.features.rsi < 30 ? 'text-brandGreen' : 'text-slate-300')">
                {{ f.features.rsi ? f.features.rsi.toFixed(2) : '0.00' }}
              </td>
            </tr>
            <tr v-if="!queryResult.features || queryResult.features.length === 0" class="text-slate-500 text-center py-10">
              <td colspan="5">조회된 DuckDB 테크니컬 피처 연산 데이터가 없습니다.</td>
            </tr>
          </tbody>
        </table>

        <!-- Postgres configuration lists -->
        <div v-else-if="activeDb === 'postgres'" class="flex flex-col gap-4 text-xs font-sans">
          <div class="bg-slate-900/40 p-4 rounded-xl border border-slate-800/80 flex flex-col gap-3">
            <h5 class="text-xs font-bold text-brandPurple uppercase tracking-wider border-b border-slate-800 pb-2">Watchlist Table Rows</h5>
            <div class="flex flex-wrap gap-2">
              <span v-for="t in queryResult.watchlist" :key="t" class="bg-slate-800 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 font-mono font-bold">{{ t }}</span>
              <span v-if="!queryResult.watchlist || queryResult.watchlist.length === 0" class="text-slate-500 italic">No watchlist tickers found in relational store.</span>
            </div>
          </div>
          <div class="bg-slate-900/40 p-4 rounded-xl border border-slate-800/80 flex justify-between items-center">
            <span class="text-slate-300 font-bold">Total Orders Count in RDB (orders table)</span>
            <span class="text-base font-extrabold text-brandPurple font-mono">{{ queryResult.orders_count || 0 }} rows</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
