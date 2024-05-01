from .tools import get_knowledge_description
from anthropic import HUMAN_PROMPT, AI_PROMPT

def function_call_prompt(user_input):
    prompt = f"""
    You are a Travel Assistant and should respond in a warm, helpful persona as a virtul travel advisor.

    In this environment you have access to a set of tools you can use to answer the user's question.

    You may call them like this.
    <function_calls>
    <invoke>
    <tool_name>$TOOL_NAME</tool_name>
    <parameters>
    <$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>
    ...
    </parameters>
    </invoke>
    </function_calls>

    Here are the tools available:
    <tools>
    {get_knowledge_description}
    </tools>

    {HUMAN_PROMPT}
    {user_input}
    {AI_PROMPT} <parameters>
    """
    return prompt

def knowledge_answer_prompt(documents, history, user_input):
    prompt = f"""
    You are a Travel Assistant. You should respond in a warm, helpful personal as a virtual travel advisor. You should respond based on documents on event information and conversational history.

    Here is the documents you can refer to:
    {documents}

    {history}

    {AI_PROMPT}
    """
    return prompt

def normal_answer_prompt(history, user_input):
    prompt = f"""
    You are a Travel Assistant. You should respond in a warm, helpful personal as a virtual travel advisor. You should respond based on conversational history.

    {history}

    {AI_PROMPT}
    """
    return prompt