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
        
        print("Chunker python unit test passed successfully!")
    finally:
        os.remove(temp_file_path)

def test_extract_generic_chunks():
    # Create a temporary js file to test generic fallback
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        # Create more than 50 lines to test chunk splitting
        js_content = "const a = 1;\n" * 60
        f.write(js_content)
        temp_file_path = f.name
        
    try:
        repo_path = os.path.dirname(temp_file_path)
        chunks = extract_chunks(temp_file_path, repo_path)
        
        # We expect 2 chunks since it's 60 lines and CHUNK_SIZE=50
        assert len(chunks) == 2, f"Expected 2 chunks, got {len(chunks)}"
        
        assert chunks[0]["start_line"] == 1
        assert chunks[0]["end_line"] == 50
        assert chunks[1]["start_line"] == 51
        assert chunks[1]["end_line"] == 60
        
        print("Chunker generic unit test passed successfully!")
    finally:
        os.remove(temp_file_path)

if __name__ == "__main__":
    test_extract_chunks()
    test_extract_generic_chunks()
