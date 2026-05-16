import json
import time
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add the repogpt directory to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.qa_chain import ask_question

def evaluate():
    evals_file = os.path.join(os.path.dirname(__file__), "evals.jsonl")
    
    with open(evals_file, "r") as f:
        evals = [json.loads(line) for line in f]
        
    correct = 0
    valid_citations = 0
    latencies = []
    
    print(f"Running {len(evals)} evaluations...")
    
    for i, eval_item in enumerate(evals):
        question = eval_item["question"]
        expected_files = eval_item.get("ground_truth_files", [])
        expected_terms = eval_item.get("answer_contains", [])
        
        start_time = time.time()
        try:
            answer, sources = ask_question(question)
        except Exception as e:
            print(f"Error on question {i+1}: {e}")
            continue
            
        latency = time.time() - start_time
        latencies.append(latency)
        
        # Accuracy check
        is_accurate = False
        if expected_files:
            if any(f in answer for f in expected_files):
                is_accurate = True
        elif expected_terms:
            if all(term.lower() in answer.lower() for term in expected_terms):
                is_accurate = True
                
        if is_accurate:
            correct += 1
            
        # Citation check: look for `file:start-end` pattern
        if "`" in answer and ":" in answer and "-" in answer:
            valid_citations += 1
            
        print(f"Q{i+1}: {'PASS' if is_accurate else 'FAIL'} | Latency: {latency:.2f}s")
        
    acc = correct / len(evals) * 100 if evals else 0
    cit_rate = valid_citations / len(evals) * 100 if evals else 0
    
    sorted_latencies = sorted(latencies)
    if sorted_latencies:
        p95_idx = int(len(sorted_latencies) * 0.95)
        # Ensure we don't go out of bounds
        p95_idx = min(p95_idx, len(sorted_latencies) - 1)
        p95_lat = sorted_latencies[p95_idx]
    else:
        p95_lat = 0
    
    print("\\n--- Evaluation Results ---")
    print(f"Accuracy: {acc:.1f}% (Target: >80%)")
    print(f"Citation Rate: {cit_rate:.1f}% (Target: 100%)")
    print(f"Latency p95: {p95_lat:.2f}s (Target: <3s)")

if __name__ == "__main__":
    evaluate()
