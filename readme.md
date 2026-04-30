# 🚗 Route-Constrained Fuel Optimization API

A Django REST API that calculates the absolute most cost-effective fueling strategy for road trips across the contiguous United States. 

Given a starting location and destination, this API fetches real-world driving routes, identifies candidate fuel stations along the physical route corridor, and uses a state-space graph optimization algorithm to calculate exactly where to stop and how much fuel to buy to minimize total trip cost.

## 🌟 Key Features
* **True Route Geometry:** Evaluates stations based on the actual drivable polyline, not straight-line (Euclidean) distance.
* **Mathematical Cost Optimization:** Uses **Dijkstra's Algorithm** over a discretized state-space graph to find the cheapest valid sequence of fuel purchases.
* **Vehicle Constraints Enforcement:** Strictly adheres to a maximum vehicle range (500 miles) and efficiency (10 MPG).
* **Real-World Safety Buffers:** Supports an optional `safety_buffer_gallons` parameter to prevent the algorithm from stranding the driver on 0.0 gallons, balancing mathematical optimization with physical reality.
* **High-Performance Spatial Querying:** Uses **SciPy cKDTree** for lightning-fast radius and nearest-neighbor searches, dropping spatial query times from seconds to milliseconds.

---

## 🏗️ System Architecture & Request Flow

When a user submits a routing request, the payload passes through several distinct layers:

1. **Geocoding Layer:** Converts input text (e.g., `"Dallas, TX"`) into exact lat/long coordinates.
2. **Routing Layer:** Calls an external routing provider (OpenRouteService) to fetch total distance, duration, and the physical route polyline.
3. **Spatial Filtering Layer:** Builds a KD-Tree over the station database to efficiently query only the stations that fall within a tight radius of the route corridor.
4. **Route-Progress Layer:** Maps each filtered station to the route geometry to calculate its exact `distance_from_start_miles`.
5. **Fuel Optimization Layer:** Generates a state-graph of `(node_index, fuel_units_remaining)` and applies Dijkstra's algorithm to find the lowest-cost path of `[Drive]` and `[Buy Fuel]` actions.
6. **Response Layer:** Packages the optimized route, stops, and financial summaries into a clean JSON response.

---

## 🧠 Core Algorithmic Concepts

### 1. Spatial Acceleration (SciPy cKDTree)
To find stations "near" the route, comparing 500+ route coordinates against thousands of database stations via brute-force Haversine calculations is too slow. 
* **Solution:** We sample the route points and build an in-memory `cKDTree`. We then execute a highly optimized `query_ball_point` (radius search) to instantly isolate candidate stations, and a nearest-neighbor lookup to assign route-progress to each station.

### 2. State-Space Fuel Optimization (Dijkstra)
A standard shortest-path algorithm cannot solve fuel pricing because the cost depends on *how much* fuel you already have in the tank. 
* **Solution:** We model the trip as a graph of states: `(current_location, fuel_remaining)`. 
* **Actions:** From any state, the algorithm can either **Buy Fuel** (stay at the station, increase fuel, increase monetary cost) or **Drive** (move to the next station, decrease fuel, $0 monetary cost). 
* **Execution:** Because all financial costs are non-negative, Dijkstra's algorithm flawlessly calculates the minimum-cost fueling strategy. Fuel is discretized into 10-mile units to keep the graph computationally manageable.

---

## 🚀 Performance & Profiling

This project was heavily optimized from its initial iteration. Based on internal logging:
* **Algorithm Speed:** The core Dijkstra optimization algorithm solves a 3,200-mile cross-country route in just **~11 to 98 milliseconds**.
* **Spatial Querying:** KD-Tree optimizations reduced station filtering to **< 300 milliseconds**.
* **Network Latency / Bottlenecks:** The primary execution time (~5-6 seconds) is bound entirely by the network I/O of the free external routing API (OpenRouteService). 
* **Caching:** Django caching is implemented to save expensive external API geometries. Subsequent requests for the same route return almost instantly.

---

## 🛠️ API Usage

### Endpoint
`POST /api/route/optimized-fuel-plan/`

### Request Payload
```json
{
 "start": "Minneapolis, MN",
  "end": "St. Louis, MO",
  "max_range_miles": 500,
  "mpg": 10,
  "start_fuel_percent": 100,
  "fuel_step_miles": 10,
  "safety_buffer_gallons": 5
}
```

### Response Example
```json
{
    "route": {
        "start": "Minneapolis, MN",
        "finish": "St. Louis, MO",
        "distance_miles": 559.03,
        "duration_hours": 9.78
    },
    "vehicle": {
        "max_range_miles": 500.0,
        "mpg": 10.0,
        "tank_capacity_gallons": 50.0,
        "safety_buffer_gallons": 5.0,
        "start_fuel_percent": 100
    },
    "candidate_station_count": 19,
    "fuel_summary": {
        "total_gallons_consumed": 55.9,
        "total_gallons_purchased": 11.0,
        "total_fuel_cost": 33.4
    },
    "fuel_stops": [
        {
            "station_id": 213623,
            "name": "Kwik Trip #281",
            "city": "Prior Lake",
            "state": "MN",
            "latitude": 44.707731,
            "longitude": -93.41018,
            "distance_from_start_miles": 19.67,
            "price_per_gallon": 2.93,
            "fuel_remaining_gallons_on_arrival": 48.0,
            "remaining_range_miles_on_arrival": 480.0,
            "gallons_purchased": 2.0,
            "cost": 5.86
        },
        {
            "station_id": 448432,
            "name": "Casey's",
            "city": "Waverly",
            "state": "IA",
            "latitude": 42.715521,
            "longitude": -92.476735,
            "distance_from_start_miles": 199.15,
            "price_per_gallon": 3.06,
            "fuel_remaining_gallons_on_arrival": 32.0,
            "remaining_range_miles_on_arrival": 320.0,
            "gallons_purchased": 9.0,
            "cost": 27.54
        }
    ]
}
```

---

## ⚠️ Real-World Assumptions & Trade-offs

* **The "Zero Range" Fallacy:** Without the `safety_buffer_gallons` parameter, pure mathematical optimization will force the vehicle to coast into cheaper gas stations with exactly `0.0` gallons left to save pennies. We highly recommend utilizing the safety buffer for real-world dispatching.
* **Data Sparsity vs. Safety Buffers:** If a user sets a strict 5-gallon safety buffer, the *effective* range of the vehicle drops to 450 miles. If the provided fuel station dataset has a geographical gap larger than 450 miles (e.g., traversing deserts in Wyoming/Nevada), the API will accurately return a "Route not feasible" error rather than violating the buffer constraint.
* **PostGIS vs. In-Memory Trees:** PostGIS is the industry standard for spatial querying. However, to minimize setup complexity for the evaluator and avoid heavy infrastructure dependencies, high-performance in-memory SciPy KD-Trees were utilized instead. This is a deliberate engineering tradeoff prioritizing deployment speed while maintaining sub-second spatial queries.

---

## 🔮 Future Enhancements
If this were to be expanded into a production-level enterprise service:
1. **Greedy Pre-Filtering:** Before feeding stations to Dijkstra, bucket the route into 50-mile segments and keep only the top 3 cheapest stations per bucket. This would reduce the graph nodes from ~500 to ~50, ensuring microsecond algorithmic execution.
2. **PostGIS Migration:** Move spatial queries directly to the database level for better persistence and precision.
3. **Redis Caching:** Replace local memory caching with Redis to allow cache sharing across distributed worker processes.
4. **Elevation/Traffic Adjusted MPG:** Integrate topographical data to dynamically alter the `mpg` variable based on mountain inclines and traffic patterns.

---

## 💻 Local Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd <repo-folder>
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  
   pip install -r requirements.txt
   ```

3. **Run database migrations & load data:**
   ```bash
   python manage.py migrate
   python manage.py import_fuel_price  
   ```

4. **Start the development server:**
   ```bash
   python manage.py runserver
   ```