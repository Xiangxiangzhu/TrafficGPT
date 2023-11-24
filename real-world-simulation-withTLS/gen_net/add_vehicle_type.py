import xml.etree.ElementTree as ET

# Load your XML file
tree = ET.parse('test4_2.rou.xml')
root = tree.getroot()

# Iterate over each vehicle and add the type element
for vehicle in root.findall('vehicle'):
    vehicle.set('type', 'type0')

# Save the modified XML back to a file
tree.write('test4_2.rou.xml')
