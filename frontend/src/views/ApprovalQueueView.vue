<script setup>
import { onMounted } from 'vue';
import {
  approvalsList,
  fetchApprovals,
  handleApprovalAction,
  formatCurrency,
  viewCurrency
} from '../store/tradingStore.js';

onMounted(() => {
  fetchApprovals();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="glass-card p-6 flex flex-col gap-4">
      <div class="flex items-center justify-between border-b border-slate-800/80 pb-4">
        <div>
          <h3 class="font-outfit font-extrabold text-base text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-brandGold" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            AI 매매 승인 대기열 (Approval Queue)
          </h3>
          <p class="text-xs text-slate-400 mt-1">블랙보드 에이전트 협업 엔진이 도출한 매매 제안을 수동 승인하는 안전 관리 게이트웨이입니다.</p>
        </div>
        <span class="text-xs bg-slate-800 text-slate-300 px-3 py-1 rounded-full font-bold font-mono">
          대기 중: {{ approvalsList.length }} 건
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-2">
        <div
          v-for="item in approvalsList"
          :key="item.queue_id"
          class="bg-slate-950/60 border border-slate-800/80 hover:border-brandIndigo/30 rounded-xl p-5 flex flex-col justify-between gap-4 transition-all duration-300"
        >
          <div class="flex flex-col gap-3">
            <div class="flex justify-between items-center">
              <span class="font-outfit font-extrabold text-base text-white tracking-tight">{{ item.intent.ticker }}</span>
              <span :class="['px-2.5 py-0.5 rounded text-[10px] font-extrabold uppercase border', 
                item.intent.action === 'BUY' ? 'bg-brandGreen/15 text-brandGreen border-brandGreen/25' : 'bg-brandRed/15 text-brandRed border-brandRed/25'
              ]">
                {{ item.intent.action }}
              </span>
            </div>

            <div class="grid grid-cols-2 gap-4 bg-slate-900/30 p-3 rounded-lg border border-slate-800/40 text-xs font-sans text-slate-400">
              <div>수량: <span class="text-white font-bold">{{ item.intent.quantity }} 주</span></div>
              <div>가격: <span class="text-white font-bold font-mono">{{ formatCurrency(item.intent.price, item.intent.ticker, viewCurrency) }}</span></div>
            </div>

            <div class="flex flex-col gap-1.5 mt-1">
              <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">AI 분석 추론 사유</span>
              <p class="text-[11px] text-slate-300 leading-relaxed italic bg-slate-900/40 p-2.5 rounded-lg border border-slate-900">
                "{{ item.reason || '전략 합성 규칙에 따라 신호가 제안되었습니다.' }}"
              </p>
            </div>
          </div>

          <div class="flex gap-3 mt-2">
            <button
              @click="handleApprovalAction(item.queue_id, 'APPROVE')"
              class="flex-1 bg-brandGreen/10 border border-brandGreen/30 text-brandGreen py-2.5 rounded-xl text-xs font-bold uppercase hover:bg-brandGreen hover:text-slate-950 cursor-pointer transition-all duration-300"
            >
              승인 (Approve)
            </button>
            <button
              @click="handleApprovalAction(item.queue_id, 'REJECT')"
              class="flex-1 bg-brandRed/10 border border-brandRed/30 text-brandRed py-2.5 rounded-xl text-xs font-bold uppercase hover:bg-brandRed hover:text-slate-950 cursor-pointer transition-all duration-300"
            >
              반려 (Reject)
            </button>
          </div>
        </div>
      </div>

      <div v-if="approvalsList.length === 0" class="text-center py-24 flex flex-col items-center justify-center gap-3">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-12 h-12 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="text-slate-500 font-sans italic text-sm">대기 중인 매매 승인 건이 없습니다. 모든 에이전트 시스템이 평온 상태입니다.</span>
      </div>
    </div>
  </div>
</template>
