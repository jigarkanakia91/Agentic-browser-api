## 1. **What This Repo Is About**

This is a **FastAPI-based REST API that wraps AI-powered browser automation agents**. It provides an HTTP interface to automate browser tasks using natural language instructions via OpenAI LLMs. The system uses the `browser-use` library to control Chromium and execute web tasks autonomously.

## 2. **Use Cases**

- **Web Automation API**: Submit natural language tasks and the agent will navigate websites to complete them
- **Autonomous Web Tasks**: Example tasks could be "find the cheapest flight," "fill out a form," "search for specific data"
- **Domain Control**: Restrict browser access to allowed domains or block prohibited domains for security
- **Concurrent Agent Execution**: Handle up to 3 concurrent browser tasks simultaneously
- **Extended Instructions**: Customize agent behavior with extended system prompts

## 3. **Tech Stack**

```
Core Framework:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- Python 3.13

AI & Browser Automation:
- browser-use (AI agent framework for browser control)
- Playwright (browser automation library)
- OpenAI API (LLM for agent decision-making)
- ChatOpenAI (OpenAI client)

Utilities:
- python-dotenv (environment variable management)
- Pydantic (request/response validation)

Infrastructure:
- Docker (containerization)
- Chromium browser (via Playwright)
```

## 4. **How to Run the Project**

### **Option A: Docker (Recommended)**

```bash
# Build the image
docker build -t agentic-browser-api .

# Run the container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e LLM_MODEL=gpt-4 \
  -e LLM_BASE_URL=https://api.openai.com/v1 \
  -e LLM_API_KEY=your_key \
  agentic-browser-api
```

The Docker setup:
- Builds on `python:3.13-slim`
- Pre-installs Chromium with Playwright
- Runs uvicorn on `0.0.0.0:8000` in headless mode
- Sets `PYTHONUNBUFFERED=1` for real-time logs

### **Option B: Manual CLI (Local Development)**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment variables
cat > .env << EOF
LLM_MODEL=gpt-4
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key
LLM_TEMPERATURE=0.2
BROWSER_USER_DATA_DIR=/path/to/profile  # (optional)
BROWSER_USER_AGENT=Mozilla/5.0...       # (optional)
EOF

# 3. Run the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 4. Access the API
# Health check: curl http://localhost:8000/health
# API docs: http://localhost:8000/docs (Swagger UI)
```

### **Key Environment Variables**

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `LLM_MODEL` | ✓ | - | Model name (e.g., `gpt-4`, `gpt-3.5-turbo`) |
| `LLM_API_KEY` | ✓ | - | API key for LLM provider |
| `LLM_BASE_URL` | ✓ | - | LLM API endpoint |
| `LLM_TEMPERATURE` | ✗ | `0.2` | LLM randomness (0=deterministic, 1=creative) |
| `BROWSER_USER_DATA_DIR` | ✗ | - | Persistent browser profile for cookies/history |
| `BROWSER_USER_AGENT` | ✗ | Chrome 136 | Custom user agent string |
| `HEADLESS` | ✗ | `true` (Docker) | Run browser in headless mode |

### **API Endpoints**

```
GET  /health              → {"status": "ok"}
POST /run-agent           → Run a browser task
     Request body:
     {
       "task": "Find the weather in New York",
       "extend_system_message": "Optional additional instructions",
       "allowed_domains": ["weather.com"],      # optional whitelist
       "prohibited_domains": ["ads.com"]        # optional blacklist
     }
     
     Response:
     {
       "success": true,
       "final_url": "https://weather.com/...",
       "llm_result": "The weather is..."
     }

GET  /docs               → Swagger UI documentation
```

### **Architecture Highlights**

- **Thread-Safe Execution**: Uses `ThreadPoolExecutor` to isolate browser agents from Uvicorn's event loop
- **Concurrency Control**: Semaphore limits concurrent agents to 3
- **Windows Compatible**: Uses `ProactorEventLoop` on Windows for proper async handling
- **CORS Enabled**: Allows requests from any origin
- **Graceful Cleanup**: Properly closes browser sessions on completion or error
 
