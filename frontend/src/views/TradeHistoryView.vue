<script setup>
import { onMounted, ref } from 'vue';
import {
  tradeHistory,
  fetchTradeHistory,
  formatCurrency,
  viewCurrency,
  formatDateTime
} from '../store/tradingStore.js';

const fromDate = ref("");
const toDate = ref("");

function applyFilters() {
  fetchTradeHistory(fromDate.value, toDate.value);
}

function clearFilters() {
  fromDate.value = "";
  toDate.value = "";
  fetchTradeHistory();
}

onMounted(() => {
  fetchTradeHistory();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="glass-card p-6 flex flex-col gap-6">
      
      <!-- Filter controls row -->
      <div class="flex flex-col md:flex-row items-end justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h3 class="font-outfit font-extrabold text-base text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-brandIndigo" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            체결 거래 이력 (Trade Execution History)
          </h3>
          <p class="text-xs text-slate-400 mt-1">거래소 어댑터 및 OMS를 통해 전량 또는 일부 체결 성공 완료된 거래 내역 기록 보관소입니다.</p>
        </div>
        
        <!-- Inputs and buttons -->
        <div class="flex items-center gap-3 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">조회 시작일</span>
            <input
              type="date"
              v-model="fromDate"
              class="bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl text-white focus:outline-none focus:border-brandIndigo"
            />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">조회 종료일</span>
            <input
              type="date"
              v-model="toDate"
              class="bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl text-white focus:outline-none focus:border-brandIndigo"
            />
          </div>
          <button
            @click="applyFilters"
            class="bg-brandIndigo hover:bg-indigo-600 text-white font-bold px-4 py-2.5 rounded-xl cursor-pointer self-end transition-colors"
          >
            검색
          </button>
          <button
            @click="clearFilters"
            class="bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold px-4 py-2.5 rounded-xl cursor-pointer self-end transition-colors"
          >
            초기화
          </button>
        </div>
      </div>

      <!-- Main Trade Log list -->
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-slate-800/80 text-slate-500 font-semibold">
              <th class="py-3 px-4">주문 ID</th>
              <th class="py-3 px-4">종목 코드</th>
              <th class="py-3 px-4">거래 유형</th>
              <th class="py-3 px-4">체결 수량</th>
              <th class="py-3 px-4">평균 체결 단가</th>
              <th class="py-3 px-4">총 거래 금액</th>
              <th class="py-3 px-4">최종 체결 시간</th>
              <th class="py-3 px-4 text-right">상태</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tradeHistory" :key="t.order_id" class="border-b border-slate-800/30 hover:bg-slate-900/10 text-white font-sans">
              <td class="py-3.5 px-4 font-mono text-slate-500">{{ t.order_id }}</td>
              <td class="py-3.5 px-4 font-bold text-white">{{ t.ticker }}</td>
              <td class="py-3.5 px-4 font-bold" :class="t.action === 'BUY' ? 'text-brandGreen' : 'text-brandRed'">
                {{ t.action === 'BUY' ? '매수 (BUY)' : '매도 (SELL)' }}
              </td>
              <td class="py-3.5 px-4 font-sans font-medium text-white">{{ t.filled_quantity }} 주</td>
              <td class="py-3.5 px-4 font-mono text-white">{{ formatCurrency(t.avg_fill_price, t.ticker, viewCurrency) }}</td>
              <td class="py-3.5 px-4 font-mono font-bold text-brandIndigo">
                {{ formatCurrency(t.filled_quantity * t.avg_fill_price, t.ticker, viewCurrency) }}
              </td>
              <td class="py-3.5 px-4 text-slate-400">{{ formatDateTime(t.timestamp) }}</td>
              <td class="py-3.5 px-4 text-right">
                <span class="bg-emerald-950/60 text-brandGreen border border-brandGreen/25 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">
                  {{ t.status }}
                </span>
              </td>
            </tr>
            <tr v-if="tradeHistory.length === 0" class="text-slate-500 text-center font-sans">
              <td colspan="8" class="py-16">체결 완료된 거래 기록이 없습니다.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
