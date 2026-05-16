import tempfile
import os
from ingestion.chunker import extract_chunks

def test_extract_chunks():
    # Create a temporary python file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
class MyClass:
    def my_method(self):
        pass

def my_function():
    return True
''')
        temp_file_path = f.name
        
    try:
        # Assuming the repo path is the parent directory of the temp file
        repo_path = os.path.dirname(temp_file_path)
        chunks = extract_chunks(temp_file_path, repo_path)
        
        # We expect 3 chunks: MyClass, my_method, my_function
        assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
        
        # Check metadata
        for chunk in chunks:
            assert "file_path" in chunk, "Missing file_path"
            assert "start_line" in chunk, "Missing start_line"
            assert "end_line" in chunk, "Missing end_line"
            assert "symbol_name" in chunk, "Missing symbol_name"
            assert "content" in chunk, "Missing content"
            
        symbols = [c["symbol_name"] for c in chunks]
        assert "MyClass" in symbols, "MyClass symbol not found"
        assert "my_method" in symbols, "my_method symbol not found"
        assert "my_function" in symbols, "my_function symbol not found"
        
        print("Chunker unit test passed successfully!")
    finally:
        os.remove(temp_file_path)

if __name__ == "__main__":
    test_extract_chunks()
