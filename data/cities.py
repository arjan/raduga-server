import json, os
data = json.loads(open(os.path.join(os.path.dirname(__file__), "cities.json")).read())
