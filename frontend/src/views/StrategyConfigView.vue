<script setup>
import { onMounted } from 'vue';
import {
  strategySettings,
  fetchStrategySettings,
  saveStrategySettings
} from '../store/tradingStore.js';

function submitSettings() {
  saveStrategySettings(strategySettings.value);
}

onMounted(() => {
  fetchStrategySettings();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="glass-card p-6 flex flex-col gap-6 max-w-4xl">
      <div class="border-b border-slate-800/80 pb-4">
        <h3 class="font-outfit font-extrabold text-base text-white tracking-wide uppercase flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-brandIndigo" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
          블랙보드 전략 합성 규칙 설정 (Strategy Config)
        </h3>
        <p class="text-xs text-slate-400 mt-1">개별 추론 에이전트(Technical, Fundamental, ML) 신호 제안의 가중치 비율과 최종 주문 승인 문턱값을 동적 튜닝합니다.</p>
      </div>

      <div class="flex flex-col gap-5 text-xs">
        
        <!-- Buy/Sell Threshold settings -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">매수 신호 임계값 (Buy Threshold)</label>
            <input
              type="number"
              step="0.05"
              v-model.number="strategySettings.buy_threshold"
              class="bg-slate-900 border border-slate-800 p-3 rounded-xl text-white font-mono font-bold focus:outline-none focus:border-brandIndigo"
            />
            <span class="text-[10px] text-slate-500">가중 합성 스코어가 해당 값 이상일 때 매수 제안을 발송합니다. (추천: 0.25)</span>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">매도 신호 임계값 (Sell Threshold)</label>
            <input
              type="number"
              step="0.05"
              v-model.number="strategySettings.sell_threshold"
              class="bg-slate-900 border border-slate-800 p-3 rounded-xl text-white font-mono font-bold focus:outline-none focus:border-brandIndigo"
            />
            <span class="text-[10px] text-slate-500">가중 합성 스코어가 해당 값 이하일 때 매도 제안을 발송합니다. (추천: -0.25)</span>
          </div>
        </div>

        <div class="border-t border-slate-800/80 pt-4 mt-2">
          <span class="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-3">에이전트 가중치 배분 목록 (Agent Weights)</span>
          
          <div class="flex flex-col gap-4">
            <div
              v-for="strategy in strategySettings.strategies"
              :key="strategy.name"
              class="bg-slate-950/60 border border-slate-800/60 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4"
            >
              <div class="flex flex-col gap-1">
                <span class="font-outfit font-extrabold text-sm text-white">{{ strategy.name }}</span>
                <span class="text-xs text-slate-500 font-light">{{ strategy.description }}</span>
              </div>
              
              <div class="flex items-center gap-4">
                <div class="flex flex-col gap-1">
                  <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider text-right">가중치 비율</span>
                  <input
                    type="number"
                    step="0.05"
                    v-model.number="strategy.weight"
                    class="bg-slate-900 border border-slate-800 p-2 rounded-lg text-white font-mono font-bold w-24 text-center focus:outline-none focus:border-brandIndigo"
                  />
                </div>
                
                <div class="flex flex-col gap-2 items-center">
                  <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">활성화</span>
                  <label class="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" v-model="strategy.active" class="sr-only peer">
                    <div class="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-brandIndigo"></div>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <button
          @click="submitSettings"
          class="w-full bg-gradient-to-tr from-brandIndigo to-brandGreen hover:opacity-90 text-white font-extrabold text-xs py-3.5 rounded-xl shadow-md font-outfit uppercase mt-4 cursor-pointer"
        >
          설정 매개변수 저장 (Save Parameters)
        </button>
      </div>
    </div>
  </div>
</template>
