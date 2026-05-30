<script setup>
import { onMounted } from 'vue';
import {
  watchlist,
  portfolio,
  pendingQueue,
  ordersLog,
  orderForm,
  submitManualOrder,
  approveQueueItem,
  rejectQueueItem,
  fetchPortfolio,
  fetchQueue,
  fetchOrdersLog,
  formatNumber,
  formatCurrency,
  viewCurrency,
  formatDateTime
} from '../store/tradingStore.js';

function getStatusBadgeClass(status) {
  if (status === 'FILLED') return 'bg-emerald-950/60 text-brandGreen border border-brandGreen/20';
  if (status === 'REJECTED' || status === 'CANCELLED') return 'bg-rose-950/60 text-brandRed border border-brandRed/20';
  if (status === 'SUBMITTED') return 'bg-indigo-950/60 text-brandIndigo border border-brandIndigo/20';
  return 'bg-amber-950/60 text-brandGold border border-brandGold/20';
}

onMounted(() => {
  fetchPortfolio();
  fetchQueue();
  fetchOrdersLog();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      
      <!-- Account & Positions Summary -->
      <div class="glass-card lg:col-span-2 p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandIndigo" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            포트폴리오 평가 및 잔고 현황
          </h3>
          <span class="text-[9px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-bold uppercase font-mono">Broker: KIS REST API</span>
        </div>

        <div class="grid grid-cols-3 gap-4 bg-slate-900/40 border border-slate-800/60 p-4 rounded-xl font-outfit">
          <div class="flex flex-col">
            <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">보유 예수금 (Cash)</span>
            <span class="text-sm font-extrabold text-white">{{ formatCurrency(portfolio.cash, '', viewCurrency) }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">주식 평가금 (Stocks)</span>
            <span class="text-sm font-extrabold text-white">{{ formatCurrency(portfolio.totalValue - portfolio.cash, '', viewCurrency) }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">보유 포지션 수</span>
            <span class="text-sm font-extrabold text-brandIndigo">{{ portfolio.positions.length }} 종목</span>
          </div>
        </div>

        <!-- Positions list sheet -->
        <div class="flex flex-col gap-2">
          <h4 class="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">실시간 보유 주식 목록 (Active Holdings)</h4>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse text-xs">
              <thead>
                <tr class="border-b border-slate-800/80 text-slate-500 font-semibold">
                  <th class="py-2.5 px-3">종목 코드</th>
                  <th class="py-2.5 px-3">잔고 수량</th>
                  <th class="py-2.5 px-3">매입 단가</th>
                  <th class="py-2.5 px-3">현재가</th>
                  <th class="py-2.5 px-3 text-right">평가 손익</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pos in portfolio.positions" :key="pos.ticker" class="border-b border-slate-800/30 text-white font-sans">
                  <td class="py-2.5 px-3 font-bold text-brandIndigo">{{ pos.ticker }}</td>
                  <td class="py-2.5 px-3">{{ pos.quantity }} 주</td>
                  <td class="py-2.5 px-3 font-mono">{{ formatCurrency(pos.avg_price, pos.ticker, viewCurrency) }}</td>
                  <td class="py-2.5 px-3 font-mono">{{ formatCurrency(pos.current_price, pos.ticker, viewCurrency) }}</td>
                  <td class="py-2.5 px-3 text-right font-bold font-mono" :class="pos.pnl >= 0 ? 'text-brandGreen' : 'text-brandRed'">
                    {{ pos.pnl >= 0 ? '+' : '' }}{{ formatCurrency(pos.pnl, '', viewCurrency) }}
                  </td>
                </tr>
                <tr v-if="portfolio.positions.length === 0" class="text-slate-500 text-center">
                  <td colspan="5" class="py-8">현재 보유한 잔여 포지션이 없습니다.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Manual OMS Order Ticket -->
      <div class="glass-card lg:col-span-1 p-5 flex flex-col justify-between gap-4">
        <div>
          <div class="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-4">
            <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandGreen" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              주문 접수 (OMS Ticket)
            </h3>
          </div>

          <div class="flex flex-col gap-4 text-xs">
            <!-- Buy / Sell Action -->
            <div class="flex flex-col gap-1.5">
              <label class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">거래 구분 (Transaction)</label>
              <div class="grid grid-cols-2 gap-2">
                <button
                  @click="orderForm.action = 'BUY'"
                  :class="[
                    'py-2 rounded-xl font-bold border transition-all cursor-pointer',
                    orderForm.action === 'BUY' ? 'border-brandGreen bg-brandGreen/10 text-brandGreen' : 'border-slate-800 text-slate-400'
                  ]"
                >
                  매수 (BUY)
                </button>
                <button
                  @click="orderForm.action = 'SELL'"
                  :class="[
                    'py-2 rounded-xl font-bold border transition-all cursor-pointer',
                    orderForm.action === 'SELL' ? 'border-brandRed bg-brandRed/10 text-brandRed' : 'border-slate-800 text-slate-400'
                  ]"
                >
                  매도 (SELL)
                </button>
              </div>
            </div>

            <!-- Ticker Selection -->
            <div class="flex flex-col gap-1.5">
              <label class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">종목 코드 선택 (Symbol)</label>
              <select
                v-model="orderForm.ticker"
                class="bg-slate-900/60 border border-slate-800/80 p-2.5 rounded-xl text-white focus:outline-none focus:border-brandIndigo cursor-pointer"
              >
                <option v-for="t in watchlist" :key="t" :value="t">{{ t }}</option>
                <option v-if="watchlist.length === 0" value="">관심종목을 먼저 등록하세요</option>
              </select>
            </div>

            <!-- Order Qty -->
            <div class="flex flex-col gap-1.5">
              <label class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">주문 수량 (Quantity)</label>
              <input
                type="number"
                v-model.number="orderForm.quantity"
                placeholder="수량 입력 (주)"
                class="bg-slate-900/60 border border-slate-800/80 p-2.5 rounded-xl text-white focus:outline-none focus:border-brandIndigo"
              />
            </div>

            <!-- Order Price -->
            <div class="flex flex-col gap-1.5">
              <label class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">지정 주문 가격 (Price)</label>
              <input
                type="number"
                v-model.number="orderForm.price"
                placeholder="가격 입력 (₩)"
                class="bg-slate-900/60 border border-slate-800/80 p-2.5 rounded-xl text-white focus:outline-none focus:border-brandIndigo"
              />
            </div>
          </div>
        </div>

        <button
          @click="submitManualOrder"
          class="w-full bg-gradient-to-tr from-brandIndigo to-brandGreen hover:opacity-90 text-white font-extrabold text-xs py-3.5 rounded-xl shadow-md font-outfit uppercase mt-4 cursor-pointer transition-opacity"
        >
          SUBMIT ORDER INTENT
        </button>
      </div>

      <!-- Pending Approval Queue Widget -->
      <div class="glass-card lg:col-span-1 p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandGold" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            AI 매매 승인 대기열
          </h3>
          <span v-if="pendingQueue.length > 0" class="text-[9px] bg-brandGold/20 text-brandGold px-2 py-0.5 rounded-full font-bold">
            {{ pendingQueue.length }} Pending
          </span>
        </div>

        <!-- Pending Items loop -->
        <div class="flex flex-col gap-3 overflow-y-auto max-h-[300px] pr-1">
          <div
            v-for="item in pendingQueue"
            :key="item.queue_id"
            class="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-col gap-3 text-xs"
          >
            <div class="flex justify-between items-center">
              <span class="font-outfit font-extrabold text-white">{{ item.intent.ticker }}</span>
              <span :class="item.intent.action === 'BUY' ? 'text-brandGreen font-bold' : 'text-brandRed font-bold'">
                {{ item.intent.action }}
              </span>
            </div>
            
            <div class="grid grid-cols-2 gap-2 text-[10px] text-slate-400">
              <div>수량: {{ item.intent.quantity }} 주</div>
              <div class="font-mono">가격: {{ formatCurrency(item.intent.price, item.intent.ticker, viewCurrency) }}</div>
            </div>
            
            <p class="text-[10px] text-slate-500 leading-normal font-light italic">
              "{{ item.reason || 'AI Blackboard 분석 조건 충족 대기 중.' }}"
            </p>

            <div class="flex gap-2">
              <button
                @click="approveQueueItem(item.queue_id)"
                class="flex-1 bg-brandGreen/15 border border-brandGreen/30 text-brandGreen py-1.5 rounded-lg text-[10px] font-bold uppercase hover:bg-brandGreen/25 cursor-pointer transition-colors"
              >
                Approve
              </button>
              <button
                @click="rejectQueueItem(item.queue_id)"
                class="flex-1 bg-brandRed/15 border border-brandRed/30 text-brandRed py-1.5 rounded-lg text-[10px] font-bold uppercase hover:bg-brandRed/25 cursor-pointer transition-colors"
              >
                Reject
              </button>
            </div>
          </div>
          <div v-if="pendingQueue.length === 0" class="text-slate-600 text-center py-10 font-sans italic">
            대기 중인 매매 승인 건이 없습니다.
          </div>
        </div>
      </div>
    </div>

    <!-- Orders Transaction Log -->
    <div class="glass-card p-5 overflow-hidden">
      <div class="border-b border-slate-800/80 pb-3 mb-4 flex justify-between items-center">
        <h3 class="font-outfit font-extrabold text-xs text-white uppercase tracking-wider">
          ACID 매매 트랜잭션 기록
        </h3>
        <button @click="fetchOrdersLog" class="text-slate-500 hover:text-white text-[9px] uppercase font-bold cursor-pointer">
          Refresh List
        </button>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-slate-800/80 text-slate-500 font-semibold">
              <th class="py-3 px-4">주문 ID</th>
              <th class="py-3 px-4">종목 코드</th>
              <th class="py-3 px-4">거래 유형</th>
              <th class="py-3 px-4">체결 수량</th>
              <th class="py-3 px-4">평균 체결가</th>
              <th class="py-3 px-4">주문 시간</th>
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
              <td class="py-3 px-4 text-slate-400">{{ formatDateTime(o.created_at) }}</td>
              <td class="py-3 px-4 text-right">
                <span :class="['px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', getStatusBadgeClass(o.status)]">
                  {{ o.status }}
                </span>
              </td>
            </tr>
            <tr v-if="ordersLog.length === 0" class="text-slate-500 text-center">
              <td colspan="7" class="py-8">최근 실행된 매매 트랜잭션 이력이 없습니다.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
