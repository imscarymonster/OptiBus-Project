<template>
  <div class="h-screen bg-gray-900 flex flex-col items-center justify-center text-white relative">
    
    <button @click="handleLogout" class="absolute top-6 left-6 text-gray-400 hover:text-white text-xl transition-colors">
      ← 退出排班
    </button>

    <div class="text-center space-y-6">
      <p class="text-3xl text-gray-400 font-bold">当前任务</p>
      <h1 class="text-7xl font-black text-green-500 tracking-widest">
        2号线 <span class="text-5xl text-white">正常行驶</span>
      </h1>
      <p class="text-4xl font-bold mt-10">下一站：体育场</p>
    </div>

    <div class="mt-8 bg-gray-800 p-4 rounded-xl border border-gray-700 shadow-inner inline-block text-left z-10">
      <div class="flex items-center gap-2 mb-2">
        <div class="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
        <span class="text-sm text-gray-400 font-bold tracking-widest">GPS 卫星连接已建立</span>
      </div>
      <div class="font-mono text-green-400">
        <p>LAT (纬度): {{ currentLat }}</p>
        <p>LNG (经度): {{ currentLng }}</p>
      </div>
    </div>
    <button @click="simulateDispatch" class="absolute bottom-12 px-8 py-4 bg-red-600 hover:bg-red-500 rounded-full text-xl font-bold transition-all active:scale-95 shadow-lg shadow-red-900">
      ⚠️ 模拟接收后台调度指令 (测试语音)
    </button>
    
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';

const router = useRouter();

// 1. 退出登录逻辑：撕毁通行证，踢回登录页
const handleLogout = () => {
  localStorage.removeItem('driverToken');
  router.push('/login');
};

// 2. 调度语音播报逻辑 (你的原版黑科技)
const simulateDispatch = () => {
  const text = "紧急调度指令：系统检测到1号线客流拥挤。请在送完本车乘客后，立即变更路线，前往1号线支援！";
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'zh-CN';
  utterance.rate = 1.1; // 语速稍快一点，更有调度的感觉
  window.speechSynthesis.speak(utterance);
};

import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

// ==========================================
// 新增：GPS 追踪系统
// ==========================================
const currentLat = ref('正在定位...'); // 纬度
const currentLng = ref('正在定位...'); // 经度
let watchId = null; // 用来存追踪器的ID

const startGPS = () => {
  // 1. 检查手机浏览器是否支持定位
  if (!navigator.geolocation) {
    alert('⚠️ 您的设备或浏览器不支持 GPS 定位！');
    return;
  }

  // 2. 开启持续追踪（只要司机移动，就会自动触发）
  watchId = navigator.geolocation.watchPosition(
    (position) => {
      // 成功拿到坐标！
      currentLat.value = position.coords.latitude.toFixed(6);  // 保留6位小数
      currentLng.value = position.coords.longitude.toFixed(6);

      console.log(`📍 当前坐标: [${currentLng.value}, ${currentLat.value}]`);

      // 3. 把坐标实时发送给后端大脑
      // 💡 注意：等后端部署到云端后，把下面的 10.180.21.71 换成云服务器公网 IP！
      axios.post('http://10.180.21.71:8000/api/buses/location/update', {
        busId: localStorage.getItem('busId') || 'driver01', // 动态获取当前车辆ID，防止多台手机冲突
        lng: currentLng.value, // 传给后端的经度（问一下，如果他写死要 x 和 y，你就改成 x 和 y）
        lat: currentLat.value, // 传给后端的纬度
        status: 'in-transit'
      })
      .then(() => {
        console.log('🚀 坐标同步成功');
      })
      .catch((e) => {
        console.error('❌ 坐标同步失败', e);
      });
    },
    (error) => {
      console.error('获取位置失败:', error.message);
      currentLat.value = '定位失败';
      currentLng.value = '请检查权限';
    },
    {
      enableHighAccuracy: true, // 开启高精度模式（强制调用手机真实GPS芯片）
      maximumAge: 0,           // 不要缓存，每次都要最新的
      timeout: 5000            // 5秒定位不到就算超时
    }
  );
};

// 页面一打开，立刻启动 GPS
onMounted(() => {
  startGPS();
});

// 司机退出页面（下班）时，立刻关闭 GPS 追踪，给手机省电！
onUnmounted(() => {
  if (watchId !== null) {
    navigator.geolocation.clearWatch(watchId);
  }
});

// 原有的退出登录逻辑...
const handleLogout = () => {
  localStorage.removeItem('driverToken');
  router.push('/login');
};

</script>