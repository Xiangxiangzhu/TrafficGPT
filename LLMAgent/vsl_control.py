from __future__ import absolute_import
from __future__ import print_function

import collections
import sys
import os
import sumolib
import xml.etree.ElementTree as ET


class VSL:
    """variable speed limit control"""

    def __init__(self, target_ID, args):
        """初始化options"""
        self.target_ID = target_ID
        self.options = self.get_options(args)

    @staticmethod
    def get_options(args=None):
        opt_parser = sumolib.options.ArgumentParser()
        opt_parser.add_option("-n", "--net-file", category="input", dest="netfile", required=True,
                              help="define the net file (mandatory)")
        opt_parser.add_option("-f", "--config-file", category="input", dest="configfile", required=True,
                              help="define the config file (mandatory)")
        opt_parser.add_option("-r", "--route-files", category="input", dest="routefiles", required=True,
                              help="define the route file separated by comma (mandatory)")
        opt_parser.add_option("-b", "--begin", category="time", dest="begin", type=float,
                              help="begin time of the optimization period with unit second (mandatory)")
        opt_parser.add_option("-v", "--verbose", category="processing", dest="verbose", action="store_true",
                              default=False, help="tell me what you are doing")
        return opt_parser.parse_args(args=args)

    def upgrade_vsl(self):
        if not self.options.netfile or not self.options.routefiles:
            raise RuntimeError("Error: Either both the net file and the route file or one of them are/is missing.")

        # check the period of the given route files, and find the peak-flow period if necessary

        def update_lane_speed(file_name: str, edge_id: str, new_speed_0: float, new_speed_1: float, new_speed_2: float):
            # Parse the XML file
            tree = ET.parse(file_name)
            root = tree.getroot()

            # Find the edge with the specified id and update the speed of lane with index 0
            for edge in root.findall(f'.//edge[@id="{edge_id}"]'):
                for lane in edge.findall('lane[@index="0"]'):
                    lane.set('speed', str(new_speed_0))
                for lane in edge.findall('lane[@index="1"]'):
                    lane.set('speed', str(new_speed_1))
                for lane in edge.findall('lane[@index="2"]'):
                    lane.set('speed', str(new_speed_2))

            # Save the modified XML to a file named 'aa.xml'
            tree.write(
                '/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/gen_net/test4_1.net.xml',
                encoding='utf-8', xml_declaration=True)

        # Example usage:
        update_lane_speed(self.options.netfile, 'ramp1MergeFrom', 7.0, 10.0, 12.0)
