<template>
  <div class="h-screen bg-gray-100 flex overflow-hidden">
    
    <div class="w-64 bg-gray-900 text-white p-6 flex flex-col shadow-2xl z-10">
      <h2 class="text-2xl font-black tracking-widest text-blue-400 mb-10">
        OptiBus <br><span class="text-sm text-gray-400 font-normal">智能调度总控台</span>
      </h2>
      
      <nav class="flex flex-col space-y-2 flex-grow">
        <button 
          @click="activeTab = 'monitor'" 
          :class="['px-4 py-3 rounded-lg text-left font-bold transition-all flex items-center gap-3', activeTab === 'monitor' ? 'bg-blue-600 shadow-md text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200']"
        >
          <span>🗺️</span> 实时监控看板
        </button>
        
        <button 
          @click="activeTab = 'schedule'" 
          :class="['px-4 py-3 rounded-lg text-left font-bold transition-all flex items-center gap-3', activeTab === 'schedule' ? 'bg-blue-600 shadow-md text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200']"
        >
          <span>🚌</span> 车辆排班管理
        </button>
        
        <button 
          @click="activeTab = 'warning'" 
          :class="['px-4 py-3 rounded-lg text-left font-bold transition-all flex items-center gap-3', activeTab === 'warning' ? 'bg-blue-600 shadow-md text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200']"
        >
          <span>⚠️</span> 运力重构预警
        </button>
      </nav>

      <button @click="handleLogout" class="mt-auto text-gray-500 hover:text-red-400 font-bold text-sm text-left transition-colors flex items-center gap-2">
        <span>🚪</span> 安全退出登录
      </button>
    </div>

    <div class="flex-1 p-8 overflow-y-auto">
      
      <div v-if="activeTab === 'monitor'" class="animate-fade-in">
        <div class="grid grid-cols-3 gap-6 mb-6">
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <p class="text-gray-500 text-sm font-bold mb-1">当前在线车辆</p>
            <span class="text-4xl font-black text-gray-800">{{ currentBusCount }}</span>
          </div>
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <p class="text-gray-500 text-sm font-bold mb-1">全网平均候车时长</p>
            <div class="flex items-end space-x-2"><span class="text-4xl font-black text-green-500">4.2</span><span class="text-gray-400 font-medium mb-1">分钟</span></div>
          </div>
          <div class="bg-white p-6 rounded-2xl shadow-sm border border-red-100 bg-red-50">
            <p class="text-red-500 text-sm font-bold mb-1">系统运力拥堵预警</p>
            <div class="flex items-end space-x-2"><span class="text-4xl font-black text-red-600">1号线</span><span class="text-red-400 font-medium mb-1">过载</span></div>
          </div>
        </div>
        
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <h3 class="text-lg font-bold text-gray-800 mb-4">📍 园区全路网实时拓扑图</h3>
          <MapCanvas :isAdmin="true" @updateBusCount="handleBusCountUpdate" />
        </div>
      </div>

      <div v-if="activeTab === 'schedule'" class="animate-fade-in bg-white p-8 rounded-2xl shadow-sm border border-gray-100 h-full">
        <div class="flex justify-between items-center mb-6">
          <h3 class="text-xl font-black text-gray-800">今日车辆排班计划</h3>
          <button class="px-4 py-2 bg-blue-600 text-white rounded-lg font-bold text-sm hover:bg-blue-700">＋ 新增排班</button>
        </div>
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-sm border-b border-gray-200">
              <th class="p-4 rounded-tl-lg">车牌号</th>
              <th class="p-4">负责线路</th>
              <th class="p-4">当班司机</th>
              <th class="p-4">当前状态</th>
              <th class="p-4 rounded-tr-lg">操作</th>
            </tr>
          </thead>
          <tbody class="text-gray-700">
            <tr class="border-b border-gray-100 hover:bg-gray-50 transition-colors">
              <td class="p-4 font-bold text-blue-600">京A·BD101</td>
              <td class="p-4"><span class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-bold">1号线</span></td>
              <td class="p-4">张师傅 (工号: driver01)</td>
              <td class="p-4"><span class="flex items-center gap-2"><div class="w-2 h-2 rounded-full bg-green-500"></div> 行驶中</span></td>
              <td class="p-4"><button @click="editDriver('京A·BD101')" class="text-blue-500 hover:underline text-sm">AI 排班</button></td>
            </tr>
            <tr class="border-b border-gray-100 hover:bg-gray-50 transition-colors">
              <td class="p-4 font-bold text-green-600">京A·BD202</td>
              <td class="p-4"><span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs font-bold">2号线</span></td>
              <td class="p-4">李师傅 (工号: driver02)</td>
              <td class="p-4"><span class="flex items-center gap-2"><div class="w-2 h-2 rounded-full bg-green-500"></div> 行驶中</span></td>
              <td class="p-4"><button @click="editDriver('京A·BD202')" class="text-blue-500 hover:underline text-sm">AI 排班</button></td>
            </tr>
            <tr class="border-b border-gray-100 hover:bg-gray-50 transition-colors">
              <td class="p-4 font-bold text-gray-600">京A·BD303</td>
              <td class="p-4"><span class="bg-gray-200 text-gray-600 px-2 py-1 rounded text-xs font-bold">待命备勤</span></td>
              <td class="p-4">王师傅 (工号: driver03)</td>
              <td class="p-4"><span class="flex items-center gap-2"><div class="w-2 h-2 rounded-full bg-gray-400"></div> 场站休息</span></td>
              <td class="p-4"><button @click="dispatchVehicle('京A·BD303')" class="text-blue-500 hover:underline text-sm">派车</button></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="activeTab === 'warning'" class="animate-fade-in space-y-6">
        <div class="bg-red-50 p-6 rounded-2xl border border-red-200 flex justify-between items-center shadow-sm">
          <div>
            <h3 class="text-xl font-black text-red-600 mb-2 flex items-center gap-2"><span>🚨</span> 紧急情况：1号线运力告急！</h3>
            <div class="mt-4 flex gap-4">
    <button @click="sendDispatchAlert" class="px-6 py-3 bg-red-600 text-white rounded-xl ...">
      授权 AI 自动执行方案
    </button>
    
    <button @click="simulateMassiveCrowd" class="px-6 py-3 border-2 border-red-600 text-red-600 font-bold rounded-xl hover:bg-red-50 active:scale-95 transition-all flex items-center gap-2">
      <span>⚠️</span> 模拟1号线极端爆满
    </button>
  </div>
            <p class="text-gray-700">系统检测到 <span class="font-bold">图书馆站、中传专享楼</span> 产生大量滞留乘客，排队人数超阀值。</p>
          </div>
          <button @click="sendDispatchAlert" class="px-6 py-3 bg-red-600 text-white rounded-xl font-black text-lg hover:bg-red-700 active:scale-95 shadow-lg shadow-red-600/30 transition-all">
  授权 AI 自动执行方案
</button>
        </div>

        <div class="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
          <h3 class="text-lg font-bold text-gray-800 mb-4">系统建议调度方案</h3>
          <ul class="space-y-3 text-gray-600">
            <li class="flex items-center gap-3"><div class="w-2 h-2 rounded-full bg-blue-500"></div> 建议将场站待命的 <strong>京A·BD303</strong> 立即发往 1号线 支援。</li>
            <li class="flex items-center gap-3"><div class="w-2 h-2 rounded-full bg-green-500"></div> 建议 2号线 <strong>京A·BD202</strong> 卸客后，临时变更线路前往 1号线。</li>
          </ul>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import MapCanvas from '../components/MapCanvas.vue';


const router = useRouter();
// 控制当前显示哪个模块的变量，默认显示 map (监控看板)
const activeTab = ref('monitor'); 

const handleLogout = () => {
  localStorage.removeItem('adminToken');
  router.push('/login');
};

// 模拟发送调度指令 (全自动)
const sendDispatchAlert = () => {
  alert('🚀 全网运力自动重构完成！\nAI 已自动接管所有车辆路线，司机端已全部收到最新导航指令！');
};

// 更换司机逻辑 (全自动)
const editDriver = (busPlate) => {
  alert(`🤖 AI 自动排班触发：\n已自动为 ${busPlate} 匹配并指派了最优备班司机。`);
};

// 派车支援逻辑 (全自动)
const dispatchBus = (busPlate) => {
  alert(`⚡ AI 自动调度执行完毕！\n系统已根据实时运力算法，将待命车辆 ${busPlate} 自动编入【1号线】缓解客流压力。指令已瞬间同步至司机端！`);
};

// 删掉你原本 156~165 行的内容，替换成下面这几行：
const currentBusCount = ref(0); 

const handleBusCountUpdate = (count) => {
  currentBusCount.value = count;
};

import axios from 'axios'; // 确保上面引入了 axios

// 🚀 终极测试：一键触发柔性调度大招
const simulateMassiveCrowd = async () => {
  const confirmMsg = "确定要向【公共教学楼】瞬间注入 40 名排队乘客吗？这将立刻触发后端的跨线调度大招！";
  if (!confirm(confirmMsg)) return;

  console.log("🔥 开始执行高并发注入...");
  let successCount = 0;

  // 利用 Promise.all 瞬间并发 40 个请求
  const requests = Array.from({ length: 40 }).map((_, index) => {
    return axios.post('http://10.180.21.71:8000/api/dispatch/passenger_action', {
      user_id: `mock_burst_${Date.now()}_${index}`,
      route_key: 'line1_cw',
      action: 'join',
      station_id: '公共教学楼'
    }).then(() => successCount++);
  });

  // 找到原来的这段代码：
  try {
    await Promise.all(requests);
    alert(`🎯 注入完毕！成功发送 ${successCount} 名虚拟乘客。\n👉 现在请盯紧地图...`);
  } catch (err) {
    alert("部分请求失败，请检查后端网络！");
  }

// 🚀 替换为下面这段【不卡顿、不阻塞】的版本：
  try {
    await Promise.all(requests);
    // 放弃使用阻塞的 alert，改用控制台打印 + 自动非阻塞弹窗
    console.log(`🎯 注入完毕！成功发送 ${successCount} 名虚拟乘客。`);
    
    // 用原生 JS 在右上角悄悄浮现一个成功提示，3秒后自动消失，绝对不卡顿地图！
    const toast = document.createElement('div');
    toast.innerHTML = `🔥 成功注入 ${successCount} 名排队乘客！后端开始调度...`;
    toast.style.cssText = "position:fixed; top:20px; right:20px; background:#ef4444; color:white; padding:15px 20px; border-radius:8px; z-index:9999; font-weight:bold; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); transition: opacity 0.5s;";
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
    }, 4000);

  } catch (err) {
    console.error("部分请求失败，请检查后端网络！", err);
  }
};

</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>