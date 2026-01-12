import subprocess
import time
import sys
import threading
import requests
import os
import signal
import argparse
from datetime import datetime

# Colored Output
def print_green(msg): print(f"\033[92m{msg}\033[0m")
def print_cyan(msg): print(f"\033[96m{msg}\033[0m")
def print_red(msg): print(f"\033[91m{msg}\033[0m")
def print_yellow(msg): print(f"\033[93m{msg}\033[0m")
def print_blue(msg): print(f"\033[94m{msg}\033[0m")

RELAY_PORT = 5000
AGENT_PORT = 7500

def start_relay():
    print_cyan(f"☁️  Starting Cloud Relay Server on port {RELAY_PORT}...")
    cmd = [sys.executable, "src/cloud_relay_server.py", "--port", str(RELAY_PORT)]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def start_agent():
    print_green(f"🧑‍💼 Starting HR Service Agent on port {AGENT_PORT}...")
    cmd = [sys.executable, "src/server.py", "--port", str(AGENT_PORT)]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def check_port_open(port, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=1)
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)
        except:
            return True
    return False

def stream_output(process, prefix):
    """Stream process output with prefix"""
    for line in iter(process.stdout.readline, b''):
        if line:
            print(f"[{prefix}] {line.decode().strip()}")

def main():
    parser = argparse.ArgumentParser(description="HR Service Request Agent - Production Runner")
    parser.add_argument("--with-ngrok", action="store_true", help="Print ngrok instructions")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode with test webhook")
    args = parser.parse_args()

    print("=" * 70)
    print("      HR SERVICE REQUEST AGENT - PRODUCTION SYSTEM")
    print("      Dr. Reddy's HR Automation powered by Atomicwork")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 1. Start Relay
    relay_process = start_relay()
    # relay server doesn't have /health but acts as simple proxy
    time.sleep(2)
    
    print_green("✅ Cloud Relay started (assuming success).")

    # 2. Start Agent
    agent_process = start_agent()
    # Agent typically takes a moment to start
    if not check_port_open(AGENT_PORT):
        print_red("❌ Failed to start HR Agent (or health check timed out).")
        # We continue anyway to see logs
    else:
        print_green("✅ HR Service Agent is RUNNING.")
    
    print("\n" + "-" * 70)
    print_blue(" 🚀 SYSTEM ONLINE")
    print("-" * 70)
    
    print("\n📡 ENDPOINTS:")
    print(f"   Local Webhook:  http://localhost:{AGENT_PORT}/webhook")
    print(f"   Cloud Relay:    http://localhost:{RELAY_PORT}/webhook")
    print(f"   Health Check:   http://localhost:{AGENT_PORT}/health")
    
    if args.with_ngrok:
        print_yellow("\n🔗 NGROK INSTRUCTIONS:")
        print("   1. Open a new terminal.")
        print(f"   2. Run: ngrok http {RELAY_PORT}")
        print("   3. Copy the 'Forwarding' URL (e.g., https://xyz.ngrok-free.app)")
        print("   4. Configure your Atomicwork Webhook to point to:")
        print("      → https://xyz.ngrok-free.app/webhook")
        
    print_yellow("\n📋 ATOMICWORK WEBHOOK CONFIGURATION:")
    print("   URL: https://your-ngrok-url.ngrok-free.app/webhook")
    print("   Method: POST")
    print("   Payload:")
    print('''   {
     "ticket_id": "{{request.request_id}}",
     "issue_description": "{{request.subject}}",
     "user_email": "{{request.requester.work_email}}",
     "requester_name": "{{request.requester.name}}"
   }''')

    print_cyan("\n📝 SUPPORTED HR REQUESTS:")
    print("   • Payslip download (e.g., 'I need my December 2024 payslip')")
    print("   • Leave application (e.g., 'Apply casual leave from 15/01 to 17/01')")
    print("   • Leave balance check (e.g., 'What is my leave balance?')")
    print("   • Employment letter (e.g., 'Need employment letter for visa')")
    print("   • Salary certificate (e.g., 'Generate salary certificate')")
    print("   • Insurance e-card (e.g., 'Download my medical insurance card')")
    print("   • Attendance correction (e.g., 'Mark attendance for yesterday')")
    print("   • Bank account change (e.g., 'Update my salary account to HDFC')")
    print("   • Form 16 download (e.g., 'Need Form 16 for FY 2023-24')")
    
    if args.demo:
        print_yellow("\n🧪 DEMO MODE - Sending test webhook in 5 seconds...")
        
        def run_demo():
            time.sleep(5)
            try:
                test_payload = {
                    "ticket_id": "REQ-DEMO-001",
                    "issue_description": "I need my payslip for December 2024",
                    "user_email": "vijay@drreddy.com",
                    "requester_name": "Vijay Kumar"
                }
                print_yellow(f"Sending payload: {test_payload}")
                response = requests.post(
                    f"http://localhost:{AGENT_PORT}/webhook",
                    json=test_payload
                )
                print_green(f"✅ Demo webhook sent! Response: {response.json()}")
            except Exception as e:
                print_red(f"❌ Demo webhook failed: {e}")

        threading.Thread(target=run_demo, daemon=True).start()

    print("\n" + "-" * 70)
    print("Logs will appear below. Press Ctrl+C to stop.")
    print("-" * 70 + "\n")

    # Start output streaming threads
    relay_thread = threading.Thread(target=stream_output, args=(relay_process, "RELAY"), daemon=True)
    agent_thread = threading.Thread(target=stream_output, args=(agent_process, "AGENT"), daemon=True)
    relay_thread.start()
    agent_thread.start()

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
            # Check if processes are still running
            if relay_process.poll() is not None:
                print_red("❌ Relay process died unexpectedly")
                break
            if agent_process.poll() is not None:
                print_red("❌ Agent process died unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        relay_process.terminate()
        agent_process.terminate()
        print_green("✅ Services stopped. Goodbye!")

if __name__ == "__main__":
    main()
