from flask import Flask, render_template, request, jsonify
import googlemaps
from datetime import datetime
from itertools import permutations

app = Flask(__name__)
API_KEY = "API_KEY"
map_client = googlemaps.Client(key=API_KEY)
get_duration_cache = {}

def get_duration(origin, destination):
    print(f"Getting duration from {origin} → {destination}")

    key = (origin, destination)
    #Check dictionary for duplicates to save runtime and reduce API calls
    if key in get_duration_cache:
        return get_duration_cache[key]

    directions_result = map_client.directions( #creates JSON object
        origin,
        destination,
        mode="driving",
        departure_time=datetime.now(), #Tells google to consider current traffic conditions
    )

    if directions_result:
        leg = directions_result[0]["legs"][0]
        duration = leg["duration"]["value"] / 3600 # convert seconds → hours
        return float(duration)
    return None

def calculate_shortest_travel(origin, destinations):
    most_efficient_option = None
    shortest_time = float("inf")
    all_routes = []

    for order in permutations(destinations):
        route = [origin] + list(order)
        total = 0

        for i in range(len(route) - 1):
            key = (route[i], route[i + 1])
            if key in get_duration_cache:
                duration = get_duration_cache[key]
            else:
                duration = get_duration(route[i], route[i + 1])
                get_duration_cache[key] = duration
                reverse_key = (route[i + 1], route[i])
                if reverse_key not in get_duration_cache:
                    get_duration_cache[reverse_key] = duration
            total += duration

        all_routes.append((route, total))

        if total < shortest_time:
            shortest_time = total
            most_efficient_option = route

    return most_efficient_option, shortest_time, all_routes


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/calculate", methods=["POST"])
@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json()
    origin = data.get("origin")
    destinations = data.get("destinations", [])

    best_route, best_time, all_routes = calculate_shortest_travel(origin, destinations)
    return jsonify({
        "best_route": best_route,
        "best_time": round(best_time, 2),
        "all_routes": [{ "route": r, "time": round(t, 2) } for r, t in all_routes]
    })

if __name__ == "__main__":
    app.run(debug=True)


"""
""Ex: To Call the program:
origin = "Texas Tech University, Lubbock, TX"
destinations = [
    "Dallas, TX",
    "Austin, TX, 6th Street",
    "Houston, TX",
    "Waco, TX"]


calculate_shortest_travel(origin, destinations)


"""
