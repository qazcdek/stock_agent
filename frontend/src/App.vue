<script setup>
import { onMounted } from 'vue';
import {
  currentTab,
  automatedMode,
  portfolio,
  connectWS,
  toggleMode,
  formatNumber,
  formatCurrency,
  viewCurrency,
  approvalsList,
  fetchApprovals,
  activeOrders,
  fetchActiveOrders
} from './store/tradingStore.js';

// Component imports
import DashboardView from './views/DashboardView.vue';
import ApprovalQueueView from './views/ApprovalQueueView.vue';
import WatchlistView from './views/WatchlistView.vue';
import AgentRecommendationsView from './views/AgentRecommendationsView.vue';
import PositionsOrdersView from './views/PositionsOrdersView.vue';
import TradeHistoryView from './views/TradeHistoryView.vue';
import StrategyConfigView from './views/StrategyConfigView.vue';
import ModelRegistryView from './views/ModelRegistryView.vue';
import NotificationConfigView from './views/NotificationConfigView.vue';
import SystemConfigView from './views/SystemConfigView.vue';
import BacktestView from './views/BacktestView.vue';
import DataViewerView from './views/DataViewerView.vue';
import AgentDebuggerView from './views/AgentDebuggerView.vue';
import SystemHealthView from './views/SystemHealthView.vue';

onMounted(() => {
  connectWS();
  fetchApprovals();
  fetchActiveOrders();
});
</script>

<template>
  <div class="flex min-h-screen relative font-sans text-slate-200 bg-[#070A13]">
    <!-- Background Glowing Blobs -->
    <div class="absolute top-20 left-1/4 w-[350px] h-[350px] rounded-full bg-brandIndigo/5 blur-[120px] pointer-events-none"></div>
    <div class="absolute bottom-20 right-1/4 w-[400px] h-[400px] rounded-full bg-brandGreen/5 blur-[120px] pointer-events-none"></div>

    <!-- LEFT NAVIGATION SIDEBAR -->
    <aside class="w-64 border-r border-slate-800/80 bg-[#070A13]/90 backdrop-blur-xl flex flex-col justify-between p-6 z-30 shrink-0 select-none">
      <div class="flex flex-col gap-6 overflow-y-auto max-h-[85vh] pr-1">
        <!-- Branding Logo -->
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brandIndigo to-brandGreen flex items-center justify-center font-outfit font-extrabold text-xl text-white shadow-lg shadow-indigo-500/20">A</div>
          <div>
            <h1 class="font-outfit font-extrabold text-lg tracking-tight text-white leading-none">ANTIGRAVITY</h1>
            <p class="text-[10px] text-slate-400 font-medium tracking-wide mt-1">AI Blackboard Engine</p>
          </div>
        </div>

        <!-- Navigation Links -->
        <nav class="flex flex-col gap-1 mt-2">
          
          <!-- 1. 대시보드 -->
          <button
            @click="currentTab = 'dashboard'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'dashboard' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4zM14 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2v-4z" />
            </svg>
            <span>대시보드</span>
          </button>
          
          <!-- 2. 승인 큐 -->
          <button
            @click="currentTab = 'approval-queue'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left relative',
              currentTab === 'approval-queue' ? 'sidebar-btn-active' : ''
            ]"
          >
            <span class="relative flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              <span v-if="approvalsList.length > 0" class="absolute -top-1 -right-1 w-2 h-2 bg-brandGold rounded-full animate-ping"></span>
            </span>
            <span class="flex items-center justify-between w-full">
              <span>승인 큐</span>
              <span v-if="approvalsList.length > 0" class="text-[9px] bg-brandGold/20 text-brandGold px-1.5 py-0.2 rounded font-bold font-mono">
                {{ approvalsList.length }}
              </span>
            </span>
          </button>

          <!-- 3. 관심종목 -->
          <button
            @click="currentTab = 'watchlist'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'watchlist' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.907c.961 0 1.367 1.243.583 1.83l-3.978 2.89a1 1 0 00-.364 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.583-1.83h4.907a1 1 0 00.95-.69l1.519-4.674z" />
            </svg>
            <span>관심종목</span>
          </button>

          <!-- 에이전트 추천 -->
          <button
            @click="currentTab = 'agent-recommendations'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'agent-recommendations' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
            </svg>
            <span>에이전트 추천</span>
          </button>

          <!-- 4. 포지션 & 주문 -->
          <button
            @click="currentTab = 'positions-orders'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left relative',
              currentTab === 'positions-orders' ? 'sidebar-btn-active' : ''
            ]"
          >
            <span class="relative flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
              <span v-if="activeOrders.length > 0" class="absolute -top-1 -right-1 w-2 h-2 bg-brandIndigo rounded-full animate-ping"></span>
            </span>
            <span class="flex items-center justify-between w-full">
              <span>포지션 & 주문</span>
              <span v-if="activeOrders.length > 0" class="text-[9px] bg-brandIndigo/20 text-brandIndigo px-1.5 py-0.2 rounded font-bold font-mono">
                {{ activeOrders.length }}
              </span>
            </span>
          </button>

          <!-- 5. 거래 이력 -->
          <button
            @click="currentTab = 'trades'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'trades' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>거래 이력</span>
          </button>

          <!-- 6. 전략 -->
          <button
            @click="currentTab = 'strategies'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'strategies' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
            <span>전략 설정</span>
          </button>

          <!-- 7. 모델 관리 -->
          <button
            @click="currentTab = 'models'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'models' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 9.172V5L8 4z" />
            </svg>
            <span>모델 관리</span>
          </button>

          <!-- 8. 알림 설정 -->
          <button
            @click="currentTab = 'notifications'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'notifications' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            <span>알림 설정</span>
          </button>

          <!-- 9. 시스템 설정 -->
          <button
            @click="currentTab = 'system-settings'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'system-settings' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span>시스템 설정</span>
          </button>

          <!-- 10. 백테스트 -->
          <button
            @click="currentTab = 'backtest'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'backtest' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>백테스트</span>
          </button>

          <!-- 11. 데이터 뷰어 -->
          <button
            @click="currentTab = 'data-viewer'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'data-viewer' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
            <span>데이터 뷰어</span>
          </button>

          <!-- 12. 에이전트 디버거 -->
          <button
            @click="currentTab = 'agent-debugger'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'agent-debugger' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span>에이전트 디버거</span>
          </button>

          <!-- 13. 시스템 상태 -->
          <button
            @click="currentTab = 'system-health'"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-all cursor-pointer w-full text-left',
              currentTab === 'system-health' ? 'sidebar-btn-active' : ''
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>시스템 상태</span>
          </button>
        </nav>
      </div>

      <!-- Footer Stats / Settings -->
      <div class="flex flex-col gap-3 border-t border-slate-800/80 pt-4 shrink-0">
        <!-- System Mode Toggle -->
        <div class="flex items-center justify-between bg-slate-900/50 p-2.5 rounded-xl border border-slate-800/60">
          <div class="flex flex-col">
            <span class="text-[9px] text-slate-500 font-semibold uppercase tracking-wider">시스템 매매 모드</span>
            <span class="text-[10px] font-bold" :class="automatedMode ? 'text-brandGreen' : 'text-brandGold'">
              {{ automatedMode ? '자동 우회 (Auto)' : '수동 승인 (Manual)' }}
            </span>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="automatedMode" @change="toggleMode" class="sr-only peer">
            <div class="w-8 h-4.5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:bg-brandGreen"></div>
          </label>
        </div>
        
        <div class="flex items-center gap-2 text-[9px] text-slate-500 font-medium">
          <span class="w-1.5 h-1.5 rounded-full bg-brandGreen glow-dot text-brandGreen"></span>
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
            currentTab === 'approval-queue' ? ApprovalQueueView :
            currentTab === 'watchlist' ? WatchlistView :
            currentTab === 'agent-recommendations' ? AgentRecommendationsView :
            currentTab === 'positions-orders' ? PositionsOrdersView :
            currentTab === 'trades' ? TradeHistoryView :
            currentTab === 'strategies' ? StrategyConfigView :
            currentTab === 'models' ? ModelRegistryView :
            currentTab === 'notifications' ? NotificationConfigView :
            currentTab === 'system-settings' ? SystemConfigView :
            currentTab === 'backtest' ? BacktestView :
            currentTab === 'data-viewer' ? DataViewerView :
            currentTab === 'agent-debugger' ? AgentDebuggerView :
            SystemHealthView
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
