from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import json
from datetime import datetime
from collections import deque
from typing import Optional

# root_path="/weather" lets FastAPI know it's mounted at /weather behind nginx
app = FastAPI(title="City Weather API", root_path="/weather")

app.mount("/static", StaticFiles(directory="/app/static"), name="static")
templates = Jinja2Templates(directory="/app/templates")

# In-memory search history (max 50 entries)
search_history: deque = deque(maxlen=50)

WEATHER_API = "https://wttr.in/{city}?format=j1"

WEATHER_CODES = {
    113: ("Sunny", "☀️"),
    116: ("Partly Cloudy", "⛅"),
    119: ("Cloudy", "☁️"),
    122: ("Overcast", "☁️"),
    143: ("Mist", "🌫️"),
    176: ("Patchy Rain", "🌦️"),
    179: ("Patchy Snow", "🌨️"),
    182: ("Patchy Sleet", "🌧️"),
    185: ("Patchy Freezing Drizzle", "🌧️"),
    200: ("Thundery Outbreaks", "⛈️"),
    227: ("Blowing Snow", "🌨️"),
    230: ("Blizzard", "❄️"),
    248: ("Fog", "🌫️"),
    260: ("Freezing Fog", "🌫️"),
    263: ("Light Drizzle", "🌦️"),
    266: ("Drizzle", "🌧️"),
    281: ("Freezing Drizzle", "🌧️"),
    284: ("Heavy Freezing Drizzle", "🌧️"),
    293: ("Light Rain", "🌧️"),
    296: ("Rain", "🌧️"),
    299: ("Moderate Rain", "🌧️"),
    302: ("Heavy Rain", "🌧️"),
    305: ("Heavy Rain", "🌧️"),
    308: ("Very Heavy Rain", "🌧️"),
    311: ("Light Sleet", "🌨️"),
    314: ("Moderate Sleet", "🌨️"),
    317: ("Light Snow/Sleet", "🌨️"),
    320: ("Moderate Snow", "❄️"),
    323: ("Light Snow", "❄️"),
    326: ("Light Snow", "❄️"),
    329: ("Moderate Snow", "❄️"),
    332: ("Heavy Snow", "❄️"),
    335: ("Heavy Snow", "❄️"),
    338: ("Heavy Snow", "❄️"),
    350: ("Ice Pellets", "🧊"),
    353: ("Light Rain Shower", "🌦️"),
    356: ("Rain Shower", "🌧️"),
    359: ("Heavy Rain Shower", "🌧️"),
    362: ("Light Sleet Shower", "🌨️"),
    365: ("Sleet Shower", "🌨️"),
    368: ("Light Snow Shower", "🌨️"),
    371: ("Snow Shower", "❄️"),
    374: ("Light Ice Pellet Shower", "🧊"),
    377: ("Ice Pellet Shower", "🧊"),
    386: ("Thundery Rain", "⛈️"),
    389: ("Heavy Thunder Rain", "⛈️"),
    392: ("Thundery Snow", "⛈️"),
    395: ("Heavy Thundery Snow", "⛈️"),
}

def parse_weather(data: dict, city: str) -> dict:
    current = data["current_condition"][0]
    code = int(current["weatherCode"])
    desc, emoji = WEATHER_CODES.get(code, ("Unknown", "🌡️"))

    # nearest area
    area = data.get("nearest_area", [{}])[0]
    area_name = area.get("areaName", [{}])[0].get("value", city)
    country = area.get("country", [{}])[0].get("value", "")

    # 3-day forecast
    forecast = []
    for day in data.get("weather", [])[:3]:
        date_str = day["date"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        day_code = int(day["hourly"][4]["weatherCode"]) if day.get("hourly") else 113
        _, day_emoji = WEATHER_CODES.get(day_code, ("", "🌡️"))
        forecast.append({
            "day": date_obj.strftime("%a"),
            "date": date_obj.strftime("%b %d"),
            "max_temp_c": day["maxtempC"],
            "min_temp_c": day["mintempC"],
            "max_temp_f": day["maxtempF"],
            "min_temp_f": day["mintempF"],
            "emoji": day_emoji,
        })

    return {
        "city": area_name,
        "country": country,
        "display_name": f"{area_name}, {country}" if country else area_name,
        "temp_c": current["temp_C"],
        "temp_f": current["temp_F"],
        "feels_like_c": current["FeelsLikeC"],
        "feels_like_f": current["FeelsLikeF"],
        "humidity": current["humidity"],
        "wind_kmph": current["windspeedKmph"],
        "wind_mph": current["windspeedMiles"],
        "visibility": current["visibility"],
        "description": desc,
        "emoji": emoji,
        "uv_index": current.get("uvIndex", "N/A"),
        "forecast": forecast,
        "fetched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }


async def fetch_weather(city: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = WEATHER_API.format(city=city.replace(" ", "+"))
            resp = await client.get(url)
            if resp.status_code == 200:
                return parse_weather(resp.json(), city)
    except Exception:
        pass
    return None


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, city: Optional[str] = None, error: Optional[str] = None):
    weather = None
    err_msg = error

    if city:
        weather = await fetch_weather(city)
        if weather is None:
            err_msg = f"Could not find weather for \"{city}\". Check the city name and try again."
        else:
            # save to history
            search_history.appendleft({
                "city": weather["display_name"],
                "query": city,
                "temp_c": weather["temp_c"],
                "temp_f": weather["temp_f"],
                "description": weather["description"],
                "emoji": weather["emoji"],
                "searched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            })

    return templates.TemplateResponse("home.html", {
        "request": request,
        "weather": weather,
        "city_query": city or "",
        "error": err_msg,
    })


@app.post("/home", response_class=HTMLResponse)
async def home_post(request: Request, city: str = Form(...)):
    return RedirectResponse(url=f"/home?city={city}", status_code=303)


@app.get("/city", response_class=HTMLResponse)
async def city_history(request: Request):
    return templates.TemplateResponse("city.html", {
        "request": request,
        "history": list(search_history),
    })


@app.post("/city/clear")
async def clear_history():
    search_history.clear()
    return RedirectResponse(url="/city", status_code=303)


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "service": "city-weather-api"}
