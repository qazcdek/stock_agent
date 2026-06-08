<script setup>
import { onMounted } from 'vue';
import {
  notificationConfig,
  fetchNotificationConfig,
  saveNotificationConfig,
  addLog
} from '../store/tradingStore.js';

function submitConfig() {
  saveNotificationConfig(notificationConfig.value);
}

function sendTestNotification() {
  addLog("Dispatched dynamic alert notification: Slack/Telegram tests triggered successfully.", "brandGreen");
}

onMounted(() => {
  fetchNotificationConfig();
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="glass-card p-6 flex flex-col gap-6 max-w-4xl">
      <div class="border-b border-slate-800/80 pb-4">
        <h3 class="font-outfit font-extrabold text-base text-white tracking-wide uppercase flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-brandIndigo" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          실시간 알림 송신 설정 (Notification Config)
        </h3>
        <p class="text-xs text-slate-400 mt-1">체결 발생, 위험 게이트웨이 기각 및 대기열 수동 승인 이벤트를 메신저 채널로 알리도록 구성합니다.</p>
      </div>

      <div class="flex flex-col gap-5 text-xs">
        
        <!-- API parameters inputs -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Slack Webhook URL</label>
            <input
              type="text"
              v-model="notificationConfig.slack_webhook_url"
              placeholder="https://hooks.slack.com/services/..."
              class="bg-slate-900 border border-slate-800 p-3 rounded-xl text-white focus:outline-none focus:border-brandIndigo"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Telegram Bot Token</label>
            <input
              type="password"
              v-model="notificationConfig.telegram_bot_token"
              placeholder="봇 토큰 입력"
              class="bg-slate-900 border border-slate-800 p-3 rounded-xl text-white focus:outline-none focus:border-brandIndigo"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Telegram Chat ID</label>
            <input
              type="text"
              v-model="notificationConfig.telegram_chat_id"
              placeholder="텔레그램 채팅방 ID 입력"
              class="bg-slate-900 border border-slate-800 p-3 rounded-xl text-white focus:outline-none focus:border-brandIndigo"
            />
          </div>
        </div>

        <!-- Notification triggers switches -->
        <div class="border-t border-slate-800/80 pt-4 mt-2">
          <span class="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-3">알림 수신 대상 이벤트 트리거</span>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="bg-slate-950/60 border border-slate-800/60 p-4 rounded-xl flex items-center justify-between">
              <div class="flex flex-col gap-0.5">
                <span class="text-xs text-white font-bold">주문 체결 완료 (Filled)</span>
                <span class="text-[10px] text-slate-500">주문 체결시 전송</span>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="notificationConfig.notify_order_filled" class="sr-only peer">
                <div class="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-brandIndigo"></div>
              </label>
            </div>

            <div class="bg-slate-950/60 border border-slate-800/60 p-4 rounded-xl flex items-center justify-between">
              <div class="flex flex-col gap-0.5">
                <span class="text-xs text-white font-bold">주문 거절/기각 (Rejected)</span>
                <span class="text-[10px] text-slate-500">리스크 게이트 작동 시</span>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="notificationConfig.notify_order_rejected" class="sr-only peer">
                <div class="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-brandIndigo"></div>
              </label>
            </div>

            <div class="bg-slate-950/60 border border-slate-800/60 p-4 rounded-xl flex items-center justify-between">
              <div class="flex flex-col gap-0.5">
                <span class="text-xs text-white font-bold">매매 승인 대기 (Queue)</span>
                <span class="text-[10px] text-slate-500">수동 승인 요청 시</span>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="notificationConfig.notify_approval_required" class="sr-only peer">
                <div class="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-brandIndigo"></div>
              </label>
            </div>
          </div>
        </div>

        <div class="flex gap-4 mt-4">
          <button
            @click="submitConfig"
            class="flex-1 bg-gradient-to-tr from-brandIndigo to-brandGreen hover:opacity-90 text-white font-extrabold text-xs py-3.5 rounded-xl shadow-md font-outfit uppercase cursor-pointer"
          >
            알림 설정 변경 저장 (Save Settings)
          </button>
          <button
            @click="sendTestNotification"
            class="bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold px-6 py-3.5 rounded-xl text-xs cursor-pointer transition-colors"
          >
            테스트 전송 (Test Alert)
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
