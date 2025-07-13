import os
import kuzu
from typing import TypedDict, Annotated, List, Optional
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
import operator
from langchain_openai import ChatOpenAI
import numpy as np
from openai import OpenAI
import json
import pandas as pd

from dotenv import load_dotenv
load_dotenv()

DB_PATH = "kuzu_real_estate_db"

client = OpenAI()
logic_llm = ChatOpenAI(model="gpt-4.1-mini-2025-04-14", temperature=0)  # Using a powerful model is good for following complex instructions
EMBEDDING_MODEL = "text-embedding-3-small"

def get_db_schema(db_path: str) -> str:
    """Dynamically gets the schema of all nodes and relationships in the Kuzu database."""
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    
    schema_str = "Kuzu Graph Database Schema:\n"
    node_tables = conn._get_node_table_names()
    schema_str += "## Node Tables:\n"
    for table_name in node_tables:
        schema_str += f"- **{table_name}**:\n"
        properties = conn._get_node_property_names(table_name)
        for prop, dtype in properties.items():
            schema_str += f"  - {prop} ({dtype})\n"

    rel_tables = conn._get_rel_table_names()
    schema_str += "\n## Relationship Tables:\n"
    for table_name in rel_tables:
        schema_str += f"- **{table_name}**\n"

    return schema_str

@tool
def query_real_estate_database(question: str):
    """
    The only tool you need to answer any question about real estate.
    Provide the user's entire question to the 'question' argument.
    """
    print(f"--- Smart Tool Activated with Question: '{question}' ---")
    
    # Step 1: Internal Router - Classify the user's intent
    router_prompt = f"""
    You are a classification model. Your task is to determine if the following user question is asking about a specific street address or is a general query requiring a database search or if it just normal conversational context like Hi, Hello, Thank You, or Goodbye.
    Scale to questions unrelated to real estate to NORMAL_QUERY.
    Answer with only 'ADDRESS_SEARCH' or 'GENERAL_QUERY' or 'NORMAL_QUERY'.

    Question: {question}
    Classification:
    """
    router_response = logic_llm.invoke(router_prompt).content
    print(f"Internal Router Classified as: {router_response}")

    db = kuzu.Database(DB_PATH, read_only=True)
    conn = kuzu.Connection(db)

    try:
        # --- Branch 1: The question is about a specific address ---
        if "ADDRESS_SEARCH" in router_response:
            print("Executing address search logic...")
            # Find the canonical address first
            addr_response = conn.execute("MATCH (l:Listing) RETURN l.address, l.address_embedding")
            addr_df = addr_response.get_as_df()
            if addr_df.empty: return "No listings found."

            db_embeddings = np.array([json.loads(e) for e in addr_df['l.address_embedding']])
            query_response = client.embeddings.create(model=EMBEDDING_MODEL, input=question)
            query_embedding = query_response.data[0].embedding

            similarities = np.dot(db_embeddings, np.array(query_embedding)) / (np.linalg.norm(db_embeddings, axis=1) * np.linalg.norm(query_embedding))
            best_match_address = addr_df.iloc[np.argmax(similarities)]['l.address']

            # Now, get all details for that canonical address
            cypher_query = "MATCH (l:Listing) WHERE l.address = $address_filter RETURN l.*"
            result = conn.execute(cypher_query, {"address_filter": best_match_address})
            result_df = result.get_as_df()
            
            # We no longer need to find and process a column 'l'.
            # We just need to drop the embedding column before display.
            if 'l.address_embedding' in result_df.columns:
                result_df = result_df.drop(columns=['l.address_embedding'])

            return result_df.to_markdown(index=False)

        # --- Branch 2: The question is a general query ---
        elif "GENERAL_QUERY" in router_response:
            print("Executing general query logic...")
            db_schema = get_db_schema(DB_PATH)
            cypher_gen_prompt = f"Schema: {db_schema}\nQuestion: {question}\nGenerate a Cypher query. Respond with only the query."
            cypher_query = logic_llm.invoke(cypher_gen_prompt).content.strip()
            print(f"Generated Cypher: {cypher_query}")
            
            result = conn.execute(cypher_query)
            return result.get_as_df().to_markdown(index=False)
        
        # --- Branch 3: The question is a normal conversational context ---
        elif "NORMAL_QUERY" in router_response:

            result = logic_llm.invoke(f"{question}")
            return result.content.strip()


    except Exception as e:
        return f"An error occurred within the tool: {e}"


# --- LANGGRAPH AGENT DEFINITION ---

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

def call_model(state: AgentState):
    """The primary node that calls the LLM. It decides whether to use a tool or respond."""
    messages = state['messages']
    db_schema = get_db_schema(DB_PATH)
    
    # ---! IMPORTANT PROMPT UPDATE !---
    system_prompt = (
        "You are an assistant. You have one tool: `query_real_estate_database`.\n"
        "To answer questions about real estate, you MUST call this tool.\n"
        "Your ONLY job is to pass the user's full question into the `question` argument."
    )
    
    messages_with_system_prompt = [HumanMessage(content=system_prompt)] + messages
    
    response = llm_with_tools.invoke(messages_with_system_prompt)
    return {"messages": [response]}

# The rest of the LangGraph setup remains the same
def call_tool(state: AgentState):
    last_message = state['messages'][-1]
    tool_call = last_message.tool_calls[0]
    result = query_real_estate_database.invoke(tool_call['args'])
    tool_message = ToolMessage(content=str(result), tool_call_id=tool_call['id'])
    return {"messages": [tool_message]}

def should_continue(state: AgentState):
    if state['messages'][-1].tool_calls:
        return "execute_tool"
    else:
        return END

schema = get_db_schema(DB_PATH)
print(f"Current Kuzu DB Schema:\n{schema}\n")

llm = ChatOpenAI(model="gpt-4.1-mini-2025-04-14", temperature=0) # Using a powerful model is good for following complex instructions
tools = [query_real_estate_database]
llm_with_tools = llm.bind_tools(tools)

graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("execute_tool", call_tool)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"execute_tool": "execute_tool", END: END})
graph.add_edge("execute_tool", "agent")
app = graph.compile()

print("\n--- Agent Initialized with Kuzu DB (Numeric/Text schema). Ready for questions. ---\n")

if __name__ == '__main__':
    
    questions = [
        # "How many listings are there?",
        # "What are the details for the largest suite by square footage?",
        # "Which broker is associated with the most expensive property based on Rent/SF/Year? I need the broker's associate name and their 3-year GCI.",
        # "Which broker is associated with the most expensive property based on Rent/SF/Year? I need the broker's email and the property's rent.",
        "How many listing are there in 18 west 38th street?",
    ]

    for i, question in enumerate(questions):
        print(f"--- Running Question {i+1}: {question} ---\n")
    
        events = app.stream({"messages": [HumanMessage(content=question)]}, {"recursion_limit": 10})
        
        for event in events:
            if "agent" in event:
                print(event["agent"]["messages"][-1])
            if "execute_tool" in event:
                print(event["execute_tool"]["messages"][-1])
                
        final_state = app.invoke({"messages": [HumanMessage(content=question)]})
        print(f"\nFinal Answer: {final_state['messages'][-1].content}\n")
        print("--------------------------------------------------\n")
