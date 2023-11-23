from __future__ import absolute_import
from __future__ import print_function

import collections
import sys
import os
import sumolib
import xml.etree.ElementTree as ET


def getEdges(veh, net, routes):
    if isinstance(veh.route, str):
        edges = routes[veh.route]
    else:
        edges = veh.route[0].edges
    return [net.getEdge(e) for e in edges.split()]


def getRoutes(files):
    route_dict = {}
    for file in files:
        for route in sumolib.output.parse(file, 'route'):
            route_dict[route.id] = route.edges
    return route_dict


def getFlows(net, routeFiles, tlsList, begin, scale_fac, verbose, isSorted=False):
    tlsFlowsMap = {}
    end = begin + 3600
    for tls in tlsList:
        tlsFlowsMap[tls._id] = collections.defaultdict(
            lambda: collections.defaultdict(int))
    route_dict = getRoutes(routeFiles.split(','))
    for file in routeFiles.split(','):
        if verbose:
            print("parsing route file:", file)
        triggered = parsed = 0
        for veh in sumolib.output.parse(file, 'vehicle'):
            if veh.depart == "triggered":
                triggered += 1
                continue
            if sumolib.miscutils.parseTime(veh.depart) >= end:
                if isSorted:
                    break
                continue
            if sumolib.miscutils.parseTime(veh.depart) >= begin:
                edgeList = getEdges(veh, net, route_dict)
                for idx, edge in enumerate(edgeList):
                    tls = None if edge.getToNode().getType() in (
                        "rail_crossing", "rail_signal") else edge.getTLS()
                    if tls and idx < len(edgeList) - 1:
                        # c: [[inLane, outLane, linkNo],[],..]
                        for c in tls.getConnections():
                            inEdge = c[0].getEdge()
                            outEdge = c[1].getEdge()
                            if inEdge == edge and outEdge == edgeList[idx + 1]:
                                pce = 1.
                                if veh.type == "bicycle":
                                    pce = 0.2
                                elif veh.type in ["moped", "motorcycle"]:
                                    pce = 0.5
                                elif veh.type in ["truck", "trailer", "bus", "coach"]:
                                    pce = 3.5
                                tlsFlowsMap[tls.getID()][inEdge.getID(
                                ) + " " + outEdge.getID()][c[2]] += pce
                                parsed += 1
        if triggered > 0:
            print("Warning: Ignored %s triggered vehicles in %s." %
                  (triggered, file))
        if parsed == 0:
            print("Warning: No vehicles parsed from %s." % file)
        elif verbose:
            print("Parsed %s vehicles from %s." % (parsed, file))
    # scale up flow
    if scale_fac != 1.:
        for t in tlsList:
            for subRoute in tlsFlowsMap[t.getID()]:
                for conn in tlsFlowsMap[t.getID()][subRoute]:
                    tlsFlowsMap[t.getID()][subRoute][conn] *= scale_fac

    # remove the doubled counts
    connFlowsMap = {}
    for t in tlsList:
        connFlowsMap[t.getID()] = {}
        for subRoute in tlsFlowsMap[t.getID()]:
            totalConns = len(tlsFlowsMap[t.getID()][subRoute])
            for conn in tlsFlowsMap[t.getID()][subRoute]:
                tlsFlowsMap[t.getID()][subRoute][conn] /= totalConns
                connFlowsMap[t.getID()][conn] = tlsFlowsMap[t.getID()
                ][subRoute][conn]
        # remove the redundant connection flows
        connFlowsMap = removeRedundantFlows(t, connFlowsMap)

    return connFlowsMap


def getEffectiveTlsList(tlsList, connFlowsMap, skipList, verbose, TARGET_ID):
    effectiveTlsList = []
    tlsList = [tl for tl in tlsList if tl._id not in skipList]
    for tl in tlsList:
        if tl._id not in TARGET_ID:
            continue
        if len(tl.getPrograms()) == 0:
            continue

        for program in tl.getPrograms().values():
            for phase in program.getPhases():
                if len(phase.state) > len(tl.getConnections()):
                    print("Warning: the number of unused states at TLS %s: %s (%s states, %s connections)" %
                          (tl.getID(), (len(phase.state) - len(tl.getConnections())),
                           len(phase.state), len(tl.getConnections())))
                    break

        for conn in connFlowsMap[tl.getID()]:
            if connFlowsMap[tl.getID()][conn] > 0:
                effectiveTlsList.append(tl)
                break
    return effectiveTlsList


def removeRedundantFlows(t, connFlowsMap):
    # if two or more intersections share the lane-lane connection indices together,
    # the redundant connection flows will set to zero.
    connsList = t.getConnections()
    connsList = sorted(connsList, key=lambda connsList: connsList[2])
    redundantConnsList = []
    identical = True
    for c1 in connsList:
        for c2 in connsList:
            if c1[2] != c2[2]:
                if c1[1]._edge == c2[0]._edge:
                    identical = identityCheck(
                        c1[0]._edge, c2[0]._edge._incoming, identical)
                    if identical:
                        for toEdge in c2[0]._edge._outgoing:
                            for c in c2[0]._edge._outgoing[toEdge]:
                                if c._tlLink not in redundantConnsList:
                                    redundantConnsList.append(c._tlLink)
                    else:
                        for conn_1 in c1[0]._edge._outgoing[c2[0]._edge]:
                            if conn_1._direction == 's':
                                for toEdge in c2[0]._edge._outgoing:
                                    for conn_2 in c2[0]._edge._outgoing[toEdge]:
                                        if conn_2._tlLink not in redundantConnsList:
                                            redundantConnsList.append(
                                                conn_2._tlLink)
    for conn in redundantConnsList:
        if conn in connFlowsMap[t._id]:
            connFlowsMap[t._id][conn] = 0.
    return connFlowsMap


def identityCheck(e1, incomingLinks, identical):
    for i in incomingLinks:
        if i != e1:
            identical = False
            break
    return identical


def getLaneGroupFlows(tl, connFlowsMap, phases, greenFilter, multiOwnGreenMap, getmultiOwnGreen, options):
    connsList = tl.getConnections()
    groupFlowsMap = {}  # i(phase): duration, laneGroup1, laneGroup2, ...
    # tls-linkIndex: connsList[i][2]
    connsList = sorted(connsList, key=lambda connsList: connsList[2])
    aktiveLinkIndices = set()

    # get acktive link indices that used in the current TLS plan
    # the connections with internal links for walking areas and crossings are also considered
    for conn in connsList:
        for toEdge in conn[0]._edge._outgoing:
            for c in conn[0]._edge._outgoing[toEdge]:
                if c._tlLink >= 0 and toEdge._function not in ["crossing", "walkingarea", "internal"]:
                    aktiveLinkIndices.add(c._tlLink)

    # check if there are shared lane groups, i.e. some lane groups have only "g" (no "G")
    ownGreenConnsList = []  # connections with major green
    for i, p in enumerate(phases):
        # j is the linkIndex
        for j, control in enumerate(p.state):
            if control == "G" and j in aktiveLinkIndices:
                if j not in ownGreenConnsList:
                    ownGreenConnsList.append(j)
                elif not getmultiOwnGreen:  # j could be put more than once in the map
                    multiOwnGreenMap[tl._id].append(j)
    if options.verbose:
        if multiOwnGreenMap[tl._id]:
            print('TLS: %s --> the tl-indices with more than one major-green:%s' %
                  (tl._id, multiOwnGreenMap[tl._id]))
    yellowRedTime = 0
    greenTime = 0
    currentLength = 0
    phaseLaneIndexMap = collections.defaultdict(list)

    for i, p in enumerate(phases):
        currentLength += p.duration
        if 'G' in p.state and 'y' not in p.state and p.duration >= greenFilter:
            greenTime += p.duration
            groupFlowsMap[i] = [p.duration]
            groupFlows = 0
            laneIndexList = []
            exEdge = None
            for j, control in enumerate(p.state):
                if j in aktiveLinkIndices:
                    inEdge = connsList[j][0]._edge._id
                    multiOwnGreenFactor = 1
                    multiOwnGreenFactor += multiOwnGreenMap[tl._id].count(
                        j)
                    processed = False
                    if not exEdge:
                        exEdge = inEdge
                    # protected green directly after major green for the same edge
                    if ((inEdge == exEdge) and ((control == 'G') or (control == 'g' and j not in ownGreenConnsList))):
                        if j in connFlowsMap[tl._id]:
                            # if a connection flow has more than one major green,
                            # the flow is regularly distributed in each "major green"
                            groupFlows += connFlowsMap[tl._id][j] / \
                                          float(multiOwnGreenFactor)

                        if connsList[j][0].getIndex() not in laneIndexList:
                            laneIndexList.append(
                                connsList[j][0].getIndex())
                        processed = True

                    # fromEdge is different from the previous one or the last state
                    if exEdge != inEdge or j == len(p.state) - 1:
                        # save the data of the previous group
                        if laneIndexList:
                            phaseLaneIndexMap[i].append(laneIndexList)
                            groupFlowsMap[i].append(groupFlows)
                            # reset
                            laneIndexList = []
                            groupFlows = 0
                            if (j == len(p.state) - 1) and processed:
                                break

                        if control == "G":
                            if connsList[j][0].getIndex() not in laneIndexList:
                                laneIndexList.append(
                                    connsList[j][0].getIndex())
                            if j in connFlowsMap[tl._id]:  # only flows > 0
                                groupFlows += connFlowsMap[tl._id][j] / \
                                              float(multiOwnGreenFactor)
                        elif control == 'g' and j not in ownGreenConnsList:
                            if connsList[j][0].getIndex() not in laneIndexList:
                                laneIndexList.append(
                                    connsList[j][0].getIndex())
                            if j in connFlowsMap[tl._id]:  # only flows > 0
                                groupFlows += connFlowsMap[tl._id][j] / \
                                              float(multiOwnGreenFactor)

                        if (j == len(p.state) - 1) and laneIndexList:
                            phaseLaneIndexMap[i].append(laneIndexList)
                            groupFlowsMap[i].append(groupFlows)

                            # reset
                            laneIndexList = []
                            groupFlows = 0

                    exEdge = inEdge
        elif 'G' not in p.state and 'g' in p.state and 'y' not in p.state and 'r' not in p.state:
            print("Check: only g for all connections:%s in phase %s" %
                  (tl._id, i))
        elif ('G' not in p.state and 'g' not in p.state) or ('G' not in p.state and 'y' in p.state and 'r' in p.state):
            yellowRedTime += int(p.duration)
        if options.verbose and i in groupFlowsMap:
            print("phase: %s" % i)
            print("group flows: %s" % groupFlowsMap[i])
            print("The used lanes: %s" % phaseLaneIndexMap[i])
    if options.verbose:
        print("the current cycle length:%s sec" % currentLength)
    return groupFlowsMap, phaseLaneIndexMap, currentLength, multiOwnGreenMap, getmultiOwnGreen


def getMaxOptimizedCycle(groupFlowsMap, phaseLaneIndexMap, currentLength, cycleList, multiOwnGreenMap, options):
    lostTime = len(groupFlowsMap) * options.losttime + options.allred
    satFlows = 3600. / options.satheadway
    # calculate the critical flow ratios and the respective sum
    criticalFlowRateMap = {}
    for i in groupFlowsMap:  # [duration. groupFlow1, groupFlow2...]
        criticalFlowRateMap[i] = 0.
        maxFlow = 0
        index = None
        if len(groupFlowsMap[i][1:]) > 0:
            for j, f in enumerate(groupFlowsMap[i][1:]):
                if f >= maxFlow:
                    maxFlow = f
                    index = j
            criticalFlowRateMap[i] = (
                                             maxFlow / float((len(phaseLaneIndexMap[i][index])))) / satFlows
        else:
            criticalFlowRateMap[i] = 0.
    sumCriticalFlows = sum(criticalFlowRateMap.values())

    if options.existcycle:
        optCycle = currentLength
    elif sumCriticalFlows >= 1.:
        optCycle = options.maxcycle
        if options.verbose:
            print("Warning: the sum of the critical flows >= 1:%s" %
                  sumCriticalFlows)
    else:
        optCycle = int(
            round((1.5 * lostTime + 5.) / (1. - sumCriticalFlows)))

    if not options.existcycle and optCycle < options.mincycle:
        optCycle = options.mincycle
    elif not options.existcycle and optCycle > options.maxcycle:
        optCycle = options.maxcycle

    cycleList.append(optCycle)

    return cycleList


def optimizeGreenTime(tl, groupFlowsMap, phaseLaneIndexMap, currentLength, multiOwnGreenMap, options):
    lostTime = len(groupFlowsMap) * options.losttime + options.allred
    satFlows = 3600. / options.satheadway
    # calculate the critical flow ratios and the respective sum
    criticalFlowRateMap = {}
    for i in groupFlowsMap:  # [duration. groupFlow1, groupFlow2...]
        criticalFlowRateMap[i] = 0.
        maxFlow = 0
        index = None
        if len(groupFlowsMap[i][1:]) > 0:
            for j, f in enumerate(groupFlowsMap[i][1:]):
                if f >= maxFlow:
                    maxFlow = f
                    index = j
            criticalFlowRateMap[i] = (
                                             maxFlow / float((len(phaseLaneIndexMap[i][index])))) / satFlows
        else:
            criticalFlowRateMap[i] = 0.
    sumCriticalFlows = sum(criticalFlowRateMap.values())
    if options.write_critical_flows:
        print(tl.getID(), criticalFlowRateMap)
        print('sum of the critical flow ratios: ', sumCriticalFlows)

    if options.existcycle:
        optCycle = currentLength
    elif sumCriticalFlows >= 1.:
        optCycle = options.maxcycle
        if options.verbose:
            print("Warning: the sum of the critical flows >= 1:%s" %
                  sumCriticalFlows)
            print(
                'Warning: the maximal cycle defined in the option will be used as the optimal cycle.')
    else:
        optCycle = int(
            round((1.5 * lostTime + 5.) / (1. - sumCriticalFlows)))

    if not options.existcycle and optCycle < options.mincycle:
        optCycle = options.mincycle
    elif not options.existcycle and optCycle > options.maxcycle:
        optCycle = options.maxcycle

    # calculate the green time for each critical group
    effGreenTime = optCycle - lostTime
    totalLength = len(groupFlowsMap) * options.yellowtime + options.allred
    minGreenPhasesList = []
    adjustGreenTimes = 0
    totalGreenTimes = 0
    subtotalGreenTimes = 0

    for i in criticalFlowRateMap:
        groupFlowsMap[i][0] = effGreenTime * \
                              (criticalFlowRateMap[i] / sum(criticalFlowRateMap.values())
                               ) - options.yellowtime + options.losttime
        groupFlowsMap[i][0] = int(round(groupFlowsMap[i][0]))
        totalGreenTimes += groupFlowsMap[i][0]
        if groupFlowsMap[i][0] < options.mingreen:
            groupFlowsMap[i][0] = options.mingreen
            minGreenPhasesList.append(i)
        else:
            subtotalGreenTimes += groupFlowsMap[i][0]
        totalLength += groupFlowsMap[i][0]

    # adjust the green times if minimal green times are applied for keeping the defined maximal cycle length.
    if minGreenPhasesList and totalLength > options.maxcycle and options.restrict:
        totalLength = len(groupFlowsMap) * \
                      options.yellowtime + options.allred
        if options.verbose:
            print("Re-allocate the green splits!")
        adjustGreenTimes = totalGreenTimes - \
                           len(minGreenPhasesList) * options.mingreen
        for i in groupFlowsMap:
            if i not in minGreenPhasesList:
                groupFlowsMap[i][0] = int(
                    round((groupFlowsMap[i][0] / float(subtotalGreenTimes)) * adjustGreenTimes))
            totalLength += groupFlowsMap[i][0]

    if options.unified_cycle and totalLength != optCycle:
        diff = optCycle - totalLength
        secs_to_distribute = [int(diff / abs(diff))] * abs(diff)
        keys = list(groupFlowsMap.keys())
        for i, s in enumerate(secs_to_distribute):
            groupFlowsMap[keys[i % len(groupFlowsMap)]][0] += s

    if options.verbose:
        totalLength = len(groupFlowsMap) * \
                      options.yellowtime + options.allred
        for i in groupFlowsMap:
            totalLength += groupFlowsMap[i][0]
            print("Green time for phase %s: %s" % (i, groupFlowsMap[i][0]))
        print("The optimal cycle length:%s\n" % totalLength)

    return groupFlowsMap


def checkRoutePeriod(routefiles, begin):
    scale_fac = 1.
    # find the last vehicle's departure time
    veh_starttime = -1.
    veh_endtime = -1.
    for file in routefiles.split(','):
        for veh in sumolib.output.parse(file, 'vehicle'):
            if veh.depart != "triggered":
                depart = float(veh.depart)
                if veh_starttime == -1.:
                    veh_starttime = veh_endtime = depart

                if veh_endtime < depart:
                    veh_endtime = depart
                if veh_starttime > depart:
                    veh_starttime = depart

    # check the begin time
    checkPeak = False
    if begin is None or begin < 0.:
        print("Warning: The begin time '%s' is not valid." % begin)
        begin = veh_starttime
        print(
            "Warning: The begin time is set to the first vehicle's departure time: %s." % veh_starttime)
        checkPeak = True

    # check how to process the flow
    end = begin + 3599.
    if veh_endtime < end:
        scale_fac += (end - veh_endtime) / 3600.
        print("Warning: The period is less than 1 hour. "
              "The flows will be proportionally scaled up to 1-hour flow with the scaling factor %s." % scale_fac)
    elif checkPeak and veh_endtime > end:
        begin, peakFlow = getPeakFlowBegin(
            routefiles, begin, veh_endtime)
        print("Warning: The period (begining with %s) with the peak flow (%s) is used." % (
            begin, peakFlow))

    return begin, scale_fac


def getPeakFlowBegin(routefiles, begin, veh_endtime):
    minuteFlowMap = {}
    end_intl = int(veh_endtime // 60.) + 1
    for n in range(0, end_intl + 1):
        minuteFlowMap[n] = 0.
    peak_begin = begin
    peakFlow = 0.

    for file in routefiles.split(','):
        for veh in sumolib.output.parse(file, 'vehicle'):
            if veh.depart != "triggered" and sumolib.miscutils.parseTime(veh.depart) >= begin:
                pce = 1.
                if veh.type == "bicycle":
                    pce = 0.2
                elif veh.type in ["moped", "motorcycle"]:
                    pce = 0.5
                elif veh.type in ["truck", "trailer", "bus", "coach"]:
                    pce = 3.5
                intl = int(float(veh.depart) // 60.)
                minuteFlowMap[intl] += pce

    for i in range(0, end_intl - 59):
        temp_sum = 0
        sub_end = i + 60
        if sub_end > end_intl:
            print(
                "Warning: The end time is larger and set to the last vehicle's departure time(%s)" % end_intl)
            sub_end = end_intl + 1
        for j in range(i, sub_end):
            temp_sum += minuteFlowMap[j]
        if temp_sum > peakFlow:
            peakFlow = temp_sum
            peak_begin = i

    return peak_begin, peakFlow


class VSL:
    """variable speed limit control"""

    def __init__(self, target_ID, args):
        """初始化options"""
        self.target_ID = target_ID
        self.options = self.get_options(args)

    def get_options(self, args=None):
        optParser = sumolib.options.ArgumentParser()
        optParser.add_option("-n", "--net-file", category="input", dest="netfile", required=True,
                             help="define the net file (mandatory)")
        optParser.add_option("-f", "--config-file", category="input", dest="configfile", required=True,
                             help="define the config file (mandatory)")
        optParser.add_option("-r", "--route-files", category="input", dest="routefiles", required=True,
                             help="define the route file separated by comma (mandatory)")
        optParser.add_option("-b", "--begin", category="time", dest="begin", type=float,
                             help="begin time of the optimization period with unit second (mandatory)")
        optParser.add_option("-v", "--verbose", category="processing", dest="verbose", action="store_true",
                             default=False, help="tell me what you are doing")
        return optParser.parse_args(args=args)

    def run_vsl(self):
        if not self.options.netfile or not self.options.routefiles:
            raise RuntimeError("Error: Either both the net file and the route file or one of them are/is missing.")

        # check the period of the given route files, and find the peak-flow period if necessary

        def update_lane_speed(file_name: str, edge_id: str, new_speed: float):
            # Parse the XML file
            tree = ET.parse(file_name)
            root = tree.getroot()

            # Find the edge with the specified id and update the speed of lane with index 0
            for edge in root.findall(f'.//edge[@id="{edge_id}"]'):
                for lane in edge.findall('lane[@index="0"]'):
                    lane.set('speed', str(new_speed))
                for lane in edge.findall('lane[@index="1"]'):
                    lane.set('speed', str(new_speed))

            # Save the modified XML to a file named 'aa.xml'
            tree.write(
                '/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/gen_net/test4_1.net.xml',
                encoding='utf-8', xml_declaration=True)

        # Example usage:
        update_lane_speed(self.options.netfile, '29496808#1.959', 3.0)
