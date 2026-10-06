import numpy as np
from regret.config import get_config
from regret.figures.showcase_map import showcase_plans
cfg = get_config("fixture"); p = showcase_plans(cfg)
truth, h, fl = p["truth"], p["hindsight"], p["flight"]
print("hindsight", h.source, h.lead_h, "n", len(h.lat_deg))
t0 = np.datetime64(fl.departure_time, "ns")
def along(lat, lon):
    u, v = truth.uv(np.asarray(lat), np.asarray(lon), np.full(len(lat), t0))
    return np.hypot(u, v), u
# great circle from origin to destination
lat0, lon0, lat1, lon1 = map(np.radians, (h.lat_deg[0], h.lon_deg[0], h.lat_deg[-1], h.lon_deg[-1]))
f = np.linspace(0, 1, 200)
d = np.arccos(np.sin(lat0)*np.sin(lat1)+np.cos(lat0)*np.cos(lat1)*np.cos(lon1-lon0))
A = np.sin((1-f)*d)/np.sin(d); B = np.sin(f*d)/np.sin(d)
x = A*np.cos(lat0)*np.cos(lon0)+B*np.cos(lat1)*np.cos(lon1); y = A*np.cos(lat0)*np.sin(lon0)+B*np.cos(lat1)*np.sin(lon1); z = A*np.sin(lat0)+B*np.sin(lat1)
gclat, gclon = np.degrees(np.arctan2(z, np.hypot(x, y))), np.degrees(np.arctan2(y, x))
s_h, u_h = along(h.lat_deg, h.lon_deg); s_g, u_g = along(gclat, gclon)
print(f"hindsight: mean speed {s_h.mean():.1f} m/s, mean u {u_h.mean():.1f}; great circle: mean speed {s_g.mean():.1f}, mean u {u_g.mean():.1f}")
# per-longitude jet core latitude (max ERA5 speed) vs hindsight latitude
lats = np.arange(30, 70.01, 0.5)
rows = []
for lo in range(-70, 1, 10):
    i = np.argmin(abs(h.lon_deg - lo))
    s, _ = along(lats, np.full(len(lats), lo))
    rows.append((lo, round(float(h.lat_deg[i]),1), float(lats[s.argmax()]), round(float(s.max()),1), round(float(along([h.lat_deg[i]],[h.lon_deg[i]])[0][0]),1)))
print("lon, hindsight lat, jet-core lat, core speed, speed on hindsight")
for r in rows: print(r)
# all plans mean speed
for pl in p["plans"]:
    if pl.lead_h in (24, 72) or pl.source == "era5":
        print(pl.source, pl.lead_h, round(float(along(pl.lat_deg, pl.lon_deg)[0].mean()),1))
