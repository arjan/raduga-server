import json, re
data = json.loads(open(re.sub("\..*?$", ".json", __file__)).read())
