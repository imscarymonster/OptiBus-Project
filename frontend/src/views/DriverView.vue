<template>
  <div class="h-screen bg-gray-900 flex flex-col items-center justify-center text-white relative">

    <button @click="handleLogout" class="absolute top-6 left-6 text-gray-400 hover:text-white text-xl transition-colors">
      ← 退出排班
    </button>

    <!-- 线路选择 -->
    <div class="absolute top-6 right-6 flex items-center gap-3">
      <span class="text-gray-400 text-sm">驾驶线路：</span>
      <select
        v-model="selectedRouteKey"
        @change="onRouteChange"
        class="bg-gray-800 text-white border border-gray-600 rounded-lg px-3 py-2 text-sm font-bold focus:outline-none focus:border-blue-500"
      >
        <option value="line1_cw">1号线（顺时针）</option>
        <option value="line1_ccw">1号线（逆时针）</option>
        <option value="line2_cw">2号线（顺时针）</option>
        <option value="line2_ccw">2号线（逆时针）</option>
        <option value="teacher_cw">教师专线（顺时针）</option>
        <option value="teacher_ccw">教师专线（逆时针）</option>
      </select>
    </div>

    <div class="text-center space-y-6">
      <p class="text-3xl text-gray-400 font-bold">当前任务</p>
      <h1 class="text-7xl font-black text-green-500 tracking-widest">
        {{ displayRouteName }} <span class="text-5xl text-white">{{ connectionStatus }}</span>
      </h1>
      <p class="text-4xl font-bold mt-10">下一站：{{ nextStation }}</p>
    </div>

    <!-- 模拟行驶按钮（无需真实 GPS） -->
    <div class="mt-6 flex gap-4">
      <button
        @click="toggleSimulateGPS"
        :class="['px-6 py-3 rounded-xl font-bold text-sm transition-all active:scale-95',
          simRunning ? 'bg-yellow-600 hover:bg-yellow-500 text-white' : 'bg-blue-600 hover:bg-blue-500 text-white']"
      >
        {{ simRunning ? '⏸ 停止模拟' : '📍 模拟行驶（无需GPS）' }}
      </button>
    </div>

    <!-- GPS 状态面板 -->
    <div class="mt-8 bg-gray-800 p-4 rounded-xl border border-gray-700 shadow-inner inline-block text-left z-10 min-w-[320px]">
      <div class="flex items-center gap-2 mb-2">
        <div :class="['w-3 h-3 rounded-full animate-pulse', gpsOnline ? 'bg-green-500' : 'bg-red-500']"></div>
        <span class="text-sm text-gray-400 font-bold tracking-widest">
          {{ gpsOnline ? 'GPS 卫星连接已建立' : 'GPS 定位中...' }}
        </span>
      </div>
      <div class="font-mono text-green-400 text-sm">
        <p>LAT (纬度): {{ currentLat }}</p>
        <p>LNG (经度): {{ currentLng }}</p>
        <p class="text-gray-500 text-xs mt-1">后端同步: {{ syncStatus }}</p>
      </div>
    </div>

    <!-- 调度模拟按钮 -->
    <button
      @click="simulateDispatch"
      class="absolute bottom-12 px-8 py-4 bg-red-600 hover:bg-red-500 rounded-full text-xl font-bold transition-all active:scale-95 shadow-lg shadow-red-900"
    >
      ⚠️ 模拟接收后台调度指令 (测试语音)
    </button>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const router = useRouter();

// ==========================================
// 司机身份 & 线路
// ==========================================
const driverId = ref(localStorage.getItem('driverId') || 'driver01');
const selectedRouteKey = ref(localStorage.getItem('driverRoute') || 'line2_cw');

const routeNameMap = {
  line1_cw: '1号线', line1_ccw: '1号线',
  line2_cw: '2号线', line2_ccw: '2号线',
  teacher_cw: '教师专线', teacher_ccw: '教师专线',
};
const displayRouteName = computed(() => routeNameMap[selectedRouteKey.value] || selectedRouteKey.value);

const connectionStatus = ref('正常行驶');
const nextStation = ref('--');
const gpsOnline = ref(false);
const syncStatus = ref('等待首次定位...');

// ==========================================
// 1. 路线切换 → 通知后端
// ==========================================
const onRouteChange = () => {
  localStorage.setItem('driverRoute', selectedRouteKey.value);
  // 立即发送一次定位，让后端更新路线关联
  if (currentLat.value !== '正在定位...' && currentLat.value !== '定位失败') {
    sendLocation(parseFloat(currentLat.value), parseFloat(currentLng.value));
  }
};

// ==========================================
// 2. 退出登录
// ==========================================
const handleLogout = () => {
  localStorage.removeItem('driverToken');
  localStorage.removeItem('driverId');
  localStorage.removeItem('driverRoute');
  router.push('/login');
};

// ==========================================
// 3. 调度语音播报
// ==========================================
const simulateDispatch = () => {
  const text = "紧急调度指令：系统检测到1号线客流拥挤。请在送完本车乘客后，立即变更路线，前往1号线支援！";
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'zh-CN';
  utterance.rate = 1.1;
  window.speechSynthesis.speak(utterance);
};

// ==========================================
// 4. GPS 追踪 + 后端实时同步
// ==========================================
const currentLat = ref('正在定位...');
const currentLng = ref('正在定位...');
let watchId = null;
let syncTimer = null;

const sendLocation = async (lat, lng) => {
  try {
    const res = await axios.post('/api/buses/location/update', {
      busId: driverId.value,
      lat: lat,
      lng: lng,
      status: 'driving',
      routeKey: selectedRouteKey.value,
    });
    syncStatus.value = `已同步 (${res.data.meter?.x?.toFixed(0)}, ${res.data.meter?.y?.toFixed(0)})`;
    gpsOnline.value = true;
  } catch (e) {
    syncStatus.value = '同步失败: ' + (e.response?.status || e.message);
    gpsOnline.value = false;
  }
};

const startGPS = () => {
  if (!navigator.geolocation) {
    currentLat.value = '设备不支持';
    currentLng.value = '设备不支持';
    syncStatus.value = '浏览器不支持GPS';
    return;
  }

  watchId = navigator.geolocation.watchPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      currentLat.value = lat.toFixed(6);
      currentLng.value = lng.toFixed(6);
      gpsOnline.value = true;
      sendLocation(lat, lng);
    },
    (error) => {
      console.error('GPS 错误:', error.message);
      gpsOnline.value = false;

      // 区分不同错误类型给出明确提示
      if (error.code === 1) {
        // PERMISSION_DENIED
        currentLat.value = '权限被拒';
        currentLng.value = '请在浏览器设置中允许定位';
        syncStatus.value = 'GPS 被拒绝，使用模拟坐标';
      } else if (error.code === 2) {
        // POSITION_UNAVAILABLE
        currentLat.value = '信号不可用';
        currentLng.value = '请移至开阔地带';
        syncStatus.value = 'GPS 信号弱，使用模拟坐标';
      } else if (error.code === 3) {
        // TIMEOUT
        currentLat.value = '定位超时';
        currentLng.value = '请重试';
        syncStatus.value = 'GPS 超时，使用模拟坐标';
      } else {
        currentLat.value = '定位失败';
        currentLng.value = '非安全上下文(需HTTPS)';
        syncStatus.value = 'HTTP下GPS不可用，使用模拟坐标';
      }

      // GPS 不可用时自动发送模拟坐标，让车出现在地图上
      sendLocation(18.4300, 110.0000);
    },
    {
      enableHighAccuracy: true,
      maximumAge: 5000,
      timeout: 10000,
    }
  );
};

// ==========================================
// 5. 获取当前车辆的实时拓扑信息
// ==========================================
const fetchBusInfo = async () => {
  try {
    const res = await axios.get('/api/buses/locations');
    const myBus = res.data.buses?.find(b => b.busId === driverId.value);
    if (myBus) {
      nextStation.value = myBus.toStation || '--';
      connectionStatus.value = myBus.status === 'arrived' ? '已到站' : '行驶中';
    }
  } catch (e) {
    // 静默失败
  }
};

// ==========================================
// 生命周期
// ==========================================
onMounted(() => {
  startGPS();
  syncTimer = setInterval(fetchBusInfo, 3000);
});

onUnmounted(() => {
  if (watchId !== null) navigator.geolocation.clearWatch(watchId);
  if (syncTimer) clearInterval(syncTimer);
  stopSimulateGPS();
});

// ==========================================
// 6. 模拟行驶 —— 手机无法获取 GPS 时的演示方案
// ==========================================
const simRunning = ref(false);
let simTimer = null;

// 米制坐标 → 模拟 GPS（逆转换，让后端 gps_to_meters 还原回正确位置）
const meterToGps = (mx, my) => {
  const METERS_PER_DEG_LAT = 111320.0;
  const METERS_PER_DEG_LNG = 105600.0;
  return {
    lat: my / METERS_PER_DEG_LAT + 18.4300,
    lng: mx / METERS_PER_DEG_LNG + 110.0000,
  };
};

// 各线路途径站点米制坐标（与后端 STATIONS_XY 一致）
const ROUTE_STATION_METERS = {
  line1_cw: [
    [0, 0], [287, -78], [77, -260], [-54, -300], [-228, -516],
    [-54, -300], [107, -509], [599, 304], [811, 616], [0, 0],
  ],
  line1_ccw: [
    [0, 0], [811, 616], [599, 304], [107, -509], [-54, -300],
    [-228, -516], [-54, -300], [77, -260], [287, -78], [0, 0],
  ],
  line2_cw: [
    [0, 0], [-195, 67], [-588, -257], [-924, -455],
    [-588, -257], [-195, 67], [-11, 253], [236, 531], [294, 620],
    [624, 693], [591, 636], [418, 444], [338, 296], [186, 140], [0, 0],
  ],
  line2_ccw: [
    [0, 0], [186, 140], [338, 296], [418, 444], [591, 636],
    [624, 693], [294, 620], [236, 531], [-11, 253], [-195, 67],
    [-588, -257], [-924, -455], [-588, -257], [-195, 67], [0, 0],
  ],
  teacher_cw: [
    [0, 0], [186, 140], [338, 296], [186, 140], [0, 0],
    [312, -334], [0, 0],
  ],
  teacher_ccw: [
    [0, 0], [312, -334], [0, 0], [186, 140], [338, 296],
    [186, 140], [0, 0],
  ],
};

const toggleSimulateGPS = () => {
  if (simRunning.value) {
    stopSimulateGPS();
    return;
  }
  startSimulateGPS();
};

const stopSimulateGPS = () => {
  simRunning.value = false;
  if (simTimer) { clearInterval(simTimer); simTimer = null; }
  syncStatus.value = '模拟已停止';
};

const startSimulateGPS = () => {
  const waypoints = ROUTE_STATION_METERS[selectedRouteKey.value];
  if (!waypoints || waypoints.length < 2) {
    alert('当前线路无模拟数据');
    return;
  }

  simRunning.value = true;
  let idx = 0;

  simTimer = setInterval(() => {
    const [mx, my] = waypoints[idx];
    const gps = meterToGps(mx, my);
    currentLat.value = gps.lat.toFixed(6);
    currentLng.value = gps.lng.toFixed(6);
    gpsOnline.value = true;
    sendLocation(gps.lat, gps.lng);
    syncStatus.value = `模拟行驶: ${idx + 1}/${waypoints.length}`;
    idx = (idx + 1) % waypoints.length;
  }, 1500); // 每 1.5 秒移动到下一站

  syncStatus.value = '模拟行驶已启动';
};
</script>
