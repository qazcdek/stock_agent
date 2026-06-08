<script setup>
import { onMounted } from 'vue';
import {
  watchlist,
  simRequest,
  simLoading,
  simReport,
  simLogs,
  triggerAsyncBacktest,
  fetchWatchlist,
  formatNumber,
  formatCurrency,
  viewCurrency
} from '../store/tradingStore.js';

function startBacktestRun() {
  triggerAsyncBacktest(simRequest.tickers, simRequest.days);
}

onMounted(() => {
  fetchWatchlist();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Setup parameters box -->
      <div class="glass-card lg:col-span-1 p-5 flex flex-col gap-4 h-fit">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandGold" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
            백테스트 엔진 시뮬레이터 설정
          </h3>
        </div>
        
        <div class="flex flex-col gap-4">
          <!-- Tickers checkbox list -->
          <div class="flex flex-col gap-2">
            <label class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">대상 종목 선택 (Multi-Tickers)</label>
            <div class="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3 flex flex-col gap-2 max-h-[150px] overflow-y-auto">
              <div v-for="t in watchlist" :key="t" class="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  :id="'sim-'+t"
                  :value="t"
                  v-model="simRequest.tickers"
                  class="rounded border-slate-700 bg-slate-900 text-brandIndigo focus:ring-brandIndigo cursor-pointer"
                />
                <label :for="'sim-'+t" class="text-slate-300 font-outfit select-none cursor-pointer">{{ t }}</label>
              </div>
              <div v-if="watchlist.length === 0" class="text-slate-500 text-xs italic text-center py-2">Watchlist is empty.</div>
            </div>
          </div>

          <!-- Backtest Duration selection -->
          <div class="flex flex-col gap-2">
            <label class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">백테스팅 기간 (과거 lookback)</label>
            <select
              v-model="simRequest.days"
              class="bg-slate-900/60 border border-slate-800/80 text-xs px-3 py-2.5 rounded-xl text-white focus:outline-none focus:border-brandIndigo cursor-pointer"
            >
              <option :value="1">1일 과속 테스트 (1 Day)</option>
              <option :value="2">2일 과속 테스트 (2 Days)</option>
              <option :value="5">5일 고화질 분석 (5 Days)</option>
            </select>
          </div>

          <button
            @click="startBacktestRun"
            :disabled="simRequest.tickers.length === 0 || simLoading"
            class="w-full bg-gradient-to-tr from-brandIndigo to-brandGreen hover:opacity-90 disabled:opacity-50 text-white font-extrabold text-sm py-3.5 rounded-xl shadow-md font-outfit uppercase mt-2 cursor-pointer transition-opacity"
          >
            {{ simLoading ? '시뮬레이션 실행 중...' : '비동기 백테스트 실행' }}
          </button>
        </div>
      </div>

      <!-- Backtest engine simulator reports & logs -->
      <div class="glass-card lg:col-span-2 p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandIndigo" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            시뮬레이터 평가 리포트 (Async Backtest)
          </h3>
          <span v-if="simLoading" class="text-[9px] bg-brandIndigo/20 text-brandIndigo px-2 py-0.5 rounded-full font-bold animate-pulse font-mono">
            Running Fast-Forward Ticks...
          </span>
        </div>

        <!-- Final metrics card -->
        <div v-if="simReport" class="grid grid-cols-2 md:grid-cols-4 gap-4 bg-indigo-950/20 border border-brandIndigo/20 rounded-xl p-4 font-outfit">
          <div class="flex flex-col">
            <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">최종 포트폴리오 평가액</span>
            <span class="text-lg font-extrabold text-white">{{ formatCurrency(simReport.final_value, '', viewCurrency) }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">누적 수익률</span>
            <span class="text-lg font-extrabold" :class="simReport.return_pct >= 0 ? 'text-brandGreen' : 'text-brandRed'">
              {{ simReport.return_pct >= 0 ? '+' : '' }}{{ simReport.return_pct }}%
            </span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">최대 낙폭 (MDD)</span>
            <span class="text-lg font-extrabold text-brandRed">{{ simReport.mdd }}%</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">샤프 지수 (Sharpe Ratio)</span>
            <span class="text-lg font-extrabold text-brandGreen">{{ simReport.sharpe_ratio }}</span>
          </div>
        </div>

        <!-- Live simulation progress terminal -->
        <div class="flex flex-col gap-2">
          <label class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">백테스팅 백그라운드 엔진 로그</label>
          <div class="h-[200px] bg-slate-950/90 border border-slate-900 rounded-xl p-4 overflow-y-auto flex flex-col gap-2 font-mono text-[10px]">
            <div v-for="(log, idx) in simLogs" :key="idx" class="flex gap-2">
              <span class="text-slate-600 select-none">[{{ log.time }}]</span>
              <span :class="log.color ? 'text-' + log.color : 'text-slate-300'">{{ log.text }}</span>
            </div>
            <div v-if="simLogs.length === 0" class="text-slate-600 text-center py-16 font-sans italic">
              비동기 시뮬레이션을 실행하면 백그라운드 스레드에서 생성된 체결 모의 Adapter 로그가 즉시 실시간 갱신됩니다.
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
