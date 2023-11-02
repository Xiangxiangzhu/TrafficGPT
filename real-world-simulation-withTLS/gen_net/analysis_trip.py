import xml.etree.ElementTree as ET


def parse_rou_file(filename):
    tree = ET.parse(filename)
    root = tree.getroot()

    from_set = set()
    to_set = set()

    for trip in root.findall('trip'):
        from_set.add(trip.get('from'))
        to_set.add(trip.get('to'))

    return from_set, to_set


if __name__ == "__main__":
    filename = "trips.trips.xml"
    from_set, to_set = parse_rou_file(filename)

    for it in from_set:
        print("from ", it)

    for it in to_set:
        print("to ", it)

    # print("Unique 'from' parameters:", from_set)
    # print("Unique 'to' parameters:", to_set)
