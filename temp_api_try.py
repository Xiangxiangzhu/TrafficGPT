import openai
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

inference_server_url = "http://localhost:8000/v1"
inference_key = "EMPTY"

openai.api_key = inference_key
openai.api_base = inference_server_url


vllm_model = openai.Model.list()["data"][0]["id"]

print("##########")
print(type(vllm_model))
print(vllm_model)
print("##########")



chat = ChatOpenAI(
    model=vllm_model,
    openai_api_key=inference_key,
    openai_api_base=inference_server_url,
    max_tokens=5,
    temperature=0,
)

messages = [
    SystemMessage(
        content="You are a helpful assistant that translates English to Italian."
    ),
    HumanMessage(
        content="Translate the following sentence from English to Italian: I love programming."
    ),
]
temp = chat(messages)

print("#########")
print(temp)
print("#########")

