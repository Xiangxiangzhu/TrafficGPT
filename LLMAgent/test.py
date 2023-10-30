from trafficTools import intersectionVisulization, intersectionPerformance, simulationControl

test_visualization = False
test_performance = False
test_simulation = True

if __name__ == '__main__':
    if test_visualization:
        vision_agent = intersectionVisulization(
            netfile="/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/gen_net/test4.net.xml",
            figfolder="./fig1/"
        )
        vision_agent.inference(target="2287714189")
        # vision_agent.inference(target="5165545261")

        # vision_agent = intersectionVisulization(
        #     netfile="/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/xuancheng.net.xml",
        #     figfolder="./fig1/"
        # )
        # vision_agent.inference(target="4650")

    elif test_performance:
        # # intersectionPerformance(sumoNetFile, sumoEdgeDataFile)
        # perform_agent = intersectionPerformance(
        #     netfile="/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/gen_net/test4.net.xml",
        #     dumpfile="/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/gen_net/test4.net.xml"
        # )
        # perform_agent.inference(target="2287714189")

        perform_agent = intersectionPerformance(
            netfile="/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/xuancheng.net.xml",
            dumpfile="/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/edgedata.xml"
        )
        perform_agent.inference(target="4650")

    elif test_simulation:
        simulate_agent = simulationControl(
            sumocfgfile = None,
            netfile = None,
            dumpfile = None,
            originalstatefile = None,
            tempstatefile = None,
            figfolder = None
        )
