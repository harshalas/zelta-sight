import base64
import io
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import matplotlib.pyplot as plt
import yfinance as yf
import matplotlib
matplotlib.use('Agg') # Force Matplotlib to use a non-interactive backend

app = FastAPI(title="Zelta Sight API")

# Enable CORS so your frontend app can talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/analyze/{ticker}")
def analyze_stock(ticker: str):
    try:
        stock = yf.Ticker(ticker.upper())
        df = stock.history(period="5d", interval="5m")

        if df.empty:
            raise HTTPException(
                status_code=404, detail=f"No data found for ticker {ticker}"
            )

        # Generate the chart image in-memory
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

        # Calculate RVOL
        current_volume = df["Volume"].iloc[-1]
        avg_volume = df["Volume"].mean()
        rvol = round(current_volume / avg_volume, 2) if avg_volume > 0 else 0

        latest_price = round(df["Close"].iloc[-1], 4)

        # Mock Outlook for initial testing
        mock_outlook = (
            f"**{ticker.upper()}** is trading at **${latest_price}** with an RVOL of **{rvol}**. "
            "Volume profile is stable. Watch for structural breaks on the intraday tape."
        )

        return {
            "ticker": ticker.upper(),
            "latest_price": latest_price,
            "rvol": rvol,
            "chart_img": f"data:image/png;base64,{img_base64}",
            "outlook": mock_outlook,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))