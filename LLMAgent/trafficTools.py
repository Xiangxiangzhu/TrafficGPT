import os
import sys
import pandas as pd
import traci
import json
from sumolib import checkBinary

from LLMAgent.buildGraph import Lane, Edge, Junction, Graph, build_graph
from LLMAgent.websterOptimize import Webster
from LLMAgent.vsl_control import VSL
from LLMAgent.plotIntersections import plot_intersections
from LLMAgent.plotHeatmap import plot_heatmap
from LLMAgent.readDump import read_last_dump


def prompts(name, description):
    def decorator(func):
        func.name = name
        func.description = description
        return func

    return decorator


class SimulationControl:
    def __init__(self, sumocfgfile: str, netfile: str, dumpfile: str, originalstatefile: str, tempstatefile: str,
                 figfolder: str) -> None:
        self.sumocfgfile = sumocfgfile
        self.netfile = netfile
        self.dumpfile = dumpfile
        self.originalstatefile = originalstatefile
        self.tempstatefile = tempstatefile
        self.figfolder = figfolder

    @prompts(name='Simulation Controller',
             description="""
             This tool is used to proceed and run the traffic simulation on SUMO. 
             The output will tell you whether you have finished this command successfully.
             This tool will also return the file path of a heat map of the road network as a supplementary information for you to provide the final answer. 
             The input should be a string, representing how many times have you called this tool, which shoule be a number greater than or equal to 0. 
             For example: if you never called this tool before and this is your first time calling this tool, the input should be 0; if you have called this tool twice, the imput should be 2.""")
    def inference(self, ordinal: str) -> str:
        ordinal_number = eval(ordinal)
        print("ordinal number is: ", ordinal_number)
        STEP = 600

        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            raise RuntimeError(
                "please declare environment variable 'SUMO_HOME'")

        if_show_gui = True

        if not if_show_gui:
            sumoBinary = checkBinary('sumo')
        else:
            sumoBinary = checkBinary('sumo-gui')

        traci.start([sumoBinary, "-c", self.sumocfgfile])
        # print('start reading state')
        # if ordinal_number > 0:
        #     traci.simulation.loadState(self.tempstatefile)
        # else:
        #     traci.simulation.loadState(self.originalstatefile)

        start_time = int(traci.simulation.getTime() / 1000)
        print('read state done!')
        for step in range(start_time, start_time + STEP):
            traci.simulationStep()

        traci.simulation.saveState(self.tempstatefile)

        traci.close()
        args = f'''-v -n {self.netfile} --measures speed,occupancy -i {self.dumpfile} \
            --default-width .5 --colormap RdYlGn  --max-width 3 --min-width .5 \
            --min-color-value 0 --max-color-value 50 --max-width-value 100 --min-width-value 0'''
        fig_path = plot_heatmap(self.figfolder, args)

        return f"You have successfully proceeded the traffic simulation on SUMO for 600 seconds. And your final answer should include this sentence without changing anything: the road network heat map is kept at: `{fig_path}`. Just answer the user, do not come up with any thought if the task is just run the simulation!!!"


class IntersectionTrafficSituation:
    def __init__(self, netfile: str, dumpfile: str) -> None:
        self.netfile = netfile
        self.dumpfile = dumpfile

    @prompts(name='Get Traffic Situation',
             description="""
            This tool is used to get the traffic situation of all the intersections or several target intersections in the simulation road network.
            The output will provide traffic status information of intersections in a tabular dataset.
            with various columns, such as Junction_id, speed_avg, volume_avg, and timeLoss_avg. Each row represents data for a specific junction. 
            Include the tabular dataset in markdown format directly in your final answer! Do not try to change anything including the format! 
            The input If you do not have information of any specific intersection ID and the human didn't specify to get information of all the intersections, the input should be a string: 'None', and the tool will give you an overview data for the final answer so you don't need more specific information about certain intersections. 
            If you have specific target intersection IDs, the input should be a comma seperated string, with each part representing a target intersection ID.
            Only if you can find a word 'all' in the human message, the input can be a string: 'All'. """)
    def inference(self, target: str) -> str:

        if 'None' in target.replace(' ', '') or 'All' in target.replace(' ', ''):
            # print('no target' + target.replace(' ', ''))
            have_target = False
            target_junction_id = []
        else:
            have_target = True
            target_junction_id = target.replace(' ', '').split(',')
            # print('target'+ str(target.replace(' ', '').split(',')))

        graph = build_graph(self.netfile)
        edgedata = read_last_dump(self.dumpfile)

        junction_list = graph.junctions
        junction_summary_table = pd.DataFrame(
            columns=['Junction_id', 'speed_avg', 'volume_avg', 'timeLoss_avg'])

        for j_id, junction in junction_list.items():
            if len(junction.inEdges) < 2:
                continue
            # print(j_id)
            # print("junction id is: ", j_id)
            # print("junction in edges have: ", len(junction.inEdges))

            if have_target and j_id not in target_junction_id:
                continue
            upstream_list = []
            for edge in junction.inEdges:
                upstream_list.append(edge.id[0])
            junction_data = edgedata[edgedata["edgeID"].isin(upstream_list)]
            speed_avg = (junction_data['speed'] * junction_data['left']).sum() / junction_data['left'].sum()
            waitingTime_avg = (junction_data['waitingTime'] * junction_data['left']).sum() / junction_data['left'].sum()
            timeLoss_avg = (junction_data['timeLoss'] * junction_data['left']).sum() / junction_data['left'].sum()
            volume_avg = (junction_data['speed'] * 3.6 * junction_data['density']).mean()
            junction_summary_dic = {"Junction_id": j_id, "speed_avg": speed_avg,
                                    "volume_avg": volume_avg, "timeLoss_avg": timeLoss_avg}
            new_row = pd.DataFrame(junction_summary_dic, index=[0])
            junction_summary_table = pd.concat([junction_summary_table, new_row], axis=0).reset_index(drop=True)
            # print(junction_summary_dic)
        sorted_table = junction_summary_table.sort_values(
            by=['speed_avg', 'volume_avg', 'timeLoss_avg'], ascending=[True, False, False]).reset_index(drop=True)
        # print(sorted_table)
        if 'None' in target.replace(' ', ''):
            msg = 'No specific target intersections. So, I can show you the overview by providing the traffic status of 5 intersections in the worst operating condition by default. Make sure you output the tabular content in markdown format into your final answer. \n'
            return msg + sorted_table.head().to_markdown()
        elif 'All' in target.replace(' ', ''):
            msg = 'Here are the traffic status of all intersections. Make sure you output the tabular content in markdown format into your final answer. \n'
            return msg + sorted_table.to_markdown()
        else:
            msg = 'Here are the traffic status of your targeted intersections. Make sure you output the tabular content in markdown format into your final answer. \n'
            return msg + sorted_table.to_markdown()


class IntersectionVisualization:
    def __init__(self, netfile: str, figfolder: str) -> None:
        self.netfile = netfile
        self.figfolder = figfolder

    @prompts(name='Visualize Intersections',
             description="""
            This tool is used to show the locations of several target intersections by visualize them on a map.
            Use this tool only if the user ask you to visualize an intersection!!!
            Use this tool more than others if the question is about locations of intersections.
            The output will tell you whether you have finished this command successfully.
            The input should be a comma seperated string, with each part representing a target intersection ID. """)
    def inference(self, target: str) -> str:
        target_junction_id = target.replace(' ', '').split(',')
        options = f'-n {self.netfile} --width 5 --edge-color #606060'

        fig_path = plot_intersections(
            target_junction_id,
            self.figfolder,
            options
        )

        return f"You have successfully visualized the location of intersection {target} on the following map. And your final answer should include this sentence without changing anything: The location of intersection {target} is kept at: `{fig_path}`."


class IntersectionSpeedOptimization:
    def __init__(self, netfile: str, configfile: str, routefile: str) -> None:
        self.netfile = netfile
        self.configfile = configfile
        self.routefile = routefile

    @prompts(name='Optimize Intersection Speed Limits',
             description="""
            This tool is used to optimize the speed limits of several target intersections in the simulation road network.
            Do not use this tool unless the human user asks to optimize intersections.
            Use this tool when human asks to optimize the speed limits of intersections.
            The output will tell you whether you have finished this command successfully.
            The input should be a comma seperated string, with each part representing a target intersection ID. """)
    def inference(self, target: str) -> str:
        if 'None' in target:
            return "Please provide the target intersection IDs."

        options = f'-n {self.netfile} -f {self.configfile} -r {self.routefile}'
        target_ID = target.replace(' ', '').split(',')

        optimizer = VSL(target_ID, options)
        optimizer.upgrade_vsl()

        return f"The speed limit optimization for the target intersection {target} has already been optimized successfully. The new speed limit has been written to the network file. You have finished optimize the speed limit of target intersection, just tell the user you have finished."


class IntersectionAnalysis:
    def __init__(self, netfile: str, configfile: str, routefile: str, interfile: str) -> None:
        self.netfile = netfile
        self.configfile = configfile
        self.routefile = routefile
        self.interfile = interfile

    @prompts(name='Analyze Intersection Structure',
             description="""
             This tool is used to get the intersection structure of several target intersections in the simulation road network.
             Use this tool when the human user asks to analyze the structure of intersections.
             Or use this tool when you need to optimize an intersection but still do not know the structure of this intersection.
             The output will provide you the intersection structure in json form including the relationship of incoming roads and outgoing roads, whether this intersection have speed limit control device or traffic signal control device. You should tell the user whether the intersection have speed limit control item or traffic signal control device, then print the json form of intersection info.
             Do not try to change anything of the json form intersection structure.
             The input If you do not have information of any specific intersection ID 
             and the human didn't specify to get information of all the intersections, the input should be a string: 'None', and the tool will give you an overview data for the final answer so you don't need more specific information about certain intersections. 
             The input should be a comma seperated string, with each part representing a target intersection ID.
             """)
    def inference(self, target: str) -> str:
        if 'None' in target:
            return "Please provide the target intersection IDs."

        options = f'-n {self.netfile} -f {self.configfile} -r {self.routefile} -i {self.interfile}'
        target_ID = target.replace(' ', '').split(',')
        if "ramp1In" not in target_ID:
            return "I haven't add the information of this intersection right now!"

        with open(self.interfile, 'r') as file:
            inter_struct = json.load(file)

        inter_struct_json = json.dumps(inter_struct['ramp1In'], indent=4)

        return f"Here are the structure of your targeted intersections. The results are show in json form:\n{inter_struct_json}\n"


class IntersectionOptimization:
    def __init__(self) -> None:
        pass

    @prompts(name='Optimize Intersection',
             description="""
             This tool is used to determine what kind of optimization you need to do.
             Use this tool when the user ask to optimize the intersection but do not specify to optimize the speed limit or optimize the traffic signal.
             This tool will help you determine what to do next, base on the previous results, if the intersection only have any variable speed limit control device, you need to use 'optimize the speed limit' tool; if the intersection only have traffic light, you need to use 'optimize the traffic signal' tool; only if the intersection have both variable speed limit control device and traffic light, you need to use both 'optimize the speed limit' tool and 'optimize the traffic signal' tool.
             You need to choose from 'optimize the speed limit', 'optimize the traffic signal' if you already have enough information or 'use the IntersectionAnalysis tool' to get more information to decide what to do next.
             The input should be a comma seperated string, with each part representing a target intersection ID.
             The output will ask you to determine what to do next, like 'optimize the speed limit', 'optimize the traffic signal' or 'use the IntersectionAnalysis tool'.
             """)
    def inference(self, target: str) -> str:
        if 'None' in target:
            return "Please provide the target intersection IDs."
        target_ID = target.replace(' ', '').split(',')
        return f"Based on the current information of intersection {target_ID}, you need to determine what to do next, if you already have enough information, then you need to need to choose from 'optimize the speed limit' or 'optimize the traffic signal' of intersection {target_ID}; If you do not have enough information to determine what to optimize, you need to use the 'IntersectionAnalysis' to get the intersection information."
        # return f"You need to determine what to optimize, you need to choose from 'optimize the speed limit' or 'optimize the traffic signal' of intersection {target_ID}. If you do not have enough information to determine what to optimize, you need to use the 'IntersectionAnalysis' to get the intersection information."
