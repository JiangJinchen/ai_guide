import requests

def test_stream():
    print("Testing streaming chat endpoint...")
    try:
        response = requests.post(
            'http://127.0.0.1:8000/api/visitor/chat/stream',
            headers={'Content-Type': 'application/json', 'X-User-Id': 'testuser', 'Accept': 'text/event-stream'},
            json={'text': '你好', 'user_id': 'testuser'},
            timeout=60,
            stream=True
        )
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print("\nStreaming data:")
        chunk_count = 0
        start_time = time.time()
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            elapsed = time.time() - start_time
            if chunk:
                chunk_count += 1
                lines = chunk.strip().split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        data_str = line[6:]
                        print(f"  [{chunk_count}] ({elapsed:.1f}s) {data_str[:200]}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    import time
    test_stream()