import streamlit as st
import requests
import re
import leafmap.foliumap as leafmap

# ------------------------------
# Utility functions
# ------------------------------

def extract_location(text):
    text = text.lower()
    # Remove common filler words
    text = re.sub(r"(show|where is|locate|find|me|please|can you|display|on the map)", "", text)
    return text.strip()

def geocode_location(location):
    url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json"
    try:
        response = requests.get(url, headers={"User-Agent": "streamlit-app"})
        data = response.json()
        print(f"[DEBUG] Geocoding results for '{location}': {data}")
        if not data:
            return None, None
        return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"[DEBUG] Error in geocode_location: {e}")
        return None, None

def call_groq(prompt, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error from Groq: {response.status_code} - {response.text}"

# ------------------------------
# Streamlit UI
# ------------------------------

st.title("🗺️ GIS Mapping Chatbot (Groq + Nominatim)")

groq_api_key = st.text_input("Enter your Groq API Key", type="password")

if not groq_api_key:
    st.info("Please enter your Groq API key to continue.", icon="🔐")
else:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a location (e.g., 'Show me Shailer Park') or anything else"):

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Check if prompt likely contains a location request
        if any(x in prompt.lower() for x in ["show", "where is", "locate", "find"]):
            location = extract_location(prompt)
            lat, lon = geocode_location(location)
            if lat and lon:
                response = f"📍 **{location.title()}** is at:\n- Latitude: {lat:.4f}\n- Longitude: {lon:.4f}"
                with st.chat_message("assistant"):
                    st.markdown(response)

                    m = leafmap.Map(center=(lat, lon), zoom=13)
                    m.add_marker((lat, lon), popup=f"{location.title()}")
                    m.to_streamlit()

                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                # fallback to Groq if location not found
                fallback = call_groq(f"Where is {location}?", groq_api_key)
                with st.chat_message("assistant"):
                    st.markdown("❌ Could not locate on map. Here's what I found instead:\n\n" + fallback)
                st.session_state.messages.append({"role": "assistant", "content": fallback})
        else:
            # Pure chat response
            response = call_groq(prompt, groq_api_key)
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
