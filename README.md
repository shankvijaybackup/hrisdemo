# HR Service Request Agent

NLP-powered HR service request automation for Atomicwork ITSM. Receives tickets via webhook, understands the HR request using NLP, executes actions, and updates tickets with results.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Atomicwork ITSM                                   │
│   User submits HR request → Workflow triggers webhook               │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ POST /webhook
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Cloud Relay (ngrok)                               │
│   https://xyz.ngrok-free.app/webhook → localhost:10000              │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ Forward
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    HR Service Agent                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌────────────────┐    ┌──────────────────┐    │
│  │ Intent Router│───▶│  Entity        │───▶│  Action Executor │    │
│  │  (NLP Core)  │    │  Extraction    │    │   (PDF, HRIS)    │    │
│  └──────────────┘    └────────────────┘    └──────────────────┘    │
│                                                   │                 │
│                                                   ▼                 │
│                               ┌─────────────────────────────────┐  │
│                               │   Atomicwork Client             │  │
│                               │   (Update ticket with results)  │  │
│                               └─────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd hr_service_agent
pip install -r requirements.txt
```

### 2. Run the Agent

```bash
# Basic run
python main.py

# With ngrok instructions
python main.py --with-ngrok

# Demo mode (sends test webhook)
python main.py --demo
```
