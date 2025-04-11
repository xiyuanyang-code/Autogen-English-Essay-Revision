# Import required modules
import Requirement
import os
import json
from datetime import datetime
from typing import Dict, List
from pydantic import BaseModel
from autogen import (
    AssistantAgent,
    UserProxyAgent,
    GroupChat,
    GroupChatManager,
    config_list_from_json,
)

# Load requirements from external files
total_task = Requirement.total_task
requirements = Requirement.requirments

# Configure Pydantic model settings
BaseModel.model_config = {"protected_namespaces": ()}

class AutoGenArticleEditor:
    def __init__(self):
        # Initialize configuration
        self.config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST.json")
        self.original_article = self._read_file("Original.txt")
        self.total_task = total_task
        self.requirements = requirements
        self.log_dir = "log"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Initialize agents
        self.task_decomposer = None
        self.editor1 = None
        self.editor2 = None
        self.integrator = None
        self.user_proxy = None
        self.group_chat = None
        
        self._setup_agents()
    
    def _read_file(self, filename: str) -> str:
        """Read file content"""
        with open(filename, "r", encoding="utf-8") as f:
            return f.read().strip()
    
    def _write_file(self, filename: str, content: str):
        """Write content to file"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
    
    def _get_log_filename(self) -> str:
        """Generate timestamp-based log filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.log_dir, f"log_{timestamp}.txt")
    
    def _log_conversation(self, message: str):
        """Record conversation to log file"""
        log_file = self._get_log_filename()
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(message + "\n\n")
    
    def _print_progress(self, message: str):
        """Print progress message and log it"""
        print(f"[PROGRESS] {message}")
        self._log_conversation(f"[SYSTEM] {message}")

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
        self._print_progress("Starting article editing process...")
        self._print_progress(f"Original article length: {len(self.original_article.split())} words")
        
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
            self._write_file("Final.txt", final_text)
            self._print_progress(f"Final article saved to Final.txt. Length: {len(final_text.split())} words")
        else:
            self._print_progress("Process completed but final version format invalid. Check logs.")
        
        self._print_progress(f"Conversation log saved to {self._get_log_filename()}")

if __name__ == "__main__":
    editor = AutoGenArticleEditor()
    editor.run()