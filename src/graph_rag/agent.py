from datetime import datetime
import os
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from .config import CHAT_MODEL
from .tools import ALL_TOOLS
from .prompts.agent_prompt import SYSTEM_PROMPT

agent = create_agent(
    model=ChatGoogleGenerativeAI(
        model=CHAT_MODEL,
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0
    ),
    tools=ALL_TOOLS,
    system_prompt=SYSTEM_PROMPT
)

message_history = []

ERROR_FALLBACK = (
    "Error: the agent couldn't generate a response. "
    "Please try rephrasing your question."
)

def chat(user_query: str) -> dict:
    global message_history

    message_history.append({"role": "user", "content": user_query})

    try:
        response = agent.invoke({"messages": message_history})

        if isinstance(response, dict) and "messages" in response and response["messages"]:
            message_history = response["messages"]
        else:
            if message_history:
                message_history.pop()
            return {
                "query": user_query,
                "response": ERROR_FALLBACK,
                "timestamp": datetime.now().isoformat(),
                "signature": "MovieDB Graph-RAG Agent v1.0",
            }

        last_msg = message_history[-1] if message_history else None
        final_message = getattr(last_msg, "content", None) if last_msg is not None else None

        if isinstance(final_message, list):
            text_parts = []
            for item in final_message:
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                elif isinstance(item, str):
                    text_parts.append(item)
            final_message = "\n".join(text_parts)

        if not final_message or (isinstance(final_message, str) and not final_message.strip()):
            final_message = ERROR_FALLBACK

    except Exception:
        if message_history:
            message_history.pop()
        return {
            "query": user_query,
            "response": ERROR_FALLBACK,
            "timestamp": datetime.now().isoformat(),
            "signature": "MovieDB Graph-RAG Agent v1.0",
        }

    return {
        "query": user_query,
        "response": final_message,
        "timestamp": datetime.now().isoformat(),
        "signature": "MovieDB Graph-RAG Agent v1.0"
    }

if __name__ == "__main__":
    print("🎬 MovieDB Graph-RAG Agent")
    print("Commands: 'quit' to exit, 'reset' to clear memory\n")

    while True:
        user_input = input("\n> ").strip()

        if user_input.lower() in {"quit", "exit", "q"}:
            break

        if user_input.lower() == "reset":
            message_history.clear()
            print("Memory cleared")
            continue

        if not user_input:
            continue

        result = chat(user_input)

        print("\n" + "=" * 70)
        print(result["response"])
        print("=" * 70)
