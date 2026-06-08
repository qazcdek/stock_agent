<script setup>
import { onMounted } from 'vue';
import {
  watchlist,
  newTickerInput,
  tickerCorrection,
  onTickerInput,
  applyTickerCorrection,
  addWatchlistTicker,
  removeWatchlistTicker,
  fetchWatchlist,
  dbData,
  loadDBData,
  dbActiveTab
} from '../store/tradingStore.js';

onMounted(async () => {
  await fetchWatchlist();
  dbActiveTab.value = 'mongodb';
  await loadDBData(); // load news from MongoDB
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Left: Watchlist Editor Card -->
      <div class="glass-card lg:col-span-1 p-5 flex flex-col gap-4 h-fit">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandGold" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.907c.961 0 1.367 1.243.583 1.83l-3.978 2.89a1 1 0 00-.364 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.583-1.83h4.907a1 1 0 00.95-.69l1.519-4.674z" />
            </svg>
            관심종목 관리 (Watchlist)
          </h3>
        </div>

        <div class="flex flex-col gap-4">
          <!-- Input Form with Autocomplete -->
          <div class="flex flex-col gap-2 relative">
            <label class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">새 종목 코드 등록 (Standard Ticker)</label>
            <div class="flex gap-2">
              <input
                type="text"
                v-model="newTickerInput"
                @input="onTickerInput"
                placeholder="예: 005930, AAPL, BTC"
                class="flex-1 bg-slate-900/60 border border-slate-800/80 px-3.5 py-2 rounded-xl text-white text-xs focus:outline-none focus:border-brandIndigo"
              />
              <button
                @click="addWatchlistTicker"
                class="bg-brandIndigo hover:bg-indigo-600 text-white font-bold px-4 rounded-xl text-xs cursor-pointer transition-colors"
              >
                추가
              </button>
            </div>

            <!-- Autocomplete Suggestion Dropdown -->
            <div
              v-if="tickerCorrection"
              class="absolute top-16 left-0 right-0 z-40 bg-slate-900 border border-brandIndigo/40 rounded-xl p-3 shadow-2xl flex flex-col gap-2 cursor-pointer"
              @click="applyTickerCorrection"
            >
              <div class="flex items-center gap-2">
                <span class="w-1.5 h-1.5 rounded-full bg-brandIndigo animate-ping"></span>
                <span class="text-[10px] text-slate-400 font-medium">LLM 추천 교정 코드:</span>
              </div>
              <div class="flex justify-between items-center text-xs">
                <span class="text-white font-bold font-outfit">{{ tickerCorrection.corrected }}</span>
                <span class="text-slate-400 font-medium">{{ tickerCorrection.name }} ({{ tickerCorrection.exchange }})</span>
              </div>
            </div>
          </div>

          <!-- Watchlist Symbols list -->
          <div class="flex flex-col gap-2 mt-2">
            <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">등록된 감시 종목 목록</span>
            <div class="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-1">
              <div
                v-for="t in watchlist"
                :key="t"
                class="flex items-center justify-between bg-slate-900/40 border border-slate-800/60 p-3 rounded-xl"
              >
                <div class="flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-brandGreen glow-dot text-brandGreen"></span>
                  <span class="font-outfit font-extrabold text-xs text-white">{{ t }}</span>
                </div>
                <button
                  @click="removeWatchlistTicker(t)"
                  class="text-[10px] text-slate-500 hover:text-brandRed font-bold cursor-pointer transition-colors"
                >
                  삭제
                </button>
              </div>
              <div v-if="watchlist.length === 0" class="text-center py-6 text-xs text-slate-500 italic">
                관심종목 대기열이 비어있습니다.
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Real-time News Articles Grid -->
      <div class="glass-card lg:col-span-2 p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandIndigo" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
            </svg>
            관심종목 실시간 뉴스 수집 현황 (MongoDB)
          </h3>
        </div>

        <div class="flex flex-col gap-4 overflow-y-auto max-h-[450px] pr-1">
          <div
            v-for="(news, idx) in dbData.news"
            :key="idx"
            class="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-col gap-2 hover:border-slate-700/60 transition-colors"
          >
            <div class="flex justify-between items-start">
              <span class="text-[9px] bg-brandIndigo/10 text-brandIndigo px-2 py-0.5 rounded font-mono font-bold">{{ news.ticker }}</span>
              <span class="text-[10px] text-slate-500 font-mono">{{ news.published_at.replace('T', ' ').substring(0, 16) }}</span>
            </div>
            <h4 class="text-xs font-bold text-white leading-snug">{{ news.title }}</h4>
            <p class="text-[11px] text-slate-400 leading-normal">{{ news.summary }}</p>
            <div class="flex justify-between items-center text-[9px] text-slate-500 font-medium mt-1">
              <span>출처: {{ news.source }}</span>
              <a :href="news.url" target="_blank" class="text-brandIndigo hover:underline">기사 원문 보기 &rarr;</a>
            </div>
          </div>
          <div v-if="dbData.news.length === 0" class="text-center py-24 text-slate-500 text-xs italic">
            수집된 실시간 감시 뉴스가 없습니다.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
