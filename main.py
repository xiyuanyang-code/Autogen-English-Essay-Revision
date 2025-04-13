# Import required modules
from prompts import *
from construct import *
from autogen import (
    AssistantAgent,
    UserProxyAgent,
    GroupChat,
    GroupChatManager,
    config_list_from_json,
)


"""
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
"""

# Configure Pydantic model settings
# BaseModel.model_config = {"protected_namespaces": ()}


class AutoGenArticleEditor:
    def __init__(self):
        create_dirs("log")

        # Initialize configuration
        self.config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST.json")
        self.original_article = read_file()
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
            The total task: {total_prompt}
            

            You are an expert in task decomposition. Your responsibilities:
            1. Analyze requirements: \n{requirements}\n
            2. Read the original passage, the passage is shown below\n:{self.original_article}\n
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
            llm_config={
                "config_list": self.config_list,
                "temperature": 0.3,
            },
        )

        # Conservative editor agent
        self.editor1 = AssistantAgent(
            name="Editor_Conservative",
            system_message=f"""

            {total_prompt}\n
            You will receive the specific requirements from the previous agents.\n
            The original text: {self.original_article}\n

            Attention!!!, particularly for you, as a more meticulous writer, your revisions should focus on the logic and organizational structure of the article, making it more coherent.
            
            Provide complete edited text and brief feedback (<50 words).
            Ensure native English usage and <{1.2*self.max_length} word limit.
            
            Response format:
            ### Version ###
            [full edited text]
            
            ### Feedback ###
            [comments]
            """,
            llm_config={"config_list": self.config_list, "temperature": 0.2},
        )

        # Creative editor agent
        self.editor2 = AssistantAgent(
            name="Editor_Creative",
            system_message=f"""
            {total_prompt}\n
            For the specified requirements: {specified_requirements}\n
            The original text: {self.original_article}\n

            Attention!!!, Note that, particularly for you, as a free-spirited and imaginative writer, your revisions should focus on the innovative sentence structures and rhetorical techniques in the article, making it more creative and eye-catching.
            Provide complete edited text and brief feedback (<50 words).
            Ensure native English usage and <{1.2*self.max_length} word limit.
            
            Response format:
            ### Version ###
            [full edited text]
            
            ### Feedback ###
            [comments]
            """,
            llm_config={"config_list": self.config_list, "temperature": 0.8},
        )

        # Integration agent
        self.integrator = AssistantAgent(
            name="Integrator",
            system_message=f"""
            {total_prompt}\n
            You are the final integrator. Your responsibilities:
            1.You will receive three documents: the original article and two modified articles by two editors(one conservative and one creative)
            2.You need to take an overall perspective to compare the highlights of the two revised drafts against the original manuscript, and integrate the two articles, taking the strengths from each.
            3.!!Attention: You need to make sure your passage (after integrated) is no more than {1.5*self.max_length} words.

            Response format:
            ### Final Version ###
            [text after integrated]
            
            ### Feedback ###
            [comments]
            """,
            llm_config={
                "config_list": self.config_list,
                "temperature": 0.5,  # Balanced randomness
            },
        )

        self.reporter = AssistantAgent(
            name="Reporter",
            system_message=f"""
            {total_prompt},\n
            The original article is: {self.original_article}\n
            You are the final reporter, you will receive the final scripts modified, and make the last modifications:
            1. Make sure all your modifications adhere to the English Usage.
            2. Make sure the total length is no more than {self.max_length} words.
            
            Response format:
            ### Final version ###
            [final text]

            ### Feedback ###
            In this section, you are asked to generate a report about the modifications between the final version and the original version.
            """,
            llm_config={
                "config_list": self.config_list,
                "temperature": 0.1,
            },
        )

        # Configure group chat without custom_speaker_order
        self.group_chat = GroupChat(
            agents=[
                self.user_proxy,
                self.task_decomposer,
                self.editor1,
                self.editor2,
                self.integrator,
                self.reporter,
            ],
            messages=[],
            max_round=5,
            speaker_selection_method="round_robin",  
        )

        # Group chat manager
        self.manager = GroupChatManager(
            groupchat=self.group_chat, llm_config={"config_list": self.config_list}
        )

    def run(self):
        """Execute the editing workflow"""
        print_progress("Starting article editing process...")

        # Step 1: User proxy initiates the chat
        self.user_proxy.initiate_chat(
            self.manager,
            message=f"""
            Article to edit:
            {self.original_article}
            
            Requirements:
            {requirements}
            
            Please begin editing process.
            """,
        )

        # Step 2: Task decomposer processes the requirements
        self.manager.step("Task_Decomposer")

        # Step 3: Editors (Conservative and Creative) run in parallel
        self.manager.step(["Editor_Conservative", "Editor_Creative"])

        # Step 4: Integrator combines the outputs
        self.manager.step("Integrator")

        # Step 5: Reporter finalizes the output
        self.manager.step("Reporter")

        # Process final output
        final_message = self.group_chat.messages[-1]["content"]
        if "### Final Version ###" in final_message:
            final_text = (
                final_message.split("### Final Version ###")[1]
                .split("### Feedback ###")[0]
                .strip()
            )
            write_file("Final.txt", final_text)
            print_progress(f"Final article saved to Final.txt.")
        else:
            print_progress(
                "Process completed but final version format invalid. Check logs."
            )

        print_progress(f"Conversation log saved to {self.log_filename}")


if __name__ == "__main__":
    editor = AutoGenArticleEditor()
    editor.run()
