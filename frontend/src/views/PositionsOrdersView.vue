<script setup>
import { onMounted } from 'vue';
import {
  watchlist,
  activePositions,
  activeOrders,
  orderForm,
  submitManualOrder,
  fetchWatchlist,
  fetchActivePositions,
  fetchActiveOrders,
  formatNumber,
  formatCurrency,
  viewCurrency,
  formatDateTime
} from '../store/tradingStore.js';

function getStatusBadgeClass(status) {
  if (status === 'FILLED') return 'bg-emerald-950/60 text-brandGreen border border-brandGreen/25';
  if (status === 'REJECTED' || status === 'CANCELLED') return 'bg-rose-950/60 text-brandRed border border-brandRed/25';
  if (status === 'SUBMITTED') return 'bg-indigo-950/60 text-brandIndigo border border-brandIndigo/25';
  return 'bg-amber-950/60 text-brandGold border border-brandGold/25';
}

onMounted(() => {
  fetchWatchlist();
  fetchActivePositions();
  fetchActiveOrders();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      
      <!-- Account Holdings Grid -->
      <div class="glass-card lg:col-span-3 p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandIndigo" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
            실시간 포지션 잔고 현황 (Active Positions)
          </h3>
          <button @click="fetchActivePositions" class="text-slate-500 hover:text-white text-[10px] uppercase font-bold cursor-pointer">
            새로고침
          </button>
        </div>

        <div class="overflow-x-auto mt-2">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="border-b border-slate-800/80 text-slate-500 font-semibold">
                <th class="py-3 px-4">종목 코드</th>
                <th class="py-3 px-4">잔고 수량</th>
                <th class="py-3 px-4">평균 매입 단가</th>
                <th class="py-3 px-4">현재 시장가</th>
                <th class="py-3 px-4 text-right">미실현 평가 손익</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pos in activePositions" :key="pos.ticker" class="border-b border-slate-800/30 hover:bg-slate-900/10 text-white font-sans">
                <td class="py-3.5 px-4 font-bold text-brandIndigo">{{ pos.ticker }}</td>
                <td class="py-3.5 px-4">{{ pos.quantity }} 주</td>
                <td class="py-3.5 px-4 font-mono">{{ formatCurrency(pos.avg_price, pos.ticker, viewCurrency) }}</td>
                <td class="py-3.5 px-4 font-mono">{{ formatCurrency(pos.current_price, pos.ticker, viewCurrency) }}</td>
                <td :class="['py-3.5 px-4 text-right font-bold font-mono', pos.floating_pnl >= 0 ? 'text-brandGreen' : 'text-brandRed']">
                  {{ pos.floating_pnl >= 0 ? '+' : '' }}{{ formatCurrency(pos.floating_pnl, '', viewCurrency) }}
                </td>
              </tr>
              <tr v-if="activePositions.length === 0" class="text-slate-500 text-center font-sans">
                <td colspan="5" class="py-12">보유 중인 Active 포지션이 없습니다.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Manual OMS Ticket -->
      <div class="glass-card lg:col-span-1 p-5 flex flex-col justify-between gap-4">
        <div>
          <div class="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-4">
            <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandGreen" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              수동 주문 Ticket (OMS)
            </h3>
          </div>

          <div class="flex flex-col gap-4 text-xs">
            <!-- Buy / Sell Action -->
            <div class="flex flex-col gap-1.5">
              <label class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">거래 유형 (Action)</label>
              <div class="grid grid-cols-2 gap-2">
                <button
                  @click="orderForm.action = 'BUY'"
                  :class="[
                    'py-2 rounded-xl font-bold border transition-all cursor-pointer text-center',
                    orderForm.action === 'BUY' ? 'border-brandGreen bg-brandGreen/10 text-brandGreen' : 'border-slate-800 text-slate-400'
                  ]"
                >
                  매수
                </button>
                <button
                  @click="orderForm.action = 'SELL'"
                  :class="[
                    'py-2 rounded-xl font-bold border transition-all cursor-pointer text-center',
                    orderForm.action === 'SELL' ? 'border-brandRed bg-brandRed/10 text-brandRed' : 'border-slate-800 text-slate-400'
                  ]"
                >
                  매도
                </button>
              </div>
            </div>

            <!-- Ticker -->
            <div class="flex flex-col gap-1.5">
              <label class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">종목 코드 (Symbol)</label>
              <select
                v-model="orderForm.ticker"
                class="bg-slate-900/60 border border-slate-800/80 p-2.5 rounded-xl text-white focus:outline-none focus:border-brandIndigo cursor-pointer"
              >
                <option v-for="t in watchlist" :key="t" :value="t">{{ t }}</option>
                <option v-if="watchlist.length === 0" value="">관심종목을 등록하세요</option>
              </select>
            </div>

            <!-- Qty -->
            <div class="flex flex-col gap-1.5">
              <label class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">주문 수량 (Shares)</label>
              <input
                type="number"
                v-model.number="orderForm.quantity"
                class="bg-slate-900/60 border border-slate-800/80 p-2.5 rounded-xl text-white focus:outline-none focus:border-brandIndigo"
              />
            </div>

            <!-- Price -->
            <div class="flex flex-col gap-1.5">
              <label class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">주문 단가 (Limit Price)</label>
              <input
                type="number"
                v-model.number="orderForm.price"
                class="bg-slate-900/60 border border-slate-800/80 p-2.5 rounded-xl text-white focus:outline-none focus:border-brandIndigo"
              />
            </div>
          </div>
        </div>

        <button
          @click="async () => { await submitManualOrder(); fetchActiveOrders(); fetchActivePositions(); }"
          class="w-full bg-gradient-to-tr from-brandIndigo to-brandGreen hover:opacity-90 text-white font-extrabold text-xs py-3.5 rounded-xl shadow-md font-outfit uppercase cursor-pointer"
        >
          주문 전송 (Submit Order)
        </button>
      </div>
    </div>

    <!-- Active Orders Terminal Grid -->
    <div class="glass-card p-5">
      <div class="border-b border-slate-800/80 pb-3 mb-4 flex justify-between items-center">
        <h3 class="font-outfit font-extrabold text-xs text-white uppercase tracking-wider">
          접수된 활성 주문 내역 (Active / Pending Orders)
        </h3>
        <button @click="fetchActiveOrders" class="text-slate-500 hover:text-white text-[10px] uppercase font-bold cursor-pointer">
          내역 갱신
        </button>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-slate-800/80 text-slate-500 font-semibold">
              <th class="py-3 px-4">주문 ID</th>
              <th class="py-3 px-4">종목 코드</th>
              <th class="py-3 px-4">구분</th>
              <th class="py-3 px-4">수량</th>
              <th class="py-3 px-4">단가</th>
              <th class="py-3 px-4">체결 수량</th>
              <th class="py-3 px-4">주문 일시</th>
              <th class="py-3 px-4 text-right">상태</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="o in activeOrders" :key="o.order_id" class="border-b border-slate-800/30 hover:bg-slate-900/10 text-white font-sans">
              <td class="py-3 px-4 font-mono text-slate-500">{{ o.order_id }}</td>
              <td class="py-3 px-4 font-bold">{{ o.ticker }}</td>
              <td class="py-3 px-4 font-bold" :class="o.action === 'BUY' ? 'text-brandGreen' : 'text-brandRed'">{{ o.action }}</td>
              <td class="py-3 px-4">{{ o.quantity }} 주</td>
              <td class="py-3 px-4 font-mono">{{ formatCurrency(o.price, o.ticker, viewCurrency) }}</td>
              <td class="py-3 px-4">{{ o.filled_quantity }} 주</td>
              <td class="py-3 px-4 text-slate-400">{{ formatDateTime(o.timestamp) }}</td>
              <td class="py-3 px-4 text-right">
                <span :class="['px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', getStatusBadgeClass(o.status)]">
                  {{ o.status }}
                </span>
              </td>
            </tr>
            <tr v-if="activeOrders.length === 0" class="text-slate-500 text-center font-sans">
              <td colspan="8" class="py-8">현재 접수 중이거나 실행 대기 중인 활성 주문 건이 없습니다.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
