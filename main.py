# Import required modules
from prompts import * 
from construct import *
from pydantic import BaseModel
from autogen import (
    AssistantAgent,
    UserProxyAgent,
    GroupChat,
    GroupChatManager,
    config_list_from_json,
)


'''
The intuition:
    1.We use for agents to make the revision task:
        1.Task decomposer:
            Given the original text and the original prompts, and let the agent to generate the promblems and issues strictly (no actual revisions will be made during this process.)
            The agent needs to return a simple report pointing several problems that the passage have faced.
        2.Editor Conservative and Editor Creative
            Where actual revisions take place. Set different temperatures for the "imagination"
            !The two editor will not influence each other, works parallelly.
        3.integrator: 
            Integrate for both two passage to make better improvements
            To make better improvements and allow more diversity, we allow the maxlength of current passage is the 1.5*max_length
        4.Reporter
            Check the format and restrict words.( \le maxlength)

    2.For the first version, we will just make one round conversation:
        User -> Task decomposer -> Editor Conservative  -> Integrator -> Reporter
                                -> Editor Creative      ->
    3. To avoid information loss, we will pass total_prompt and the original text for all agents.
'''

# Configure Pydantic model settings
BaseModel.model_config = {"protected_namespaces": ()}

class AutoGenArticleEditor:
    def __init__(self):
        create_dirs()

        # Initialize configuration
        self.config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST.json")
        self.original_article = read_file(file_name)
        self.log_filename = get_log_filename("log")
        self.max_length = 200
        
        # Initialize agents
        self.task_decomposer = None
        self.editor1 = None
        self.editor2 = None
        self.integrator = None
        self.reporter = None
        self.user_proxy = None
        self.group_chat = None
        self._setup_agents()
    

    def _setup_agents(self):
        """Configure all agent instances"""
        
        # User proxy agent (human admin simulator)
        self.user_proxy = UserProxyAgent(
            name="Admin",
            system_message="A human admin who provides the article and requirements.",
            human_input_mode="NEVER",
            code_execution_config=False,
            default_auto_reply="Task received. Passing to the team...",
            max_consecutive_auto_reply=1,
        )
        
        # Task decomposition agent
        self.task_decomposer = AssistantAgent(
            name="Task_Decomposer",
            system_message=f"""
            The total task: {self.total_task}

            You are an expert in task decomposition. Your responsibilities:
            1. Analyze requirements: {self.requirements}
            2. Break down editing task into subtasks
            3. Assign subtasks to editing team
            
            Provide subtasks in numbered list format.
            """,
            llm_config={
                "config_list": self.config_list,
                "temperature": 0.3,  # Low randomness for accurate task breakdown
            },
        )
        
        # Conservative editor agent
        self.editor1 = AssistantAgent(
            name="Editor_Conservative",
            system_message="""
            You are a conservative editor specializing in:
            - Grammar accuracy
            - Precise word choice
            - Formal tone
            - Citation consistency
            
            Provide complete edited text and brief feedback (<50 words).
            Ensure native English usage and <250 word limit.
            
            Response format:
            ### Version ###
            [full edited text]
            
            ### Feedback ###
            [comments]
            """,
            llm_config={
                "config_list": self.config_list,
                "temperature": 0.3,  # Low randomness for conservative edits
            },
        )
        
        # Creative editor agent
        self.editor2 = AssistantAgent(
            name="Editor_Creative",
            system_message="""
            You are a creative editor focusing on:
            - Flow and readability
            - Argument clarity
            - Structural improvements
            - Engagement
            
            Provide complete edited text and brief feedback (<50 words).
            Ensure native English usage and <250 word limit.
            
            Response format:
            ### Version ###
            [full edited text]
            
            ### Feedback ###
            [comments]
            """,
            llm_config={
                "config_list": self.config_list,
                "temperature": 0.7,  # Higher randomness for creative edits
            },
        )
        
        # Integration agent
        self.integrator = AssistantAgent(
            name="Integrator",
            system_message=f"""
            You are the final integrator. Your responsibilities:
            1. Evaluate all editor suggestions
            2. Incorporate changes based on: {self.requirements}
            3. Produce final version
            
            Response format:
            ### Final Version ###
            [text]
            
            ### Feedback ###
            [comments]
            """,
            llm_config={
                "config_list": self.config_list,
                "temperature": 0.5,  # Balanced randomness
            },
        )
        
        # Configure group chat with manual speaker selection
        self.group_chat = GroupChat(
            agents=[
                self.user_proxy,
                self.task_decomposer,
                self.editor1,
                self.editor2,
                self.integrator,
            ],
            messages=[],
            max_round=20,
            speaker_selection_method="manual",  # Manual control for sequential workflow
        )
        
        # Group chat manager
        self.manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config={"config_list": self.config_list}
        )
    
    def run(self):
        """Execute the editing workflow"""
        print_progress("Starting article editing process...")
        
        # Initiate the chat workflow
        self.user_proxy.initiate_chat(
            self.manager,
            message=f"""
            Article to edit:
            {self.original_article}
            
            Requirements:
            {self.requirements}
            
            Please begin editing process.
            """,
        )
        
        # Process final output
        final_message = self.group_chat.messages[-1]["content"]
        if "### Final Version ###" in final_message:
            final_text = final_message.split("### Final Version ###")[1].split("### Feedback ###")[0].strip()
            write_file("Final.txt", final_text)
            print_progress(f"Final article saved to Final.txt.")
        else:
            print_progress("Process completed but final version format invalid. Check logs.")
        
        print_progress(f"Conversation log saved to {self.log_filename}")

if __name__ == "__main__":
    editor = AutoGenArticleEditor()
    editor.run()