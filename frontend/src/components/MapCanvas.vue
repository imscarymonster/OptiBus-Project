<template>
  <div class="map-container relative">
    <svg viewBox="0 0 1200 700" class="electronic-map">
      
      <path
        v-for="line in routes"
        :key="line.id"
        :d="line.path"
        :stroke="line.color"
        fill="none"
        :stroke-width="12"
        stroke-linejoin="round"
        stroke-linecap="round"
        class="route-line"
      />

      <g
        v-for="station in stations"
        :key="station.id"
        class="station-group"
        @click="handleStationClick(station)"
      >
        <circle 
          v-if="!station.isTransfer"
          :cx="station.x" 
          :cy="station.y" 
          r="10" 
          fill="#fff" 
          :stroke="station.color" 
          stroke-width="4" 
          class="station-dot" 
        />

        <g v-else class="transfer-capsule" :transform="station.isHorizontal ? `rotate(90 ${station.x} ${station.y})` : ''">
      <rect 
        :x="station.x - 12" 
        :y="station.y - 25" 
        width="24" 
        height="50" 
        rx="12" 
        fill="#fff" 
        stroke="#6c757d" 
        stroke-width="4" 
      />
      <circle :cx="station.x" :cy="station.y - 12" r="3" fill="#adb5bd" />
      <circle :cx="station.x" :cy="station.y + 12" r="3" fill="#adb5bd" />
    </g>

        <text 
          :x="getTextX(station)" 
          :y="getTextY(station)" 
          :text-anchor="getTextAnchor(station)" 
          class="station-text"
        >
          <tspan :x="getTextX(station)" class="text-cn">
            {{ station.nameCN }}
          </tspan>
          <tspan :x="getTextX(station)" dy="16" class="text-en">
            {{ station.nameEN }}
          </tspan>
        </text>
      </g>
      
<g v-for="bus in activeBuses" :key="bus.busId" class="transition-all duration-1000 ease-linear">
      <circle 
        :cx="getBusX(bus)" 
        :cy="getBusY(bus)" 
        r="12" 
        fill="#ffffff" 
        stroke="#3b82f6" 
        stroke-width="4" 
        class="shadow-lg"
      />
      <text 
        :x="getBusX(bus)" 
        :y="getBusY(bus) - 18" 
        text-anchor="middle" 
        class="text-[10px] font-bold fill-blue-800"
      >
        {{ bus.busId }}
      </text>
    </g>
    </svg><div class="absolute bottom-6 right-6 bg-white/90 backdrop-blur-sm p-4 rounded-xl shadow-lg border border-gray-200 flex gap-6 text-xs font-bold text-gray-700 pointer-events-none z-20">
      <div class="flex items-center gap-2"><div class="w-8 h-2 bg-[#102c4c] rounded-full"></div>1号线</div>
      <div class="flex items-center gap-2"><div class="w-8 h-2 bg-[#7ab829] rounded-full"></div>2号线</div>
      <div class="flex items-center gap-2"><div class="w-8 h-2 bg-[#c42126] rounded-full"></div>教师专线</div>
      <div class="flex items-center gap-2"><div class="w-4 h-4 rounded-full border-[3px] border-[#102c4c] bg-white"></div>普通站点</div>
      <div class="flex items-center gap-1">
        <div class="w-3 h-6 rounded-full border-2 border-gray-500 bg-white flex flex-col justify-center gap-[2px] items-center">
          <div class="w-1 h-1 bg-gray-400 rounded-full"></div><div class="w-1 h-1 bg-gray-400 rounded-full"></div>
        </div>
        换乘站
      </div>
    </div>
    
  </div>

</template>

<script setup>
// 声明我们要向外发射一个叫 stationClick 的事件
const emit = defineEmits(['stationClick', 'updateBusCount']);

defineProps({
  isAdmin: {
    type: Boolean,
    default: false
  }
});
import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';

// ---------------------------------
// 1. 严格映射原图的路径拓扑 (修复了你指出的所有走向问题)
// ---------------------------------
const routes = ref([
  { 
    id: 'line2', name: '2号线', color: '#7ab829', 
    path: 'M 100 100 L 980 100 Q 1000 100 1000 120 L 1000 265 Q 1000 285 980 285 L 370 285 Q 350 285 350 265 L 350 100' 
  },
  { 
    id: 'faculty', name: '教师专线', color: '#c42126', 
    // 修复 3: 红线在 X=720 (公共实验楼) 精准停住，绝不往右多出半点
    path: 'M 350 620 L 350 320 Q 350 300 370 300 L 720 300' 
  },
  { 
    id: 'line1', name: '1号线', color: '#102c4c', 
    // 修复 2 & 4: 
    // 线路A (底部主轴): 双创(100) -> 1号食堂(840) -> 向上拐弯切入平行的北体(Y=315)
    // 线路B (十字分支): 会堂(260) -> 向上直行 -> 向右拐弯(先左再下逻辑) -> 一路贯穿北体、游泳馆 -> 下落至自强路
    // 完美还原从左侧下沉，绕过立德路站，再从右侧上浮的真实轨迹
      path: 'M 100 500 L 338 500 Q 342 500 342 508 L 342 620 A 8 8 0 0 0 358 620 L 358 508 Q 358 500 362 500 L 840 500 L 840 315 M 260 620 L 260 335 Q 260 315 280 315 L 980 315 Q 1000 315 1000 335 L 1000 500' 
  }
]);

const getLineColor = (lineName) => {
  return routes.value.find(r => r.name === lineName)?.color || '#999';
};

// ---------------------------------
// 2. 站点 1:1 像素级定位与排版
// ---------------------------------
const stations = ref([
  // 顶部 (Green) Y=100
  // 修复 1: 名字正式更为“北邮”
  { id: 1, nameCN: '北邮专享楼', nameEN: 'BUPT Exclusive Building', x: 100, y: 100, color: '#7ab829', lines: ['2号线'], textPos: 'bottom' },
  { id: 2, nameCN: '电科专享楼', nameEN: 'UESTC Exclusive Building', x: 200, y: 100, color: '#7ab829', lines: ['2号线'], textPos: 'top' },
  { id: 3, nameCN: '体育场', nameEN: 'Stadium', x: 350, y: 100, color: '#7ab829', lines: ['2号线'], textPos: 'top' },
  { id: 4, nameCN: '图书馆', nameEN: 'Library', x: 540, y: 100, color: '#7ab829', lines: ['2号线'], textPos: 'top' },
  { id: 5, nameCN: '民大专享楼', nameEN: 'MUC Exclusive Building', x: 720, y: 100, color: '#7ab829', lines: ['2号线'], textPos: 'top' },
  { id: 6, nameCN: '黎安书院', nameEN: "Li'an Academy", x: 1000, y: 100, color: '#7ab829', lines: ['2号线'], textPos: 'top' },
  
  // 中部平行枢纽 (Y=300)
  { id: 7, nameCN: '中传专享楼', nameEN: 'CUC Exclusive Building', x: 350, y: 300, isTransfer: true, lines: ['1号线', '2号线', '教师专线'], textPos: 'left' },
  { id: 8, nameCN: '公共教学楼', nameEN: 'Public Teaching Building', x: 540, y: 300, isTransfer: true, lines: ['1号线', '2号线', '教师专线'], textPos: 'top' },
  { id: 9, nameCN: '公共实验楼', nameEN: 'Public Laboratory Building', x: 720, y: 300, isTransfer: true, lines: ['1号线', '2号线', '教师专线'], textPos: 'top' },
  { id: 10, nameCN: '北体专享楼', nameEN: 'BSU Exclusive Building', x: 840, y: 300, isTransfer: true, lines: ['1号线', '2号线'], textPos: 'top' },
  // 修复 4: 游泳馆严丝合缝地插在北体和大学生活动中心之间 (X=920)
  { id: 11, nameCN: '综合体育中心游泳馆', nameEN: 'Natatorium of Complex Sports Gymnasium', x: 920, y: 300, isTransfer: true, lines: ['1号线', '2号线'], textPos: 'bottom' },
  { id: 12, nameCN: '大学生活动中心', nameEN: 'Student Activity Center', x: 1000, y: 300, isTransfer: true, lines: ['1号线', '2号线'], textPos: 'top' },
  
  // 底部 (Blue) Y=500
  { id: 13, nameCN: '双创中心', nameEN: 'Innovation Center', x: 100, y: 500, color: '#102c4c', lines: ['1号线'], textPos: 'bottom' },
  // 修复 2: 会堂文字移至左侧，防止压线
  { id: 14, nameCN: '会堂', nameEN: 'Auditorium', x: 260, y: 500, color: '#102c4c', lines: ['1号线'], textPos: 'left' },
  // 修复 3: 生活一区/二区 2号门分列红线(X=350)两侧，且只归属于1号线
  { id: 15, nameCN: '生活一区2号门', nameEN: 'No.2 Gate Area I', x: 305, y: 500, color: '#102c4c', lines: ['1号线'], textPos: 'bottom' },
  { id: 16, nameCN: '生活二区2号门', nameEN: 'No.2 Gate Area II', x: 420, y: 500, color: '#102c4c', lines: ['1号线'], textPos: 'bottom' },
  // 修复 4: 1号食堂放置在拐弯点，其后路线直插上方北体
  { id: 17, nameCN: '1号食堂', nameEN: 'Student Canteen I', x: 840, y: 500, color: '#102c4c', lines: ['1号线'], textPos: 'bottom' },
  { id: 18, nameCN: '自强路站', nameEN: 'Ziqiang Road Stop', x: 1000, y: 500, color: '#102c4c', lines: ['1号线'], textPos: 'right' },
  
  // 底部垂直分支 (Y=620)
  { id: 19, nameCN: '生活一区食堂', nameEN: 'Canteen Area I', x: 260, y: 620, color: '#102c4c', lines: ['1号线'], textPos: 'bottom' },
  { id: 20, nameCN: '立德路站', nameEN: 'Lide Road Stop', x: 350, y: 620, color: '#c42126', lines: ['1号线', '教师专线'], textPos: 'bottom', isTransfer: true, isHorizontal: true },
]);

// 智能文字坐标排版系统
const getTextX = (s) => {
  if (s.textPos === 'left') return s.x - 22;
  if (s.textPos === 'right') return s.x + 22;
  return s.x;
};
const getTextY = (s) => {
  if (s.textPos === 'left' || s.textPos === 'right') return s.y - 4; 
  if (s.textPos === 'top') return s.isTransfer ? s.y - 42 : s.y - 20;
  if (s.textPos === 'bottom') return s.isTransfer ? s.y + 35 : s.y + 24;
  return s.y;
};
const getTextAnchor = (s) => {
  if (s.textPos === 'left') return 'end';
  if (s.textPos === 'right') return 'start';
  return 'middle';
};

// ---------------------------------
// 3. 交互逻辑层
// ---------------------------------

const handleStationClick = (station) => {
  // 提取站点的中文名，通过我们在 118行 定义的 emit 发射出去
  emit('stationClick', station);
};



// ==========================================
// 1. 终极坐标系转换引擎 (来自后端兄弟的降维打击)
// ==========================================
const MIN_X = -924;
const MAX_X = 811;
const MIN_Y = -516;
const MAX_Y = 857;

// 计算总跨度
const SPAN_X = MAX_X - MIN_X; // 1735
const SPAN_Y = MAX_Y - MIN_Y; // 1373

// 前端 SVG 画布的写死尺寸
const SVG_WIDTH = 1200;
const SVG_HEIGHT = 700;

// 计算缩放比例尺
const scaleX = SVG_WIDTH / SPAN_X;
const scaleY = SVG_HEIGHT / SPAN_Y;

// X轴转换：消除负数偏移，再乘以比例尺
const getSvgX = (realX) => {
  return (realX - MIN_X) * scaleX;
};

// Y轴转换：必须用最大值减去真实值 (Y轴翻转)，再乘以比例尺
const getSvgY = (realY) => {
  return (MAX_Y - realY) * scaleY;
};

// ==========================================
// 2. Axios 自动轮询雷达 (每 1.5 秒扫描一次)
// ==========================================
const activeBuses = ref([]); // 用来装后端发来的真车数据
let radarInterval = null;    // 雷达定时器

// 找到你原本获取小车数据的那个函数（比如 fetchBusLocations），在拿到数据后加上这一句：
const fetchBusLocations = async () => {
  try {
    const res = await axios.get('http://10.180.21.71:8000/api/buses/locations');
    activeBuses.value = res.data.buses;
    
    // 🚀 核心新增：把当前数组的长度（有几辆车）发射给外面的父组件！
    emit('updateBusCount', activeBuses.value.length); 
    
  } catch (error) {
    console.error("获取车辆数据失败", error);
  }
};

// 当地图一打开，立刻启动雷达
onMounted(() => {
  fetchBusLocations(); // 先扫第一眼
  radarInterval = setInterval(fetchBusLocations, 1500); // 以后每隔 1.5 秒扫一眼
});

// 当退出地图时，记得关掉雷达，省电！
onUnmounted(() => {
  if (radarInterval) clearInterval(radarInterval);
});


// ==========================================
// 💡 拓扑状态解耦：根据前后站点和进度，计算真实屏幕坐标
// ==========================================

// ==========================================
// 💡 终极拓扑渲染引擎 (带智能轨道偏移)
// ==========================================

// 1. 获取站点真实坐标
const getStationCoords = (stationName) => {
  const station = stations.value.find(s => s.nameCN === stationName);
  if (!station) {
    console.warn(`🚨 警告：后端传了未知站点 [${stationName}]，小车可能会乱飞！`);
    return { x: 0, y: 0 };
  }
  return { x: station.x, y: station.y };
};

// 💡 终极物理引擎：智能坐标系 + 防穿模闪现
const getBusPosition = (bus) => {
  const from = getStationCoords(bus.fromStation);
  const to = (bus.status === 'arrived' || !bus.toStation) ? from : getStationCoords(bus.toStation);
  const progress = bus.progress ?? 0.5;

  // 1. 获取起点的真实发车坐标
  let startX = from.x, startY = from.y;
  const fromData = stations.value.find(s => s.nameCN === bus.fromStation);
  if (fromData?.isTransfer) {
    if (fromData.isHorizontal) {
       if (bus.line === '1号线' || bus.line === '1') startX -= 12;
       if (bus.line === '教师专线') startX += 12;
    } else {
       if (bus.line === '1号线' || bus.line === '1') startY += 12;
       if (bus.line === '2号线' || bus.line === '2') startY -= 12;
    }
  }

  if (bus.status === 'arrived' || !bus.toStation) return { x: startX, y: startY };

  // 2. 获取终点的真实到达坐标
  let endX = to.x, endY = to.y;
  const toData = stations.value.find(s => s.nameCN === bus.toStation);
  if (toData?.isTransfer) {
    if (toData.isHorizontal) {
       if (bus.line === '1号线' || bus.line === '1') endX -= 12;
       if (bus.line === '教师专线') endX += 12;
    } else {
       if (bus.line === '1号线' || bus.line === '1') endY += 12;
       if (bus.line === '2号线' || bus.line === '2') endY -= 12;
    }
  }

  // 3. 直线检测：如果在同一条横线或竖线上，完美平滑移动
  const dx = Math.abs(endX - startX);
  const dy = Math.abs(endY - startY);
  if (dx < 15 || dy < 15) {
      return { x: startX + (endX - startX) * progress, y: startY + (endY - startY) * progress };
  }

  // 4. 合法 L 型弯道过弯处理 (去除后端可能带来的空格)
  const fName = (bus.fromStation || '').trim();
  const tName = (bus.toStation || '').trim();
  const pair = [fName, tName].sort().join('-');
  
  let cornerX = null, cornerY = null;
  if (pair === '中传专享楼-会堂') {
     cornerX = 260; 
     cornerY = fName === '中传专享楼' ? startY : endY; 
  } else if (pair === '立德路站-生活一区2号门') {
     cornerX = 342; cornerY = 500;
  } else if (pair === '立德路站-生活二区2号门') {
     cornerX = 358; cornerY = 500;
  } else if (pair === '中传专享楼-生活一区食堂') {
     cornerX = 260;
     cornerY = fName === '中传专享楼' ? startY : endY;
  }

  if (cornerX !== null && cornerY !== null) {
     const dist1 = Math.abs(cornerX - startX) + Math.abs(cornerY - startY);
     const dist2 = Math.abs(endX - cornerX) + Math.abs(endY - cornerY);
     const p1 = dist1 / (dist1 + dist2 || 1); 
     if (progress <= p1) {
        const subP = progress / p1;
        return { x: startX + (cornerX - startX) * subP, y: startY + (cornerY - startY) * subP };
     } else {
        const subP = (progress - p1) / (1 - p1);
        return { x: cornerX + (endX - cornerX) * subP, y: cornerY + (endY - cornerY) * subP };
     }
  }

  // 5. 🚨 终极防穿模机制 (就是你提的思路！)
  // 如果后端发来了地图上不存在连线的两个站（未知对角线），直接拒绝越野！
  // 进度 < 0.6 时乖乖待在起点，> 0.6 时直接“闪现”到终点！
  if (progress < 0.6) {
      return { x: startX, y: startY };
  } else {
      return { x: endX, y: endY };
  }
};

// 完美桥接给 HTML
const getBusX = (bus) => getBusPosition(bus).x;
const getBusY = (bus) => getBusPosition(bus).y;
  

</script>

<style scoped>
.map-container {
  width: 100%;
  max-width: 1350px;
  margin: 0 auto;
  background-color: #f4f6f9;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid #e9ecef;
}

.electronic-map {
  width: 100%;
  height: auto;
  display: block;
}

.route-line {
  opacity: 0.95;
}

.station-group {
  cursor: pointer;
}

.station-dot, .transfer-capsule rect {
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.station-text {
  user-select: none;
  pointer-events: none; 
}

.text-cn {
  font-size: 14px;
  font-weight: 900;
  fill: #111;
}
.text-en {
  font-size: 10px;
  font-weight: 500;
  fill: #6c757d;
}

.station-group:hover .station-dot {
  r: 13;
  stroke-width: 6;
  filter: drop-shadow(0 0 6px rgba(0,0,0,0.15));
}
.station-group:hover .transfer-capsule rect {
  stroke-width: 6;
  stroke: #343a40;
  filter: drop-shadow(0 0 6px rgba(0,0,0,0.15));
}
.station-group:hover .text-cn {
  fill: #000;
  font-size: 15px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}
</style>