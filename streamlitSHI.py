import tkinter as tk
from tkinter import ttk
import math, random, time, json, urllib.request, urllib.parse, threading
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

MAP_W, MAP_H = 1000.0, 650.0
BG="#07111d"; PANEL="#0d1a2a"; PANEL2="#12243a"; BORDER="#223b55"
TEXT="#e8f0f8"; MUTED="#8fa5ba"; BLUE="#43a5ff"; GREEN="#55d47b"
RED="#ff5e6c"; CYAN="#56d9ee"; AMBER="#ffc857"; PURPLE="#bd9cff"; WHITE="#fff"
RC={"Safety":RED,"Balanced":BLUE,"Fuel Efficient":GREEN}
SPEEDS={"0.25x":.25,"0.5x":.5,"1x":1,"2x":2,"5x":5,"10x":10,"25x":25,"50x":50,"100x":100}

def clamp(v,a,b): return max(a,min(b,v))
def dist(a,b): return math.hypot(a[0]-b[0],a[1]-b[1])
def lerp(a,b,t): return a+(b-a)*t
def angle(a,b): return math.atan2(b[1]-a[1],b[0]-a[0])
def along(a,b,d):
    z=dist(a,b)
    if z<1e-9:return a
    t=clamp(d/z,0,1)
    return lerp(a[0],b[0],t),lerp(a[1],b[1],t)

@dataclass
class Ship:
    sid:str; name:str; start:tuple; dest:tuple; x:float; y:float
    speed:float; fuel_rate:float; safety:float
    progress:float=0; travelled:float=0; fuel:float=0; active:bool=True
    history:list=field(default_factory=list)
    @property
    def total(self): return dist(self.start,self.dest)
    @property
    def remain(self): return max(0,self.total-self.progress)
    @property
    def pct(self): return 100*self.progress/self.total if self.total else 100

@dataclass
class Iceberg:
    iid:str; x:float; y:float; vx:float; vy:float; size:float; confidence:float
    history:list=field(default_factory=list)
    def pos(self,h): return clamp(self.x+self.vx*h,5,MAP_W-5),clamp(self.y+self.vy*h,5,MAP_H-5)
    def unc(self,h): return 2+(1-self.confidence)*5+.35*h
    def conf(self,h): return clamp(self.confidence*math.exp(-.018*h),.35,.99)

@dataclass
class Route:
    name:str; points:list; distance:float; fuel:float; eta:float; risk:float; confidence:float

def pathdist(p): return sum(dist(a,b) for a,b in zip(p,p[1:]))
def sample(p,spacing=8):
    out=[p[0]]
    for a,b in zip(p,p[1:]):
        d=dist(a,b); n=max(1,int(math.ceil(d/spacing)))
        for i in range(1,n+1):
            t=i/n; out.append((lerp(a[0],b[0],t),lerp(a[1],b[1],t)))
    return out
def nearest(q,p):
    ds=[dist(q,x) for x in p]; i=min(range(len(ds)),key=ds.__getitem__)
    return ds[i],p[i],i

def make_route(ship,name,icebergs):
    a,b=ship.start,ship.dest; mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
    ang=angle(a,b); nx,ny=-math.sin(ang),math.cos(ang)
    offset={"Safety":125,"Balanced":72,"Fuel Efficient":38}[name]
    scorep=scoren=0
    for ice in icebergs:
        cross=(ice.x-mid[0])*ny-(ice.y-mid[1])*nx
        if abs(cross)<180:
            (scorep if cross>=0 else scoren)
            if cross>=0: scorep+=180-abs(cross)
            else: scoren+=180-abs(cross)
    side=-1 if scorep>scoren else 1
    if name=="Fuel Efficient": pts=sample([a,b])
    else:
        wp=(clamp(mid[0]+nx*offset*side,30,MAP_W-30),
            clamp(mid[1]+ny*offset*side,30,MAP_H-30))
        pts=sample([a,wp,b])
    d=pathdist(pts); fuel=d*ship.fuel_rate*({"Safety":1.10,"Balanced":1.04,"Fuel Efficient":1}[name])
    eta=d/max(ship.speed,1); risk=0; warning=None
    for ice in icebergs:
        for h in range(0,49,2):
            ip=ice.pos(h); sep,rp,_=nearest(ip,pts); danger=ship.safety+ice.size+ice.unc(h)
            if warning is None or sep<warning["sep"]:
                warning={"ice":ice,"h":h,"ip":ip,"rp":rp,"sep":sep,"unc":ice.unc(h),"conf":ice.conf(h)}
            if sep<danger:
                risk=max(risk,clamp((danger-sep)/max(danger,1),0,1)*ice.conf(h))
    return Route(name,pts,d,fuel,eta,risk,clamp(1-.75*risk,.25,.99)),warning


class WeatherService:
    """Live marine weather for the selected Atlantic point, with an offline model fallback."""
    def __init__(self, callback):
        self.callback = callback
        self.cache = {}
        self.lock = threading.Lock()

    def atlantic_coords(self, x, y):
        # The simulator's abstract map is projected onto a useful North Atlantic box.
        lon = -60.0 + (x / MAP_W) * 70.0
        lat = 35.0 + (y / MAP_H) * 30.0
        return lat, lon

    def _fetch_json(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "PolarAware/2.0"})
        with urllib.request.urlopen(req, timeout=7) as r:
            return json.loads(r.read().decode("utf-8"))

    def request(self, dt_utc, x, y):
        key = (dt_utc.strftime("%Y-%m-%dT%H"), round(x), round(y))
        with self.lock:
            if key in self.cache:
                self.callback(self.cache[key])
                return
        threading.Thread(target=self._worker, args=(dt_utc, x, y, key), daemon=True).start()

    def _worker(self, dt_utc, x, y, key):
        lat, lon = self.atlantic_coords(x, y)
        now = datetime.now(timezone.utc)
        result = None
        try:
            # Open-Meteo marine forecast/current endpoint is used only for the
            # live/near-future window. Historical dates use the archive service.
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

            marine = self._fetch_json(marine_url)
            wind = self._fetch_json(wind_url)

            target = dt_utc.replace(minute=0, second=0, microsecond=0)
            times = marine.get("hourly", {}).get("time", [])
            if times:
                target_s = target.strftime("%Y-%m-%dT%H:00")
                idx = min(range(len(times)), key=lambda i: abs(
                    datetime.fromisoformat(times[i].replace("Z", "+00:00")).replace(tzinfo=None)
                    - target.replace(tzinfo=None)
                ))
                wh = marine["hourly"]
                wave_h = wh.get("wave_height", [None])[idx]
                wave_d = wh.get("wave_direction", [None])[idx]
                wave_p = wh.get("wave_period", [None])[idx]
            else:
                cur = marine.get("current", {})
                wave_h, wave_d, wave_p = cur.get("wave_height"), cur.get("wave_direction"), cur.get("wave_period")

            wt = wind.get("hourly", {}).get("time", [])
            if wt:
                idxw = min(range(len(wt)), key=lambda i: abs(
                    datetime.fromisoformat(wt[i].replace("Z", "+00:00")).replace(tzinfo=None)
                    - target.replace(tzinfo=None)
                ))
                wh = wind["hourly"]
                wind_sp = wh.get("wind_speed_10m", [None])[idxw]
                wind_di = wh.get("wind_direction_10m", [None])[idxw]
            else:
                curw = wind.get("current", {})
                wind_sp, wind_di = curw.get("wind_speed_10m"), curw.get("wind_direction_10m")

            result = {
                "source": "OPEN-METEO • LIVE MARINE / ARCHIVE",
                "live": dt_utc >= now - timedelta(hours=1) and dt_utc <= now + timedelta(days=7),
                "lat": lat, "lon": lon,
                "wave_height": wave_h, "wave_direction": wave_d, "wave_period": wave_p,
                "wind_speed": wind_sp, "wind_direction": wind_di,
                "timestamp": dt_utc
            }
        except Exception as exc:
            # Deterministic fallback means the simulator remains usable offline.
            phase = (dt_utc.timestamp() / 3600.0) * 0.07 + x * .004 - y * .002
            result = {
                "source": "OFFLINE SYNTHETIC WEATHER MODEL",
                "live": False, "lat": lat, "lon": lon,
                "wave_height": round(1.2 + 1.5 * abs(math.sin(phase)), 1),
                "wave_direction": round((210 + 70 * math.sin(phase * .7)) % 360, 0),
                "wave_period": round(7 + 3 * abs(math.cos(phase)), 1),
                "wind_speed": round(10 + 22 * abs(math.sin(phase * .8)), 1),
                "wind_direction": round((250 + 85 * math.cos(phase)) % 360, 0),
                "timestamp": dt_utc, "error": str(exc)
            }

        with self.lock:
            self.cache[key] = result
        self.callback(result)


class CalendarPopup(tk.Toplevel):
    def __init__(self, parent, initial, callback):
        super().__init__(parent)
        self.parent, self.callback = parent, callback
        self.title("Select simulation date")
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.year, self.month = initial.year, initial.month
        self.selected = initial
        self.build()

    def build(self):
        for w in self.winfo_children(): w.destroy()
        head = tk.Frame(self, bg=PANEL); head.pack(fill="x", padx=10, pady=10)
        tk.Button(head, text="‹", command=lambda: self.shift(-1), bg=PANEL2, fg=TEXT, bd=0, width=3).pack(side="left")
        tk.Label(head, text=f"{datetime(self.year,self.month,1):%B %Y}", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(side="left", expand=True)
        tk.Button(head, text="›", command=lambda: self.shift(1), bg=PANEL2, fg=TEXT, bd=0, width=3).pack(side="right")

        grid = tk.Frame(self, bg=PANEL); grid.pack(padx=10, pady=(0,10))
        for j, name in enumerate(["Mo","Tu","We","Th","Fr","Sa","Su"]):
            tk.Label(grid, text=name, bg=PANEL, fg=MUTED, width=4, font=("Segoe UI",8,"bold")).grid(row=0,column=j)
        import calendar
        for r, week in enumerate(calendar.monthcalendar(self.year, self.month), 1):
            for c, day in enumerate(week):
                if day:
                    b = tk.Button(grid, text=str(day), width=3, bd=0,
                                  bg=CYAN if (day == self.selected.day and self.month == self.selected.month and self.year == self.selected.year) else PANEL2,
                                  fg=BG if (day == self.selected.day and self.month == self.selected.month and self.year == self.selected.year) else TEXT,
                                  command=lambda d=day: self.pick(d))
                    b.grid(row=r, column=c, padx=2, pady=2)

    def shift(self, delta):
        import calendar
        idx = self.year * 12 + self.month - 1 + delta
        self.year, self.month = idx // 12, idx % 12 + 1
        self.build()

    def pick(self, day):
        self.selected = self.selected.replace(year=self.year, month=self.month, day=day)
        self.callback(self.selected)
        self.destroy()


class App:
    def __init__(self,root):
        self.root=root; root.title("POLAR-AWARE • Continuous Navigation Simulator")
        root.geometry("1600x950"); root.minsize(1200,760); root.configure(bg=BG)
        self.sim=0.; self.running=True; self.mult=5.; self.last=time.perf_counter()
        self.zoom=1.; self.panx=self.pany=0.; self.drag=None
        self.shipid="S001"; self.route_name="Balanced"
        self.selected_dt=datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        self.weather={}
        self.weather_service=WeatherService(self.receive_weather)
        self.ships=self.make_ships(); self.ice=self.make_ice()
        self.routes={}; self.warn={}
        self.build(); self.populate(); self.replan(); self.request_weather(); self.draw(); self.loop()

    def make_ships(self):
        return [
            Ship("S001","NCPOR RESEARCHER",(60,100),(900,550),60,100,18,2.1,18),
            Ship("S002","POLAR SURVEYOR",(80,520),(920,100),80,520,15,1.7,22),
            Ship("S003","OCEAN EXPLORER",(120,300),(850,320),120,300,20,2.5,16)]
    def make_ice(self):
        d=[("ICE-001",330,260,2.2,.6,22,.94),("ICE-002",510,370,-1.5,1.1,17,.91),
           ("ICE-003",690,430,-1,-1.3,28,.88),("ICE-004",760,210,-1.4,.7,14,.95),
           ("ICE-005",430,510,.8,-1.5,20,.86),("ICE-006",590,160,-.5,1.8,12,.90),
           ("ICE-007",850,390,-1.8,-.4,25,.84)]
        r=random.Random(44)
        d += [(f"ICE-{i:03d}",r.randint(180,880),r.randint(100,550),r.uniform(-1.5,1.5),
               r.uniform(-1.5,1.5),r.uniform(8,18),r.uniform(.75,.95)) for i in range(8,13)]
        return [Iceberg(*x) for x in d]

    def build(self):
        h=tk.Frame(self.root,bg=BG,height=74); h.pack(fill="x",padx=22,pady=(15,8)); h.pack_propagate(False)
        l=tk.Frame(h,bg=BG); l.pack(side="left")
        tk.Label(l,text="POLAR-AWARE",bg=BG,fg=WHITE,font=("Segoe UI",23,"bold")).pack(anchor="w")
        tk.Label(l,text="CONTINUOUS ICEBERG • ROUTE • FUEL SIMULATION",bg=BG,fg=MUTED,font=("Segoe UI",9)).pack(anchor="w")
        self.clock=tk.Label(h,text="T+ 00:00:00",bg=PANEL2,fg=CYAN,font=("Consolas",13,"bold"),padx=15,pady=9); self.clock.pack(side="right")
        body=tk.Frame(self.root,bg=BG); body.pack(fill="both",expand=True,padx=22,pady=(0,20))
        self.left=tk.Frame(body,bg=PANEL,width=285,highlightbackground=BORDER,highlightthickness=1); self.left.pack(side="left",fill="y",padx=(0,12)); self.left.pack_propagate(False)
        center=tk.Frame(body,bg=PANEL,highlightbackground=BORDER,highlightthickness=1); center.pack(side="left",fill="both",expand=True)
        self.right=tk.Frame(body,bg=PANEL,width=360,highlightbackground=BORDER,highlightthickness=1); self.right.pack(side="right",fill="y",padx=(12,0)); self.right.pack_propagate(False)
        self.left_ui(); self.map_ui(center); self.right_ui()

    def sep(self): tk.Frame(self.left,bg=BORDER,height=1).pack(fill="x",padx=18,pady=13)
    def left_ui(self):
        outer=self.left
        canvas=tk.Canvas(outer,bg=PANEL,highlightthickness=0)
        sb=ttk.Scrollbar(outer,orient="vertical",command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right",fill="y"); canvas.pack(side="left",fill="both",expand=True)
        host=tk.Frame(canvas,bg=PANEL)
        win=canvas.create_window((0,0),window=host,anchor="nw")
        self.left=host
        host.bind("<Configure>",lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e: canvas.itemconfigure(win,width=e.width))
        canvas.bind("<MouseWheel>",lambda e: canvas.yview_scroll(-int(e.delta/120), "units"))

        tk.Label(self.left,text="MISSION CONTROL",bg=PANEL,fg=TEXT,font=("Segoe UI",12,"bold")).pack(anchor="w",padx=18,pady=(18,10))
        tk.Label(self.left,text="VESSEL",bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=18)
        self.combo=ttk.Combobox(self.left,state="readonly"); self.combo.pack(fill="x",padx=18,pady=(5,12)); self.combo.bind("<<ComboboxSelected>>",lambda e:self.change_ship())
        self.sep()

        tk.Label(self.left,text="SIMULATION DATE & TIME",bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=18)
        df=tk.Frame(self.left,bg=PANEL); df.pack(fill="x",padx=18,pady=(5,3))
        self.date_var=tk.StringVar(value=self.selected_dt.strftime("%Y-%m-%d"))
        self.date_entry=tk.Entry(df,textvariable=self.date_var,bg="#091522",fg=TEXT,insertbackground=TEXT,relief="flat",font=("Consolas",9))
        self.date_entry.pack(side="left",fill="x",expand=True,ipady=7)
        tk.Button(df,text="▣",command=self.open_calendar,bg=PANEL2,fg=TEXT,bd=0,padx=10).pack(side="right",padx=(4,0))
        tf=tk.Frame(self.left,bg=PANEL); tf.pack(fill="x",padx=18,pady=(2,6))
        self.time_var=tk.StringVar(value=self.selected_dt.strftime("%H:%M"))
        tk.Entry(tf,textvariable=self.time_var,bg="#091522",fg=TEXT,insertbackground=TEXT,relief="flat",font=("Consolas",9)).pack(side="left",fill="x",expand=True,ipady=7)
        tk.Button(tf,text="APPLY TIME",command=self.apply_datetime,bg=CYAN,fg=BG,relief="flat",bd=0,font=("Segoe UI",8,"bold"),padx=10,pady=7).pack(side="right",padx=(5,0))
        self.time_hint=tk.Label(self.left,text="Historical = replay  •  Future = forecast  •  Current = live marine weather",bg=PANEL,fg=MUTED,justify="left",font=("Segoe UI",7))
        self.time_hint.pack(anchor="w",padx=18,pady=(0,5))

        self.sep()
        tk.Label(self.left,text="TIME ACCELERATION",bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=18)
        self.speed=tk.StringVar(value="5x"); c=ttk.Combobox(self.left,state="readonly",textvariable=self.speed,values=list(SPEEDS)); c.pack(fill="x",padx=18,pady=5); c.bind("<<ComboboxSelected>>",lambda e:self.set_speed())
        fr=tk.Frame(self.left,bg=PANEL); fr.pack(fill="x",padx=18,pady=4)
        self.pause=tk.Button(fr,text="Ⅱ PAUSE",command=self.toggle,bg=AMBER,fg=BG,relief="flat",bd=0,font=("Segoe UI",9,"bold"),pady=9); self.pause.pack(side="left",fill="x",expand=True,padx=(0,3))
        tk.Button(fr,text="↻ RESET",command=self.reset,bg=PANEL2,fg=TEXT,relief="flat",bd=0,font=("Segoe UI",9,"bold"),pady=9).pack(side="left",fill="x",expand=True,padx=(3,0))

        self.sep(); tk.Label(self.left,text="ROUTE STRATEGY",bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=18)
        self.rb={}
        for n in RC:
            b=tk.Button(self.left,text=n,command=lambda x=n:self.select_route(x),bg=PANEL2,fg=TEXT,relief="flat",bd=0,anchor="w",padx=12,pady=9,font=("Segoe UI",9,"bold")); b.pack(fill="x",padx=18,pady=3); self.rb[n]=b

        self.sep(); tk.Label(self.left,text="FUEL PROFILE",bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=18)
        self.fuel_info=tk.Label(self.left,text="",bg=PANEL2,fg=TEXT,justify="left",anchor="w",font=("Consolas",8),padx=10,pady=10)
        self.fuel_info.pack(fill="x",padx=18,pady=5)

        self.sep(); tk.Label(self.left,text="MARINE WEATHER",bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=18)
        self.weather_info=tk.Label(self.left,text="Waiting for weather…",bg=PANEL2,fg=TEXT,justify="left",anchor="w",font=("Consolas",8),padx=10,pady=10)
        self.weather_info.pack(fill="x",padx=18,pady=5)

        self.sep(); self.status=tk.Label(self.left,bg=PANEL,fg=TEXT,justify="left",font=("Consolas",9)); self.status.pack(anchor="w",padx=18)
        tk.Label(self.left,text="\nMAP LEGEND\n\n━━ Safety\n━━ Balanced\n━━ Fuel efficient\n● Ship\n◆ Iceberg\n◇ Forecast position\n✕ Closest approach\n◌ Uncertainty",bg=PANEL,fg=MUTED,justify="left",font=("Segoe UI",8)).pack(anchor="w",padx=18,pady=12)

    def map_ui(self,p):
        top=tk.Frame(p,bg=PANEL,height=48); top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top,text="LIVE NORTH ATLANTIC NAVIGATION",bg=PANEL,fg=TEXT,font=("Segoe UI",11,"bold")).pack(side="left",padx=15)
        self.mapinfo=tk.Label(top,text="",bg=PANEL,fg=MUTED,font=("Segoe UI",8)); self.mapinfo.pack(side="left")
        for t,f in [("-",lambda:self.zoom_by(.85)),("100%",self.reset_view),("+",lambda:self.zoom_by(1.18))]:
            tk.Button(top,text=t,command=f,bg=PANEL2,fg=TEXT,relief="flat",bd=0,padx=9).pack(side="right",padx=3)
        self.cv=tk.Canvas(p,bg="#081522",highlightthickness=0); self.cv.pack(fill="both",expand=True)
        self.cv.bind("<Button-1>",self.click); self.cv.bind("<B1-Motion>",self.drag_map); self.cv.bind("<ButtonRelease-1>",lambda e:setattr(self,"drag",None)); self.cv.bind("<MouseWheel>",lambda e:self.zoom_by(1.12 if e.delta>0 else .89))

    def right_ui(self):
        tk.Label(self.right,text="LIVE INSPECTOR",bg=PANEL,fg=TEXT,font=("Segoe UI",12,"bold")).pack(anchor="w",padx=18,pady=(18,4))
        self.ititle=tk.Label(self.right,text="Select an object",bg=PANEL,fg=MUTED,font=("Segoe UI",8)); self.ititle.pack(anchor="w",padx=18,pady=(0,10))
        box=tk.Frame(self.right,bg=PANEL); box.pack(fill="both",expand=True,padx=12,pady=(0,12))
        self.txt=tk.Text(box,bg="#091522",fg=TEXT,relief="flat",bd=0,wrap="word",padx=14,pady=14,font=("Consolas",9))
        rsb=ttk.Scrollbar(box,orient="vertical",command=self.txt.yview); self.txt.configure(yscrollcommand=rsb.set)
        rsb.pack(side="right",fill="y"); self.txt.pack(side="left",fill="both",expand=True)

    @property
    def ship(self): return next(s for s in self.ships if s.sid==self.shipid)

    def populate(self):
        self.combo["values"]=[f"{s.sid} • {s.name}" for s in self.ships]; self.combo.current(0)

    def open_calendar(self):
        CalendarPopup(self.root, self.selected_dt, self.calendar_selected)

    def calendar_selected(self, dt):
        self.selected_dt=dt.replace(tzinfo=timezone.utc)
        self.date_var.set(self.selected_dt.strftime("%Y-%m-%d"))
        self.time_var.set(self.selected_dt.strftime("%H:%M"))
        self.apply_datetime()

    def apply_datetime(self):
        try:
            dt=datetime.strptime(f"{self.date_var.get().strip()} {self.time_var.get().strip()}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            self.time_hint.configure(text="Use YYYY-MM-DD and HH:MM (UTC).", fg=RED)
            return
        self.selected_dt=dt
        self.time_hint.configure(text=self.datetime_mode_text(), fg=MUTED)
        self.request_weather()
        self.draw()

    def datetime_mode_text(self):
        now=datetime.now(timezone.utc)
        if abs((self.selected_dt-now).total_seconds()) < 3600:
            return "CURRENT WINDOW  •  live marine weather when network is available"
        if self.selected_dt < now:
            return "HISTORICAL WINDOW  •  archive weather / deterministic fallback"
        return "FUTURE WINDOW  •  forecast weather / deterministic fallback"

    def receive_weather(self, data):
        self.root.after(0, lambda: self._receive_weather_ui(data))

    def _receive_weather_ui(self, data):
        self.weather=data
        mode="LIVE" if data.get("live") else ("ARCHIVE" if "ARCHIVE" in data.get("source","") else "MODEL")
        self.weather_info.configure(text=(
            f"{mode} WEATHER\n"
            f"Position  {data['lat']:.2f}°N  {data['lon']:.2f}°W\n"
            f"Wind      {data.get('wind_speed') if data.get('wind_speed') is not None else '—'} km/h  "
            f"{data.get('wind_direction') if data.get('wind_direction') is not None else '—'}°\n"
            f"Waves     {data.get('wave_height') if data.get('wave_height') is not None else '—'} m  "
            f"{data.get('wave_period') if data.get('wave_period') is not None else '—'} s\n"
            f"Wave dir  {data.get('wave_direction') if data.get('wave_direction') is not None else '—'}°\n"
            f"Source    {data.get('source','—')}"
        ))
        self.show_ship()
        self.draw()

    def request_weather(self):
        s=self.ship
        self.weather_service.request(self.selected_dt, s.x, s.y)

    def set_speed(self): self.mult=SPEEDS[self.speed.get()]
    def change_ship(self):
        self.shipid=self.combo.get().split("•")[0].strip(); self.replan(); self.request_weather(); self.show_ship()

    def replan(self):
        self.routes={}; self.warn={}
        for n in RC:
            self.routes[n],self.warn[n]=make_route(self.ship,n,self.ice)
        self.refresh_status(); self.select_route(self.route_name,False)

    def select_route(self,n,redraw=True):
        self.route_name=n
        for k,b in self.rb.items(): b.configure(bg=RC[k] if k==n else PANEL2,fg=BG if k==n else TEXT)
        self.show_route()
        if redraw:self.draw()

    def toggle(self):
        self.running=not self.running; self.pause.configure(text="Ⅱ PAUSE" if self.running else "▶ RESUME",bg=AMBER if self.running else GREEN); self.last=time.perf_counter()

    def reset(self):
        self.sim=0
        for s in self.ships: s.x,s.y=s.start; s.progress=s.travelled=s.fuel=0;s.active=True;s.history=[]
        self.ice=self.make_ice(); self.running=True; self.pause.configure(text="Ⅱ PAUSE",bg=AMBER); self.last=time.perf_counter(); self.replan(); self.request_weather()

    def loop(self):
        now=time.perf_counter(); dt=min(now-self.last,.2); self.last=now
        if self.running:self.update(dt*SPEEDS[self.speed.get()]/60)
        self.draw(); self.root.after(40,self.loop)

    def update(self,dt):
        self.sim+=dt
        for i in self.ice:
            i.x=clamp(i.x+i.vx*dt,5,MAP_W-5); i.y=clamp(i.y+i.vy*dt,5,MAP_H-5)
            i.history.append((self.sim,i.x,i.y)); i.history=i.history[-300:]
        for s in self.ships:
            if not s.active:continue
            route=self.routes[self.route_name] if s.sid==self.shipid else make_route(s,"Balanced",self.ice)[0]
            rem=s.speed*dt
            if s.progress>=route.distance:s.active=False;continue
            old=s.progress;s.progress=min(route.distance,s.progress+rem); left=s.progress; pos=route.points[0]
            for a,b in zip(route.points,route.points[1:]):
                d=dist(a,b)
                if left<=d:pos=along(a,b,left);break
                left-=d;pos=b
            s.x,s.y=pos; moved=s.progress-old;s.travelled+=moved;s.fuel+=moved*s.fuel_rate
            s.history.append((self.sim,s.x,s.y));s.history=s.history[-500:]
            if s.progress>=route.distance:s.active=False
        # The calendar represents the simulation's absolute reference time.
        self.selected_dt += timedelta(hours=dt)
        if int(self.sim*10)%20==0:
            self.replan()
            self.request_weather()

    def transform(self,x,y):
        w,h=self.cv.winfo_width(),self.cv.winfo_height(); sc=min((w-70)/MAP_W,(h-70)/MAP_H)*self.zoom
        return w/2+(x-MAP_W/2)*sc+self.panx,h/2-(y-MAP_H/2)*sc+self.pany
    def inv(self,x,y):
        w,h=self.cv.winfo_width(),self.cv.winfo_height(); sc=min((w-70)/MAP_W,(h-70)/MAP_H)*self.zoom
        return MAP_W/2+(x-w/2-self.panx)/sc,MAP_H/2-(y-h/2-self.pany)/sc
    def zoom_by(self,f):self.zoom=clamp(self.zoom*f,.5,4);self.draw()
    def reset_view(self):self.zoom=1;self.panx=self.pany=0;self.draw()

    def draw(self):
        c=self.cv;c.delete("all");w,h=c.winfo_width(),c.winfo_height();c.create_rectangle(0,0,w,h,fill="#081522",outline="")
        for x in range(0,1001,50):
            x1,y1=self.transform(x,0);x2,y2=self.transform(x,MAP_H);c.create_line(x1,y1,x2,y2,fill="#102a40")
            if x%100==0:c.create_text(x1+3,h-10,text=f"{x} km",fill="#536b80",anchor="w",font=("Segoe UI",7))
        for y in range(0,651,50):
            x1,y1=self.transform(0,y);x2,y2=self.transform(MAP_W,y);c.create_line(x1,y1,x2,y2,fill="#102a40")
        s=self.ship
        if len(s.history)>1:
            q=[]; 
            for _,x,y in s.history[-150:]:q+=list(self.transform(x,y))
            c.create_line(*q,fill="#27425b",width=2,dash=(3,5),smooth=True)
        for n,r in self.routes.items():
            q=[]
            for x,y in r.points:q+=list(self.transform(x,y))
            if n==self.route_name:c.create_line(*q,fill="#172f47",width=11,smooth=True)
            c.create_line(*q,fill=RC[n],width=5 if n==self.route_name else 2,dash=None if n==self.route_name else (8,5),smooth=True)
            if n==self.route_name:
                stride=max(1,len(r.points)//8)
                for i in range(0,len(r.points),stride):
                    x,y=r.points[i];cx,cy=self.transform(x,y);c.create_oval(cx-4,cy-4,cx+4,cy+4,fill=RC[n],outline=BG)
                    c.create_text(cx+7,cy-5,text=f"W{i+1} ({x:.0f},{y:.0f})",fill="#bcd1e4",anchor="sw",font=("Consolas",7))
            z=self.warn.get(n)
            if z:
                cx,cy=self.transform(*z["rp"]);c.create_line(cx-9,cy-9,cx+9,cy+9,fill=RED,width=2);c.create_line(cx-9,cy+9,cx+9,cy-9,fill=RED,width=2)
                c.create_text(cx+12,cy,text=f"CLOSEST\n{z['sep']:.1f} km @ {z['h']}h",fill=RED,anchor="w",font=("Consolas",7,"bold"))
        sc=min((w-70)/MAP_W,(h-70)/MAP_H)*self.zoom
        for i in self.ice:
            cx,cy=self.transform(i.x,i.y);ur=i.unc(0)*sc
            c.create_oval(cx-ur,cy-ur,cx+ur,cy+ur,outline="#34546a",dash=(4,5))
            fx,fy=i.pos(24);px,py=self.transform(fx,fy);fur=i.unc(24)*sc
            c.create_oval(px-fur,py-fur,px+fur,py+fur,outline="#2b566e",dash=(4,5))
            c.create_line(cx,cy,px,py,fill="#39718a",dash=(5,4),arrow=tk.LAST)
            c.create_oval(px-5,py-5,px+5,py+5,fill="#d8f8ff",outline=CYAN,width=2)
            z=clamp(7+i.size*.25,8,18);c.create_polygon(cx,cy-z,cx+z,cy,cx,cy+z,cx-z,cy,fill="#79dfff",outline=WHITE)
            c.create_text(cx+z+7,cy-4,text=f"{i.iid}\nNOW ({i.x:.0f},{i.y:.0f})",fill=WHITE,anchor="w",font=("Consolas",7,"bold"))
            c.create_text(px+7,py+3,text=f"24H ({fx:.0f},{fy:.0f})",fill=CYAN,anchor="w",font=("Consolas",7))
        for sh in self.ships:
            cx,cy=self.transform(sh.x,sh.y);dx,dy=self.transform(*sh.dest)
            c.create_polygon(dx,dy-8,dx+8,dy,dx,dy+8,dx-8,dy,fill=PURPLE,outline=WHITE)
            c.create_text(dx,dy+15,text=f"DEST\n({sh.dest[0]:.0f},{sh.dest[1]:.0f})",fill="#ded0ff",anchor="n",font=("Consolas",7,"bold"))
            sc2=sh.safety*sc;c.create_oval(cx-sc2,cy-sc2,cx+sc2,cy+sc2,outline="#36556e",dash=(4,5))
            sel=sh.sid==self.shipid;r=10 if sel else 7;c.create_oval(cx-r,cy-r,cx+r,cy+r,fill=WHITE,outline=BLUE,width=3 if sel else 2)
            c.create_text(cx,cy-17,text=f"{sh.sid}\n({sh.x:.0f},{sh.y:.0f})",fill=WHITE,anchor="s",font=("Consolas",8,"bold"))
        self.date_var.set(self.selected_dt.strftime("%Y-%m-%d"))
        self.time_var.set(self.selected_dt.strftime("%H:%M"))
        self.clock.configure(text="UTC "+self.selected_dt.strftime("%Y-%m-%d  %H:%M"))
        self.mapinfo.configure(text=f"   {s.name} • {self.route_name} • {s.pct:.1f}% complete • {self.datetime_mode_text()}")
        self.refresh_status()

    def refresh_status(self):
        s=self.ship;r=self.routes.get(self.route_name)
        if not r:return
        self.status.configure(text=f"SIM TIME\nT+ {self.fmt(self.sim)}\n\nVESSEL\n{s.sid}  {s.name}\n\nPROGRESS\n{s.pct:6.1f}%\n\nREMAINING\n{s.remain:6.1f} km\n\nFUEL USED\n{s.fuel:6.1f} L\n\nROUTE RISK\n{r.risk*100:6.1f}%\n\nCONFIDENCE\n{r.confidence*100:6.1f}%")

    def write(self,title,text):self.ititle.configure(text=title);self.txt.delete("1.0",tk.END);self.txt.insert(tk.END,text)

    def show_ship(self):
        s=self.ship; r=self.routes[self.route_name]
        weather=self.weather
        t=(f"VESSEL\n════════════════════════════\n\n"
           f"REFERENCE TIME\n{self.selected_dt.strftime('%Y-%m-%d %H:%M')} UTC\n"
           f"MODE          {self.datetime_mode_text()}\n\n"
           f"{s.name}\nID          {s.sid}\n\n"
           f"CURRENT\nX           {s.x:.2f} km\nY           {s.y:.2f} km\n\n"
           f"DESTINATION\nX           {s.dest[0]:.2f} km\nY           {s.dest[1]:.2f} km\n\n"
           f"JOURNEY\nProgress    {s.pct:.2f}%\nTravelled   {s.travelled:.2f} km\n"
           f"Remaining   {s.remain:.2f} km\nFuel used   {s.fuel:.1f} L\n\n"
           f"ROUTE\n{r.name}\nDistance    {r.distance:.1f} km\nFuel est.   {r.fuel:.1f} L\n"
           f"ETA         {r.eta:.1f} h\nRisk        {r.risk*100:.1f}%\nConfidence  {r.confidence*100:.1f}%\n\n"
           f"MARINE WEATHER\n{weather.get('source','Waiting for weather')}\n"
           f"Wind          {weather.get('wind_speed','—')} km/h\n"
           f"Waves         {weather.get('wave_height','—')} m\n"
           f"Wave period   {weather.get('wave_period','—')} s")
        self.write("Selected vessel", t)

    def show_route(self):
        r=self.routes.get(self.route_name);s=self.ship
        if not r:return
        z=self.warn.get(self.route_name)
        t=f"ROUTE: {r.name.upper()}\n════════════════════════════\n\nDISTANCE       {r.distance:.1f} km\nFUEL           {r.fuel:.1f} L\nETA            {r.eta:.1f} h\nRISK           {r.risk*100:.1f}%\nCONFIDENCE     {r.confidence*100:.1f}%\n\nCURRENT SHIP\n({s.x:.2f}, {s.y:.2f})\nProgress {s.pct:.1f}%\n\nCLOSEST APPROACH\n"
        if z:t+=f"{z['ice'].iid}\nRoute point   ({z['rp'][0]:.2f}, {z['rp'][1]:.2f})\nIceberg point ({z['ip'][0]:.2f}, {z['ip'][1]:.2f})\nSeparation    {z['sep']:.2f} km\nAt            {z['h']} h\nUncertainty   ±{z['unc']:.2f} km\nConfidence    {z['conf']*100:.1f}%\n"
        else:t+="No predicted close approach.\n"
        t+="\nWAYPOINTS\n";stride=max(1,len(r.points)//10)
        for i in range(0,len(r.points),stride):
            x,y=r.points[i];t+=f"W{i+1:<3} X={x:8.2f} Y={y:8.2f}\n"
        self.write("Route analytics",t)

    def show_ice(self,i):
        t=f"ICEBERG\n════════════════════════════\n\nID           {i.iid}\nSIZE         {i.size:.1f} km\nBASE CONF.   {i.confidence*100:.1f}%\n\nCURRENT\nX            {i.x:.2f} km\nY            {i.y:.2f} km\nVx           {i.vx:.2f} km/h\nVy           {i.vy:.2f} km/h\n\nPREDICTION\n"
        for h in (6,12,24):
            p=i.pos(h);t+=f"{h}H           ({p[0]:.2f}, {p[1]:.2f})\n             ±{i.unc(h):.1f} km\n             conf {i.conf(h)*100:.1f}%\n\n"
        self.write("Selected iceberg",t)

    def click(self,e):
        self.drag=(e.x,e.y); cand=[]
        for i in self.ice:
            x,y=self.transform(i.x,i.y);cand.append((math.hypot(e.x-x,e.y-y),"i",i))
        for s in self.ships:
            x,y=self.transform(s.x,s.y);cand.append((math.hypot(e.x-x,e.y-y),"s",s))
        cand.sort(key=lambda x:x[0])
        if cand and cand[0][0]<25:
            if cand[0][1]=="i":self.show_ice(cand[0][2])
            else:self.shipid=cand[0][2].sid;self.show_ship()
        else:
            x,y=self.inv(e.x,e.y);self.write("Map coordinate",f"COORDINATE\n════════════════════════════\n\nX = {x:.3f} km\nY = {y:.3f} km")

    def drag_map(self,e):
        if self.drag:
            self.panx+=e.x-self.drag[0];self.pany+=e.y-self.drag[1];self.drag=(e.x,e.y);self.draw()

    def fmt(self,h):
        sec=int(h*3600);d,sec=divmod(sec,86400);hh,sec=divmod(sec,3600);mm,ss=divmod(sec,60)
        return f"{d:02d}:{hh:02d}:{mm:02d}:{ss:02d}" if d else f"{hh:02d}:{mm:02d}:{ss:02d}"

if __name__=="__main__":
    root=tk.Tk();App(root);root.mainloop()

