<script setup>
import { onMounted } from 'vue';
import {
  systemHealth,
  fetchSystemHealth,
  formatNumber
} from '../store/tradingStore.js';

onMounted(() => {
  fetchSystemHealth();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- System Load Stats -->
      <div class="glass-card p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandIndigo" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
            </svg>
            시스템 리소스 모니터 (Load)
          </h3>
          <button @click="fetchSystemHealth" class="text-slate-500 hover:text-white text-[10px] uppercase font-bold cursor-pointer">
            갱신
          </button>
        </div>

        <div v-if="systemHealth.system_load" class="flex flex-col gap-5 mt-2">
          <!-- CPU Usage bar -->
          <div class="flex flex-col gap-1.5">
            <div class="flex justify-between items-center text-xs">
              <span class="text-slate-400">CPU Usage Rate</span>
              <span class="text-white font-extrabold font-mono">{{ formatNumber(systemHealth.system_load.cpu_usage_pct) }}%</span>
            </div>
            <div class="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
              <div
                class="bg-brandIndigo h-full rounded-full transition-all duration-500"
                :style="{ width: systemHealth.system_load.cpu_usage_pct + '%' }"
              ></div>
            </div>
          </div>

          <!-- Memory Usage bar -->
          <div class="flex flex-col gap-1.5">
            <div class="flex justify-between items-center text-xs">
              <span class="text-slate-400">Memory Allocation</span>
              <span class="text-white font-extrabold font-mono">{{ formatNumber(systemHealth.system_load.memory_usage_pct) }}%</span>
            </div>
            <div class="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
              <div
                class="bg-brandGreen h-full rounded-full transition-all duration-500"
                :style="{ width: systemHealth.system_load.memory_usage_pct + '%' }"
              ></div>
            </div>
          </div>

          <!-- Process ID -->
          <div class="bg-slate-900/40 border border-slate-800/80 p-3.5 rounded-xl flex justify-between items-center text-xs">
            <span class="text-slate-400">Web server process PID</span>
            <span class="text-white font-mono font-bold">{{ systemHealth.system_load.pid }}</span>
          </div>
        </div>
      </div>

      <!-- Databases Connections Status -->
      <div class="glass-card lg:col-span-2 p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 class="font-outfit font-extrabold text-sm text-white tracking-wide uppercase flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-brandGreen" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
            데이터베이스 클라이언트 연결 현황 (Databases Status)
          </h3>
        </div>

        <div v-if="systemHealth.databases" class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
          <div
            v-for="(dbInfo, dbName) in systemHealth.databases"
            :key="dbName"
            class="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex items-center justify-between"
          >
            <div class="flex flex-col gap-0.5">
              <span class="text-xs text-white font-outfit font-extrabold uppercase">{{ dbName }}</span>
              <span class="text-[10px] text-slate-500 font-mono">{{ dbInfo.engine || dbInfo.path }}</span>
            </div>
            
            <span :class="['px-2 py-0.5 rounded text-[9px] font-extrabold border uppercase flex items-center gap-1.5',
              dbInfo.active ? 'bg-brandGreen/10 border-brandGreen/30 text-brandGreen' : 'bg-brandRed/10 border-brandRed/30 text-brandRed'
            ]">
              <span class="w-1 h-1 rounded-full bg-current" :class="dbInfo.active ? 'glow-dot' : ''"></span>
              {{ dbInfo.active ? 'Active' : 'Offline' }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- LLM Provider configurations status -->
    <div v-if="systemHealth.llm_provider" class="glass-card p-5">
      <div class="border-b border-slate-800/80 pb-3 mb-4 flex justify-between items-center">
        <h3 class="font-outfit font-extrabold text-xs text-white uppercase tracking-wider">
          LLM Provider & LLM Agents Configuration
        </h3>
        <span :class="['px-2.5 py-0.5 rounded text-[9px] font-extrabold border uppercase',
          systemHealth.llm_provider.initialized ? 'bg-brandGreen/10 border-brandGreen/30 text-brandGreen' : 'bg-brandRed/10 border-brandRed/30 text-brandRed'
        ]">
          {{ systemHealth.llm_provider.initialized ? 'Provider Ready' : 'Initializing' }}
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
        <div class="bg-slate-900/40 p-4 rounded-xl border border-slate-800/80 flex flex-col gap-1.5">
          <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">Fast LLM Model (Standard autocomplete & suggestions)</span>
          <span class="text-white font-mono font-bold">{{ systemHealth.llm_provider.fast_model || '-' }}</span>
        </div>
        
        <div class="bg-slate-900/40 p-4 rounded-xl border border-slate-800/80 flex flex-col gap-1.5">
          <span class="text-[9px] text-slate-500 font-bold uppercase tracking-wider">Deep LLM Model (Advanced analysis & reasoning strategy)</span>
          <span class="text-white font-mono font-bold">{{ systemHealth.llm_provider.deep_model || '-' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
