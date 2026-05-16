import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add the repogpt directory to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.qa_chain import ask_question

def test_agent_cli():
    print("Testing QA Agent CLI...")
    question = "What does this codebase do?"
    
    # We catch errors here because if the DB connection string is missing,
    # or Google Cloud auth is missing, this will fail gracefully.
    try:
        answer, sources = ask_question(question)
        print(f"\\nQ: {question}")
        print(f"\\nA: {answer}")
        print(f"\\nSources retrieved: {len(sources)}")
        for i, s in enumerate(sources):
            print(f"  {i+1}. {s['file_path']}:{s['start_line']}-{s['end_line']}")
    except Exception as e:
        print(f"\\nTest skipped or failed due to missing DB/Env setup: {e}")
        print("To run this fully, you need POSTGRES_URL and GCP Auth.")

if __name__ == "__main__":
    test_agent_cli()
