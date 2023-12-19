import os
import re
import yaml
from rich import print
# from langchain import OpenAI
from langchain.chat_models import AzureChatOpenAI, ChatOpenAI

from LLMAgent.ConversationBot import ConversationBot

from LLMAgent.trafficTools import (
    SimulationControl,
    IntersectionTrafficSituation,
    # intersectionSignalOptimization,
    IntersectionOptimization,
    IntersectionVisualization,
    IntersectionSpeedOptimization,
    IntersectionAnalysis
)

import gradio as gr
import openai.api_requestor

openai.api_requestor.TIMEOUT_SECS = 30

# ------------------------------------------------------------------------------
# --ZH 初始化 LLM
# --EN Initialize a LLM
OPENAI_CONFIG = yaml.load(open('config.yaml'), Loader=yaml.FullLoader)
if OPENAI_CONFIG['OPENAI_API_TYPE'] == 'azure':
    os.environ["OPENAI_API_TYPE"] = OPENAI_CONFIG['OPENAI_API_TYPE']
    os.environ["OPENAI_API_VERSION"] = OPENAI_CONFIG['AZURE_API_VERSION']
    os.environ["OPENAI_API_BASE"] = OPENAI_CONFIG['AZURE_API_BASE']
    os.environ["OPENAI_API_KEY"] = OPENAI_CONFIG['AZURE_API_KEY']
    llm = AzureChatOpenAI(
        deployment_name=OPENAI_CONFIG['AZURE_MODEL'],
        temperature=0,
        max_tokens=1024,
        request_timeout=60
    )
elif OPENAI_CONFIG['OPENAI_API_TYPE'] == 'openai':
    os.environ["OPENAI_API_KEY"] = OPENAI_CONFIG['OPENAI_KEY']
    if OPENAI_CONFIG['OPENAI_KEY'] == "EMPTY":
        import openai

        openai.api_key = OPENAI_CONFIG['OPENAI_KEY']
        openai.api_base = OPENAI_CONFIG['OPENAI_BASE']
        model_name = openai.Model.list()["data"][0]["id"]
    else:
        OPENAI_CONFIG['OPENAI_BASE'] = 'https://api.openai.com/v1'
        model_name = 'gpt-3.5-turbo-16k-0613'

    llm = ChatOpenAI(
        temperature=0,
        model_name=model_name,  # or any other model with 8k+ context
        openai_api_base=OPENAI_CONFIG['OPENAI_BASE'],
        openai_api_key=OPENAI_CONFIG['OPENAI_KEY'],
        max_tokens=1024,
        request_timeout=60
    )
else:
    llm = None

# ------------------------------------------------------------------------------
# --ZH 初始化工具
# --EN Initialize the tools

if not os.path.exists('fig/'):
    os.mkdir('fig/')

sumoCFGFile = './real-world-simulation-withTLS/gen_net/test4_1.sumocfg'
sumoNetFile = './real-world-simulation-withTLS/gen_net/test4_1.net.xml'
sumoRouFile = './real-world-simulation-withTLS/gen_net/test4_2.rou.xml'
sumoEdgeDataFile = './real-world-simulation-withTLS/gen_net/edgedata.xml'
sumoOriginalStateFile = './real-world-simulation-withTLS/gen_net/originalstate.xml'
sumoTempStateFile = './real-world-simulation-withTLS/gen_net/tempstate.xml'
sumoNewTLSFile = './real-world-simulation-withTLS/gen_net/newTLS.add.xml'
targetFilePath = './fig/'
sumoIntersectionDescription = '/Users/christtzm/tzm/PyWork/trans_llm/TrafficGPT/real-world-simulation-withTLS/gen_net/intersection_description.json'

toolModels = [
    SimulationControl(
        sumoCFGFile, sumoNetFile, sumoEdgeDataFile,
        sumoOriginalStateFile, sumoTempStateFile, targetFilePath
    ),
    IntersectionTrafficSituation(sumoNetFile, sumoEdgeDataFile),
    IntersectionVisualization(sumoNetFile, targetFilePath),
    IntersectionOptimization(),
    IntersectionSpeedOptimization(sumoNetFile, sumoCFGFile, sumoRouFile),
    IntersectionAnalysis(sumoNetFile, sumoCFGFile, sumoRouFile, sumoIntersectionDescription)
]

# ------------------------------------------------------------------------------
# --ZH 定义 prompts，催眠 LLM，让 LLM 了解工作内容，减少幻觉
# --EN Define prompts, hypnotize LLM, let LLM understand the work content
#      and reduce hallucinations
botPrefix = """
[WHO ARE YOU]
You are a AI to assist human with traffic simulation control, making traffic and transportation decisions, or providing traffic analysis reports. Although you have access to a set of tools, your abilities are not limited to the tools at your disposal
[YOUR ACTION GUILDLINES]
1. You need to determine whether the human message is a traffic simulation control command or a question before making any move. If it is a traffic simulation control command, just execute the command and don't do any further information analysis. If it is a question before making any move, just answer it using your own ability.
2. You need to remember the human message exactly. Your only purpose is to complete the task that is explicitly expressed in the human message. 
3. Whenever you are about to come up with a thought, recall the human message to check if you already have enough information for the final answer!!!! If so, you shouldn't infer or fabricate any more needs or questions based on your own ideas. 
4. Remember what tools you have used, DO NOT use the same tool repeatedly. Try to use the least amount of tools.
5. If you can not find any appropriate tool for your task, try to do it using your own ability and knowledge as a chat AI. 
6. When you encounter tabular content in Observation, make sure you output the tabular content in markdown format into your final answer.
7. When you realize that existing tools are not solving the problem at hand, you need to end your actions and ask the human for more information as your final answer.
8. Note that since you can not access to the simulation configuration, every simulation is identical. You are not doing the same thing when asked to run the simulation.
9. The most important thing is just follow the user's instruction, do not do anything the user do not asked to do.
[THINGS YOU CANNOT DO]
You are forbidden to fabricate any tool names. 
You are forbidden to fabricate any input parameters when calling tools!
[HOW TO GENERATE TRAFFIC REPORTS]
Act as a human. And provide as much information as possible, including file path and tabular datasets.
When human need to provide a report of the traffic situation of a road network, they usually start by observing the operation of the network, 
find a few intersections in the network that are in a poor operating condition, as well as their locations, try to optimize them, 
and evaluate which parameters have become better and which ones are worse after the optimization. And form a report of the complete thought process in markdown format.
For example:
Macroscopic traffic operations on the entire road network can be viewed on the basis of road network heatmaps: 'replace the correct filepath here'.
To be more specific, these 5 intersections are in the worst operation status.
|    |   Juction_id |   speed_avg |   volume_avg |   timeLoss_avg |
|---:|-------------:|------------:|-------------:|---------------:|
|  0 |         4605 |     8.02561 |       734.58 |        8155.83 |
|  1 |         4471 |     8.11299 |       797.92 |       16500.6  |
|  2 |         4493 |     8.36199 |       532.26 |        8801.71 |
|  3 |         4616 |     8.62853 |       898.08 |        5897.33 |
|  4 |         4645 |     9.38659 |       360.03 |       11689    |
the locations of these intersections are shown in the map: 'replace the correct filepath here'.
I tried to optimize the traffic signal shceme of them and run the simulation again.
The new traffic stauts of these 5 intersections are as follows:
|    |   Juction_id |   speed_avg |   volume_avg |   timeLoss_avg |
|---:|-------------:|------------:|-------------:|---------------:|
|  0 |         4605 |     5.02561 |      1734.58 |        9155.83 |
|  1 |         4471 |     5.11299 |      1797.92 |       17500.6  |
|  2 |         4493 |     5.36199 |      1532.26 |        9901.71 |
|  3 |         4616 |     5.62853 |      1898.08 |        6897.33 |
|  4 |         4645 |     5.38659 |      1360.03 |       13689    |
According to the data above, after optimization, Traffic volume has increased at these intersections, but average speeds have slowed and time loss have become greater.
"""

# ------------------------------------------------------------------------------
# --ZH 初始化对话模型
# --EN Initilize the ConversationBot
bot = ConversationBot(llm, toolModels, botPrefix, verbose=True)


# ------------------------------------------------------------------------------
# --ZH 设置 gradio 界面
# --EN Configure the grdio interface


def reset(chat_history: list, thoughts: str):
    chat_history = []
    thoughts = ""
    bot.agent_memory.clear()
    bot.ch.memory = [[]]
    return chat_history, thoughts


def respond(msg: str, chat_history: list, thoughts: str):
    res, cb = bot.dialogue(msg)
    regex = re.compile(r'`([^`]+)`')
    try:
        filenames = regex.findall(res)
    except AttributeError:
        filenames = None
    if filenames:
        chat_history += [(msg, None)]
        for fn in filenames:
            chat_history += [(None, (fn,))]
        chat_history += [(None, res)]
    else:
        chat_history += [(msg, res)]

    thoughts += f"\n>>> {msg}\n"
    for actionMemory in bot.ch.memory[-2]:
        thoughts += actionMemory
        thoughts += '\n'
    thoughts += f"<<< {res}\n"
    return "", chat_history, thoughts


with gr.Blocks(
        title="Demo Traffic Management Bot 哈哈哈", theme=gr.themes.Default(text_size=gr.themes.sizes.text_lg)
) as demo:
    with gr.Row(visible=True, variant="panel"):
        with gr.Column(visible=True, variant='default'):
            chatbot = gr.Chatbot(scale=2)

            with gr.Row():
                humanMsg = gr.Textbox(scale=2)
                submitBtn = gr.Button("提交", scale=1)
            clearBtn = gr.ClearButton()
            gr.Examples(
                label='一些提问示例:',
                examples=[
                    "Run the simulation",
                    "What's the most congested intersection?",
                    "How's the traffic for intersections? Show me the data in a table",
                    "Locate intersection [ID] on the map",
                    "Optimize the intersection [ID]"
                ],
                inputs=[humanMsg],
                # outputs=[humanMsg, chatbot],
                # fn=testFunc
            )
        ReActMsg = gr.Text(
            label="大模型应答思维链及行为链",
            interactive=False,
            lines=35
        )

    humanMsg.submit(
        respond,
        [humanMsg, chatbot, ReActMsg],
        [humanMsg, chatbot, ReActMsg]
    )
    submitBtn.click(
        respond,
        [humanMsg, chatbot, ReActMsg],
        [humanMsg, chatbot, ReActMsg]
    )
    clearBtn.click(reset, [chatbot, ReActMsg], [chatbot, ReActMsg])

if __name__ == "__main__":
    # demo.launch()
    demo.launch(share=True)
