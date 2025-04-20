import os
import dotenv
import construct
import prompts

from pydantic import BaseModel
from typing import List
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType, TaskType, RoleType
from camel.configs import ChatGPTConfig
from camel.agents import ChatAgent, TaskPlannerAgent
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.societies import RolePlaying
from camel.societies.workforce import Workforce
from camel.toolkits import ThinkingToolkit, SearchToolkit, HumanToolkit, FunctionTool
from camel.tasks import Task


# Load api key and url
dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("BASE_URL")

# define prompts and models
system_message = prompts.total_system_message
base_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig().as_dict(),
    api_key=OPENAI_API_KEY,
    url=BASE_URL,
)

# For the settings of base agents
single_agent = ChatAgent(
    system_message=system_message,
    model=base_model,
    message_window_size=10,
    tools=[
        # *SearchToolkit().get_tools(),
        # *ThinkingToolkit().get_tools(),
        # *HumanToolkit().get_tools(),
    ],
)

# Add several prompts for the single agents
topic_message = BaseMessage(
    role_name="User",
    role_type=RoleType.USER,
    content=f"The text topic is {prompts.text_topic}",
    meta_dict={},
)

initial_reuqirements = BaseMessage(
    role_name="User",
    role_type=RoleType.USER,
    content=f"The Initial requirements are as follows: {prompts.requirements}",
    meta_dict={},
)

original_text = construct.read_file("Camel_demo/English-Essay-Revision/Original.txt")
# print(original_text)
original_passage = BaseMessage(
    role_name="User",
    role_type=RoleType.USER,
    content=f"""the text of my argumentative essay is given below:\n\n\
        =================ORIGINAL passage BEGIN================\n\
            {original_text}\n\
        =================ORIGINAL passage END================
            """,
    meta_dict={},
)


class ResponseFormat(BaseModel):
    whole_text_after_edited: str
    Modification_summary: str


max_length = 250


# Act for the single agents
def run_single_agents():
    single_agent.record_message(initial_reuqirements)
    single_agent.record_message(topic_message)
    single_agent.record_message(original_passage)
    UserMessage = "Start revising the essay and generate a report"
    response = single_agent.step(UserMessage, response_format=ResponseFormat)
    # print(type(response))
    print(response.msgs[0].content)


# Define the Agentic workflow
work_force = Workforce(
    description="Automated English Essay Revision",
    new_worker_agent_kwargs={"model": base_model},
    coordinator_agent_kwargs={"model": base_model},
    task_agent_kwargs={"model": base_model},
)

# Define worker
# search_tool = FunctionTool(SearchToolkit.search_baidu(max_results=6))

# search_agent = ChatAgent(
#     system_message=system_message
#     + "For your specified task, you need to search the web for more information and provide them with the downstream agents",
#     model=base_model,
#     message_window_size=10,
#     tools=[search_tool],
# )

task_agent = ChatAgent(
    model=base_model,
    system_message=f"""
            The total task: {prompts.total_prompt}
            

            You are an expert in task decomposition. Your responsibilities:
            1. Analyze requirements: \n{prompts.requirements}\n
            2. Read the original passage, the passage is shown below\n:{original_text}\n
            3. You need to provide a more specific modification plan based on the requirements, 
            combining it with the original text, but without making specific changes. 
            For example: the relative clause in a certain sentence does not conform to specific grammatical rules and needs to be revised; 
            or the word choice in a certain part is too simplistic and needs to be optimized; 
            or the logic in a certain section needs to be further strengthened.
            4. More detailed modification requirements are needed, covering all aspects such as grammar, logic, word choice, and sentence structure.
            

            Response format:
            ### Specific Requirements
            [Return specified and modified requirements]

            """,
    message_window_size=10,
)

conservative_agent = ChatAgent(
    system_message=f"""

            {prompts.total_prompt}\n
            You will receive the specific requirements from the previous agents.\n
            The original text: {original_text}\n

            Attention!!!, particularly for you, as a more meticulous writer, your revisions should focus on the logic and organizational structure of the article, making it more coherent.
            
            Provide complete edited text and brief feedback (<50 words).
            Ensure native English usage and <{1.2 * max_length} word limit.
            
            Response format:
            ### Version ###
            [full edited text]
            
            ### Feedback ###
            [comments]
            """,
    model=base_model,
    message_window_size=10,
)

imaginative_agent = ChatAgent(
    system_message=f"""

            {prompts.total_prompt}\n
            You will receive the specific requirements from the previous agents.\n
            The original text: {original_text}\n

            Attention!!!, particularly for you, as a more meticulous writer, your revisions should focus on the logic and organizational structure of the article, making it more coherent.
            
            Provide complete edited text and brief feedback (<50 words).
            Ensure native English usage and <{1.2 * max_length} word limit.
            
            Response format:
            ### Version ###
            [full edited text]
    
            ### Feedback ###
            [comments]
            """,
    model=base_model,
    message_window_size=10,
)

integrator_agent = ChatAgent(
    system_message=f"""
            {prompts.total_prompt}\n
            You are the final integrator. Your responsibilities:
            1.You will receive three documents: the original article and two modified articles by two editors(one conservative and one creative)
            2.You need to take an overall perspective to compare the highlights of the two revised drafts against the original manuscript, and integrate the two articles, taking the strengths from each.
            3.!!Attention: You need to make sure your passage (after integrated) is no more than {1.5 * max_length} words.

            Response format:
            ### Final Version ###
            [text after integrated]
            
            ### Feedback ###
            [comments]
            """,
    model=base_model,
    message_window_size=10,
)

reporter_agent = ChatAgent(
    system_message=f"""
            {prompts.total_prompt},\n
            The original article is: {original_text}\n
            You are the final reporter, you will receive the final scripts modified, and make the last modifications:
            1. Make sure all your modifications adhere to the English Usage.
            2. Make sure the total length is no more than {max_length} words.
            
            Response format:
            ### Final version ###
            [final text]

            ### Feedback ###
            In this section, you are asked to generate a report about the modifications between the final version and the original version.
            """,
    model=base_model,
    message_window_size=10,
)

# Add WorkNode
work_force.add_single_agent_worker(
    description="Specify the task into subtasks",
    worker=task_agent,
).add_single_agent_worker(
    description="Make some modifications conservatively",
    worker=conservative_agent,
).add_single_agent_worker(
    description="Make some modifications imaginaively",
    worker=imaginative_agent,
).add_single_agent_worker(
    description="Integrate all the modifications",
    worker=integrator_agent,
).add_single_agent_worker(
    description="Generate the modifications report",
    worker=reporter_agent,
)

def run_workforce():
    task = Task(
        content=prompts.total_task,
        id = "0",
    )

    task = work_force.process_task(task)
    print(task.result)

if __name__ == "__main__":
    # If you want to use the single agent...
    run_single_agents()

    # If you want to use the multiagent framework
    run_workforce()

    
