# Running this project

## You need
- Python 3.10+, Node.js 18+
- `ecommerce.db` (220 MB) — NOT in this zip. Get it from Ali and put it in this folder.
- A free Groq API key: https://console.groq.com/keys

## 1. Your API key
Copy `.env.example` to `.env`, then edit `.env`:

    GROQ_API_KEY=gsk_your_key_here
    GROQ_MODEL=llama-3.1-8b-instant

No quotes, no spaces. `llama-3.1-8b-instant` has the most generous free-tier limits;
`openai/gpt-oss-120b` is higher quality but the free quota runs out quickly.

## 2. Install
    pip install -r backend/requirements.txt
    cd frontend
    npm install
    cd ..

## 3. Run — two terminals
Terminal 1 (backend):

    python -m uvicorn backend.app.main:app --port 8001 --reload

Wait for "Application startup complete".

Terminal 2 (frontend):

    cd frontend
    npm run dev

Open http://localhost:3001

## 4. Verify
    python -m pytest backend/tests -q

Two tests download an embedding model on first run — give it a minute.

## If it breaks
- "No active database connected" — ecommerce.db is missing from this folder
- 401 from Groq — bad or expired key in .env
- 404 model not found — that model is not on your account; use llama-3.1-8b-instant
- Rate limit exceeded — free quota used up; wait or switch model
- ChunkLoadError in the browser — in frontend/, delete .next, run npm run dev, Ctrl+Shift+R
- Port already in use — npx next dev -p 3005
