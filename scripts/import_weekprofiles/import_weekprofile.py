import logging
import itertools
import json
import fhem

# Connect via HTTP, port 8083:
fh = fhem.Fhem("osmc", protocol="http", port=8083)

logging.basicConfig(level=logging.DEBUG)

PROFILE_JSON = "./scripts/import_weekprofiles/HeizungsProfile.json"

WEEKPROFILE_DEVICE = "HZ_Schedule"
TOPICS = ["Arbeit", "HomeOffice", "Aus"]
ROOMS = [
    "Arbeitszimmer",
    "Badezimmer",
    "Kinderzimmer",
    "Schlafzimmer",
    "Wohnzimmer"]

with open(PROFILE_JSON, encoding="utf8") as fop:
    data = json.load(fop)

# Create cartesian product between Topics & Rooms to generate
# all possible weekprofile topics
combinations = itertools.product(TOPICS, ROOMS)

for comb in combinations:
    topic = comb[0]
    room = comb[1]

    profile_name = f"{topic}:{room}"
    profile = str(data[profile_name])

    # Weekprofile jsons need a very specific format. Neither
    # space nor single quotes are allowed. Thus, replacing them.
    profile = profile.replace(" ", "").replace("'", "\"")

    profile_str = f"{profile_name} {profile}"

    command = f"set {WEEKPROFILE_DEVICE} profile_data {profile_str}"
    fh.send_cmd(command)

