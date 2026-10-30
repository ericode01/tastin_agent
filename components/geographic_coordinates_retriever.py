import requests
from haystack.nodes.base import BaseComponent
from requests.models import PreparedRequest

from utilities import require_env


class GeographicCoordinatesRetriever(BaseComponent):
    # If it's not a decision component, there is only one outgoing edge
    outgoing_edges = 1

    def __init__(self):
        super().__init__()
        self.api_key = require_env("GOOGLE_MAPS_API_KEY")

    def run(self, query: str, **kwargs):
        # Insert code here to manipulate the input and produce an output dictionary

        print("Enter GeographicCoordinatesRetriever.run")

        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {'address': query, 'key': self.api_key}
        req = PreparedRequest()
        req.prepare_url(url, params)
        print(req.url)

        response = requests.get(req.url)
        print(response.json())
        response_json = response.json()

        if len(response_json["results"]) == 0:
            output = {
                "coordinates_str": "Invalid input:" + query + ". Please try to modify the input if possible.",
            }

            return output, "output_1"

        formatted_address = response_json["results"][0]["formatted_address"]
        latitude = response_json["results"][0]["geometry"]["location"]["lat"]
        longitude = response_json["results"][0]["geometry"]["location"]["lng"]
        # google_place_id = response_json["results"][0]["place_id"]
        # google_plus_code = response_json["results"][0]["plus_code"]

        coordinates_str = "latitude:" + str(latitude) + "," + "longitude:" + str(longitude)
        print("address:" + query + ",,,coordinates_str:" + coordinates_str)

        output = {
            "coordinates_str": coordinates_str,
            "latitude": latitude,
            "longitude": longitude,
            "formatted_address": formatted_address
        }

        return output, "output_1"

    def run_batch(self, query: str, **kwargs):
        # Insert code here to manipulate the input and produce an output dictionary
        pass
