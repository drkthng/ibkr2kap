import webview
import subprocess
import sys
import time
import socket
import os
import signal

def find_free_port():
    """Finds a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def main():
    # Find a free port
    port = find_free_port()
    
    # Determine the path to the streamlit executable
    # We look for it relative to the current python interpreter
    python_exe = sys.executable
    venv_dir = os.path.dirname(os.path.dirname(python_exe))
    
    # Standard location for streamlit in venv
    if os.name == 'nt':
        streamlit_exe = os.path.join(venv_dir, 'Scripts', 'streamlit.exe')
    else:
        streamlit_exe = os.path.join(venv_dir, 'bin', 'streamlit')
    
    # Base command
    cmd = []
    if os.path.exists(streamlit_exe):
        cmd = [streamlit_exe, "run", "src/ibkr_tax/main.py"]
    else:
        # Fallback to python -m streamlit
        cmd = [python_exe, "-m", "streamlit", "run", "src/ibkr_tax/main.py"]
    
    # Append common arguments
    cmd += [
        "--server.port", str(port),
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ]
    
    print(f"Starting Streamlit server on port {port}...")
    
    # Start streamlit as a background process
    # Using CREATE_NO_WINDOW on Windows to keep it hidden
    kwargs = {}
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
    p = subprocess.Popen(cmd, **kwargs)
    
    # Wait for the server to start (polling)
    # We try to connect to the port until it succeeds or times out
    max_retries = 30
    ready = False
    for i in range(max_retries):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                ready = True
                break
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(1)
            
    if not ready:
        print("Error: Streamlit server failed to start in time.")
        p.terminate()
        sys.exit(1)
    
    print("Streamlit server is ready. Opening native window...")
    
    try:
        # Create a native window pointing to the local streamlit server
        # We specify gui='qt' to ensure it uses PySide6/Qt if possible
        webview.create_window(
            'IBKR2KAP - German Tax Assistant', 
            f'http://localhost:{port}', 
            width=1280, 
            height=900,
            min_size=(800, 600)
        )
        
        # Start the webview (this blocks until the window is closed)
        webview.start()
        
    finally:
        print("Closing application...")
        # Ensure the streamlit server is terminated when the window is closed
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()

if __name__ == '__main__':
    main()
