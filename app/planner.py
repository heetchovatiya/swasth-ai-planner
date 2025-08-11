import os
import json
import logging
from typing import TypedDict, List

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from user_profile import UserProfile
from tools import create_meal_plan, get_recipe_details

class AgentState(TypedDict):
    messages: List[BaseMessage]

def add_messages_to_state(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]:
    return left + right

class MealPlanner:
    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.2)
        tools = [create_meal_plan, get_recipe_details] 
        llm_with_tools = llm.bind_tools(tools)
        
        def agent(state: AgentState, config: RunnableConfig):
            profile = config["configurable"]["user_profile"]
            profile_summary = profile.get_summary()
            allergies = ", ".join(profile.allergies)
            # --- NEW: Get diet preference for the tool ---
            diet_preference = profile.diet_preference or "Any"

            # --- MODIFIED: Updated system prompt ---
            system_prompt = (
                "You are 'Swa-Swa', a friendly AI nutritionist. Your goal is to help the user.\n"
                "Based on the user's message, decide which tool is most appropriate.\n"
                "- If the user asks for a MEAL PLAN, ideas, or suggestions for what to eat, use the `create_meal_plan` tool. You must pass the user's request, their profile summary, allergies, and their diet_preference to this tool.\n"
                "- If the user asks about a SINGLE, SPECIFIC food item, how to make it, or for its details (e.g., 'tell me about dhokla'), use the `get_recipe_details` tool.\n"
                "- If it's just a greeting, respond conversationally without using a tool."
            )
            
            # --- MODIFIED: Pass diet_preference as necessary context for the tool call ---
            contextual_messages = state["messages"] + [
                HumanMessage(content=f"INTERNAL CONTEXT:\n- user_request: '{state['messages'][-1].content}'\n- profile_summary: '{profile_summary}'\n- allergies: '{allergies}'\n- diet_preference: '{diet_preference}'")
            ]
            
            messages = [SystemMessage(content=system_prompt)] + contextual_messages
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}

        tool_node = ToolNode(tools)

        def should_continue(state: AgentState):
            return "tools" if state["messages"][-1].tool_calls else END

        workflow = StateGraph(AgentState, {"messages": add_messages_to_state})
        workflow.add_node("agent", agent)
        workflow.add_node("tools", tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent") 
        
        return workflow.compile()

    def get_response(self, user_request: str, user_profile: UserProfile) -> dict:
        config = {"configurable": {"user_profile": user_profile}}
        final_state = self.graph.invoke(
            {"messages": [HumanMessage(content=user_request)]},
            config=config
        )
        
        last_tool_message = None
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, ToolMessage):
                last_tool_message = msg
                break
        
        if last_tool_message:
            tool_name = last_tool_message.name
            try:
                tool_output = json.loads(last_tool_message.content)
            except json.JSONDecodeError:
                return {"type": "message", "data": "I received an unexpected response. Please try again."}

            if "error" in tool_output:
                return {"type": "message", "data": tool_output["error"]}

            if tool_name == "create_meal_plan":
                return {"type": "plan", "data": tool_output}
            elif tool_name == "get_recipe_details":
                if tool_output.get('status') == "WEB_ONLY":
                    return {"type": "web_recipe", "data": tool_output}
                else: # FOUND_IN_DB or other cases
                    return {"type": "item_details", "data": tool_output.get('db_data', {})}
        
        # If no tool was called, return the conversational response
        return {"type": "message", "data": final_state["messages"][-1].content}