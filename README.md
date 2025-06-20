# 🧭 AI Trip Planner

A modern, AI-powered trip planning web app that generates personalized travel itineraries using natural language prompts. The backend leverages FastAPI, LangChain, Amadeus, SerpAPI, and more. The frontend is a creative, interactive HTML UI.

---

## ✨ Features

- **AI-Powered Planning:** Enter a single prompt describing your trip, and get a full itinerary (flights, hotels, activities).
- **Multi-Tool Integration:** Uses Amadeus for flights/hotels, SerpAPI for activities, Google Calendar, and email delivery.
- **Modern UI:** Beautiful, interactive frontend with prompt guidance and live streaming results.
- **Email Delivery:** Optionally sends your plan to your email.
- **Streaming API:** Real-time updates as your plan is generated.

---

## 🚀 Quickstart

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/your-repo.git
cd your-repo
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On Mac/Linux

pip install -r requirements.txt
```

#### Environment Variables

Create a `.env` file in `backend/` with the following (replace with your keys):

```
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
SERPAPI_API_KEY=your_serpapi_key
SENDGRID_API_KEY=your_sendgrid_key
GOOGLE_API_KEY=your_google_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REFRESH_TOKEN=your_google_refresh_token
```

### 3. Run the Backend

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### 4. Frontend

Open `frontend/index.html` directly in your browser, or serve it with a static server.

---

## 🖥️ Project Structure

```
Planner-Agents/
  backend/
    app/
      agent/         # Agent logic and graph
      api/           # FastAPI router
      core/          # Config and logging
      schemas/       # Pydantic models
      tools/         # Flight, hotel, email, calendar, search tools
    main.py          # FastAPI entrypoint
    requirements.txt
  frontend/
    index.html       # Modern, creative UI
  README.md
```

---

## 🛠️ API Usage

### Endpoint

`POST /plan-trip`

**Request Body:**
```json
{
  "prompt": "Plan a 5-day trip from Delhi to Goa for 2 people, departing June 10 and returning June 15. We like beaches, parties, and local food. Email the plan to me at user@example.com. Budget: 50,000 INR."
}
```

**Response:**  
A server-sent event (SSE) stream with JSON messages:
- `{"type": "log", "content": "Searching for flights..."}`  
- `{"type": "result", "content": "Here is your trip plan..."}`  
- `{"type": "error", "content": "Error details..."}`

---

## 📝 Prompt Format & Rules

> **Notice:**  
> The AI works best when you follow the sample prompt format. Please use the sample as a template and only make small changes.

**Sample Prompt:**
```
Plan a 5-day trip from Delhi to Goa for 2 people, departing June 10 and returning June 15. We like beaches, parties, and local food. Email the plan to me at user@example.com. Budget: 50,000 INR.
```

**Rules:**
- Clearly specify **origin** and **destination** cities.
- Include **departure** and **return** dates.
- Mention **number of travelers**.
- List **interests** (e.g., beaches, food, adventure).
- Provide your **email** if you want the plan sent to you.
- Optionally specify **budget** and **duration**.
- Use natural language, but keep the structure similar to the sample.

---

## 🌐 Deployment (Railway Example)

1. Push your code to GitHub.
2. Create a new project on [Railway](https://railway.app/).
3. Add a service for the backend (`uvicorn main:app --host 0.0.0.0 --port 8000`).
4. Add all required environment variables in the Railway dashboard.
5. (Optional) Add a static site service for the frontend, or serve `index.html` from the backend.
6. Update the frontend to use the Railway backend URL for API calls.

---

## 📄 License

MIT 
