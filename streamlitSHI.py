import math
import random
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
import streamlit as st


# --- CONFIGURATION & CONSTANTS ---
MAP_W, MAP_H = 1000.0, 650.0
RC = {"Safety": "#ff5e6c", "Balanced": "#43a5ff", "Fuel Efficient": "#55d47b"}

st.set_page_config(
    page_title="POLAR-AWARE • Continuous Navigation Simulator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MATH & GEOMETRY HELPERS ---
def clamp(v, a, b): return max(a, min(b, v))
def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
def lerp(a, b, t): return a + (b - a) * t
def angle(a, b): return math.atan2(b[1] - a[1], b[0] - a[0])

def along(a, b, d):
    z = dist(a, b)
    if z < 1e-9: return a
    t = clamp(d / z, 0, 1)
    return lerp(a[0], b[0], t), lerp(a[1], b[1], t)

def pathdist(p): return sum(dist(a, b) for a, b in zip(p, p[1:]))

def sample(p, spacing=8):
    out = [p[0]]
    for a, b in zip(p, p[1:]):
        d = dist(a, b)
        n = max(1, int(math.ceil(d / spacing)))
        for i in range(1, n + 1):
            t = i / n
            out.append((lerp(a[0], b[0], t), lerp(a[1], b[1], t)))
    return out

def nearest(q, p):
    ds = [dist(q, x) for x in p]
    i = min(range(len(ds)), key=ds.__getitem__)
    return ds[i], p[i], i

# --- DATA MODELS ---
@dataclass
class Ship:
    sid: str; name: str; start: tuple; dest: tuple; x: float; y: float
    speed: float; fuel_rate: float; safety: float
    progress: float = 0; travelled: float = 0; fuel: float = 0; active: bool = True
    history: list = field(default_factory=list)

    @property
    def total(self): return dist(self.start, self.dest)
    @property
    def remain(self): return max(0, self.total - self.progress)
    @property
    def pct(self): return 100 * self.progress / self.total if self.total else 100

@dataclass
class Iceberg:
    iid: str; x: float; y: float; vx: float; vy: float; size: float; confidence: float
    history: list = field(default_factory=list)

    def pos(self, h): return clamp(self.x + self.vx * h, 5, MAP_W - 5), clamp(self.y + self.vy * h, 5, MAP_H - 5)
    def unc(self, h): return 2 + (1 - self.confidence) * 5 + 0.35 * h
    def conf(self, h): return clamp(self.confidence * math.exp(-0.018 * h), 0.35, 0.99)

@dataclass
class Route:
    name: str; points: list; distance: float; fuel: float; eta: float; risk: float; confidence: float

# --- ROUTING ALGORITHM ---
def make_route(ship, name, icebergs):
    a, b = ship.start, ship.dest
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    ang = angle(a, b)
    nx, ny = -math.sin(ang), math.cos(ang)
    offset = {"Safety": 125, "Balanced": 72, "Fuel Efficient": 38}[name]
    scorep = scoren = 0
    for ice in icebergs:
        cross = (ice.x - mid[0]) * ny - (ice.y - mid[1]) * nx
        if abs(cross) < 180:
            if cross >= 0: scorep += 180 - abs(cross)
            else: scoren += 180 - abs(cross)
    side = -1 if scorep > scoren else 1
    if name == "Fuel Efficient":
        pts = sample([a, b])
    else:
        wp = (clamp(mid[0] + nx * offset * side, 30, MAP_W - 30),
              clamp(mid[1] + ny * offset * side, 30, MAP_H - 30))
        pts = sample([a, wp, b])
    
    d = pathdist(pts)
    fuel = d * ship.fuel_rate * ({"Safety": 1.10, "Balanced": 1.04, "Fuel Efficient": 1}[name])
    eta = d / max(ship.speed, 1)
    risk = 0
    warning = None
    for ice in icebergs:
        for h in range(0, 49, 2):
            ip = ice.pos(h)
            sep, rp, _ = nearest(ip, pts)
            danger = ship.safety + ice.size + ice.unc(h)
            if warning is None or sep < warning["sep"]:
                warning = {"ice": ice, "h": h, "ip": ip, "rp": rp, "sep": sep, "unc": ice.unc(h), "conf": ice.conf(h)}
            if sep < danger:
                risk = max(risk, clamp((danger - sep) / max(danger, 1), 0, 1) * ice.conf(h))
    return Route(name, pts, d, fuel, eta, risk, clamp(1 - 0.75 * risk, 0.25, 0.99)), warning

# --- WEATHER SERVICE ---
@st.cache_data(ttl=300)
def fetch_weather(dt_utc: datetime, x: float, y: float):
    lat = 35.0 + (y / MAP_H) * 30.0
    lon = -60.0 + (x / MAP_W) * 70.0
    now = datetime.now(timezone.utc)
    try:
        if dt_utc >= now - timedelta(hours=1):
            marine_url = "https://marine-api.open-meteo.com/v1/marine?" + urllib.parse.urlencode({
                "latitude": lat, "longitude": lon,
                "current": "wave_height,wave_direction,wave_period",
                "hourly": "wave_height,wave_direction,wave_period",
                "forecast_days": 7, "timezone": "UTC"
            })
            wind_url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
                "latitude": lat, "longitude": lon,
                "current": "wind_speed_10m,wind_direction_10m",
                "hourly": "wind_speed_10m,wind_direction_10m",
                "forecast_days": 7, "timezone": "UTC"
            })
        else:
            day = dt_utc.date().isoformat()
            marine_url = "https://marine-api.open-meteo.com/v1/marine?" + urllib.parse.urlencode({
                "latitude": lat, "longitude": lon,
                "hourly": "wave_height,wave_direction,wave_period",
                "start_date": day, "end_date": day, "timezone": "UTC"
            })
            wind_url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode({
                "latitude": lat, "longitude": lon,
                "hourly": "wind_speed_10m,wind_direction_10m",
                "start_date": day, "end_date": day, "timezone": "UTC"
            })

        req_m = urllib.request.Request(marine_url, headers={"User-Agent": "PolarAware/2.0"})
        with urllib.request.urlopen(req_m, timeout=5) as r: marine = json.loads(r.read().decode("utf-8"))
        req_w = urllib.request.Request(wind_url, headers={"User-Agent": "PolarAware/2.0"})
        with urllib.request.urlopen(req_w, timeout=5) as r: wind = json.loads(r.read().decode("utf-8"))

        target = dt_utc.replace(minute=0, second=0, microsecond=0)
        times = marine.get("hourly", {}).get("time", [])
        if times:
            idx = min(range(len(times)), key=lambda i: abs(datetime.fromisoformat(times[i].replace("Z", "+00:00")).replace(tzinfo=None) - target.replace(tzinfo=None)))
            wh = marine["hourly"]
            wave_h, wave_d, wave_p = wh.get("wave_height", [None])[idx], wh.get("wave_direction", [None])[idx], wh.get("wave_period", [None])[idx]
        else:
            cur = marine.get("current", {})
            wave_h, wave_d, wave_p = cur.get("wave_height"), cur.get("wave_direction"), cur.get("wave_period")

        wt = wind.get("hourly", {}).get("time", [])
        if wt:
            idxw = min(range(len(wt)), key=lambda i: abs(datetime.fromisoformat(wt[i].replace("Z", "+00:00")).replace(tzinfo=None) - target.replace(tzinfo=None)))
            wh = wind["hourly"]
            wind_sp, wind_di = wh.get("wind_speed_10m", [None])[idxw], wh.get("wind_direction_10m", [None])[idxw]
        else:
            curw = wind.get("current", {})
            wind_sp, wind_di = curw.get("wind_speed_10m"), curw.get("wind_direction_10m")

        return {
            "source": "OPEN-METEO • LIVE MARINE / ARCHIVE",
            "lat": lat, "lon": lon, "wave_height": wave_h, "wave_direction": wave_d,
            "wave_period": wave_p, "wind_speed": wind_sp, "wind_direction": wind_di, "timestamp": dt_utc
        }
    except Exception as exc:
        phase = (dt_utc.timestamp() / 3600.0) * 0.07 + x * 0.004 - y * 0.002
        return {
            "source": "OFFLINE SYNTHETIC WEATHER MODEL",
            "lat": lat, "lon": lon,
            "wave_height": round(1.2 + 1.5 * abs(math.sin(phase)), 1),
            "wave_direction": round((210 + 70 * math.sin(phase * 0.7)) % 360, 0),
            "wave_period": round(7 + 3 * abs(math.cos(phase)), 1),
            "wind_speed": round(10 + 22 * abs(math.sin(phase * 0.8)), 1),
            "wind_direction": round((250 + 85 * math.cos(phase)) % 360, 0),
            "timestamp": dt_utc, "error": str(exc)
        }

# --- INITIALIZATION ---
def init_state():
    if "ships" not in st.session_state:
        st.session_state.ships = [
            Ship("S001", "NCPOR RESEARCHER", (60, 100), (900, 550), 60, 100, 18, 2.1, 18),
            Ship("S002", "POLAR SURVEYOR", (80, 520), (920, 100), 80, 520, 15, 1.7, 22),
            Ship("S003", "OCEAN EXPLORER", (120, 300), (850, 320), 120, 300, 20, 2.5, 16)
        ]
    if "ice" not in st.session_state:
        d = [("ICE-001", 330, 260, 2.2, .6, 22, .94), ("ICE-002", 510, 370, -1.5, 1.1, 17, .91),
             ("ICE-003", 690, 430, -1, -1.3, 28, .88), ("ICE-004", 760, 210, -1.4, .7, 14, .95),
             ("ICE-005", 430, 510, .8, -1.5, 20, .86), ("ICE-006", 590, 160, -.5, 1.8, 12, .90),
             ("ICE-007", 850, 390, -1.8, -.4, 25, .84)]
        r = random.Random(44)
        d += [(f"ICE-{i:03d}", r.randint(180, 880), r.randint(100, 550), r.uniform(-1.5, 1.5),
               r.uniform(-1.5, 1.5), r.uniform(8, 18), r.uniform(.75, .95)) for i in range(8, 13)]
        st.session_state.ice = [Iceberg(*x) for x in d]
    if "sim_time" not in st.session_state:
        st.session_state.sim_time = 0.0
    if "selected_dt" not in st.session_state:
        st.session_state.selected_dt = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

init_state()

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.title("POLAR-AWARE Control")

# Ship selection
ship_dict = {f"{s.sid} • {s.name}": s.sid for s in st.session_state.ships}
selected_ship_label = st.sidebar.selectbox("Select Vessel", list(ship_dict.keys()))
ship_id = ship_dict[selected_ship_label]
current_ship = next(s for s in st.session_state.ships if s.sid == ship_id)

# Strategy selection
route_strategy = st.sidebar.radio("Route Strategy", list(RC.keys()), index=1)

# Datetime Picker
st.sidebar.subheader("Simulation Time Settings")
d_val = st.sidebar.date_input("Simulation Date", value=st.session_state.selected_dt.date())
t_val = st.sidebar.time_input("Simulation Time (UTC)", value=st.session_state.selected_dt.time())
st.session_state.selected_dt = datetime.combine(d_val, t_val).replace(tzinfo=timezone.utc)

# Step forward simulation engine
st.sidebar.subheader("Simulation Engine")
step_hours = st.sidebar.number_input("Advance Time (Hours)", min_value=0.1, max_value=48.0, value=2.0, step=0.5)

if st.sidebar.button("Step Simulation Forward"):
    st.session_state.sim_time += step_hours
    st.session_state.selected_dt += timedelta(hours=step_hours)
    
    # Update Icebergs
    for i in st.session_state.ice:
        i.x = clamp(i.x + i.vx * step_hours, 5, MAP_W - 5)
        i.y = clamp(i.y + i.vy * step_hours, 5, MAP_H - 5)
        i.history.append((st.session_state.sim_time, i.x, i.y))

    # Update Ships
    for s in st.session_state.ships:
        if not s.active: continue
        r_obj, _ = make_route(s, route_strategy if s.sid == ship_id else "Balanced", st.session_state.ice)
        rem = s.speed * step_hours
        if s.progress >= r_obj.distance:
            s.active = False
            continue
        old = s.progress
        s.progress = min(r_obj.distance, s.progress + rem)
        left = s.progress
        pos = r_obj.points[0]
        for a, b in zip(r_obj.points, r_obj.points[1:]):
            d_len = dist(a, b)
            if left <= d_len:
                pos = along(a, b, left)
                break
            left -= d_len
            pos = b
        s.x, s.y = pos
        moved = s.progress - old
        s.travelled += moved
        s.fuel += moved * s.fuel_rate
        s.history.append((st.session_state.sim_time, s.x, s.y))
        if s.progress >= r_obj.distance:
            s.active = False

if st.sidebar.button("Reset Simulation"):
    st.session_state.clear()
    st.rerun()

# --- COMPUTE ROUTES & WEATHER ---
routes, warnings = {}, {}
for name in RC:
    routes[name], warnings[name] = make_route(current_ship, name, st.session_state.ice)

active_route = routes[route_strategy]
active_warning = warnings[route_strategy]
weather_data = fetch_weather(st.session_state.selected_dt, current_ship.x, current_ship.y)

# --- MAIN DISPLAY ---
st.title("POLAR-AWARE • Marine Navigation Simulator")
st.caption(f"UTC Reference Time: {st.session_state.selected_dt.strftime('%Y-%m-%d %H:%M')} | Sim Elapsed: {st.session_state.sim_time:.1f} hrs")

col_map, col_info = st.columns([2.5, 1])

with col_map:
    fig = go.Figure()

    # Draw grid/background
    fig.update_layout(
        xaxis=dict(range=[0, MAP_W], showgrid=True, gridcolor="#102a40", zeroline=False),
        yaxis=dict(range=[0, MAP_H], showgrid=True, gridcolor="#102a40", zeroline=False),
        plot_bgcolor="#081522",
        paper_bgcolor="#07111d",
        margin=dict(l=10, r=10, t=10, b=10),
        height=620
    )

    # Render Routes
    for name, r in routes.items():
        rx, ry = zip(*r.points)
        is_active = (name == route_strategy)
        fig.add_trace(go.Scatter(
            x=rx, y=ry, mode='lines',
            line=dict(color=RC[name], width=4 if is_active else 1.5, dash=None if is_active else 'dash'),
            name=f"Route: {name}"
        ))

    # Render Icebergs and 24h prediction circles
    ice_x, ice_y, ice_text = [], [], []
    pred_x, pred_y = [], []
    for ice in st.session_state.ice:
        ice_x.append(ice.x)
        ice_y.append(ice.y)
        ice_text.append(f"{ice.iid}<br>Size: {ice.size}km")
        px, py = ice.pos(24)
        pred_x.append(px)
        pred_y.append(py)

    fig.add_trace(go.Scatter(
        x=ice_x, y=ice_y, mode='markers+text',
        marker=dict(symbol='diamond', size=12, color='#79dfff', line=dict(color='white', width=1)),
        text=[i.iid for i in st.session_state.ice], textposition="top center",
        hovertext=ice_text, name="Icebergs"
    ))

    fig.add_trace(go.Scatter(
        x=pred_x, y=pred_y, mode='markers',
        marker=dict(symbol='circle-open', size=10, color='#56d9ee'),
        name="24h Ice Forecast"
    ))

    # Render Ships & Destinations
    for s in st.session_state.ships:
        is_sel = (s.sid == ship_id)
        fig.add_trace(go.Scatter(
            x=[s.x], y=[s.y], mode='markers+text',
            marker=dict(size=14 if is_sel else 10, color='white' if is_sel else '#43a5ff',
                        line=dict(color='#43a5ff', width=3 if is_sel else 1)),
            text=[s.sid], textposition="bottom center", name=f"Ship {s.sid}"
        ))
        fig.add_trace(go.Scatter(
            x=[s.dest[0]], y=[s.dest[1]], mode='markers',
            marker=dict(symbol='square', size=10, color='#bd9cff'),
            name=f"Dest {s.sid}"
        ))

    # Closest Approach Warning Point
    if active_warning:
        fig.add_trace(go.Scatter(
            x=[active_warning['rp'][0]], y=[active_warning['rp'][1]], mode='markers',
            marker=dict(symbol='x', size=12, color='#ff5e6c'),
            name="Closest Approach"
        ))

    st.plotly_chart(fig, use_container_width=True)

with col_info:
    st.subheader("Vessel Inspector")
    st.markdown(f"""
    **Ship**: {current_ship.name} (`{current_ship.sid}`)  
    **Position**: ({current_ship.x:.1f}, {current_ship.y:.1f})  
    **Progress**: {current_ship.pct:.1f}% ({current_ship.travelled:.1f} / {current_ship.total:.1f} km)  
    **Fuel Expended**: {current_ship.fuel:.1f} L
    """)

    st.divider()
    st.subheader("Active Route Metrics")
    st.markdown(f"""
    **Strategy**: `{active_route.name}`  
    **Distance**: {active_route.distance:.1f} km  
    **Fuel Estimate**: {active_route.fuel:.1f} L  
    **ETA**: {active_route.eta:.1f} hrs  
    **Risk Factor**: {active_route.risk*100:.1f}%  
    **Confidence**: {active_route.confidence*100:.1f}%
    """)

    st.divider()
    st.subheader("Marine Weather")
    st.markdown(f"""
    **Source**: {weather_data.get('source', 'N/A')}  
    **Wind Speed**: {weather_data.get('wind_speed', '—')} km/h  
    **Wind Direction**: {weather_data.get('wind_direction', '—')}°  
    **Wave Height**: {weather_data.get('wave_height', '—')} m  
    **Wave Period**: {weather_data.get('wave_period', '—')} s
    """)
