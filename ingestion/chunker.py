# pyrefly: ignore [missing-import]
import tree_sitter_python as tspython
# pyrefly: ignore [missing-import]
from tree_sitter import Language, Parser

def get_parser():
    # tree-sitter v0.21 initialization
    LANGUAGE = Language(tspython.language(), "python")
    parser = Parser()
    parser.set_language(LANGUAGE)
    return parser

def extract_chunks(file_path: str, repo_path: str) -> list[dict]:
    """Parses a Python file and returns AST chunks (classes and functions)."""
    parser = get_parser()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception:
        return []
        
    tree = parser.parse(bytes(code, "utf8"))
    
    def walk(node):
        chunks = []
        if node.type in ('function_definition', 'class_definition'):
            # find the identifier
            symbol_name = "unknown"
            for child in node.children:
                if child.type == 'identifier':
                    symbol_name = child.text.decode('utf8')
                    break
            
            # Start line is 1-indexed for standard metadata, tree-sitter is 0-indexed
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            # Get the exact source code for this chunk
            chunk_code = code.encode('utf8')[node.start_byte:node.end_byte].decode('utf8')
            
            rel_path = file_path.replace(repo_path, "").lstrip("/\\")
            
            chunks.append({
                "file_path": rel_path,
                "start_line": start_line,
                "end_line": end_line,
                "symbol_name": symbol_name,
                "content": chunk_code
            })
            
        for child in node.children:
            chunks.extend(walk(child))
            
        return chunks
        
    return walk(tree.root_node)
