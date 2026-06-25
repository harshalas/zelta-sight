import base64
import io
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
import matplotlib
import matplotlib.pyplot as plt
import yfinance as yf
import json

# Force Matplotlib to use a non-interactive backend
matplotlib.use("Agg")

app = FastAPI(title="Zelta Sight API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Gemini Client
client = genai.Client()

# System prompt modified to explicitly require the Strategy Suitability breakdown
SYSTEM_PROMPT = (
    "You are an elite, concise momentum trading assistant. Analyze the incoming ticker data "
    "and structural metrics. Give a blunt, scannable summary under 175 words highlighting "
    "immediate risks, key support lines, and whether it is an extended chase or a valid breakout setup.\n\n"
    "CRITICAL: Conclude your analysis with an explicit 'STRATEGY SUITABILITY' breakdown. For each of the "
    "following three categories, state either 'YES' or 'NO' followed by a single-sentence reason:\n"
    "1. Day Trade Candidate (For today's session based on current volume and volatility)\n"
    "2. Swing Trade Candidate (For a multi-day holding period based on current market structure)\n"
    "3. Long-Term Hold (Based on macro relevance, asset type, or structural position)"
)


@app.get("/analyze/{ticker}")
def analyze_stock(ticker: str):
    try:
        # 1. Fetch Intraday Stock Data
        stock = yf.Ticker(ticker.upper())
        df = stock.history(period="5d", interval="5m")

        if df.empty:
            raise HTTPException(
                status_code=404, detail=f"No data found for ticker {ticker}"
            )

        # 2. Extract key metrics for the AI prompt
        latest_price = round(df["Close"].iloc[-1], 4)
        day_high = round(df["High"].iloc[-1], 4)
        day_low = round(df["Low"].iloc[-1], 4)

        current_volume = df["Volume"].iloc[-1]
        avg_volume = df["Volume"].mean()
        rvol = round(current_volume / avg_volume, 2) if avg_volume > 0 else 0

        # 3. Generate the Chart Image in-memory
        plt.figure(figsize=(6, 3.5))
        color = "green" if df["Close"].iloc[-1] > df["Close"].iloc[0] else "red"
        plt.plot(df.index, df["Close"], color=color, linewidth=1.5)
        plt.title(f"{ticker.upper()} Intraday Chart", fontsize=12, pad=10)
        plt.grid(True, linestyle="--", alpha=0.5)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()

        # 4. Construct the prompt with hard data points
        prompt = (
            f"Analyze ticker {ticker.upper()} currently trading at ${latest_price} with a Relative Volume (RVOL) of {rvol}.\n\n"
            f"CRITICAL INSTRUCTION: You must start your response with the suitability verdict on the very first line using this exact format:\n"
            f"**SUITABILITY VERDICT:** [Day Trade OR Swing Trade OR Long Hold]\n\n"
            f"--- (Add a horizontal line break here) ---\n\n"
            f"Immediately following the verdict and line break, provide your extensive momentum scorecard for an intraday day trader. "
            f"Include the momentum characteristics, suitability for quick scaling, and critical levels on the tape. "
            f"Keep the scorecard comprehensive, direct, and cleanly formatted using markdown bullet points.\n\n"
            f"Determine an overall Technical Rating select exactly one from: [Strong Buy, Buy, Neutral, Sell, Strong Sell]."
        )

        # 5. Live AI Generation Call
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': {
                    'type': 'OBJECT',
                    'properties': {
                        'outlook_text': {'type': 'STRING'},
                        'technical_rating': {
                            'type': 'STRING',
                            'enum': ['Strong Buy', 'Buy', 'Neutral', 'Sell', 'Strong Sell']
                        }
                    },
                    'required': ['outlook_text', 'technical_rating']
                }
            }
        )

        # 6. Parse the structured response components safely
        try:
            result_data = json.loads(response.text)
        except (TypeError, json.JSONDecodeError):
            result_data = {}

        live_outlook = result_data.get('outlook_text', '')
        tech_rating = result_data.get('technical_rating', 'Neutral')

        return {
            "ticker": ticker.upper(),
            "latest_price": latest_price,
            "rvol": rvol,
            "chart_img": f"data:image/png;base64,{img_base64}",
            "outlook": live_outlook,
            "technical_rating": tech_rating,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))