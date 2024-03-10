import requests
from haystack.nodes.base import BaseComponent
from requests.models import PreparedRequest


class GeographicCoordinatesRetriever(BaseComponent):
    # If it's not a decision component, there is only one outgoing edge
    outgoing_edges = 1

    def run(self, query: str, **kwargs):
        # Insert code here to manipulate the input and produce an output dictionary

        print("Enter GeographicCoordinatesRetriever.run")

        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {'address': query, 'key': 'AIzaSyDdsT4WNL9aWk4fRC3NYC86bgFB9ZlW3u0'}
        req = PreparedRequest()
        req.prepare_url(url, params)
        print(req.url)

        response = requests.get(req.url)
        print(response.json())
        response_json = response.json()

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
