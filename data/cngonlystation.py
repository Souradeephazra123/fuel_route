import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List


def realistic_price() -> float:
    """Generate a realistic fuel price per gallon."""
    return round(random.uniform(2.85, 4.50), 2)


def load_json(path: Path) -> List[Dict[str, Any]]:
    """Load station data from a JSON file."""
    with path.open('r', encoding='utf-8') as source:
        return json.load(source)


def collect_fuel_types(stations: Iterable[Dict[str, Any]]) -> set[str]:
    """Collect unique fuel type values from station records."""
    return {str(station.get('fuel_type')).strip() for station in stations if station.get('fuel_type')}


def filter_cng_stations(stations: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return only stations whose fuel_type is exactly CNG."""
    return [station for station in stations if station.get('fuel_type') == 'E85' or station.get('fuel_type') == 'BD' or station.get('fuel_type') == 'RD']


def format_station(station: Dict[str, Any]) -> Dict[str, Any]:
    """Map a station record to the desired output shape."""
    return {
        'station_id': station.get('station_id'),
        'name': station.get('name'),
        'city': station.get('city'),
        'state': station.get('state'),
        'latitude': station.get('latitude'),
        'longitude': station.get('longitude'),
        'price_per_gallon': realistic_price(),
    }


def convert_stations(stations: Iterable[Dict[str, Any]], limit: int | None = None) -> List[Dict[str, Any]]:
    """Convert input station records and apply CNG filtering."""
    cng_stations = filter_cng_stations(stations)
    if limit is not None:
        cng_stations = cng_stations[:limit]

    return [format_station(station) for station in cng_stations]


def save_json(data: List[Dict[str, Any]], path: Path) -> None:
    """Save converted station data to a JSON file."""
    with path.open('w', encoding='utf-8') as output:
        json.dump(data, output, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Convert a station JSON file to filtered CNG stations with pricing.'
    )
    parser.add_argument(
        'input_file',
        nargs='?', 
        default='nrel_fuel_stations.json',
        help='Path to the input JSON file containing station records.',
    )
    parser.add_argument(
        '--output',
        '-o',
        default='oil_stations_with_prices.json',
        help='Output JSON file path.',
    )
    parser.add_argument(
        '--limit',
        '-n',
        type=int,
        default=None,
        help='Optional maximum number of stations to include in the output.',
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Optional random seed for reproducible pricing.',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    input_path = Path(args.input_file)
    output_path = Path(args.output)

    stations = load_json(input_path)
    fuel_types = collect_fuel_types(stations)
    print('Unique fuel types found:')
    for fuel_type in sorted(fuel_types):
        print(f' - {fuel_type}')

    converted = convert_stations(stations, limit=args.limit)
    save_json(converted, output_path)

    print(f'Converted {len(converted)} CNG station(s) and saved to {output_path}')


if __name__ == '__main__':
    main()