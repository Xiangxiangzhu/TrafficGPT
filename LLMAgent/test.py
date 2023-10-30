from trafficTools import intersectionVisulization

if __name__ == '__main__':
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
