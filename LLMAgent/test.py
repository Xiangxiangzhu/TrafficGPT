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
        # simulate_agent = simulationControl(
        #     sumocfgfile='/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/xuancheng.sumocfg',
        #     netfile='/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/xuancheng.net.xml',
        #     dumpfile='/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/edgedata.xml',
        #     originalstatefile='/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/originalstate.xml',
        #     tempstatefile='/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/tempstate.xml',
        #     figfolder='/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/fig/'
        # )
        # simulate_agent.inference("0")
        print("3333333")
        simulate_agent = simulationControl(
            sumocfgfile='/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/gen_net/test4_1.sumocfg',
            netfile='/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/gen_net/test4_1.net.xml',
            dumpfile='/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/gen_net/edgedata.xml',
            originalstatefile='/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/gen_net/originalstate.xml',
            tempstatefile='/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/gen_net/tempstate.xml',
            figfolder='./fig1/'
        )
        simulate_agent.inference("0")
