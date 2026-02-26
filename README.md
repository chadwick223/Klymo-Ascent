Veil – Anonymous Matchmaking & Chat Platform
----------------------------------------------------------------------------------------------------------------------------------------------------
Veil is an anonymous matchmaking and chat platform focused on privacy, simplicity, and real-time
communication.

TECH STACK : Backend: Django, Django REST Framework, Redis, SQLite (development),
Server-Sent Events (SSE), HTTPS. Frontend: React (Vite), EventSource (SSE). for mvp

Core Concepts: Users are represented by devices, not accounts. Every action is tied to a device
identity. Matchmaking pairs two devices and creates a unique chat session. Each chat session is
isolated and acts as its own communication channel

Chat System: Real-time chat is implemented using Server-Sent Events (SSE). The server streams
messages continuously to connected clients. Messages are stored in the database and published
via Redis. The browser connection stays open by design. after mvp worked changed sse with django channels

HTTPS & Security: The backend runs on HTTPS using a self-signed certificate. The certificate must
be manually trusted in the browser during development. Failure to trust the certificate results in
frontend network errors.

CORS: Frontend and backend run on different origins. CORS must be enabled for development to
allow communication.

