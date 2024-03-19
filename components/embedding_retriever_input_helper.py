import json
from json import JSONDecodeError

import requests
from haystack import Document
from haystack.nodes.base import BaseComponent
from requests.models import PreparedRequest


class EmbeddingRetrieverInputHelper(BaseComponent):
    # If it's not a decision component, there is only one outgoing edge
    outgoing_edges = 1

    def run(self, query: str, **kwargs):
        # Insert code here to manipulate the input and produce an output dictionary

        print("Enter EmbeddingRetrieverInputHelper.run")

        try:
            query_json = json.loads(query)
        except JSONDecodeError:
            print("[EmbeddingRetrieverInputHelper.run] Failed to deserialize to JSON from string:" + query)
            content = "Invalid input. Please try to modify the input JSON if possible. Failed to deserialize to JSON from string: " + query
            doc = Document(
                content=content
            )
            output = {
                "documents": [doc],
            }

            return output, "output_2"

        output = {}
        if "Query" in query_json:
            output["query"] = query_json["Query"]
        elif "query" in query_json:
            output["query"] = query_json["query"]
        else:
            output["query"] = query

        delta = 0.02
        latitude_upper = float()
        latitude_lower = float()
        longitude_upper = float()
        longitude_lower = float()
        if "Latitude" in query_json:
            latitude = query_json["Latitude"]
            latitude_f = float(latitude)
            latitude_upper = latitude_f + delta
            latitude_lower = latitude_f - delta
        elif "latitude" in query_json:
            latitude = query_json["latitude"]
            latitude_f = float(latitude)
            latitude_upper = latitude_f + delta
            latitude_lower = latitude_f - delta

        if "Longitude" in query_json:
            longitude = query_json["Longitude"]
            longitude_f = float(longitude)
            longitude_upper = longitude_f + delta
            longitude_lower = longitude_f - delta
        elif "longitude" in query_json:
            longitude = query_json["longitude"]
            longitude_f = float(longitude)
            longitude_upper = longitude_f + delta
            longitude_lower = longitude_f - delta

        if latitude_upper != 0 and latitude_lower != 0 and longitude_upper != 0 and longitude_lower != 0:
            filters = {
                "$and": {
                    "latitude": {"$gte": latitude_lower, "$lte": latitude_upper},
                    "longitude": {"$gte": longitude_lower, "$lte": longitude_upper},
                }
            }

            output["filters"] = filters

        print("[EmbeddingRetrieverInputHelper.run] output: " + json.dumps(output))

        return output, "output_1"

    def run_batch(self, query: str, **kwargs):
        # Insert code here to manipulate the input and produce an output dictionary
        pass
