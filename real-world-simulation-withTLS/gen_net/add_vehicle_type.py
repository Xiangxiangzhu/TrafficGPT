import xml.etree.ElementTree as ET
import random

# Load your XML file
tree = ET.parse('test4_2.rou.xml')
root = tree.getroot()

# Iterate over each vehicle and add the type element
for vehicle in root.findall('vehicle'):
    random_number = random.randint(10, 16)
    # vehicle.set('type', 'type0')
    vehicle.set('departLane', "random")
    vehicle.set('departSpeed', str(random_number))

# Save the modified XML back to a file
tree.write('test4_2.rou.xml')
