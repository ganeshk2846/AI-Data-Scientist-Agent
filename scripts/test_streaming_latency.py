import sys
import os
sys.path.insert(0, os.path.abspath("."))
import asyncio
import json
import httpx
from backend.app.api.v1.endpoints.agentic import stream_agentic_query, SuperviseRequest
from backend.app.observability.tracer import observability_tracer

class DummyRequest:
    def __init__(self):
        self.state = type("State", (), {"request_id": "test_req_stream"})()
    async def is_disconnected(self):
        return False

async def test_stream():
    print("Testing SSE Streaming Latency Instrumentation...")
    req = DummyRequest()
    body = SuperviseRequest(question="What are our total orders?", session_id="test_stream_session")
    
    event_response = await stream_agentic_query(body, req)
    
    events = []
    async for raw_event in event_response.body_iterator:
        events.append(raw_event)
        # raw_event is bytes or string formatted SSE
    
    print(f"Captured {len(events)} SSE chunks.")
    
    # Check trace in DB
    traces = observability_tracer.get_recent_traces(limit=1)
    if traces:
        last_t = traces[0]
        print(f"Last trace ID: {last_t.run_id}")
        print(f"Streaming TTFE: {last_t.streaming_ttfe_ms} ms")
        print(f"Streaming TTFO: {last_t.streaming_ttfo_ms} ms")
        print(f"Total Latency:  {last_t.latency_ms} ms")

if __name__ == "__main__":
    asyncio.run(test_stream())
