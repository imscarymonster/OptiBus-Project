"""FastAPI 应用入口模块。"""

import json
import math
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import models, schemas
from .database import engine, redis_client, Base
from .websocket import manager

# ============================================================================
# ETA 算法全局常量
# ============================================================================

BUS_SPEED = 8.0                # 大巴速度 (m/s)
STATION_THRESHOLD = 20.0       # 到站判定距离 (m)

# ---------------------------------------------------------------------------
# 1. 核心坐标库 (单位: 米)
# ---------------------------------------------------------------------------
STATIONS_XY: dict[str, tuple[float, float]] = {
    "中传专享楼": (0, 0), "公共教学楼": (186, 140), "公共实验楼": (338, 296),
    "北体专享楼": (418, 444), "综合体育中心游泳馆": (591, 636), "大学生活动中心": (624, 693),
    "会堂": (-54, -300), "双创中心": (-228, -516), "生活一区食堂": (107, -509),
    "生活一区2号门": (77, -260), "生活二区2号门": (287, -78), "1号食堂": (599, 304),
    "自强路站": (811, 616), "北邮专享楼": (-924, -455), "电科专享楼": (-588, -257),
    "体育场": (-195, 67), "图书馆": (-11, 253), "民大专享楼": (236, 531),
    "黎安书院": (294, 620), "立德路站": (312, -334),
    "拐点1": (-147, -189), "拐点2": (-22, -353), "拐点3": (176, -178),
    "拐点5": (639, 731), "拐点6": (449, 857), "拐点7": (-116, 129),
}

# ---------------------------------------------------------------------------
# 2. 线路行进展开数组 (含死胡同折返，索引顺序即真实行驶轨迹)
# ---------------------------------------------------------------------------
ROUTES_SEQUENCE: dict[str, list[str]] = {
    # ---- 二号线 顺时针 ----
    "line2_cw": [
        "中传专享楼", "拐点7", "体育场", "电科专享楼", "北邮专享楼",
        "电科专享楼", "体育场", "拐点7", "图书馆", "民大专享楼",
        "黎安书院", "拐点6", "拐点5", "大学生活动中心", "综合体育中心游泳馆",
        "北体专享楼", "公共实验楼", "公共教学楼", "中传专享楼",
    ],
    # ---- 二号线 逆时针 (倒序) ----
    "line2_ccw": [],  # 下方自动生成

    # ---- 一号线 顺时针 (南区 + 西南折返) ----
    "line1_cw": [
        "中传专享楼", "拐点3", "生活二区2号门", "生活一区2号门",
        "拐点1", "会堂", "双创中心",
        "会堂", "拐点1", "拐点2", "生活一区食堂",
        "拐点2", "拐点1", "拐点3", "中传专享楼",
    ],
    # ---- 一号线 逆时针 ----
    "line1_ccw": [],  # 下方自动生成

    # ---- 教师专线 顺时针 ----
    "teacher_cw": [
        "中传专享楼", "公共教学楼", "公共实验楼", "公共教学楼",
        "中传专享楼", "拐点3", "立德路站", "拐点3", "中传专享楼",
    ],
    # ---- 教师专线 逆时针 ----
    "teacher_ccw": [],  # 下方自动生成
}

# 自动生成逆时针路线（倒序）
ROUTES_SEQUENCE["line2_ccw"] = list(reversed(ROUTES_SEQUENCE["line2_cw"]))
ROUTES_SEQUENCE["line1_ccw"] = list(reversed(ROUTES_SEQUENCE["line1_cw"]))
ROUTES_SEQUENCE["teacher_ccw"] = list(reversed(ROUTES_SEQUENCE["teacher_cw"]))

# ---------------------------------------------------------------------------
# 3. 公交编队：10 辆车，3 条线 × 2 方向，首波齐发 1 辆/方向，
#    3 分钟后发第二波 (教师专线仅 1 波)
# ---------------------------------------------------------------------------
BUS_FLEET: list[dict] = [
    # 首波 (t=0)
    {"busId": "101", "route_key": "line1_cw",   "departure_offset_s": 0},
    {"busId": "102", "route_key": "line1_ccw",  "departure_offset_s": 0},
    {"busId": "103", "route_key": "line2_cw",   "departure_offset_s": 0},
    {"busId": "104", "route_key": "line2_ccw",  "departure_offset_s": 0},
    {"busId": "105", "route_key": "teacher_cw", "departure_offset_s": 0},
    {"busId": "106", "route_key": "teacher_ccw","departure_offset_s": 0},
    # 第二波 (t=180s)
    {"busId": "107", "route_key": "line1_cw",   "departure_offset_s": 180},
    {"busId": "108", "route_key": "line1_ccw",  "departure_offset_s": 180},
    {"busId": "109", "route_key": "line2_cw",   "departure_offset_s": 180},
    {"busId": "110", "route_key": "line2_ccw",  "departure_offset_s": 180},
]

# 仿真起始时间戳（lifespan 中赋值）
_sim_t0: float | None = None


# ============================================================================
# ETA 核心算法
# ============================================================================

def get_distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """两点欧氏距离。"""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def point_to_segment_projection(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float,
) -> tuple[float, float, float, float]:
    """点 P 到线段 AB 的投影。

    Returns:
        (proj_x, proj_y, dist_to_segment, dist_proj_to_B)
    """
    abx, aby = x2 - x1, y2 - y1
    ab_len_sq = abx * abx + aby * aby
    if ab_len_sq == 0:
        dist = math.hypot(px - x1, py - y1)
        return (x1, y1, dist, 0.0)

    t = max(0.0, min(1.0, ((px - x1) * abx + (py - y1) * aby) / ab_len_sq))
    proj_x = x1 + t * abx
    proj_y = y1 + t * aby
    dist_to_seg = math.hypot(px - proj_x, py - proj_y)
    dist_to_b = math.hypot(x2 - proj_x, y2 - proj_y)
    return (proj_x, proj_y, dist_to_seg, dist_to_b)


def snap_vehicle(
    x: float, y: float, route_key: str,
) -> tuple[int, float, float]:
    """将车辆吸附到路线上最近的路段。

    Returns:
        (segment_start_index, distance_to_segment, dist_proj_to_seg_end)
    """
    route = ROUTES_SEQUENCE[route_key]
    best_idx, best_dist, best_to_end = 0, float("inf"), 0.0

    for i in range(len(route) - 1):
        x1, y1 = STATIONS_XY[route[i]]
        x2, y2 = STATIONS_XY[route[i + 1]]
        _, _, d_seg, d_to_end = point_to_segment_projection(x, y, x1, y1, x2, y2)
        if d_seg < best_dist:
            best_dist = d_seg
            best_idx = i
            best_to_end = d_to_end

    return best_idx, best_dist, best_to_end


def calculate_eta(
    x: float, y: float, route_key: str, target_station: str,
) -> int | None:
    """计算车辆到目标站点的 ETA（分钟，向上取整）。

    车辆已到站 (<20m) 返回 0；站点不在路线中返回 None。
    """
    route = ROUTES_SEQUENCE[route_key]
    if target_station not in route:
        return None

    # 已到站
    tx, ty = STATIONS_XY[target_station]
    if get_distance((x, y), (tx, ty)) < STATION_THRESHOLD:
        return 0

    seg_idx, _, dist_to_end = snap_vehicle(x, y, route_key)

    # 找到 seg_idx 之后所有目标站点的出现位置，取最近
    best_eta = float("inf")
    n = len(route)

    for offset in range(n):
        idx = (seg_idx + 1 + offset) % n
        if route[idx] == target_station:
            # 累加距离：当前段剩余 + 中间完整段
            total = dist_to_end
            cursor = seg_idx + 1
            while cursor % n != idx:
                a = STATIONS_XY[route[cursor % n]]
                b = STATIONS_XY[route[(cursor + 1) % n]]
                total += get_distance(a, b)
                cursor += 1
            eta_min = math.ceil(total / BUS_SPEED / 60)
            if eta_min < best_eta:
                best_eta = eta_min

    return int(best_eta) if best_eta != float("inf") else None


# ============================================================================
# 发车模拟器
# ============================================================================

def get_simulated_position(
    bus: dict, elapsed_s: float,
) -> tuple[float, float] | None:
    """根据发车时刻与已流逝时间，推算车辆当前 (x, y) 坐标。"""
    route = ROUTES_SEQUENCE[bus["route_key"]]
    if len(route) < 2:
        return None

    travel_time = max(0.0, elapsed_s - bus["departure_offset_s"])
    distance_traveled = travel_time * BUS_SPEED

    # 计算路线总长
    total_route_len = 0.0
    seg_lengths = []
    for i in range(len(route) - 1):
        d = get_distance(STATIONS_XY[route[i]], STATIONS_XY[route[i + 1]])
        seg_lengths.append(d)
        total_route_len += d

    if total_route_len == 0:
        return STATIONS_XY[route[0]]

    # 循环行驶（取模）
    distance_traveled %= total_route_len

    cumulative = 0.0
    for i, seg_len in enumerate(seg_lengths):
        if cumulative + seg_len >= distance_traveled:
            fraction = (distance_traveled - cumulative) / seg_len
            x1, y1 = STATIONS_XY[route[i]]
            x2, y2 = STATIONS_XY[route[i + 1]]
            return (x1 + fraction * (x2 - x1), y1 + fraction * (y2 - y1))
        cumulative += seg_len

    return STATIONS_XY[route[-1]]


def build_station_route_map() -> dict[str, list[str]]:
    """构建 站点名 → 途经路线键列表 的索引。"""
    mapping: dict[str, list[str]] = {}
    for rk, seq in ROUTES_SEQUENCE.items():
        for name in seq:
            if name not in mapping:
                mapping[name] = []
            if rk not in mapping[name]:
                mapping[name].append(rk)
    return mapping


# ============================================================================
# FastAPI 应用
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化数据库、检查 Redis，并记录仿真起始时间。"""
    global _sim_t0
    try:
        Base.metadata.create_all(bind=engine)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("✅ PostgreSQL 连接成功")
    except Exception:
        print("⚠️ PostgreSQL 连接失败，请检查服务是否启动")

    try:
        redis_client.ping()
        print("✅ Redis 连接成功")
    except Exception:
        print("⚠️ Redis 连接失败，请检查服务是否启动")

    _sim_t0 = time.time()
    print(f"🚌 发车模拟器已启动（{len(BUS_FLEET)} 辆虚拟公交）")

    yield


app = FastAPI(title="Optibus Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 基础接口 ====================

@app.get("/")
async def welcome():
    return {"message": "Welcome to OptiBus backend", "status": "ok"}


@app.get("/health")
async def health():
    postgres_online = False
    redis_online = False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        postgres_online = True
    except Exception:
        postgres_online = False
    try:
        redis_online = bool(redis_client.ping())
    except Exception:
        redis_online = False
    return {
        "postgres": "online" if postgres_online else "offline",
        "redis": "online" if redis_online else "offline",
    }


@app.get("/ping")
async def ping():
    return {"message": "pong"}


# ==================== 管理员端 HTTP 接口 ====================

@app.post("/api/admin/login")
async def admin_login():
    return {"token": "admin_mock_token_888"}


# ==================== 司机端 HTTP 接口 ====================

@app.post("/api/driver/check_in")
async def driver_check_in(data: schemas.DriverDailyCheckIn):
    driver_id = str(data.driver_id)
    initial_status = json.dumps({
        "route_id": data.route_id,
        "lat": 0.0,
        "lng": 0.0,
        "status": "idle",
    })
    redis_client.hset("bus:status:all", driver_id, initial_status)
    redis_client.sadd(f"route:buses:{data.route_id}", driver_id)
    return {
        "status": "ok",
        "driver_id": data.driver_id,
        "route_id": data.route_id,
    }


# ==================== 车辆位置查询接口 ====================

@app.get("/api/buses/locations")
async def get_bus_locations():
    """全网车辆实时位置 —— 真车 (Redis) + 仿真车 (计算)。"""
    result = []

    # 1) 真实车辆（来自司机打卡 + WebSocket 坐标上报）
    all_buses = redis_client.hgetall("bus:status:all")
    for driver_id, raw_json in all_buses.items():
        try:
            data = json.loads(raw_json)
        except (json.JSONDecodeError, TypeError):
            continue
        route_id = data.get("route_id", 0)
        raw_status = data.get("status", "idle")
        status_map = {"idle": "idle", "driving": "in-transit"}
        result.append({
            "busId": driver_id,
            "line": f"{route_id}号线",
            "x": data.get("lng", 0.0),
            "y": data.get("lat", 0.0),
            "status": status_map.get(raw_status, raw_status),
        })

    # 2) 仿真车辆（无真车时提供占位数据）
    if _sim_t0 is not None:
        elapsed = time.time() - _sim_t0
        for bus in BUS_FLEET:
            # 若已有同 busId 的真车数据则跳过
            if any(b["busId"] == bus["busId"] for b in result):
                continue
            pos = get_simulated_position(bus, elapsed)
            if pos is None:
                continue
            route_name = bus["route_key"].replace("_cw", "").replace("_ccw", "")
            display_name = {"line1": "1号线", "line2": "2号线", "teacher": "教师专线"}.get(route_name, route_name)
            result.append({
                "busId": bus["busId"],
                "line": display_name,
                "x": round(pos[1], 2),  # lng → x
                "y": round(pos[0], 2),  # lat → y
                "status": "in-transit",
            })

    return {"buses": result}


# ==================== ETA 接口 ====================

@app.get("/api/eta/{station_id}")
async def get_eta(station_id: str):
    """查询最近一班车到达指定站点的预计时间（分钟）。

    优先使用 Redis 中真实车辆位置；无真车时回退到发车模拟器。
    """
    if station_id not in STATIONS_XY:
        return {"error": f"未知站点: {station_id}"}

    station_route_map = build_station_route_map()
    candidate_routes = station_route_map.get(station_id, [])
    if not candidate_routes:
        return {"stationId": station_id, "etaMinutes": None, "busId": None,
                "message": "无线路经过此站"}

    best_eta = float("inf")
    best_bus_id = None

    # ---------- 真车 ETA ----------
    all_buses = redis_client.hgetall("bus:status:all")
    for driver_id, raw_json in all_buses.items():
        try:
            data = json.loads(raw_json)
        except (json.JSONDecodeError, TypeError):
            continue
        lat = data.get("lat", 0.0)
        lng = data.get("lng", 0.0)
        route_id = data.get("route_id", 0)

        # 找出该 route_id 对应的路线键
        matching_keys = [rk for rk in candidate_routes
                         if str(route_id) in rk or rk.startswith(f"line{route_id}")]
        # 更宽松的匹配：teacher 路线也试试
        if not matching_keys:
            matching_keys = [rk for rk in candidate_routes]

        for rk in matching_keys:
            eta = calculate_eta(lat, lng, rk, station_id)
            if eta is not None and eta < best_eta:
                best_eta = eta
                best_bus_id = driver_id

    # ---------- 仿真 ETA（若无真车结果） ----------
    if best_bus_id is None and _sim_t0 is not None:
        elapsed = time.time() - _sim_t0
        for bus in BUS_FLEET:
            if bus["route_key"] not in candidate_routes:
                continue
            pos = get_simulated_position(bus, elapsed)
            if pos is None:
                continue
            eta = calculate_eta(pos[0], pos[1], bus["route_key"], station_id)
            if eta is not None and eta < best_eta:
                best_eta = eta
                best_bus_id = bus["busId"]

    if best_bus_id is None:
        return {"stationId": station_id, "etaMinutes": None, "busId": None,
                "message": "暂无可用车辆"}

    return {
        "stationId": station_id,
        "etaMinutes": best_eta,
        "busId": best_bus_id,
    }


# ==================== WebSocket 路由 ====================

@app.websocket("/ws/driver/{driver_id}")
async def driver_websocket(websocket: WebSocket, driver_id: int):
    driver_id_str = str(driver_id)
    await manager.connect(websocket, "driver", driver_id_str)
    try:
        while True:
            raw = await websocket.receive_json()
            loc = schemas.LocationUpdate(**raw)
            current = redis_client.hget("bus:status:all", driver_id_str)
            if current:
                status_data = json.loads(current)
            else:
                status_data = {"route_id": 0}
            status_data["lat"] = loc.lat
            status_data["lng"] = loc.lng
            status_data["status"] = "driving"
            redis_client.hset("bus:status:all", driver_id_str, json.dumps(status_data))
    except WebSocketDisconnect:
        manager.disconnect("driver", driver_id_str)
    except Exception:
        manager.disconnect("driver", driver_id_str)


@app.websocket("/ws/passenger/{client_id}")
async def passenger_websocket(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, "passenger", client_id)
    try:
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        manager.disconnect("passenger", client_id)
    except Exception:
        manager.disconnect("passenger", client_id)
