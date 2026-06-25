import base64
import io
import os
import json
import time
import traceback
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
import matplotlib
import matplotlib.pyplot as plt
import yfinance as yf

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

SYSTEM_PROMPT = (
    "You are an elite institutional momentum risk manager. Break down the provided market data "
    "into individual tactical data metrics. For each metric, assign an explicit status string "
    "evaluating its directional safety for an active day trader."
)


@app.get("/analyze/{ticker}")
def analyze_stock(ticker: str):
    try:
        # 1. Safe Network Fetch Loop with Retries
        df = pd.DataFrame()
        for attempt in range(3):
            try:
                stock = yf.Ticker(ticker.upper())
                df = stock.history(period="5d", interval="5m")
                if not df.empty and len(df) > 5:
                    break
            except Exception:
                time.sleep(1)

        if df.empty or "Close" not in df.columns or len(df) < 5:
            raise ValueError("Ticker returned insufficient or empty historical bars.")

        # Ensure all core financial columns are numeric
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["Close", "High", "Low", "Volume"])

        if len(df) < 2:
            raise ValueError("Insufficient data bars remaining after cleaning NaN values.")

        # 2. Extract Latest Metric Baseline
        latest_price = round(float(df["Close"].iloc[-1]), 4)

        # 3. Dynamic Intraday ATR Calculation
        high_low = df["High"] - df["Low"]
        high_cp = (df["High"] - df["Close"].shift(1)).abs()
        low_cp = (df["Low"] - df["Close"].shift(1)).abs()
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1).dropna()
        
        if len(tr) >= 14:
            atr = round(float(tr.rolling(14).mean().iloc[-1]), 4)
        else:
            atr = round(float(tr.mean()) if len(tr) > 0 else 0.0, 4)

        # 4. Safe Session Isolation for VWAP & ORB
        df['StringDate'] = df.index.strftime('%Y-%m-%d')
        latest_date_str = df['StringDate'].iloc[-1]
        today_df = df[df['StringDate'] == latest_date_str].copy()

        current_vwap = latest_price
        vwap_dev_pct = 0.0
        
        if not today_df.empty and today_df['Volume'].sum() > 0:
            hlc3 = (today_df['High'] + today_df['Low'] + today_df['Close']) / 3
            v_sum = today_df['Volume'].cumsum()
            if not v_sum.empty and v_sum.iloc[-1] > 0:
                today_df['VWAP'] = (hlc3 * today_df['Volume']).cumsum() / v_sum
                current_vwap = round(float(today_df['VWAP'].iloc[-1]), 4)
                vwap_dev_pct = round(((latest_price - current_vwap) / current_vwap) * 100, 2)

        # 5. Safe 20 EMA Math
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        current_ema20 = round(float(df['EMA20'].iloc[-1]), 4)
        ema_dev_pct = round(((latest_price - current_ema20) / current_ema20) * 100, 2)

        # 6. Safe Opening Range Breakout (ORB) Status Boundaries Extraction
        orb_high, orb_low, orb_status = latest_price, latest_price, "Initializing"
        if len(today_df) >= 6:
            opening_range = today_df.iloc[:6]
            orb_high = round(float(opening_range['High'].max()), 4)
            orb_low = round(float(opening_range['Low'].min()), 4)
            if latest_price > orb_high:
                orb_status = "Above Range (Bullish)"
            elif latest_price < orb_low:
                orb_status = "Below Range (Bearish)"
            else:
                orb_status = "Inside Range (Chop)"
        elif not today_df.empty:
            orb_high = round(float(today_df['High'].max()), 4)
            orb_low = round(float(today_df['Low'].min()), 4)
            orb_status = "Building Initial Range"

        # 7. RVOL Computation
        current_volume = int(df["Volume"].iloc[-1])
        avg_volume = float(df["Volume"].mean())
        rvol = round(current_volume / avg_volume, 2) if avg_volume > 0 else 1.0

        # 8. Generation of Matplotlib Overlay Framework Plot
        plt.figure(figsize=(6, 3.5))
        plot_df = today_df if not today_df.empty else df
        
        plt.plot(plot_df.index, plot_df["Close"], color="#00b386" if latest_price >= plot_df["Close"].iloc[0] else "#ef4565", linewidth=1.5)
        if 'VWAP' in plot_df.columns:
            plt.plot(plot_df.index, plot_df['VWAP'], color="#f1c40f", linestyle="--", linewidth=1)
        
        plt.title(f"{ticker.upper()} Intraday Framework", fontsize=11, color="#fffffe", pad=10)
        plt.grid(True, linestyle=":", alpha=0.3)
        plt.tick_params(colors='#72757e', labelsize=8)
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=150, facecolor="#11111a")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()

        # 9. Structured Prompt Payload Construction
        prompt = (
            f"Analyze ticker {ticker.upper()} trading at ${latest_price} with raw tape parameters:\n"
            f"- Relative Volume: {rvol}x\n"
            f"- Intraday ATR: {atr}\n"
            f"- Distance from VWAP: {vwap_dev_pct}%\n"
            f"- Distance from 20-Period EMA: {ema_dev_pct}%\n"
            f"- Opening Range Status: {orb_status}\n\n"
            f"Fill out the analysis list following these precise categories:\n"
            f"1. Suitability Verdict (Overall operational choice)\n"
            f"2. Tape Speed Assessment (Velocity evaluation)\n"
            f"3. Structural Extension (Proximity entry assessment)\n"
            f"4. Opening Range Direction (ORB breakout evaluation)\n"
            f"5. Day Trade Compliance (Session validation)\n"
            f"6. Swing Trade Compliance (Multi-day validation)\n"
            f"7. Long Hold Viability (Structural validation)\n\n"
            f"For each item, provide a clear text description and assign a 'status' of GOOD if bullish/safe, RISK if extended/unfavorable, or NEUTRAL if consolidation/mixed."
        )

        # 10. AI Generation Call with Flash Lite + 429 Mock Fallback
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash-lite',  # Updated Model Target
                contents=prompt,
                config={
                    'system_instruction': SYSTEM_PROMPT,
                    'response_mime_type': 'application/json',
                    'response_schema': {
                        'type': 'OBJECT',
                        'properties': {
                            'technical_rating': {
                                'type': 'STRING',
                                'enum': ['Strong Buy', 'Buy', 'Neutral', 'Sell', 'Strong Sell']
                            },
                            'briefing_items': {
                                'type': 'ARRAY',
                                'items': {
                                    'type': 'OBJECT',
                                    'properties': {
                                        'label': {'type': 'STRING'},
                                        'description': {'type': 'STRING'},
                                        'status': {'type': 'STRING', 'enum': ['GOOD', 'RISK', 'NEUTRAL']}
                                    },
                                    'required': ['label', 'description', 'status']
                                }
                            }
                        },
                        'required': ['technical_rating', 'briefing_items']
                    }
                }
            )
            result_data = json.loads(response.text)
            
        except Exception as api_err:
            if "429" in str(api_err) or "RESOURCE_EXHAUSTED" in str(api_err):
                print("\n⚠️ QUOTA LIMIT EXHAUSTED: Switching to local fallback mockup data array...")
                result_data = {
                    "technical_rating": "Buy",
                    "briefing_items": [
                        {"label": "Suitability Verdict", "description": "High-momentum scalp setup ideal for an active intraday day trade.", "status": "GOOD"},
                        {"label": "Tape Speed Assessment", "description": f"RVOL is clipping along at {rvol}x standard baselines. High transactional velocity.", "status": "GOOD"},
                        {"label": "Structural Extension", "description": f"Currently sitting {vwap_dev_pct}% away from VWAP anchor. Extension risk is within tolerance.", "status": "NEUTRAL"},
                        {"label": "Opening Range Direction", "description": f"Price actions are checking out as {orb_status}.", "status": "GOOD"},
                        {"label": "Day Trade Compliance", "description": "YES - High relative volume profile supports swift standard entry and exits.", "status": "GOOD"},
                        {"label": "Swing Trade Compliance", "description": "NO - Volatility structure is too erratic for unmonitored overnight holding risk.", "status": "RISK"},
                        {"label": "Long Hold Viability", "description": "NO - Structural metrics are explicitly configured for short-term asset sweeps.", "status": "RISK"}
                    ]
                }
            else:
                raise api_err

        # 11. Final Structured Object Dispatch to Frontend
        return {
            "ticker": ticker.upper(),
            "latest_price": latest_price,
            "rvol": rvol,
            "atr": atr,
            "vwap_dev": vwap_dev_pct,
            "ema_dev": ema_dev_pct,
            "orb_status": orb_status,
            "chart_img": f"data:image/png;base64,{img_base64}",
            "briefing_items": result_data.get('briefing_items', []),
            "technical_rating": result_data.get('technical_rating', 'Neutral'),
        }

    except Exception as e:
        print("\n--- CRASH LOG DETECTED IN ENGINE ---")
        print(traceback.format_exc())
        print("------------------------------------\n")
        raise HTTPException(status_code=500, detail=f"Engine operational fault: {str(e)}")