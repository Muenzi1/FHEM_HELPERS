"""Script to web scrape DB departure data, create FHEM devices, update their 
data and create a new ReadingsGroup object as visual."""

from os import device_encoding
import re
import itertools
import json

import datetime as dt
import requests

from bs4 import BeautifulSoup
from bs4.element import NavigableString

from fhem import Fhem

# CONSTANTS ----------
with open("./parameters.jsonc", mode="r", encoding="utf8") as fopen:
    PARAMETERS = json.load(fopen)

NUMBER_CONNECTIONS = PARAMETERS["NUMBER_CONNECTIONS"]
PRODUCTS = PARAMETERS["PRODUCTS"]
BASE_URL = PARAMETERS["BASE_URL"]
STATIONS = PARAMETERS["STATIONS"]
DEPARTURE_DEVICE = PARAMETERS["DEVICE"]
HOST = PARAMETERS["HOST"]


def main():
    """Entry point."""

    fhem_session = Fhem(HOST, protocol="http", port=8083)

    for station in STATIONS.values():
        
        station_id = station["ID"]
        device_reading = station["READING"]

        departures = get_departures(station_id)

        update_attr_list(data=departures, fh=fhem_session)
        update_reading_list(data=departures, device_reading = device_reading, fh=fhem_session)

        # create_readingsGroup(data=departures, fh=fhem_session)


def get_departures(station_id: str) -> dict:
    """Scrapes departure data from DB Reiseauskunft request."""

    con_type = "dep"  # dep for departure, arr for arrival

    url = (
        f"{BASE_URL}?si={station_id}&bt={con_type}&p={PRODUCTS}&max={NUMBER_CONNECTIONS}"
        "&rt=1&use_realtime_filter=1&start=yes")

    response = requests.get(url)

    css_soup = BeautifulSoup(response.content, "html.parser")

    dict_connection = {}

    for dd, dep in enumerate(css_soup.find_all(True, {'class': ['sqdetailsDep trow']})):
        str_red = " ".join(
            [entry.text for entry in dep.find_all(class_="red")])

        list_bold = dep.find_all(class_="bold")
        list_delay_on_time = dep.find_all(class_="delayOnTime")

        list_dest = [
            re.findall(r"\n>>\n([\w|\s|\(|\)|,|\-)]+)\n", item)
            for item in dep.contents if isinstance(item, NavigableString)]

        destination = "".join(list(itertools.chain.from_iterable(list_dest)))
        list_track = [
            re.findall(r"\xa0\xa0([\w|\s|,|.)]+)", item)
            for item in dep.contents if isinstance(item, NavigableString)]

        track = "".join(list(itertools.chain.from_iterable(list_track)))

        train = list_bold[0].text
        train = re.sub(r"[\s]{1,4}", " ", train) # removes multiple whitespaces

        dep_time = dt.datetime.strptime(list_bold[1].text, "%H:%M")
        diff_to_dep_time = ( dep_time - (dt.datetime.now() - dt.datetime.today())).minute
        delay_time = list_delay_on_time[0].text if len(list_delay_on_time) > 0 else None

        if delay_time:
            delay_min = int(
                (dt.datetime.strptime(delay_time, "%H:%M") - dep_time).seconds / 60)
        else:
            delay_min = 0

        dict_connection[dd] = {
            "destination": destination,
            "track": track,
            "train": train,
            "departure": dep_time.strftime("%H:%M"),
            "delay": delay_min,
            "info": str_red,
            "con_list": [train, destination, track, dep_time.strftime("%H:%M")] 
        }

    dict_connection["type"] = con_type

    return dict_connection


def get_readings(data: dict) -> dict:
    """Returns data from data dictionary."""

    readings = {}
    con_type = data.get("type")

    for con_num, con in data.items():
        if con_num == "type":
            continue

        for key, value in con.items():
            name = f"{con_type}_{con_num}_{key}"
            readings[name] = value

    return readings


def update_reading_list(data: dict, device_reading: str, fh: Fhem) -> None:
    """Updates DEPARTURE_DEVICE readings."""

    con_list = []

    readings = get_readings(data)

    for reading, value in readings.items():
        if not reading.endswith("_con_list"):
            value = value if not value == "" else None
            command = f"setreading {DEPARTURE_DEVICE} {reading} {value}"
            fhem_msg = fh.send_cmd(command)
            if fhem_msg != b"":
                print(fhem_msg)

        else: 
            con_list.append(value)
        
    command = f"setreading {DEPARTURE_DEVICE} {device_reading} {con_list}".replace("'", "\"")
    fhem_msg = fh.send_cmd(command)
    if fhem_msg != b"":
        print(fhem_msg)


def get_attr_list(data: dict) -> str:
    """Returns attribute list from data dictionary."""

    attr_list = []
    con_type = data.get("type")

    for con_num, con in data.items():
        if con_num == "type":
            continue

        for key, _ in con.items():
            attr_name = f"{con_type}_{con_num}_{key}"
            attr_list.append(attr_name)

    attr_string = ", ".join(attr_list)

    return attr_string


def update_attr_list(data: dict, fh: Fhem) -> None:
    """Updates DEPARTURE_DEVICE readingList attribute."""

    attr_string = get_attr_list(data=data)

    command = f"attr {DEPARTURE_DEVICE} readingList {attr_string}"
    fhem_msg = fh.send_cmd(command)
    if fhem_msg != b"":
        print(fhem_msg)


def create_readingsgroup(data: dict, fh: Fhem) -> None:
    """Create the FHEM ReadingsGroup device as table visual."""
    command_header = (
        "define rg_departure readingsGroup "
        "<ID>,<Gl.>,<Richtung>,<Abfahrt>,<Delay>,<Info> \n")
    command_row = []

    con_type = data.get("type")

    for con_num, con in data.items():
        if con_num == "type":
            continue

        attr_list = []
        for key, _ in con.items():
            attr_name = f"{con_type}_{con_num}_{key}"
            attr_list.append(attr_name)

        attr_list = (
            attr_list[2],
            attr_list[1],
            attr_list[0],
            attr_list[3],
            attr_list[4],
            attr_list[5])

        attr_list = f"{DEPARTURE_DEVICE}:{','.join(attr_list)}"
        command_row.append(attr_list)

    command = command_header + r" \ \n".join(command_row)

    fhem_msg = fh.send_cmd(command)
    if fhem_msg != b"":
        print(fhem_msg)


if __name__ == "__main__":
    main()
