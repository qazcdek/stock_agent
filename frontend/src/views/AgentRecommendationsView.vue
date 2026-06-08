<script setup>
import { onMounted, ref, computed } from 'vue';
import {
  recommendationsList,
  recommendationsLoading,
  watchlist,
  fetchWatchlist,
  fetchRecommendations,
  generateRecommendations,
  addWatchlistTickerSymbol,
  formatDateTime
} from '../store/tradingStore.js';

// Selected recommendation for the detailed drawer
const selectedRec = ref(null);

// Active filter: 'ALL', 'BUY', 'HOLD_SELL'
const activeFilter = ref('ALL');

onMounted(async () => {
  await fetchWatchlist();
  await fetchRecommendations();
});

// Filtered recommendations list
const filteredRecs = computed(() => {
  if (!recommendationsList.value) return [];
  return recommendationsList.value.filter(rec => {
    if (activeFilter.value === 'BUY') {
      return rec.action === 'BUY';
    } else if (activeFilter.value === 'HOLD_SELL') {
      return rec.action === 'HOLD' || rec.action === 'SELL';
    }
    return true;
  });
});

// Check if ticker is already in watchlist
function isInWatchlist(ticker) {
  return watchlist.value.includes(ticker);
}

// Add to watchlist handler
const watchlistAdding = ref({});
async function handleAddToWatchlist(ticker) {
  if (isInWatchlist(ticker) || watchlistAdding.value[ticker]) return;
  
  watchlistAdding.value[ticker] = true;
  try {
    const success = await addWatchlistTickerSymbol(ticker);
    if (success) {
      // Re-fetch watchlist to update UI state
      await fetchWatchlist();
    }
  } catch (e) {
    console.error("Failed to add to watchlist", e);
  } finally {
    watchlistAdding.value[ticker] = false;
  }
}

// Open details drawer
function openDetails(rec) {
  selectedRec.value = rec;
}

// Close details drawer
function closeDetails() {
  selectedRec.value = null;
}

// Get helper classes for action badges
function getActionBadgeClass(action) {
  if (action === 'BUY') return 'bg-brandGreen/10 text-brandGreen border-brandGreen/30';
  if (action === 'SELL') return 'bg-brandRed/10 text-brandRed border-brandRed/30';
  return 'bg-brandGold/10 text-brandGold border-brandGold/30';
}

// Helper to find specific agent state from the blackboard list
function getAgentState(rec, agentName) {
  if (!rec || !rec.blackboard_state) return null;
  return rec.blackboard_state.find(s => s.source_agent === agentName);
}
</script>

<template>
  <div class="flex flex-col gap-6 relative min-h-[80vh]">
    <!-- View Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
      <div>
        <h2 class="font-outfit font-extrabold text-xl text-white tracking-tight flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-brandIndigo animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
          </svg>
          에이전트 추천 (Agent Recommendations)
        </h2>
        <p class="text-xs text-slate-400 mt-1.5 leading-relaxed">
          8인의 AI 에이전트 협력팀이 블랙보드 아키텍처를 기반으로 10대 주요 자산을 교차 검증하고 토론하여 최적의 거래 신호를 추출합니다.
        </p>
      </div>
      
      <!-- Scan Trigger Button -->
      <button
        @click="generateRecommendations"
        :disabled="recommendationsLoading"
        class="relative overflow-hidden bg-gradient-to-r from-brandIndigo to-brandPurple hover:from-indigo-600 hover:to-violet-600 disabled:from-slate-800 disabled:to-slate-900 disabled:cursor-not-allowed text-white font-extrabold px-6 py-3 rounded-2xl text-xs cursor-pointer transition-all duration-300 shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 flex items-center gap-2 group shrink-0"
      >
        <span v-if="recommendationsLoading" class="w-4 h-4 rounded-full border-2 border-white/20 border-t-white animate-spin"></span>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 transition-transform group-hover:rotate-45" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3m-3-3v12" />
        </svg>
        <span>{{ recommendationsLoading ? '에이전트 합동 분석 진행 중...' : '신규 에이전트 추천 스캔 실행' }}</span>
      </button>
    </div>

    <!-- Ticker Scan Scope Information Card -->
    <div class="glass-card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-slate-950/20 border border-slate-800/50">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-brandIndigo/10 flex items-center justify-center text-brandIndigo">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <div>
          <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">분석 대상 후보군 (10 Assets)</span>
          <div class="flex flex-wrap gap-1.5 mt-1">
            <span v-for="c in ['005930', '000660', '035420', 'AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'BTC', 'ETH']" :key="c" class="text-[9px] bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded font-mono font-bold text-slate-400">
              {{ c }}
            </span>
          </div>
        </div>
      </div>
      <div class="text-[10px] text-slate-400 max-w-sm leading-relaxed border-l-0 md:border-l border-slate-800/80 pl-0 md:pl-4">
        기술적(MACD/RSI), 기본적 가치, 사회적 감성 여론, 거시 뉴스 매크로 분석 및 강/약세 리서처 간의 토론 과정을 거친 투자 가이드를 생성합니다.
      </div>
    </div>

    <!-- Active Filter Options -->
    <div class="flex items-center justify-between gap-4 mt-2">
      <div class="flex items-center gap-1.5 bg-slate-950/40 p-1 rounded-xl border border-slate-850">
        <button
          @click="activeFilter = 'ALL'"
          :class="[
            'px-3.5 py-1.5 rounded-lg text-[10px] font-bold tracking-wide transition-all cursor-pointer',
            activeFilter === 'ALL' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-500 hover:text-slate-350'
          ]"
        >
          전체 대상 ({{ recommendationsList?.length || 0 }})
        </button>
        <button
          @click="activeFilter = 'BUY'"
          :class="[
            'px-3.5 py-1.5 rounded-lg text-[10px] font-bold tracking-wide transition-all cursor-pointer',
            activeFilter === 'BUY' ? 'bg-brandGreen/15 text-brandGreen shadow-sm' : 'text-slate-500 hover:text-slate-350'
          ]"
        >
          매수 추천 ({{ recommendationsList?.filter(r => r.action === 'BUY').length || 0 }})
        </button>
        <button
          @click="activeFilter = 'HOLD_SELL'"
          :class="[
            'px-3.5 py-1.5 rounded-lg text-[10px] font-bold tracking-wide transition-all cursor-pointer',
            activeFilter === 'HOLD_SELL' ? 'bg-slate-800 text-slate-300 shadow-sm' : 'text-slate-500 hover:text-slate-350'
          ]"
        >
          보류/매도 ({{ recommendationsList?.filter(r => r.action !== 'BUY').length || 0 }})
        </button>
      </div>
      
      <span class="text-[10px] text-slate-500 font-mono" v-if="recommendationsList?.length > 0">
        최종 스캔 시간: {{ formatDateTime(recommendationsList[0].created_at) }}
      </span>
    </div>

    <!-- Recommendation Cards Grid -->
    <div v-if="recommendationsLoading" class="flex-1 flex flex-col items-center justify-center py-20 glass-card bg-slate-950/10 border-slate-900/60">
      <div class="relative w-16 h-16 flex items-center justify-center">
        <div class="absolute inset-0 rounded-full border-4 border-brandIndigo/10 border-t-brandIndigo animate-spin"></div>
        <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 text-brandIndigo animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 9.172V5L8 4z" />
        </svg>
      </div>
      <h3 class="text-sm font-bold text-white mt-4">멀티 에이전트 의사 결정 분석 중</h3>
      <p class="text-xs text-slate-500 mt-2 max-w-sm text-center leading-relaxed">
        애널리스트 및 리서처 8인이 개별 지표를 교차 검증하고 의견 조율을 진행하고 있습니다. 잠시만 기다려 주세요. (약 15-30초 소요)
      </p>
    </div>

    <div v-else-if="filteredRecs.length === 0" class="flex-1 flex flex-col items-center justify-center py-24 glass-card bg-slate-950/10 border-slate-900/60">
      <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0a2 2 0 01-2 2H6a2 2 0 01-2-2m16 0V9a2 2 0 00-2-2H6a2 2 0 00-2 2v2m16 4h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 15H4" />
      </svg>
      <h3 class="text-xs font-bold text-slate-500 mt-4">스캔 결과가 없습니다.</h3>
      <p class="text-[11px] text-slate-600 mt-1">상단의 "신규 에이전트 추천 스캔 실행" 버튼을 클릭하여 스캔을 시작하세요.</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      <div
        v-for="rec in filteredRecs"
        :key="rec.ticker"
        class="glass-card p-5 flex flex-col justify-between hover:scale-[1.01] hover:-translate-y-0.5"
      >
        <div>
          <!-- Card Header -->
          <div class="flex items-center justify-between border-b border-slate-800/80 pb-3.5 mb-3.5">
            <div>
              <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Ticker</span>
              <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide mt-0.5">{{ rec.ticker }}</h3>
            </div>
            
            <div class="flex items-center gap-2">
              <span :class="['text-[10px] font-bold border px-2 py-0.8 rounded-lg uppercase tracking-wide', getActionBadgeClass(rec.action)]">
                {{ rec.action }}
              </span>
              <div class="bg-slate-900 border border-slate-800 px-2 py-0.8 rounded-lg flex flex-col items-center">
                <span class="text-[8px] text-slate-500 font-bold uppercase">Confidence</span>
                <span class="text-[10px] font-outfit font-extrabold text-brandIndigo leading-none mt-0.5">
                  {{ (rec.confidence * 100).toFixed(0) }}%
                </span>
              </div>
            </div>
          </div>

          <!-- Rationale Synopsis -->
          <div class="flex flex-col gap-1.5 mb-5">
            <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">최종 의사결정 요약 (Rationale)</span>
            <p class="text-[11px] text-slate-300 leading-relaxed line-clamp-3">
              {{ rec.rationale }}
            </p>
          </div>
        </div>

        <!-- Card Actions -->
        <div class="flex items-center gap-2.5 pt-3 border-t border-slate-800/60 mt-auto">
          <button
            @click="openDetails(rec)"
            class="flex-1 bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-white font-bold py-2.5 px-3 rounded-xl text-xs transition-colors cursor-pointer border border-slate-800/80 flex items-center justify-center gap-1.5"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            <span>토론 상세 정보</span>
          </button>
          
          <button
            @click="handleAddToWatchlist(rec.ticker)"
            :disabled="isInWatchlist(rec.ticker) || watchlistAdding[rec.ticker]"
            :class="[
              'px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all duration-300 flex items-center justify-center gap-1.5 shrink-0',
              isInWatchlist(rec.ticker)
                ? 'bg-slate-900 border border-slate-850 text-slate-500 cursor-not-allowed'
                : 'bg-brandIndigo/10 hover:bg-brandIndigo text-brandIndigo hover:text-white border border-brandIndigo/35 cursor-pointer shadow-md hover:shadow-indigo-500/10'
            ]"
          >
            <span v-if="watchlistAdding[rec.ticker]" class="w-3 h-3 rounded-full border border-brandIndigo/20 border-t-brandIndigo animate-spin"></span>
            <svg v-else-if="isInWatchlist(rec.ticker)" xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 text-brandGreen" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ isInWatchlist(rec.ticker) ? '등록 완료' : '관심종목 추가' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- BLACKBOARD DEBATE SLIDER DRAWER PANEL -->
    <transition name="slide">
      <div
        v-if="selectedRec"
        class="fixed inset-y-0 right-0 w-full max-w-4xl bg-[#090C16]/95 backdrop-blur-xl border-l border-slate-800/90 shadow-2xl z-50 flex flex-col justify-between select-none"
      >
        <!-- Drawer Header -->
        <div class="p-6 border-b border-slate-800/80 flex items-center justify-between shrink-0 bg-slate-950/40">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-brandIndigo/10 flex items-center justify-center font-outfit font-extrabold text-brandIndigo text-lg border border-brandIndigo/25">
              {{ selectedRec.ticker.split(':')[1] || selectedRec.ticker }}
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h3 class="font-outfit font-extrabold text-base text-white tracking-wide leading-none">{{ selectedRec.ticker }}</h3>
                <span :class="['text-[9px] font-bold border px-1.5 py-0.2 rounded font-mono', getActionBadgeClass(selectedRec.action)]">
                  {{ selectedRec.action }}
                </span>
                <span class="text-[10px] text-slate-500 font-mono">신뢰 점수: {{ (selectedRec.confidence * 100).toFixed(0) }}%</span>
              </div>
              <span class="text-[10px] text-slate-500 font-mono mt-1 block">에이전트 종합 스캔 검증 보고서</span>
            </div>
          </div>
          
          <button
            @click="closeDetails"
            class="w-8 h-8 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white flex items-center justify-center cursor-pointer transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Drawer Content (Scrollable) -->
        <div class="flex-1 overflow-y-auto p-6 flex flex-col gap-6 scrollbar">
          
          <!-- Final Approved Verdict Box (Risk Manager checked) -->
          <div class="bg-slate-900/35 border border-slate-800/80 rounded-2xl p-5 relative overflow-hidden">
            <div class="absolute top-0 right-0 w-32 h-32 rounded-full bg-brandIndigo/5 blur-2xl"></div>
            
            <div class="flex items-center gap-2.5 text-xs text-white font-extrabold mb-3">
              <span class="w-1.5 h-1.5 rounded-full bg-brandIndigo glow-dot text-brandIndigo"></span>
              <h4>최종 의사결정 합의 (Blackboard Verdict)</h4>
            </div>
            <p class="text-xs text-slate-350 leading-relaxed font-medium">
              {{ selectedRec.rationale }}
            </p>
          </div>

          <!-- Stage 1: Analyst Team Insights (4 Columns Grid) -->
          <div class="flex flex-col gap-3">
            <div class="flex items-center gap-2 border-b border-slate-800/60 pb-2">
              <span class="text-[10px] bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono font-bold">Stage 1</span>
              <h4 class="text-xs font-bold text-slate-300">애널리스트 분석 (Analyst Reports)</h4>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Technical Analyst -->
              <div class="bg-slate-900/20 border border-slate-850 rounded-xl p-4 flex flex-col justify-between">
                <div>
                  <div class="flex items-center justify-between border-b border-slate-800/60 pb-2 mb-2.5">
                    <span class="text-xs font-bold text-white">기술적 분석가</span>
                    <span :class="['text-[8px] font-bold border px-1.5 py-0.2 rounded font-mono', getActionBadgeClass(getAgentState(selectedRec, 'TechnicalAnalyst')?.action)]">
                      {{ getAgentState(selectedRec, 'TechnicalAnalyst')?.action || 'HOLD' }}
                    </span>
                  </div>
                  <p class="text-[11px] text-slate-400 leading-relaxed">
                    {{ getAgentState(selectedRec, 'TechnicalAnalyst')?.reason || '데이터 수집 대기 중...' }}
                  </p>
                </div>
                <div class="flex justify-between items-center text-[9px] text-slate-500 font-mono mt-3 pt-2 border-t border-slate-800/40">
                  <span>TechnicalAnalyst</span>
                  <span>가중치: {{ (getAgentState(selectedRec, 'TechnicalAnalyst')?.weight || 0.5).toFixed(2) }}</span>
                </div>
              </div>

              <!-- Fundamentals Analyst -->
              <div class="bg-slate-900/20 border border-slate-850 rounded-xl p-4 flex flex-col justify-between">
                <div>
                  <div class="flex items-center justify-between border-b border-slate-800/60 pb-2 mb-2.5">
                    <span class="text-xs font-bold text-white">기본적 재무 분석가</span>
                    <span :class="['text-[8px] font-bold border px-1.5 py-0.2 rounded font-mono', getActionBadgeClass(getAgentState(selectedRec, 'FundamentalsAnalyst')?.action)]">
                      {{ getAgentState(selectedRec, 'FundamentalsAnalyst')?.action || 'HOLD' }}
                    </span>
                  </div>
                  <p class="text-[11px] text-slate-400 leading-relaxed">
                    {{ getAgentState(selectedRec, 'FundamentalsAnalyst')?.reason || '기업 재무 평가 정보 없음.' }}
                  </p>
                </div>
                <div class="flex justify-between items-center text-[9px] text-slate-500 font-mono mt-3 pt-2 border-t border-slate-800/40">
                  <span>FundamentalsAnalyst</span>
                  <span>가중치: {{ (getAgentState(selectedRec, 'FundamentalsAnalyst')?.weight || 0.5).toFixed(2) }}</span>
                </div>
              </div>

              <!-- Sentiment Analyst -->
              <div class="bg-slate-900/20 border border-slate-850 rounded-xl p-4 flex flex-col justify-between">
                <div>
                  <div class="flex items-center justify-between border-b border-slate-800/60 pb-2 mb-2.5">
                    <span class="text-xs font-bold text-white">시장 여론/소셜 감성 분석가</span>
                    <span :class="['text-[8px] font-bold border px-1.5 py-0.2 rounded font-mono', getActionBadgeClass(getAgentState(selectedRec, 'SentimentAnalyst')?.action)]">
                      {{ getAgentState(selectedRec, 'SentimentAnalyst')?.action || 'HOLD' }}
                    </span>
                  </div>
                  <p class="text-[11px] text-slate-400 leading-relaxed">
                    {{ getAgentState(selectedRec, 'SentimentAnalyst')?.reason || '소셜 포럼 버즈 횡보 중.' }}
                  </p>
                </div>
                <div class="flex justify-between items-center text-[9px] text-slate-500 font-mono mt-3 pt-2 border-t border-slate-800/40">
                  <span>SentimentAnalyst</span>
                  <span>가중치: {{ (getAgentState(selectedRec, 'SentimentAnalyst')?.weight || 0.5).toFixed(2) }}</span>
                </div>
              </div>

              <!-- News Analyst -->
              <div class="bg-slate-900/20 border border-slate-850 rounded-xl p-4 flex flex-col justify-between">
                <div>
                  <div class="flex items-center justify-between border-b border-slate-800/60 pb-2 mb-2.5">
                    <span class="text-xs font-bold text-white">글로벌 매크로 뉴스 분석가</span>
                    <span :class="['text-[8px] font-bold border px-1.5 py-0.2 rounded font-mono', getActionBadgeClass(getAgentState(selectedRec, 'NewsAnalyst')?.action)]">
                      {{ getAgentState(selectedRec, 'NewsAnalyst')?.action || 'HOLD' }}
                    </span>
                  </div>
                  <p class="text-[11px] text-slate-400 leading-relaxed">
                    {{ getAgentState(selectedRec, 'NewsAnalyst')?.reason || '특이 뉴스 헤드라인 없음.' }}
                  </p>
                </div>
                <div class="flex justify-between items-center text-[9px] text-slate-500 font-mono mt-3 pt-2 border-t border-slate-800/40">
                  <span>NewsAnalyst</span>
                  <span>가중치: {{ (getAgentState(selectedRec, 'NewsAnalyst')?.weight || 0.5).toFixed(2) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Stage 2: Researcher Team Debate (Side-by-side) -->
          <div class="flex flex-col gap-3">
            <div class="flex items-center gap-2 border-b border-slate-800/60 pb-2">
              <span class="text-[10px] bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono font-bold">Stage 2</span>
              <h4 class="text-xs font-bold text-slate-300">리서처 토론 (Bullish vs Bearish Debate)</h4>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Bullish Researcher -->
              <div class="bg-brandGreen/5 border border-brandGreen/20 rounded-xl p-4.5">
                <div class="flex items-center justify-between border-b border-brandGreen/10 pb-2 mb-3">
                  <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-brandGreen"></span>
                    <h5 class="text-xs font-bold text-brandGreen">매수 강세 리서처</h5>
                  </div>
                  <span class="text-[10px] font-outfit font-extrabold text-brandGreen font-mono">
                    Conviction: {{ ((getAgentState(selectedRec, 'BullishResearcher')?.weight || 0.5) * 100).toFixed(0) }}%
                  </span>
                </div>
                <p class="text-[11px] text-slate-300 leading-relaxed whitespace-pre-line font-medium">
                  {{ getAgentState(selectedRec, 'BullishResearcher')?.reason?.replace('Bullish Thesis: ', '') || '매수 가치 논의 부재.' }}
                </p>
              </div>

              <!-- Bearish Researcher -->
              <div class="bg-brandRed/5 border border-brandRed/20 rounded-xl p-4.5">
                <div class="flex items-center justify-between border-b border-brandRed/10 pb-2 mb-3">
                  <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-brandRed"></span>
                    <h5 class="text-xs font-bold text-brandRed">위험 방어 리서처</h5>
                  </div>
                  <span class="text-[10px] font-outfit font-extrabold text-brandRed font-mono">
                    Conviction: {{ ((getAgentState(selectedRec, 'BearishResearcher')?.weight || 0.5) * 100).toFixed(0) }}%
                  </span>
                </div>
                <p class="text-[11px] text-slate-300 leading-relaxed whitespace-pre-line font-medium">
                  {{ getAgentState(selectedRec, 'BearishResearcher')?.reason?.replace('Bearish Thesis: ', '') || '매도 위험 지적 부재.' }}
                </p>
              </div>
            </div>
          </div>

          <!-- Stage 3 & 4: Trader Synthesis & Risk Agent Checks -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Stage 3: Trader Agent Decision -->
            <div class="flex flex-col gap-3">
              <div class="flex items-center gap-2 border-b border-slate-800/60 pb-2">
                <span class="text-[10px] bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono font-bold">Stage 3</span>
                <h4 class="text-xs font-bold text-slate-300">트레이더 조율 (Trader synthesis)</h4>
              </div>
              
              <div class="bg-slate-900/30 border border-slate-850 rounded-xl p-4 flex-1">
                <div class="flex items-center justify-between border-b border-slate-800/40 pb-2 mb-2.5">
                  <span class="text-[11px] font-bold text-white">TraderAgent 의사결정</span>
                  <span :class="['text-[8px] font-bold border px-1.5 py-0.2 rounded font-mono', getActionBadgeClass(getAgentState(selectedRec, 'TraderAgent')?.action)]">
                    {{ getAgentState(selectedRec, 'TraderAgent')?.action || 'HOLD' }}
                  </span>
                </div>
                <p class="text-[11px] text-slate-350 leading-relaxed">
                  {{ getAgentState(selectedRec, 'TraderAgent')?.reason || '트레이더 분석이 진행 중입니다.' }}
                </p>
                <div class="text-[9px] text-slate-500 font-mono mt-3 pt-2 border-t border-slate-800/40 text-right">
                  최종 자신감 가중치: {{ ((getAgentState(selectedRec, 'TraderAgent')?.weight || 0.5) * 100).toFixed(0) }}%
                </div>
              </div>
            </div>

            <!-- Stage 4: Risk Management Agent check -->
            <div class="flex flex-col gap-3">
              <div class="flex items-center gap-2 border-b border-slate-800/60 pb-2">
                <span class="text-[10px] bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono font-bold">Stage 4</span>
                <h4 class="text-xs font-bold text-slate-300">리스크 검증 (Risk Guard)</h4>
              </div>
              
              <div class="bg-slate-900/30 border border-slate-850 rounded-xl p-4 flex-1">
                <div class="flex items-center justify-between border-b border-slate-800/40 pb-2 mb-2.5">
                  <span class="text-[11px] font-bold text-white">리스크 평가 결과</span>
                  <span :class="[
                    'text-[8px] font-bold border px-1.5 py-0.2 rounded font-mono',
                    getAgentState(selectedRec, 'RiskManagementAgent')?.reason.includes('CRITICAL') ? 'bg-brandRed/10 text-brandRed border-brandRed/30' :
                    getAgentState(selectedRec, 'RiskManagementAgent')?.reason.includes('HIGH') ? 'bg-brandGold/10 text-brandGold border-brandGold/30' :
                    'bg-brandGreen/10 text-brandGreen border-brandGreen/30'
                  ]">
                    {{ 
                      getAgentState(selectedRec, 'RiskManagementAgent')?.reason.includes('CRITICAL') ? 'CRITICAL RISK' :
                      getAgentState(selectedRec, 'RiskManagementAgent')?.reason.includes('HIGH') ? 'HIGH RISK' : 'LOW RISK'
                    }}
                  </span>
                </div>
                <p class="text-[11px] text-slate-350 leading-relaxed">
                  {{ getAgentState(selectedRec, 'RiskManagementAgent')?.reason || '변동성/유동성 리스크 한도가 승인되었습니다.' }}
                </p>
                <div class="text-[9px] text-slate-500 font-mono mt-3 pt-2 border-t border-slate-800/40 text-right">
                  RiskManagementAgent (최종 한도 승인)
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- Drawer Footer Actions -->
        <div class="p-6 border-t border-slate-800/80 flex items-center justify-end gap-3 shrink-0 bg-slate-950/20">
          <button
            @click="closeDetails"
            class="bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white font-bold py-3 px-6 rounded-xl text-xs transition-colors cursor-pointer border border-slate-800/80"
          >
            닫기
          </button>
          
          <button
            @click="handleAddToWatchlist(selectedRec.ticker)"
            :disabled="isInWatchlist(selectedRec.ticker) || watchlistAdding[selectedRec.ticker]"
            :class="[
              'py-3 px-6 rounded-xl text-xs font-bold transition-all duration-300 flex items-center gap-1.5 cursor-pointer shadow-lg',
              isInWatchlist(selectedRec.ticker)
                ? 'bg-slate-900 border border-slate-850 text-slate-500 cursor-not-allowed shadow-none'
                : 'bg-brandIndigo hover:bg-indigo-600 text-white shadow-indigo-500/20 hover:shadow-indigo-500/30'
            ]"
          >
            <span v-if="watchlistAdding[selectedRec.ticker]" class="w-3 h-3 rounded-full border border-white/25 border-t-white animate-spin"></span>
            <svg v-else-if="isInWatchlist(selectedRec.ticker)" xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandGreen" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ isInWatchlist(selectedRec.ticker) ? '관심종목 등록 완료' : '관심종목에 추가' }}</span>
          </button>
        </div>
      </div>
    </transition>

    <!-- Background dim overlay when drawer is open -->
    <transition name="fade">
      <div
        v-if="selectedRec"
        class="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-40"
        @click="closeDetails"
      ></div>
    </transition>
  </div>
</template>

<style scoped>
.scrollbar::-webkit-scrollbar {
  width: 5px;
}
.scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 9999px;
}
.scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.18);
}

/* Slide Drawer Transitions */
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
