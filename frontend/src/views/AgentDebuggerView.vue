<script setup>
import { onMounted, ref, watch } from 'vue';
import {
  watchlist,
  blackboardState,
  fetchBlackboardState,
  fetchWatchlist
} from '../store/tradingStore.js';

const selectedTicker = ref("");

async function updateState() {
  await fetchBlackboardState(selectedTicker.value);
}

function getActionBadgeClass(action) {
  if (action === 'BUY') return 'bg-brandGreen/15 text-brandGreen border border-brandGreen/25';
  if (action === 'SELL') return 'bg-brandRed/15 text-brandRed border border-brandRed/25';
  return 'bg-slate-800 text-slate-400 border border-slate-700/50';
}

watch(selectedTicker, () => {
  updateState();
});

onMounted(async () => {
  await fetchWatchlist();
  if (watchlist.value.length > 0) {
    selectedTicker.value = watchlist.value[0];
  }
  updateState();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="glass-card p-6 flex flex-col gap-6">
      
      <!-- Top header and selector -->
      <div class="flex flex-col md:flex-row items-start md:items-end justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h3 class="font-outfit font-extrabold text-base text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-brandPurple" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            에이전트 협업 블랙보드 디버거 (Blackboard Debugger)
          </h3>
          <p class="text-xs text-slate-400 mt-1">블랙보드 아키텍처에 기록된 각 독립적 분석가 에이전트들의 실시간 추론 상태 및 신호 강도를 디버깅합니다.</p>
        </div>
        
        <div class="flex items-center gap-2 text-xs">
          <span class="text-slate-500 font-bold uppercase tracking-wider">대상 종목 선택</span>
          <select
            v-model="selectedTicker"
            class="bg-slate-900 border border-slate-800 p-2.5 rounded-xl text-white focus:outline-none focus:border-brandPurple cursor-pointer"
          >
            <option v-for="t in watchlist" :key="t" :value="t">{{ t }}</option>
            <option v-if="watchlist.length === 0" value="">관심종목을 등록하세요</option>
          </select>
        </div>
      </div>

      <!-- Live blackboard state columns -->
      <div v-if="selectedTicker && blackboardState[selectedTicker]" class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div
          v-for="cand in blackboardState[selectedTicker]"
          :key="cand.source_agent"
          class="bg-slate-950/60 border border-slate-800/80 rounded-xl p-5 flex flex-col justify-between gap-4"
        >
          <div class="flex flex-col gap-3">
            <div class="flex justify-between items-center border-b border-slate-900 pb-2">
              <span class="font-outfit font-extrabold text-sm text-slate-200">{{ cand.source_agent }}</span>
              <span :class="['px-2 py-0.5 rounded text-[10px] font-bold uppercase', getActionBadgeClass(cand.action)]">
                {{ cand.action }}
              </span>
            </div>
            
            <div class="flex items-center justify-between text-xs mt-1">
              <span class="text-slate-500 font-medium">신호 가중치 (Confidence):</span>
              <span class="text-white font-extrabold font-mono text-sm">{{ (cand.weight * 100).toFixed(0) }}%</span>
            </div>

            <div class="flex flex-col gap-1 mt-1">
              <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">추론 및 산출 사유</span>
              <p class="text-[11px] text-slate-300 leading-relaxed bg-slate-900/40 p-2.5 rounded-lg border border-slate-900 font-sans italic">
                "{{ cand.reason }}"
              </p>
            </div>
          </div>
          
          <div class="text-[9px] text-slate-600 font-mono flex items-center justify-between border-t border-slate-900/50 pt-2">
            <span>블랙보드 게시 시간</span>
            <span>{{ cand.timestamp.replace('T', ' ').substring(11, 19) }}</span>
          </div>
        </div>
      </div>

      <div v-else class="text-center py-24 text-slate-500 italic text-xs">
        관심 종목을 선택하시면 블랙보드 실시간 에이전트 기록이 렌더링됩니다.
      </div>
    </div>
  </div>
</template>
