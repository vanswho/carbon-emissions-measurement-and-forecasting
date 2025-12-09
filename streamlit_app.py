import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
import streamlit as st
from dotenv import load_dotenv

# ------------ LOAD ENV ------------ #
load_dotenv()

# ---------- GEMINI CONFIG (HTTP, no SDK) ----------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# IMPORTANT: use a model that your key supports.
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent"

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found in .env")
else:
    print("✅ GEMINI_API_KEY loaded")


# ---------- HELPER: build personalised email body (SAME AS YOUR FLASK CODE) ----------
def build_personalised_body(name, emission_value, inputs):
    # Safely read values from dict
    electricity = float(inputs.get("electricity", 0) or 0)
    electricity_source = inputs.get("electricitySource", "mixed")
    lpg = float(inputs.get("lpg", 0) or 0)

    vehicle_type = inputs.get("vehicleType", "none")
    travel = float(inputs.get("travel", 0) or 0)
    efficiency = float(inputs.get("efficiency", 0) or 0)

    diet = inputs.get("diet", "mixed")
    waste = float(inputs.get("waste", 0) or 0)
    household = int(inputs.get("household", 1) or 1)
    renewable = float(inputs.get("renewable", 0) or 0)

    per_capita = emission_value / max(household, 1)

    lines = []

    # Intro + summary
    lines.append(f"Hi {name},")
    lines.append("")
    lines.append("Thank you for using the Carbon Emission Measurement tool. 🌍")
    lines.append("Here is your personalised monthly carbon footprint report:")
    lines.append(f"→ Estimated total footprint: {emission_value:.2f} kg CO₂e / month")
    lines.append(f"→ Approx. per-person footprint: {per_capita:.2f} kg CO₂e (household size: {household})")
    lines.append("")
    lines.append("Below is a breakdown by category with suggestions tailored to your inputs:")

    # 1) Energy
    lines.append("")
    lines.append("1️⃣ Home Energy Use")

    if electricity > 250:
        lines.append(f"- Electricity use: {electricity:.0f} kWh/month — this is on the higher side.")
    elif electricity > 100:
        lines.append(f"- Electricity use: {electricity:.0f} kWh/month — moderate level.")
    else:
        lines.append(f"- Electricity use: {electricity:.0f} kWh/month — relatively low 👍.")

    lines.append(f"- Reported electricity source: {electricity_source.capitalize()}, about {renewable:.0f}% from renewables.")
    if lpg > 0:
        lines.append(f"- LPG / cooking gas usage: {lpg:.1f} kg per month.")

    energy_tips = [
        "Replace old tube lights/CFLs with LED bulbs in frequently used rooms.",
        "Turn off fans, lights and ACs whenever you leave the room.",
        "Use natural daylight and cross-ventilation to reduce the need for lights and AC.",
    ]
    if electricity > 200:
        energy_tips.append("Set AC at 24–26°C and keep doors/windows closed while it runs.")
        energy_tips.append("Use washing machine only with full loads and eco/quick wash modes.")
    if renewable < 40:
        energy_tips.append("Explore rooftop solar or green power options in your area (if available).")

    lines.append("Recommended actions for energy:")
    for tip in energy_tips:
        lines.append(f"• {tip}")

    # 2) Transport
    lines.append("")
    lines.append("2️⃣ Transport & Travel")

    if vehicle_type in ["car", "bike"] and travel > 200:
        lines.append(f"- You travel about {travel:.0f} km/month using a {vehicle_type}, mostly private transport.")
        lines.append("- This is likely one of the bigger contributors to your footprint.")
    elif vehicle_type in ["bus", "train"]:
        lines.append(f"- You mainly use {vehicle_type} for around {travel:.0f} km/month, which is lower-carbon than solo car use.")
    elif vehicle_type == "none":
        lines.append("- You reported no regular motorised transport — your travel emissions are very low. 👍")
    else:
        lines.append(f"- You travel about {travel:.0f} km/month by {vehicle_type}.")

    if efficiency > 0 and vehicle_type in ["car", "bike"]:
        lines.append(f"- Vehicle efficiency: ~{efficiency:.1f} km per litre/kWh.")

    transport_tips = []
    if vehicle_type in ["car", "bike"]:
        transport_tips.append("Use public transport, metro or shared cabs for regular routes when possible.")
        transport_tips.append("Carpool with colleagues/friends to reduce solo trips.")
        transport_tips.append("Plan errands to combine multiple small trips into one journey.")
        transport_tips.append("Keep tyres properly inflated and service your vehicle regularly for better mileage.")
    else:
        transport_tips.append("Continue choosing public transport or non-motorised options whenever possible.")
    transport_tips.append("For very short distances, prefer walking or cycling instead of using a vehicle.")

    lines.append("Recommended actions for transport:")
    for tip in transport_tips:
        lines.append(f"• {tip}")

    # 3) Diet
    lines.append("")
    lines.append("3️⃣ Food & Diet")

    if diet == "veg":
        lines.append("- You follow a vegetarian diet, which is generally lower in emissions compared to heavy meat diets. 🌱")
    elif diet == "vegan":
        lines.append("- You follow a vegan diet — one of the lowest-carbon diet patterns. 🌱💚")
    elif diet == "nonveg":
        lines.append("- You reported a mainly non-vegetarian diet, which tends to have a higher carbon footprint.")
    else:
        lines.append("- You reported a mixed diet (some vegetarian and some non-vegetarian meals).")

    diet_tips = []
    if diet in ["nonveg", "mixed"]:
        diet_tips.append("Try 2–3 fully vegetarian days per week to gradually lower your food emissions.")
        diet_tips.append("Reduce red meat (mutton/beef) and prefer pulses, paneer, eggs or chicken instead.")
    diet_tips.append("Prefer seasonal, locally grown fruits and vegetables over heavily packaged or imported options.")
    diet_tips.append("Plan meals and store leftovers properly to avoid food waste.")

    lines.append("Recommended actions for food:")
    for tip in diet_tips:
        lines.append(f"• {tip}")

    # 4) Waste
    lines.append("")
    lines.append("4️⃣ Waste & Lifestyle")

    if waste > 30:
        lines.append(f"- You generate about {waste:.0f} kg of waste per month — there is strong scope to reduce this.")
    elif waste > 10:
        lines.append(f"- You generate about {waste:.0f} kg of waste per month — moderate level.")
    else:
        lines.append(f"- You generate about {waste:.0f} kg of waste per month — relatively low 👍.")

    waste_tips = [
        "Segregate waste at source: wet (organic), dry (recyclable) and reject waste.",
        "Compost kitchen waste such as peels, leftover food and tea powder.",
        "Avoid single-use plastics (bags, cutlery, straws); carry your own bottle and cloth bag.",
        "Repair, reuse or donate usable items instead of throwing them away quickly.",
    ]

    lines.append("Recommended actions for waste & lifestyle:")
    for tip in waste_tips:
        lines.append(f"• {tip}")

    # Closing
    lines.append("")
    lines.append("You don’t need to change everything at once.")
    lines.append("Pick 2–3 actions from any section and try them this month. Small, consistent steps lead to big impact over time. 🌱")
    lines.append("")
    lines.append("Regards,")
    lines.append("Sustainability Assistant")

    return "\n".join(lines)


# ---------- EMAIL FUNCTION (SAME BEHAVIOUR AS YOUR FLASK) ----------
def send_recommendation_email(to_email, name, emission_value, inputs=None, suggestions=None):
    sender_email = "vanshikaaaaaa04@gmail.com"
    sender_password = "wvapoaojkoqtpnev"  # move to .env for real deployment

    # If we got detailed inputs, build full personalised body
    if inputs:
        subject = "Your Personalised Monthly Carbon Emission Report 🌍"
        body = build_personalised_body(name, emission_value, inputs)
    else:
        # Fallback to simple 3-line suggestions (backwards compatible)
        if not suggestions:
            suggestions = ["Use LED bulbs", "Cycle for short trips", "Compost waste"]
        subject = "Your Monthly Carbon Emission Report 🌍"
        body = f"""
Hi {name},

Your estimated carbon footprint for this month is: {emission_value:.2f} kg CO₂.

Here are some personalised suggestions to help reduce your emissions:
- {suggestions[0]}
- {suggestions[1]}
- {suggestions[2]}

Every small step counts 🌱 — together, we can make a difference!

Regards,
Sustainability Assistant
"""

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print("✅ Email sent successfully!")
            return True, "Email sent successfully!"
    except Exception as e:
        print("❌ Error sending email:", e)
        return False, f"Error sending email: {e}"


# ---------- GEMINI CHAT CALL (MATCHES YOUR /chat ENDPOINT PROMPT) ----------
def call_gemini(user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API key not configured on server."

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "You are a friendly sustainability assistant for an "
                            "Answer in 2–3 short sentences and more points if required, make it use friendly: "
                            + user_message
                        )
                    }
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    try:
        resp = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        reply = "Sorry, I couldn't generate a reply."
        try:
            reply = data["candidates"][0]["content"]["parts"][0].get("text", reply)
        except (KeyError, IndexError, TypeError):
            print("⚠️ Unexpected Gemini response format:", data)
        return reply
    except requests.exceptions.HTTPError as e:
        print("❌ Gemini HTTP error:", e.response.text)
        return f"Gemini HTTP error: {e.response.text}"
    except Exception as e:
        print("❌ Gemini request error:", repr(e))
        return f"Gemini request error: {e}"


# ----------------- STREAMLIT UI ----------------- #
st.set_page_config(
    page_title="Carbon Emission Measurement",
    page_icon="🌱",
    layout="centered"
)

st.title("Carbon Emission Measurement & Forecasting")
st.caption("SDG 13 (Climate Action) — measurement • awareness • action")

tab_home, tab_calc, tab_chat, tab_news = st.tabs(["Home", "Calculator", "Chatbot", "Govt resources"])

# ---------- HOME (same content as HTML) ----------
with tab_home:
    st.header("Why this study matters")
    st.markdown(
        "Climate change is already affecting communities, economies and ecosystems across India and the world. "
        "Individual lifestyle choices — in transport, energy use, diet, and waste — add up to national emissions. "
        "This study builds a simple, data-driven tool to measure personal carbon output, forecast trends and provide "
        "practical steps users can take to reduce impact."
    )

    st.subheader("Our goal")
    st.markdown(
        "To empower citizens with clear, research-backed information so they can act. "
        "The system estimates weekly and monthly emissions, highlights the major sources of a user’s footprint, "
        "offers personalized recommendations, and uses predictive analytics to show the future impact of behaviour change."
    )

    st.subheader("Why adopt sustainable choices?")
    st.markdown(
        "1) Reduce personal contribution to greenhouse gases and slow warming.  \n"
        "2) Save money through energy efficiency and smarter travel.  \n"
        "3) Strengthen local resilience to extreme weather (heatwaves, floods, drought).  \n"
        "4) Support national goals: India’s climate commitments depend on both policy and behaviour change."
    )

    st.subheader("How this tool helps")
    st.markdown(
        "By translating complex emission science into simple numbers and tailored suggestions: visualize your footprint, "
        "compare habits, and get short, actionable tips you can implement this week. This nudges sustained behaviour change."
    )

    st.markdown("---")
    st.subheader("SDG 13 — Climate Action")
    st.markdown(
        "SDG 13 asks countries and individuals to strengthen resilience and adaptive capacity to climate hazards, "
        "integrate climate measures into policy, and improve education and awareness. "
        "Individual action complements policy and technology."
    )

    st.markdown("**Quick actions you can take today**")
    st.markdown(
        "- Switch to LED bulbs & unplug idle devices  \n"
        "- Use public transport / cycle for short trips  \n"
        "- Reduce red-meat consumption; prefer plant-based meals  \n"
        "- Compost organic waste; avoid single-use plastics  \n"
        "- Support local tree-planting and energy-efficiency programs"
    )

# ---------- CALCULATOR (same inputs + logic + email + breakdown) ----------
with tab_calc:
    st.header("Carbon Footprint Calculator")
    st.caption("Enter your monthly details — the calculator will estimate your total carbon emissions for one month.")

    email = st.text_input("Email address (to receive personalized report)")
    name = st.text_input("Your name (optional)", value="User")

    st.markdown("### Energy")
    electricity = st.number_input("Electricity usage (kWh/month)", min_value=0.0, value=150.0, step=10.0)
    electricity_source = st.selectbox("Source of electricity", ["coal", "renewable", "mixed"])
    lpg = st.number_input("LPG / natural gas usage (kg/month)", min_value=0.0, value=10.0, step=1.0)

    st.markdown("### Transport")
    vehicle_type = st.selectbox("Vehicle type", ["car", "bike", "bus", "train", "none"])
    travel = st.number_input("Distance travelled (km/month)", min_value=0.0, value=300.0, step=10.0)
    efficiency = st.number_input("Vehicle fuel efficiency (km/litre or km/kWh)", min_value=0.0, value=15.0, step=1.0)

    st.markdown("### Food & Waste")
    diet = st.selectbox("Diet type", ["veg", "nonveg", "vegan", "mixed"])
    waste = st.number_input("Waste generated (kg/month)", min_value=0.0, value=20.0, step=1.0)

    st.markdown("### Household & Renewables")
    household = st.number_input("Number of people in household", min_value=1, value=4, step=1)
    renewable = st.number_input("Renewable energy usage (%)", min_value=0.0, max_value=100.0, value=30.0, step=5.0)

    if st.button("Calculate Monthly Emissions"):
        # Same emission model as JS
        energy_emission = electricity * 0.8
        transport_emission = travel * 0.12
        waste_emission = waste * 0.4
        diet_extra = 0
        if diet == "mixed":
            diet_extra = 5
        elif diet == "nonveg":
            diet_extra = 10

        emission_value = energy_emission + transport_emission + waste_emission + diet_extra
        st.success(f"Estimated monthly emissions: **{emission_value:.2f} kg CO₂e**")

        # Build suggestions (same logic style as JS)
        suggestions = []

        # Energy-related
        if electricity > 250:
            suggestions.append(
                "Your electricity use is quite high. Shift fully to LED bulbs, keep AC at 24–26°C, "
                "and unplug chargers/devices when not in use to reduce demand."
            )
        elif electricity > 100:
            suggestions.append(
                "Focus on home energy efficiency: use LED bulbs, switch off fans/lights when you leave the room, "
                "and run washing machines only with full loads."
            )

        # Transport-related
        if (vehicle_type in ["car", "bike"]) and travel > 300:
            suggestions.append(
                "Your private vehicle travel is a major source of emissions. Try carpooling, using public transport, "
                "and combining errands so you drive fewer kilometres."
            )
        elif (vehicle_type in ["car", "bike"]) and travel > 100:
            suggestions.append(
                "Replace some short private vehicle trips with walking, cycling, or public transport to cut fuel use and emissions."
            )
        elif vehicle_type in ["bus", "train"]:
            suggestions.append(
                "You already use public transport. Keep it up, and consider walking or cycling for very short distances."
            )

        # Diet-related
        if diet in ["nonveg", "mixed"]:
            suggestions.append(
                "Your diet includes animal products. Reduce red meat and add more plant-based meals 2–3 days a week "
                "to lower food-related emissions."
            )
        elif diet in ["veg", "vegan"]:
            suggestions.append(
                "Your diet is already climate-friendly. Continue focusing on seasonal, local foods and avoid food waste."
            )

        # Waste-related
        if waste > 30:
            suggestions.append(
                "You generate quite a lot of waste. Start segregating at source, compost kitchen scraps, "
                "and cut down on single-use plastics."
            )
        elif waste > 15:
            suggestions.append(
                "Work on reducing waste by buying only what you need, reusing containers, and saying no to single-use plastics."
            )

        # Renewable share
        if renewable < 20:
            suggestions.append(
                "Increase your share of renewable energy over time — explore rooftop solar or green power options if they are available in your area."
            )

        # Ensure at least 3 suggestions
        generic = [
            "Carry your own water bottle and cloth bag to avoid single-use plastics.",
            "Plant native trees or support local tree-planting drives.",
            "Review one habit each week (energy, travel, food, or waste) and try a small improvement.",
        ]
        for g in generic:
            if len(suggestions) >= 3:
                break
            suggestions.append(g)

        email_suggestions = suggestions[:3]
        top_suggestion = email_suggestions[0] if email_suggestions else \
            "Reduce electricity use or avoid short solo car trips."

        st.markdown(f"**Top suggestion:** *{top_suggestion}*")
        if len(email_suggestions) > 1:
            st.markdown("**Other key suggestions:**")
            for s in email_suggestions[1:]:
                st.markdown(f"- {s}")

        # Emission breakdown chart
        st.markdown("### Emission breakdown")
        st.bar_chart({
            "Energy": [energy_emission],
            "Transport": [transport_emission],
            "Waste": [waste_emission],
            "Diet extra": [diet_extra],
        })

        # Inputs dict for email (same as in JS → Flask)
        inputs = {
            "electricity": electricity,
            "electricitySource": electricity_source,
            "lpg": lpg,
            "vehicleType": vehicle_type,
            "travel": travel,
            "efficiency": efficiency,
            "diet": diet,
            "waste": waste,
            "household": household,
            "renewable": renewable,
        }

        if email:
            ok, msg = send_recommendation_email(email, name or "User", emission_value, inputs, email_suggestions)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
        else:
            st.info("Enter your email above if you want this personalised report in your inbox.")

# ---------- CHATBOT (Gemini, same prompt style as your Flask /chat) ----------
with tab_chat:
    st.header("Sustainability Chatbot")
    st.caption("Ask about saving energy, food emissions, recycling...")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_q = st.text_input("Type your question here:")

    if st.button("Send"):
        if user_q.strip():
            reply = call_gemini(user_q.strip())
            st.session_state.chat_history.append(("You", user_q.strip()))
            st.session_state.chat_history.append(("Bot", reply))
        else:
            st.warning("Please type a question first.")

    for speaker, text in st.session_state.chat_history:
        if speaker == "You":
            st.markdown(f"**You:** {text}")
        else:
            st.markdown(f"**Bot:** {text}")

# ---------- GOVT RESOURCES (same links) ----------
with tab_news:
    st.header("Latest (Central & State) — Official updates & resources")
    st.caption(
        "Curated from central ministries and state climate action portals — "
        "authoritative sources for policy, guidance and programs."
    )

    st.markdown("**Central & key institutions**")
    st.markdown(
        "- [Press Information Bureau (PIB)](https://pib.gov.in/) — Govt press releases on climate & COP updates\n"
        "- [Ministry of Environment, Forest & Climate Change (MoEFCC)](https://moef.gov.in/) — NAPCC, Annual Report\n"
        "- [NITI Aayog](https://niti.gov.in/) — policy reports, climate dashboards\n"
        "- [Central Pollution Control Board (CPCB)](https://cpcb.nic.in/) — technical guidelines & SOPs"
    )

    st.markdown("**State-level examples**")
    st.markdown(
        "- [Maharashtra SDMA](https://sdma.maharashtra.gov.in/) — State Disaster Management Authority\n"
        "- [Karnataka EMPRI](https://empri.karnataka.gov.in/) — Environmental Management & Policy Research Institute"
    )

st.markdown("---")
st.caption("Content curated from official government sources (MoEFCC, PIB, NITI Aayog, CPCB, State portals).")
