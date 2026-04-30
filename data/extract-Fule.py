import requests
import json
import os
def download_huge_nrel_data():
    # Utilizing the free public NREL Alternative Fuel Stations dataset
    # We use limit=all to grab the massive dataset in one go.
    api_key = os.getenv('NRL_API_KEY', 'DEMO_KEY')  # Replace with your actual API key or set as environment variable
    url = f"https://developer.nlr.gov/api/alt-fuel-stations/v1.json?api_key={api_key}&country=US&access=public&limit=all"

    print("Downloading massive station dataset from NREL API. This may take a minute...")

    try:
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            formatted_stations = []

            # Get the fuel stations array from the response
            fuel_stations = data.get('fuel_stations', [])

            print(f"Found {len(fuel_stations)} stations")

            # Format each station data
            for station in fuel_stations:
                formatted_station = {
                    'station_id': station.get('id'),
                    'name': station.get('station_name'),
                    'address': station.get('street_address'),
                    'city': station.get('city'),
                    'state': station.get('state'),
                    'zip': station.get('zip'),
                    'latitude': station.get('latitude'),
                    'longitude': station.get('longitude'),
                    'fuel_type': station.get('fuel_type_code'),
                    'access': station.get('access_days_time')
                }
                formatted_stations.append(formatted_station)

            # Save to JSON file
            with open('nrel_fuel_stations.json', 'w') as f:
                json.dump(formatted_stations, f, indent=2)

            print(f"Successfully downloaded and saved {len(formatted_stations)} stations to nrel_fuel_stations.json")
            return formatted_stations

        else:
            print(f"Error: API returned status code {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        return None

# Call the function
if __name__ == "__main__":
    download_huge_nrel_data()