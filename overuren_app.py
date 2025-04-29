import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# === SETTINGS ===
SHEET_NAME = "OverurenApp"
TAB_OVERUREN = "Overuren"
TAB_RECUP = "Recup"

# === Connectie maken ===
def connect_to_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    return client

client = connect_to_sheets()
sheet_overuren = client.open(SHEET_NAME).worksheet(TAB_OVERUREN)
sheet_recup = client.open(SHEET_NAME).worksheet(TAB_RECUP)

def load_data(sheet):
    try:
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame(columns=["Datum", "Type", "Aantal Uren (+) of (-)", "Opmerking"])

# === App layout ===
st.set_page_config("Overurenregistratie", layout="wide")
tab1, tab2 = st.tabs(["📋 Registratie", "🛠️ Beheer"])

# === 📋 TAB 1 – Registratie ===
with tab1:
    st.title("⏱️ Overuren & Recup Registratie")

    keuze = st.radio("Wat wil je registreren?", ["Overuren", "Recup"], horizontal=True)
    sheet = sheet_overuren if keuze == "Overuren" else sheet_recup

    with st.form("registratie_form", clear_on_submit=True):
        datum = st.date_input("Datum", datetime.today())
        col1, col2 = st.columns(2)
        with col1:
            starttijd = st.text_input("Starttijd (HH:MM)", value="08:00")
        with col2:
            eindtijd = st.text_input("Eindtijd (HH:MM)", value="17:00")
        opmerking = st.text_input("Opmerking")

        if st.form_submit_button("➕ Toevoegen"):
            try:
                start_dt = datetime.strptime(starttijd, "%H:%M")
                eind_dt = datetime.strptime(eindtijd, "%H:%M")
                if eind_dt < start_dt:
                    eind_dt += timedelta(days=1)

                aantal_uren = round((eind_dt - start_dt).total_seconds() / 3600, 2)
                formatted = "{:.2f}".format(aantal_uren if keuze == "Overuren" else -aantal_uren)

                nieuwe_regel = [
                    datum.strftime("%Y-%m-%d"),
                    keuze,
                    formatted,
                    opmerking
                ]

                sheet.append_row(nieuwe_regel)
                st.success("✅ Toegevoegd!")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Ongeldige tijd. Gebruik HH:MM formaat (bijv. 08:30).")

    # Overzicht
    overuren_df = load_data(sheet_overuren)
    recup_df = load_data(sheet_recup)

    st.subheader("📄 Overzicht Overuren")
    if overuren_df.empty:
        st.info("Nog geen overuren geregistreerd.")
    else:
        st.dataframe(overuren_df, use_container_width=True)

    st.subheader("📄 Overzicht Recup")
    if recup_df.empty:
        st.info("Nog geen recup geregistreerd.")
    else:
        st.dataframe(recup_df, use_container_width=True)

    # Saldo
    totaal_overuren = pd.to_numeric(overuren_df["Aantal Uren (+) of (-)"], errors="coerce").sum() if not overuren_df.empty else 0
    totaal_recup = pd.to_numeric(recup_df["Aantal Uren (+) of (-)"], errors="coerce").sum() if not recup_df.empty else 0
    saldo = totaal_overuren + totaal_recup

    st.markdown(f"### 💼 Huidig saldo uren")
    st.metric("Totaal", f"{round(saldo, 2)} uur")


# === 🛠️ TAB 2 – Beheer ===
with tab2:
    st.title("🛠️ Bestaande registraties beheren")

    keuze = st.radio("Welke gegevens wil je beheren?", ["Overuren", "Recup"], horizontal=True)
    sheet = sheet_overuren if keuze == "Overuren" else sheet_recup
    df = load_data(sheet)

    if df.empty:
        st.info("Geen registraties gevonden.")
    else:
        df["__label__"] = df["Datum"] + " – " + df["Opmerking"]
        selectie = st.selectbox("Selecteer registratie:", df["__label__"])
        index = df[df["__label__"] == selectie].index[0]
        geselecteerde = df.loc[index]

        with st.form("bewerken_formulier"):
            datum = st.date_input("Datum", pd.to_datetime(geselecteerde["Datum"]))
            starttijd = st.text_input("Starttijd (HH:MM)", value="08:00")
            eindtijd = st.text_input("Eindtijd (HH:MM)", value="17:00")
            opmerking = st.text_input("Opmerking", geselecteerde["Opmerking"])

            if st.form_submit_button("✅ Wijzig opslaan"):
                try:
                    start_dt = datetime.strptime(starttijd, "%H:%M")
                    eind_dt = datetime.strptime(eindtijd, "%H:%M")
                    if eind_dt < start_dt:
                        eind_dt += timedelta(days=1)

                    aantal_uren = round((eind_dt - start_dt).total_seconds() / 3600, 2)
                    formatted = "{:.2f}".format(aantal_uren if keuze == "Overuren" else -aantal_uren)

                    nieuwe_regel = [
                        datum.strftime("%Y-%m-%d"),
                        keuze,
                        formatted,
                        opmerking
                    ]

                    sheet.update(f"A{index + 2}:D{index + 2}", [nieuwe_regel])
                    st.success("✅ Registratie aangepast")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Fout bij aanpassen: {e}")
