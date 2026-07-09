from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
import googlemaps
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=API_KEY)


def get_distance_matrix(locations):
    matrix = gmaps.distance_matrix(
        locations,
        locations,
        mode="driving",
        units="metric"
    )

    distances = []

    for row in matrix["rows"]:
        distances.append([
            element["distance"]["value"]
            for element in row["elements"]
        ])

    return distances


def optimize_route(distance_matrix):
    manager = pywrapcp.RoutingIndexManager(
        len(distance_matrix),
        1,
        0
    )

    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback = routing.RegisterTransitCallback(distance_callback)

    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()

    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        return []

    index = routing.Start(0)

    order = []

    while not routing.IsEnd(index):
        order.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))

    return order


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/optimize", methods=["POST"])
def optimize():

    data = request.get_json()

    locations = data.get("locations", [])

    if len(locations) < 2:
        return jsonify({
            "success": False,
            "message": "Please enter at least two locations."
        })

    try:

        distance_matrix = get_distance_matrix(locations)

        route = optimize_route(distance_matrix)

        optimized = [locations[i] for i in route]

        directions = gmaps.directions(
            optimized[0],
            optimized[-1],
            waypoints=optimized[1:-1],
            optimize_waypoints=False,
            mode="driving"
        )

        total_distance = 0
        total_duration = 0

        if directions:

            legs = directions[0]["legs"]

            for leg in legs:
                total_distance += leg["distance"]["value"]
                total_duration += leg["duration"]["value"]

        return jsonify({
            "success": True,
            "optimized_route": optimized,
            "distance_km": round(total_distance / 1000, 2),
            "duration_min": round(total_duration / 60),
            "google_maps_link": f"https://www.google.com/maps/dir/{'/'.join(optimized)}"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


if __name__ == "__main__":
    app.run(debug=True)
