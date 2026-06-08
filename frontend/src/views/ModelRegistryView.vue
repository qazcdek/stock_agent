<script setup>
import { onMounted } from 'vue';
import {
  modelRegistry,
  watchlist,
  fetchModelRegistry,
  trainModel,
  fetchWatchlist
} from '../store/tradingStore.js';

onMounted(() => {
  fetchWatchlist();
  fetchModelRegistry();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="glass-card p-6 flex flex-col gap-6">
      
      <!-- Top header bar -->
      <div class="flex items-center justify-between border-b border-slate-800/80 pb-4">
        <div>
          <h3 class="font-outfit font-extrabold text-base text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-brandIndigo" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 9.172V5L8 4z" />
            </svg>
            머신러닝 모델 레지스트리 (Model Registry)
          </h3>
          <p class="text-xs text-slate-400 mt-1">개별 주식 종목의 과거 가격 캔들 데이터에 기초해 훈련된 예측 OLS 회귀 모델 파라미터를 관리합니다.</p>
        </div>
        <button @click="fetchModelRegistry" class="text-slate-500 hover:text-white text-[10px] uppercase font-bold cursor-pointer">
          레지스트리 갱신
        </button>
      </div>

      <!-- Main models list table -->
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-slate-800/80 text-slate-500 font-semibold">
              <th class="py-3 px-4">종목 코드</th>
              <th class="py-3 px-4">선형 추세 기울기 (Slope)</th>
              <th class="py-3 px-4">Y축 절편 (Intercept)</th>
              <th class="py-3 px-4">R-제곱 설명력 (R-Squared)</th>
              <th class="py-3 px-4">마지막 훈련 시간</th>
              <th class="py-3 px-4">학습 상태</th>
              <th class="py-3 px-4 text-right">훈련 관리</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="model in modelRegistry" :key="model.ticker" class="border-b border-slate-800/30 hover:bg-slate-900/10 text-white font-sans">
              <td class="py-3.5 px-4 font-bold text-white">{{ model.ticker }}</td>
              <td class="py-3.5 px-4 font-mono">{{ model.slope.toFixed(6) }}</td>
              <td class="py-3.5 px-4 font-mono">{{ model.intercept.toLocaleString(undefined, {minimumFractionDigits: 2}) }}</td>
              <td class="py-3.5 px-4 font-mono text-brandGreen font-bold">{{ model.r_squared.toFixed(4) }}</td>
              <td class="py-3.5 px-4 text-slate-400 font-mono">{{ model.last_trained ? model.last_trained.replace('T', ' ').substring(0, 19) : '-' }}</td>
              <td class="py-3.5 px-4">
                <span :class="['px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border', 
                  model.status === 'TRAINED' ? 'bg-emerald-950/60 text-brandGreen border-brandGreen/25' : 'bg-slate-900 text-slate-500 border-slate-800'
                ]">
                  {{ model.status }}
                </span>
              </td>
              <td class="py-3.5 px-4 text-right">
                <button
                  @click="trainModel(model.ticker)"
                  class="bg-brandIndigo/20 hover:bg-brandIndigo/40 text-brandIndigo hover:text-white px-3 py-1.5 rounded-lg border border-brandIndigo/30 text-[10px] font-bold uppercase transition-all cursor-pointer"
                >
                  모델 훈련 (Train)
                </button>
              </td>
            </tr>
            <tr v-if="modelRegistry.length === 0" class="text-slate-500 text-center font-sans">
              <td colspan="7" class="py-12">관심종목을 등록하시면 훈련 가능한 예측 모델이 레지스트리에 자동 매핑됩니다.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
