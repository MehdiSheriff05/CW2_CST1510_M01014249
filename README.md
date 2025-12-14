# multi-domain intelligence platform

I built this Streamlit project as my CST1510 coursework. It glues together three areas (incident reporting, data analysis, and IT ticketing) plus a Gemini-powered chatbot. Everything lives in one repo, but I kept the code very student-friendly: short helper classes, and zero unnecessary abstractions.

---

## how I set it up locally

These are the exact steps I take on my laptop. Copy/paste them and you should end up with the same environment.

1. clone the repo
   ```bash
   git clone https://github.com/MehdiSheriff05/CW2_CST1510_M01014249.git
   cd CST1510_CW2
   ```
2. spin up a virtualenv (recommended but optional)
   ```bash
   python -m venv venv
   source venv/bin/activate  # windows uses venv\Scripts\activate
   ```
3. install the dependencies
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. grab a free gemini api key
   - visit [google ai studio](https://aistudio.google.com/app/apikey) and create a key (costs nothing)
   - set it in your terminal so python can see it:
     ```bash
     export GEMINI_API_KEY="paste-your-key-here"
     ```
   - drop the same value inside `.streamlit/secrets.toml` so streamlit reads it securely:
     ```toml
     GEMINI_API_KEY = "paste-your-key-here"
     ```
   - if you hate editing files, open the **settings** page inside the app, paste the key there, and save it for *this session only*. that path is nice for demos because nothing hits disk.
5. run the app
   ```bash
   streamlit run Dashboard.py
   ```
   streamlit starts on the dashboard but instantly forces you to `pages/Login.py`. use the built-in admin credentials (`admin` / `admin`) for full access. new registrations deliberately get no role, so the admin must promote them.

---

## folder tour (why the filenames are numbered)

```
Dashboard.py          # landing page with large dark-mode cards
pages/
  Login.py            # authentication form
  2_Incident_Reporting.py
  3_Data_Analysis.py
  4_IT_Ticketing_Dashboard.py
  6_User_Management.py
  7_Settings.py
  8_AI_Assistant.py
services/
  auth_manager.py
  database_manager.py
  config_manager.py
  ai_assistant.py
  ui_helpers.py
models/
  user.py
  security_incident.py
  dataset.py
  it_ticket.py
demo_data/
  security_incidents.csv
  datasets.csv
  it_tickets.csv
```

streamlit respects lexicographic ordering for multipage apps. adding the numeric prefixes keeps the sidebar predictable. the dashboard is unnumbered because it is the root script.

---

## core architecture

- **database_manager** sits on top of sqlite and exposes dead-simple helpers (`execute`, `fetch_one`, `fetch_all`). `create_tables()` is called once at startup to ensure `database/platform.db` has the four tables (`users`, `security_incidents`, `it_tickets`, `datasets`).
- **auth_manager** owns registration, bcrypt hashing, login checks, and role serialization. roles get stored as strings like `"cybersec_eng,it_ops"`. I keep them in session as a python list.
- **config_manager** now only knows about gemini. it defines the provider name, default model (`gemini-2.5-flash`), and the logic for picking the key (session override → `st.secrets` → environment → `.env`).
- **ai_assistant** wraps the Gemini SDK. if the `google-generativeai` package is missing, the code installs it automatically so no one trips over missing modules. prompts route straight to `genai.GenerativeModel`.
- **ui_helpers** hides the sidebar if someone isn’t logged in, renders the user badge, and provides a shared logout button. every page imports these helpers.
- **models** are thin classes used by different dashboards mainly to keep the data handling readable (e.g., `SecurityIncident.get_severity_level()`).

---

## how guarding and roles work

inside `pages/Login.py` I initialize:
```python
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("roles", [])
```

every page calls a guard such as:
```python
if not st.session_state.get("logged_in"):
    hide_sidebar()
    st.switch_page("pages/Login.py")

if "cybersec_eng" not in st.session_state.get("roles", []) and "admin" not in ...:
    st.error("access denied")
    st.stop()
```

that simple pattern means:
- guests instantly bounce back to the login screen, and the sidebar disappears so they can’t see the routes.
- role checks live near the top of each page, usually with a local constant like `ALLOWED_ROLES = {"cybersec_eng", "admin"}`.
- logging out clears those session keys and reruns the script, which returns everyone to the login form.

registration purposely adds users with the sentinel role `"none"`. admins open **user management**, pick the new account, and assign `cybersec_eng`, `data_analyst`, `it_ops`, or `admin`. nothing else grants access.

---

## UI notes (bootstrap-inspired grids)

I never imported Bootstrap, but I mimic its grids by using Streamlit columns:
- the incident, ticketing, and admin forms all use a three-column layout so fields sit side-by-side.
- the dashboard cards use CSS to get the dark blocks with hover effects. 
- analytics pages rely on Plotly with `width="stretch"` so charts fill the container, matching the rest of the layout.

---

## gemini chatbot details

- **model**: `gemini-2.5-flash` (works with the free key straight from Google AI Studio).
- **session behavior**: admins can go to the Settings page, paste the key, and select “save for this session”. that stores it inside `st.session_state` but never writes to disk. the same page also shows the current model/provider status.
- **chat page**: `pages/8_AI_Assistant.py` keeps history in `st.session_state["ai_chat_history"]`, lets you choose a domain summary, and calls the `AIAssistant` service when you submit a message. there’s a reset button and a clear button because I kept accidentally overwriting my prompts during testing.

---

## why this project reflects my journey

CS50 drilled the habit of breaking tasks into smaller files, commenting everything, and testing often. that mindset kept this repo sane:
- the three CSVs feed the “load demo data” buttons. I debugged those ETL steps the same way I debugged CS50 psets—print statements.
- I reused the problem-solving approach from CS50’s web track to design the role system: keep state in a dictionary, guard each route, show friendly errors.
- user friendly comments so that anyone is able to understand the code at first glance (`# check if user can access this page`, `# add ticket card to kanban board`). those comments echo how I narrate my code to anyone that i'm presenting to

---

## extra tips before you explore

- `database/platform.db` stays out of git. feel free to wipe it if you want a clean slate: just delete the file and rerun the app.
- every dashboard has a “load demo data” button that pulls rows from `demo_data/*.csv`. I left roughly ten to fifty records per domain so the charts look alive.
- thanks to the guarding logic, you always log in first. once authenticated, the dashboard shows big cards that re-direct to the permitted pages, plus the AI assistant page if your role allows it.
- the repo is intentionally lightweight, so you can extend it however you like—more analytics, different Gemini models, or even another domain page.

enjoy hacking on the multi-domain intelligence platform! if anything feels confusing, open the code and read the inline `#` notes—they mirror the explanations I gave above.

## demo video link
- https://youtu.be/injLRc-r96E
