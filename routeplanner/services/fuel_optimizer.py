import heapq
from turtle import distance
from typing import List, Dict, Any, Tuple
import math
from routeplanner.utils.timing import timeit


class FuelOptimizer:
    @timeit("optimizing_fuel_plan")
    def optimizing_fuel_plan(
        self,
        station_with_progress,
        route_distance_miles,
        max_range_miles=500,
        mpg=10,
        start_fuel_percent=100,
        fuel_step_miles=10,
        start_price_per_gallon=None,
        safety_buffer_gallons=0,
    ):
        """
        Optimized fuel planar using Djikstra over fuel states

        state:
        (node_index, fuel_units_remaining)

        One fuel unit represents fuel_step_miles of diriving range
        Example:
        fuel_step_miles=10
        mpg=10

        1 fuel unit = 1 gallon


        """

        if route_distance_miles <= 0:
            return {
                "fuel_stops": [],
                "total_cost": 0,
                "total_gallon_purchased": 0,
                "message": "Route distance is zero",
            }

        tank_capacity_gallons = max_range_miles / mpg

        unit_gallons = fuel_step_miles / mpg
        capacity_units = math.ceil(max_range_miles / fuel_step_miles)
        reserve_units = math.ceil(safety_buffer_gallons / unit_gallons)

        start_fuel_miles = max_range_miles * (start_fuel_percent / 100)

        start_fuel_units = min(
            capacity_units, math.floor(start_fuel_miles / fuel_step_miles)
        )

        nodes = self._build_nodes(
            station_with_progress=station_with_progress,
            route_distance_miles=route_distance_miles,
            start_price_per_gallon=start_price_per_gallon,
        )

        if not nodes:
            raise ValueError("No route Nodes found for optimization")

        if safety_buffer_gallons >= tank_capacity_gallons:
            raise ValueError("Safety buffer gallons must be less than tank capacity.")

        destination_index = len(nodes) - 1

        start_state = (0, start_fuel_units)

        priority_queue = []

        heapq.heappush(priority_queue, (0, start_state))

        best_cost = {start_state: 0}

        previous = {}

        final_state = None

        while priority_queue:
            current_cost, current_state = heapq.heappop(priority_queue)

            current_node_index, current_fuel_units = current_state

            if current_cost > best_cost.get(current_state, float("inf")):
                continue

            if current_node_index == destination_index:
                final_state = current_state
                break

            current_node = nodes[current_node_index]

            # Action1: Buy one fuel unit at current node
            can_buy_fuel = (
                current_node.get("price_per_gallon") is not None
                and (current_fuel_units < capacity_units)
                and not current_node.get("is_destination", False)
            )

            if can_buy_fuel:
                buy_cost = unit_gallons * current_node["price_per_gallon"]

                next_state = (current_node_index, current_fuel_units + 1)

                new_cost = current_cost + buy_cost

                if new_cost < best_cost.get(next_state, float("inf")):
                    best_cost[next_state] = new_cost
                    previous[next_state] = (
                        current_state,
                        {
                            "type": "buy",
                            "node_index": current_node_index,
                            "fuel_units": 1,
                            "price_per_gallon": unit_gallons,
                            "gallons": unit_gallons,
                            "cost": buy_cost,
                        },
                    )
                    heapq.heappush(priority_queue, (new_cost, next_state))

            # Action2 : drive to any reachable future node
            for next_node_index in range(current_node_index + 1, len(nodes)):
                next_node = nodes[next_node_index]

                distance_to_next = (
                    next_node["distance_from_start_miles"]
                    - current_node["distance_from_start_miles"]
                )

                if distance_to_next < 0:
                    continue

                if distance_to_next > max_range_miles:
                    break

                needed_units = math.ceil(distance_to_next / fuel_step_miles)

                if current_fuel_units - needed_units >= reserve_units:
                    next_fuel_units = current_fuel_units - needed_units
                    next_state = (next_node_index, next_fuel_units)

                    new_cost = current_cost

                    if new_cost < best_cost.get(next_state, float("inf")):
                        best_cost[next_state] = new_cost
                        previous[next_state] = (
                            current_state,
                            {
                                "type": "drive",
                                "from_node_index": current_node_index,
                                "to_node_index": next_node_index,
                                "distance_miles": distance_to_next,
                                "fuel_units_used": needed_units,
                            },
                        )
                        heapq.heappush(priority_queue, (new_cost, next_state))

        if final_state is None:
            raise ValueError(
                "No valid fuel plan found for the given route and parameters. Route may have gaps larger than vehicle range."
            )

        actions = self._reconstruct_actions(previous, start_state, final_state)

        fuel_stops = self._build_fuel_stops_from_actions(
            actions=actions, nodes=nodes, fuel_step_miles=fuel_step_miles, mpg=mpg
        )

        total_cost = sum(stop["cost"] for stop in fuel_stops)
        total_gallon_purchased = sum(stop["gallons_purchased"] for stop in fuel_stops)

        return {
            "fuel_stops": fuel_stops,
            "total_cost": round(total_cost, 2),
            "total_gallons_purchased": round(total_gallon_purchased, 2),
            "tank_capacity_gallons": round(tank_capacity_gallons, 2),
            "fuel_step_miles": fuel_step_miles,
        }

    @timeit("_build_nodes")
    def _build_nodes(
        self, station_with_progress, route_distance_miles, start_price_per_gallon=None
    ):
        """
        Build route nodes:
        - virtual start node
        - candidate fuel stations
        - virtual destination node
        """

        nodes = []

        nodes.append(
            {
                "node_type": "start",
                "station_id": None,
                "name": "Start",
                "city": None,
                "state": None,
                "latitude": None,
                "longitude": None,
                "price_per_gallon": start_price_per_gallon,
                "distance_from_start_miles": 0.0,
                "is_destination": False,
            }
        )

        clean_stations = []

        for station in station_with_progress:
            distance = station.get("distance_from_start_miles")

            # if distance is None or distance <=0 or distance > route_distance_miles:
            #     continue

            if distance is None:
                continue
            if distance <= 0:
                continue
            if distance >= route_distance_miles:
                continue

            clean_stations.append(station)

        clean_stations.sort(key=lambda x: x["distance_from_start_miles"])

        seen_station_ids = set()

        for station in clean_stations:
            station_id = station["station_id"]

            if station_id in seen_station_ids:
                continue

            seen_station_ids.add(station_id)

            nodes.append(
                {
                    "node_type": "fuel_station",
                    "station_id": station["station_id"],
                    "name": station["name"],
                    "city": station["city"],
                    "state": station["state"],
                    "latitude": station["latitude"],
                    "longitude": station["longitude"],
                    "price_per_gallon": station["price_per_gallon"],
                    "distance_from_start_miles": station["distance_from_start_miles"],
                    "is_destination": False,
                }
            )

        nodes.append(
            {
                "node_type": "destination",
                "station_id": None,
                "name": "Destination",
                "city": None,
                "state": None,
                "latitude": None,
                "longitude": None,
                "price_per_gallon": None,
                "distance_from_start_miles": route_distance_miles,
                "is_destination": True,
            }
        )

        nodes.sort(key=lambda x: x["distance_from_start_miles"])

        return nodes

    def _reconstruct_actions(self, previous, start_state, final_state):
        """
        Reconstruct Dijikstra path from  final state  back to start date
        """

        actions_reversed = []

        current_state = final_state

        while current_state != start_state:
            previous_state, action = previous[current_state]
            actions_reversed.append(
                {
                    "from_state": previous_state,
                    "action": action,
                    "to_state": current_state,
                }
            )
            current_state = previous_state

        actions_reversed.reverse()
        return actions_reversed

    # def _build_fuel_stops_from_actions(self, actions, nodes,fuel_step_miles,mpg):
    #     """
    #         Aggregate all buy actions by station.
    #     """
    #     purchases={}
    #     for action in actions:
    #         if action["type"] !="buy":
    #             continue

    #         node_index=action["node_index"]
    #         node=nodes[node_index]

    #         if node["node_type"] != "fuel_station":
    #             continue

    #         to_state = action["to_state"]
    #         fuel_units_remaining = to_state[1]

    #         fuel_remaining_gallons = fuel_units_remaining * (fuel_step_miles / mpg)

    #         if node_index not in purchases:
    #             purchases[node_index]={
    #                 "station_id": node["station_id"],
    #                     "name": node["name"],
    #                     "city": node["city"],
    #                     "state": node["state"],
    #                     "latitude": node["latitude"],
    #                     "longitude": node["longitude"],
    #                     "distance_from_start_miles": node["distance_from_start_miles"],
    #                     "fuel_remainining_gallons_at_stop": fuel_remaining_gallons,
    #                     "price_per_gallon": node["price_per_gallon"],
    #                     "gallons_purchased": 0,
    #                     "cost": 0
    #             }

    #         purchases[node_index]["gallons_purchased"] += action["gallons"]
    #         purchases[node_index]["cost"] += action["cost"]

    #     fuel_stops=list(purchases.values())

    #     fuel_stops.sort(key=lambda x: x['distance_from_start_miles'])

    #     for stop in fuel_stops:
    #             stop["distance_from_start_miles"] = round(stop["distance_from_start_miles"], 2)
    #             stop["fuel_remainining_gallons_at_stop"] = round(stop["fuel_remainining_gallons_at_stop"], 2)
    #             stop["price_per_gallon"] = round(stop["price_per_gallon"], 2)
    #             stop["gallons_purchased"] = round(stop["gallons_purchased"], 2)
    #             stop["cost"] = round(stop["cost"], 2)

    #     return fuel_stops

    @timeit("_build_fuel_stops_from_actions")
    def _build_fuel_stops_from_actions(self, actions, nodes, fuel_step_miles, mpg):
        purchases = {}

        for item in actions:
            action = item["action"]

            if action["type"] == "drive":
                to_node_index = action["to_node_index"]
                node = nodes[to_node_index]

                if node["node_type"] != "fuel_station":
                    continue

                to_state = item["to_state"]
                fuel_units_remaining = to_state[1]

                fuel_remaining_gallons = fuel_units_remaining * (fuel_step_miles / mpg)
                remaining_range_miles = fuel_units_remaining * fuel_step_miles

                if to_node_index not in purchases:
                    purchases[to_node_index] = {
                        "station_id": node["station_id"],
                        "name": node["name"],
                        "city": node["city"],
                        "state": node["state"],
                        "latitude": node["latitude"],
                        "longitude": node["longitude"],
                        "distance_from_start_miles": node["distance_from_start_miles"],
                        "price_per_gallon": node["price_per_gallon"],
                        "fuel_remaining_gallons_on_arrival": fuel_remaining_gallons,
                        "remaining_range_miles_on_arrival": remaining_range_miles,
                        "gallons_purchased": 0,
                        "cost": 0,
                    }

            elif action["type"] == "buy":
                node_index = action["node_index"]
                node = nodes[node_index]

                if node["node_type"] != "fuel_station":
                    continue

                if node_index not in purchases:
                    purchases[node_index] = {
                        "station_id": node["station_id"],
                        "name": node["name"],
                        "city": node["city"],
                        "state": node["state"],
                        "latitude": node["latitude"],
                        "longitude": node["longitude"],
                        "distance_from_start_miles": node["distance_from_start_miles"],
                        "price_per_gallon": node["price_per_gallon"],
                        "fuel_remaining_gallons_on_arrival": None,
                        "remaining_range_miles_on_arrival": None,
                        "gallons_purchased": 0,
                        "cost": 0,
                    }

                purchases[node_index]["gallons_purchased"] += action["gallons"]
                purchases[node_index]["cost"] += action["cost"]

        fuel_stops = list(purchases.values())
        fuel_stops.sort(key=lambda x: x["distance_from_start_miles"])

        for stop in fuel_stops:
            stop["distance_from_start_miles"] = round(
                stop["distance_from_start_miles"], 2
            )
            stop["price_per_gallon"] = round(stop["price_per_gallon"], 2)
            stop["gallons_purchased"] = round(stop["gallons_purchased"], 2)
            stop["cost"] = round(stop["cost"], 2)
            if stop["fuel_remaining_gallons_on_arrival"] is not None:
                stop["fuel_remaining_gallons_on_arrival"] = round(
                    stop["fuel_remaining_gallons_on_arrival"], 2
                )
            if stop["remaining_range_miles_on_arrival"] is not None:
                stop["remaining_range_miles_on_arrival"] = round(
                    stop["remaining_range_miles_on_arrival"], 2
                )

        return fuel_stops
