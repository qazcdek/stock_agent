<script setup>
import { onMounted } from 'vue';
import {
  systemConfig,
  fetchSystemConfig,
  saveSystemConfig
} from '../store/tradingStore.js';

function submitConfig() {
  saveSystemConfig({
    max_daily_order_amount: systemConfig.value.max_daily_order_amount,
    max_position_ratio: systemConfig.value.max_position_ratio,
    risk_stop_loss_pct: systemConfig.value.risk_stop_loss_pct,
    risk_take_profit_pct: systemConfig.value.risk_take_profit_pct
  });
}

onMounted(() => {
  fetchSystemConfig();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="glass-card p-6 flex flex-col gap-6 max-w-4xl">
      <div class="border-b border-slate-800/80 pb-4">
        <h3 class="font-outfit font-extrabold text-base text-white tracking-wide uppercase flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-brandIndigo" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          시스템 환경 및 리스크 가이드라인 설정 (System Config)
        </h3>
        <p class="text-xs text-slate-400 mt-1">서버 인프라 데이터베이스 매핑 주소를 조회하고, 자동 매매 실행 시 적용할 거래 위험도 수치를 관리합니다.</p>
      </div>

      <div class="flex flex-col gap-5 text-xs">
        
        <!-- Read Only Database URLs -->
        <div>
          <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-3">연결된 시스템 데이터베이스 주소 (조회 전용)</span>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="bg-slate-900/40 border border-slate-800/80 p-3 rounded-xl flex flex-col gap-1">
              <span class="text-[9px] text-slate-500 font-bold">SQLITE STORAGE</span>
              <span class="text-[11px] font-mono text-slate-300 overflow-x-auto">{{ systemConfig.sqlite_url || '-' }}</span>
            </div>
            <div class="bg-slate-900/40 border border-slate-800/80 p-3 rounded-xl flex flex-col gap-1">
              <span class="text-[9px] text-slate-500 font-bold">POSTGRES RDB URL</span>
              <span class="text-[11px] font-mono text-slate-300 overflow-x-auto">{{ systemConfig.postgres_url || '-' }}</span>
            </div>
            <div class="bg-slate-900/40 border border-slate-800/80 p-3 rounded-xl flex flex-col gap-1">
              <span class="text-[9px] text-slate-500 font-bold">MONGODB NOSQL URL</span>
              <span class="text-[11px] font-mono text-slate-300 overflow-x-auto">{{ systemConfig.mongodb_url || '-' }}</span>
            </div>
            <div class="bg-slate-900/40 border border-slate-800/80 p-3 rounded-xl flex flex-col gap-1">
              <span class="text-[9px] text-slate-500 font-bold">CLICKHOUSE TSDB URL</span>
              <span class="text-[11px] font-mono text-slate-300 overflow-x-auto">{{ systemConfig.clickhouse_url || '-' }}</span>
            </div>
          </div>
        </div>

        <!-- Editable Risk Parameters -->
        <div class="border-t border-slate-800/80 pt-4 mt-2">
          <span class="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-3">거래 리스크 관리 가이드라인 (리스크 매니저 작동 제한)</span>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="flex flex-col gap-1.5">
              <label class="text-[10px] text-slate-400 font-bold">일일 최대 누적 매매 한도 (KRW)</label>
              <input
                type="number"
                v-model.number="systemConfig.max_daily_order_amount"
                class="bg-slate-900 border border-slate-800 p-3 rounded-xl text-white font-mono font-bold focus:outline-none focus:border-brandIndigo"
              />
              <span class="text-[9px] text-slate-500">에이전트가 하루 동안 보낼 수 있는 최대 주문 금액 총합입니다.</span>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-[10px] text-slate-400">단일 종목 최대 투자 비율 (Ratio)</label>
              <input
                type="number"
                step="0.05"
                v-model.number="systemConfig.max_position_ratio"
                class="bg-slate-900 border border-slate-800 p-3 rounded-xl text-white font-mono font-bold focus:outline-none focus:border-brandIndigo"
              />
              <span class="text-[9px] text-slate-500">포트폴리오 평가액 중 단일 종목이 차지할 수 있는 최대 비율입니다. (예: 0.3 = 30%)</span>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-[10px] text-slate-400">손절 제한 비율 (Stop Loss Ratio)</label>
              <input
                type="number"
                step="0.01"
                v-model.number="systemConfig.risk_stop_loss_pct"
                class="bg-slate-900 border border-slate-800 p-3 rounded-xl text-white font-mono font-bold focus:outline-none focus:border-brandIndigo"
              />
              <span class="text-[9px] text-slate-500">매수 가격 대비 하락 한계 비율입니다. 도달 시 시장가 즉시 손절이 권장됩니다. (예: 0.05 = 5%)</span>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-[10px] text-slate-400">익절 목표 비율 (Take Profit Ratio)</label>
              <input
                type="number"
                step="0.01"
                v-model.number="systemConfig.risk_take_profit_pct"
                class="bg-slate-900 border border-slate-800 p-3 rounded-xl text-white font-mono font-bold focus:outline-none focus:border-brandIndigo"
              />
              <span class="text-[9px] text-slate-500">매수 가격 대비 상승 목표 비율입니다. 도달 시 분할/전량 익절이 나갑니다. (예: 0.15 = 15%)</span>
            </div>
          </div>
        </div>

        <button
          @click="submitConfig"
          class="w-full bg-gradient-to-tr from-brandIndigo to-brandGreen hover:opacity-90 text-white font-extrabold text-xs py-3.5 rounded-xl shadow-md font-outfit uppercase mt-4 cursor-pointer"
        >
          위험 가이드라인 한도 저장 (Save Risk Limits)
        </button>
      </div>
    </div>
  </div>
</template>
