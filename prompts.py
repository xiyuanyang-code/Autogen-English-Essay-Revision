"""
Author: Xiyuan Yang   xiyuan_yang@outlook.com
Date: 2025-04-11 14:59:16
LastEditors: Xiyuan Yang   xiyuan_yang@outlook.com
LastEditTime: 2025-04-12 23:39:41
FilePath: /Autogen-English-Essay/Requirement.py
Description: All the prompot will be stored and written here.
Do you code and make progress today?
Copyright (c) 2025 by Xiyuan Yang, All Rights Reserved.
"""

# System message, for all agents
total_system_message = "You are an expert at writing argumentative essay of English and make revisions, \
                        make sure all your generations and modifications are logical and aligns with the habits of native English speakers.\
                        Think twice before you give your final answers."

text_topic = "Beyond internal evaluation systems, should students be allowed to post public comments and ratings about their teachers online, like people do with restaurant reviews?"

requirements = "1.Check the spelling and grammar mistakes for the whole passage.\
    2.Organize the article's ideas to make the language more fluid, the arguments more distinct, and the sentence structures more complex. But remember don’t make too many corrections! Just do some essential optimization.\
    3.Ensure that all of your modifications adhere to the conventions of English usage\
    4.Generate a report regarding your modification, including the ultimate modified passage and the detailed descriptions.\
    Ensure that all of your modifications adhere to the conventions of English usage. "

specified_requirements = ""
# Wait after the task_decomposer finish

total_task = f"The total task for you to be solved is to modify an argumentative essay based on specific topic and instructions.\
             [topic]: {text_topic}\
             [requirments]: {requirements}."

# Thus this prompts will be passed to all agents.
total_prompt = f"{total_system_message}\n\
                 The topic of the essay is {text_topic}\n\
                 {total_task}\n\
                 Try your best!"
