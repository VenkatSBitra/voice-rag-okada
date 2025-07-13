import os
import pandas as pd
import sqlite3
from typing import TypedDict, Annotated, List, Union
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
import operator
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv
load_dotenv()


DB_PATH = "normalized_real_estate.db"

def get_db_schema(db_path: str) -> str:
    """Dynamically gets the schema of all tables in the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema_str = "Database schema:\n"
    for table_name in tables:
        table = table_name[0]
        schema_str += f"Table '{table}':\n"
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        for col in columns:
            schema_str += f"  - {col[1]} ({col[2]})\n" # col[1] is name, col[2] is type
            
    conn.close()
    return schema_str

@tool
def run_sql(query: str):
    """
    Runs a given SQL query on the 'real_estate.db' database and returns the result.
    If the query is invalid, it returns an error message.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query)
        # Check if this is a query that modifies the DB or fetches data
        if cursor.description:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = "Query executed successfully."
        conn.close()
        return result
    except Exception as e:
        return f"Error executing query: {e}"
    

# --- LANGGRAPH AGENT DEFINITION ---

# Define the state for our graph
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

# Define the nodes of the graph
def call_model(state: AgentState):
    """The primary node that calls the LLM. It decides whether to use a tool or respond."""
    messages = state['messages']
    # Add the database schema to the prompt for context
    db_schema = get_db_schema(DB_PATH)
    system_prompt = (
        "You are a helpful real estate data assistant. You have access to a SQLite database "
        "with the following schema:\n\n"
        f"{db_schema}\n\n"
        "Given a user's question, first determine the intent and context. Then, see if there is any"
        " need to use the SQL database. If so, you must first generate a syntactically correct SQL query "
        "to run against the database. Then, use the `run_sql` tool to execute it. "
        "Finally, use the result of the query to answer the user's question in plain English. "
        "If a query returns a large number of rows, summarize the result. "
        "Always provide the final answer based on the tool's output."
    )
    
    # Create a new list of messages with the system prompt
    messages_with_system_prompt = [HumanMessage(content=system_prompt)] + messages
    
    response = llm_with_tools.invoke(messages_with_system_prompt)
    return {"messages": [response]}

def call_tool(state: AgentState):
    """This node executes the tool call requested by the LLM."""
    last_message = state['messages'][-1] # This will be the AIMessage with tool_calls
    
    # Extract the tool call
    tool_call = last_message.tool_calls[0]
    tool_name = tool_call['name']
    tool_args = tool_call['args']
    
    # Execute the tool
    if tool_name == 'run_sql':
        result = run_sql.invoke(tool_args)
    else:
        result = "Error: Unknown tool."
        
    # Return the result as a ToolMessage
    tool_message = ToolMessage(content=str(result), tool_call_id=tool_call['id'])
    return {"messages": [tool_message]}

# Define the conditional edge
def should_continue(state: AgentState):
    """Determines the next step: either execute a tool or end the conversation."""
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        return "execute_tool"
    else:
        return END

llm = ChatOpenAI(model="gpt-4.1-mini-2025-04-14", temperature=0)

tools = [run_sql]
llm_with_tools = llm.bind_tools(tools)

graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("execute_tool", call_tool)

graph.set_entry_point("agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "execute_tool": "execute_tool",
        END: END
    }
)
graph.add_edge("execute_tool", "agent")

app = graph.compile()


print("\n--- Agent Initialized. Ready for questions. ---\n")

if __name__ == '__main__':
    # --- Let's ask some questions! ---
    questions = [
        "How many listings are there?",
        "What are the details for the largest suite by square footage?",
        "Which broker is associated with the most expensive property based on Rent/SF/Year? I need the broker's associate name and their 3-year GCI."
    ]

    for i, question in enumerate(questions):
        print(f"--- Running Question {i+1}: {question} ---\n")
        
        # Stream the agent's thought process
        events = app.stream(
            {"messages": [HumanMessage(content=question)]},
            # The recursion limit is the max number of steps the agent can take
            {"recursion_limit": 10} 
        )
        
        final_answer = ""
        for event in events:
            for key, value in event.items():
                if key == 'agent':
                    # The agent is thinking and deciding on an action
                    print(f"Agent: {value['messages'][-1].content}")
                    if value['messages'][-1].tool_calls:
                        print(f"Action: Preparing to run tool {value['messages'][-1].tool_calls[0]['name']} with query: {value['messages'][-1].tool_calls[0]['args']}")
                elif key == 'execute_tool':
                    # The tool has run and we have the result
                    print(f"Observation: {value['messages'][-1].content}\n")
            
        # The final answer is in the last message of the final state
        final_state = app.invoke({"messages": [HumanMessage(content=question)]})
        print(f"\nFinal Answer: {final_state['messages'][-1].content}\n")
        print("--------------------------------------------------\n")