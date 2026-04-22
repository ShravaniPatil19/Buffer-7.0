import osmnx as ox
import folium
import heapq
import requests
import math
import os
import json
from datetime import datetime
from folium.plugins import MiniMap, AntPath

CACHE_FILE = "static/osm_cache.json"


# ---------------- EDGE CLASS ---------------- #
class Edge:
    def __init__(self, distance, crime, lighting, isolation,
                 density, cctv_dist, police_dist, hospital_dist, risk_zone):
        self.distance = distance
        self.crime = crime
        self.lighting = lighting
        self.isolation = isolation
        self.density = density
        self.cctv_dist = cctv_dist
        self.police_dist = police_dist
        self.hospital_dist = hospital_dist
        self.risk_zone = risk_zone


# ---------------- TIME FACTOR ---------------- #
def get_time_factor():
    now = datetime.now()
    hour = now.hour
    weekday = now.weekday()

    if 21 <= hour or hour <= 5:
        tf = 1.5
    elif 18 <= hour < 21 or 5 < hour <= 8:
        tf = 1.2
    else:
        tf = 1.0

    if weekday >= 5:
        tf *= 1.1

    return tf


# ---------------- DISTANCE ---------------- #
def distance_between(p1, p2):
    R = 6371000
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------- CACHE ---------------- #
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_cache(cache):
    os.makedirs("static", exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


# ---------------- API (BBOX BASED) ---------------- #
def get_places_bbox(north, south, east, west, tag):
    query = f"""
    [out:json][timeout:25];
    (
      node[{tag}]({south},{west},{north},{east});
      way[{tag}]({south},{west},{north},{east});
      relation[{tag}]({south},{west},{north},{east});
    );
    out center;
    """

    # Use multiple Overpass servers (fallback system)
    overpass_urls = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter",
        "https://overpass.nchc.org.tw/api/interpreter"
    ]

    headers = {
        "User-Agent": "NavSafeProject/1.0 (Educational Project)",
        "Accept": "application/json"
    }

    for url in overpass_urls:
        try:
            res = requests.post(url, data={"data": query}, headers=headers, timeout=90)

            if res.status_code == 200:
                data = res.json()
                points = []

                for el in data.get("elements", []):
                    if "lat" in el and "lon" in el:
                        points.append((el["lat"], el["lon"]))
                    elif "center" in el:
                        points.append((el["center"]["lat"], el["center"]["lon"]))

                print(f"Overpass Success from: {url} | Points: {len(points)}")
                return points

            else:
                print(f"Overpass Failed ({res.status_code}) from {url}")

        except Exception as e:
            print(f"Overpass Exception from {url}: {e}")

    return []

# ---------------- SAFETY WEIGHT ---------------- #
def calculate_safety_weight(edge):
    return (
        0.20 * (edge.distance / 1000) +
        0.25 * edge.crime +
        0.15 * (1 - edge.lighting) +
        0.15 * edge.isolation +
        0.10 * (edge.cctv_dist / 500) +
        0.10 * (edge.police_dist / 1000) +
        0.05 * (edge.hospital_dist / 1000)
    )


def normalize_score(value, min_val, max_val):
    if max_val - min_val == 0:
        return 50

    score = 100 - ((value - min_val) / (max_val - min_val)) * 100

    if score < 0:
        score = 0
    if score > 100:
        score = 100

    return score


# ---------------- DIJKSTRA ---------------- #
def dijkstra(graph, start, mode="shortest"):
    pq = [(0, start)]
    dist = {n: float('inf') for n in graph}
    dist[start] = 0
    prev = {}

    while pq:
        cd, node = heapq.heappop(pq)

        if cd > dist[node]:
            continue

        for neigh, edge in graph[node]:
            cost = edge.distance if mode == "shortest" else calculate_safety_weight(edge)
            nd = cd + cost

            if nd < dist[neigh]:
                dist[neigh] = nd
                prev[neigh] = node
                heapq.heappush(pq, (nd, neigh))

    return dist, prev


# ---------------- PATH ---------------- #
def get_path(prev, start, end):
    path = []
    cur = end

    while cur != start:
        path.append(cur)
        cur = prev.get(cur)
        if cur is None:
            return []

    path.append(start)
    return path[::-1]


# ---------------- SEGMENT RISK COLOR ---------------- #
def get_risk_color(score):
    if score >= 70:
        return "green"
    elif score >= 40:
        return "orange"
    return "red"


# ---------------- CORE FUNCTION ---------------- #
def run_navigation(start_place, end_place, city="Mumbai"):
    print("\n=== NAVIGATION STARTED ===")

    # ---------------- GRAPH ---------------- #
    try:
        graph = ox.graph_from_place(city + ", Maharashtra, India", network_type="drive")
    except:
        center = ox.geocode(city + ", Maharashtra, India")
        graph = ox.graph_from_point(center, dist=8000, network_type="drive")

    TIME_FACTOR = get_time_factor()
    coords = {n: (d["y"], d["x"]) for n, d in graph.nodes(data=True)}

    # City BBOX
    nodes_lat = [coords[n][0] for n in coords]
    nodes_lon = [coords[n][1] for n in coords]

    north, south = max(nodes_lat), min(nodes_lat)
    east, west = max(nodes_lon), min(nodes_lon)

    # ---------------- LOAD CACHE ---------------- #
    cache = load_cache()
    cache_key = f"{city}_bbox_data"

    cctv, police, hospital = [], [], []

    if cache_key in cache:
        print("Loaded safety data from cache")
        cctv = cache[cache_key].get("cctv", [])
        police = cache[cache_key].get("police", [])
        hospital = cache[cache_key].get("hospital", [])
    else:
        print("Fetching safety data from Overpass...")

        # CCTV tag corrected (most important fix)
        cctv = get_places_bbox(north, south, east, west, '"surveillance"="camera"')

        # Police and Hospital tags are correct
        police = get_places_bbox(north, south, east, west, '"amenity"="police"')
        hospital = get_places_bbox(north, south, east, west, '"amenity"="hospital"')

        print(f"CCTV Found: {len(cctv)}")
        print(f"Police Found: {len(police)}")
        print(f"Hospital Found: {len(hospital)}")

        # IMPORTANT: Don't cache empty results (Overpass might fail temporarily)
        if len(cctv) > 0 or len(police) > 0 or len(hospital) > 0:
            cache[cache_key] = {"cctv": cctv, "police": police, "hospital": hospital}
            save_cache(cache)
        else:
            print("⚠ Overpass returned empty data. Cache not saved.")

    # ---------------- BUILD GRAPH ---------------- #
    converted = {}

    for u, v, data in graph.edges(data=True):
        distance = data.get("length", 1)

        density = min(len(graph[u]) / 10, 1)
        isolation = 1 - density

        crime = (0.3 + 0.5 * (1 - density)) * TIME_FACTOR

        mid = ((coords[u][0] + coords[v][0]) / 2,
               (coords[u][1] + coords[v][1]) / 2)

        def nearest(points):
            if not points:
                return 5000
            return min(distance_between(mid, p) for p in points)

        edge = Edge(
            distance=distance,
            crime=crime,
            lighting=0.5,
            isolation=isolation,
            density=density,
            cctv_dist=nearest(cctv),
            police_dist=nearest(police),
            hospital_dist=nearest(hospital),
            risk_zone=0
        )

        converted.setdefault(u, []).append((v, edge))
        converted.setdefault(v, []).append((u, edge))

    # ---------------- GEOCODING ---------------- #
    start_coords = ox.geocode(start_place + ", " + city)
    end_coords = ox.geocode(end_place + ", " + city)

    start = ox.distance.nearest_nodes(graph, start_coords[1], start_coords[0])
    end = ox.distance.nearest_nodes(graph, end_coords[1], end_coords[0])

    # ---------------- ROUTING ---------------- #
    d1, p1 = dijkstra(converted, start, "shortest")
    d2, p2 = dijkstra(converted, start, "safest")

    path1 = get_path(p1, start, end)
    path2 = get_path(p2, start, end)

    if not path1 or not path2:
        return 0, 0, 0, "route.html", {}

    coords1 = [coords[n] for n in path1]
    coords2 = [coords[n] for n in path2]

    shortest_distance = d1[end]
    safest_cost = d2[end]

    safest_distance = sum(
        distance_between(coords[path2[i]], coords[path2[i + 1]])
        for i in range(len(path2) - 1)
    )

    safety_score = normalize_score(safest_cost, 0, safest_cost * 2)

    analytics = {
        "time_factor": TIME_FACTOR,
        "cctv_points": len(cctv),
        "police_points": len(police),
        "hospital_points": len(hospital),
        "shortest_distance": round(shortest_distance, 2),
        "safest_distance": round(safest_distance, 2),
        "safety_score": round(safety_score, 2)
    }

    # ---------------- MAP ---------------- #
    m = folium.Map(location=coords2[0], zoom_start=13, tiles="OpenStreetMap")

    shortest_layer = folium.FeatureGroup(name="🔴 Shortest Route")
    safest_layer = folium.FeatureGroup(name="🟢 Safest Route (Colored Risk)")
    cctv_layer = folium.FeatureGroup(name="📷 CCTV")
    police_layer = folium.FeatureGroup(name="👮 Police")
    hospital_layer = folium.FeatureGroup(name="🏥 Hospital")

    # Shortest route
    AntPath(coords1, color="red", weight=6).add_to(shortest_layer)

    # Safest route (segment colored)
    for i in range(len(coords2) - 1):
        seg_dist = distance_between(coords2[i], coords2[i + 1])
        seg_cost = (seg_dist / 1000) * TIME_FACTOR

        seg_score = normalize_score(seg_cost, 0, 5)
        color = get_risk_color(seg_score)

        folium.PolyLine(
            locations=[coords2[i], coords2[i + 1]],
            color=color,
            weight=7,
            opacity=0.9,
            popup=f"Segment Safety Score: {round(seg_score, 2)}/100"
        ).add_to(safest_layer)

    # Start & End Markers
    folium.Marker(coords2[0], popup="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords2[-1], popup="End", icon=folium.Icon(color="red")).add_to(m)

    # CCTV
    for p in cctv[:150]:
        folium.CircleMarker(location=p, radius=3, color="blue", fill=True).add_to(cctv_layer)

    # Police
    for p in police[:100]:
        folium.Marker(location=p, popup="Police", icon=folium.Icon(color="darkblue")).add_to(police_layer)

    # Hospital
    for p in hospital[:100]:
        folium.Marker(location=p, popup="Hospital", icon=folium.Icon(color="lightred")).add_to(hospital_layer)

    shortest_layer.add_to(m)
    safest_layer.add_to(m)
    cctv_layer.add_to(m)
    police_layer.add_to(m)
    hospital_layer.add_to(m)

    MiniMap().add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    os.makedirs("static", exist_ok=True)
    file_path = os.path.join("static", "route.html")
    m.save(file_path)

    print("Map saved: static/route.html")

    return shortest_distance, safest_distance, safety_score, "route.html", analytics