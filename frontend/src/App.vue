<script setup>
import { onMounted } from 'vue';
import {
  currentTab,
  automatedMode,
  portfolio,
  pendingQueue,
  connectWS,
  toggleMode,
  formatNumber,
  formatCurrency,
  viewCurrency
} from './store/tradingStore.js';

// Component imports
import DashboardView from './views/DashboardView.vue';
import DataInspectorView from './views/DataInspectorView.vue';
import SimulatorView from './views/SimulatorView.vue';
import TradingPortalView from './views/TradingPortalView.vue';

onMounted(() => {
  connectWS();
});
</script>

<template>
  <div class="flex min-h-screen relative font-sans text-slate-200 bg-[#070A13]">
    <!-- Background Glowing Blobs -->
    <div class="absolute top-20 left-1/4 w-[350px] h-[350px] rounded-full bg-brandIndigo/5 blur-[120px] pointer-events-none"></div>
    <div class="absolute bottom-20 right-1/4 w-[400px] h-[400px] rounded-full bg-brandGreen/5 blur-[120px] pointer-events-none"></div>

    <!-- LEFT NAVIGATION SIDEBAR -->
    <aside class="w-64 border-r border-slate-800/80 bg-[#070A13]/90 backdrop-blur-xl flex flex-col justify-between p-6 z-30 shrink-0 select-none">
      <div class="flex flex-col gap-8">
        <!-- Branding Logo -->
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brandIndigo to-brandGreen flex items-center justify-center font-outfit font-extrabold text-xl text-white shadow-lg shadow-indigo-500/20">A</div>
          <div>
            <h1 class="font-outfit font-extrabold text-lg tracking-tight text-white leading-none">ANTIGRAVITY</h1>
            <p class="text-[10px] text-slate-400 font-medium tracking-wide mt-1">AI Blackboard Engine</p>
          </div>
        </div>

        <!-- Navigation Links -->
        <nav class="flex flex-col gap-2">
          <button
            @click="currentTab = 'dashboard'"
            :class="[
              'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'dashboard' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4zM14 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2v-4z" />
            </svg>
            <span>대시보드</span>
          </button>
          
          <button
            @click="currentTab = 'data-viewer'"
            :class="[
              'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'data-viewer' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
            <span>멀티 DB 데이터 뷰어</span>
          </button>
          
          <button
            @click="currentTab = 'simulator'"
            :class="[
              'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'simulator' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>백테스트 시뮬레이터</span>
          </button>
          
          <button
            @click="currentTab = 'trading'"
            :class="[
              'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left relative',
              currentTab === 'trading' ? 'sidebar-btn-active' : ''
            ]"
          >
            <span class="relative flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
              <span v-if="pendingQueue.length > 0" class="absolute -top-1 -right-1 w-2.5 h-2.5 bg-brandGold rounded-full animate-ping"></span>
            </span>
            <span class="flex items-center justify-between w-full">
              <span>매매 & OMS</span>
              <span v-if="pendingQueue.length > 0" class="text-[9px] bg-brandGold/20 text-brandGold px-1.5 py-0.2 rounded-full font-bold">
                {{ pendingQueue.length }}
              </span>
            </span>
          </button>
        </nav>
      </div>

      <!-- Footer Stats / Settings -->
      <div class="flex flex-col gap-4 border-t border-slate-800/80 pt-6">
        <!-- System Mode Toggle -->
        <div class="flex items-center justify-between bg-slate-900/50 p-3 rounded-xl border border-slate-800/60">
          <div class="flex flex-col">
            <span class="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">시스템 매매 모드</span>
            <span class="text-[11px] font-bold" :class="automatedMode ? 'text-brandGreen' : 'text-brandGold'">
              {{ automatedMode ? '자동 우회 (Auto)' : '수동 승인 (Manual)' }}
            </span>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="automatedMode" @change="toggleMode" class="sr-only peer">
            <div class="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-brandGreen"></div>
          </label>
        </div>
        
        <div class="flex items-center gap-2 text-[10px] text-slate-500 font-medium">
          <span class="w-2 h-2 rounded-full bg-brandGreen glow-dot text-brandGreen"></span>
          <span>Blackboard Protocol Active</span>
        </div>
      </div>
    </aside>

    <!-- MAIN WINDOW CONTENT -->
    <main class="flex-1 flex flex-col min-h-screen overflow-y-auto z-10">
      <!-- Global Top Bar -->
      <header class="h-16 border-b border-slate-800/80 px-8 flex items-center justify-between bg-[#070A13]/30 backdrop-blur-md select-none shrink-0">
        <div class="flex items-center gap-3">
          <span class="text-xs bg-slate-800/80 text-slate-300 px-3 py-1 rounded-full font-semibold border border-slate-700/50">
            Workspace: /stock_agent
          </span>
        </div>
        <div class="flex items-center gap-6">
          <div class="flex flex-col">
            <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">주식 + 현금 예수금</span>
            <span class="text-sm font-outfit font-extrabold text-white">{{ formatCurrency(portfolio.totalValue, '', viewCurrency) }}</span>
          </div>
          
          <div class="flex flex-col">
            <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">미실현 손익 (PnL)</span>
            <span :class="['text-sm font-outfit font-extrabold', portfolio.floatingPnl >= 0 ? 'text-brandGreen' : 'text-brandRed']">
              {{ portfolio.floatingPnl >= 0 ? '+' : '' }}{{ formatCurrency(portfolio.floatingPnl, '', viewCurrency) }}
            </span>
          </div>
        </div>
      </header>

      <!-- TAB PAGES CONTAINER -->
      <div class="flex-1 p-8">
        <transition name="fade" mode="out-in">
          <component :is="
            currentTab === 'dashboard' ? DashboardView :
            currentTab === 'data-viewer' ? DataInspectorView :
            currentTab === 'simulator' ? SimulatorView :
            TradingPortalView
          " />
        </transition>
      </div>
    </main>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
