import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# === SETTINGS ===
SHEET_NAME = "OverurenRegistratie"
TAB_OVERUREN = "Overuren"
TAB_RECUP = "Recup"

# === Connectie naar Google Sheets ===
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

# === Data laden ===
def load_overuren():
    data = sheet_overuren.get_all_records()
    return pd.DataFrame(data)

def load_recup():
    data = sheet_recup.get_all_records()
    return pd.DataFrame(data)

# === App Interface ===
st.set_page_config("Overuren Tracker", layout="wide")
tab1, tab2 = st.tabs(["🕒 Registratie", "⚙️ Beheer"])

# === 🕒 TAB 1: Registreren ===
with tab1:
    st.title("🕒 Overuren en Recup Registratie")

    keuze = st.radio("Wat wil je registreren?", ["Overuren", "Recup"])

    with st.form("registratie_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            datum = st.date_input("Datum", datetime.today())
            starttijd_str = st.text_input("Starttijd (HH:MM)", "08:30")
        with col2:
            eindtijd_str = st.text_input("Eindtijd (HH:MM)", "17:00")
            opmerking = st.text_input("Opmerking")

        if st.form_submit_button("➕ Toevoegen"):
            try:
                start_dt = datetime.strptime(starttijd_str, "%H:%M")
                eind_dt = datetime.strptime(eindtijd_str, "%H:%M")

                if eind_dt < start_dt:
                    eind_dt += timedelta(days=1)

                aantal_uren = round((eind_dt - start_dt).total_seconds() / 3600, 2)

                nieuwe_regel = [
                    datum.strftime("%Y-%m-%d"),
                    keuze,
                    round(float(aantal_uren), 2) if keuze == "Overuren" else round(-float(aantal_uren), 2),
                    opmerking
                ]

                if keuze == "Overuren":
                    sheet_overuren.append_row(nieuwe_regel)
                    st.success("✅ Overuren toegevoegd!")
                else:
                    sheet_recup.append_row(nieuwe_regel)
                    st.success("✅ Recup toegevoegd!")

                st.rerun()
            except ValueError:
                st.error("❌ Ongeldig tijdformaat. Gebruik HH:MM zoals 08:30 of 17:15.")

    st.divider()

    overuren_df = load_overuren()
    recup_df = load_recup()

    st.subheader("📄 Overzicht Overuren")
    if not overuren_df.empty:
        st.dataframe(overuren_df, use_container_width=True)
    else:
        st.info("Nog geen overuren geregistreerd.")

    st.subheader("📄 Overzicht Recup")
    if not recup_df.empty:
        st.dataframe(recup_df, use_container_width=True)
    else:
        st.info("Nog geen recup geregistreerd.")

    st.divider()

    totaal_overuren = pd.to_numeric(overuren_df["Aantal Uren (+) of (-)"], errors="coerce").sum() if not overuren_df.empty else 0
    totaal_recup = pd.to_numeric(recup_df["Aantal Uren (+) of (-)"], errors="coerce").sum() if not recup_df.empty else 0
    saldo = totaal_overuren + totaal_recup

    st.metric(label="💼 Huidig saldo uren", value=f"{saldo:.2f} uur")

# === ⚙️ TAB 2: Beheer bestaande registraties ===
with tab2:
    st.title("⚙️ Bestaande registraties beheren")

    selectie = st.radio("Welke gegevens wil je beheren?", ["Overuren", "Recup"])

    if selectie == "Overuren":
        df = load_overuren()
        sheet = sheet_overuren
    else:
        df = load_recup()
        sheet = sheet_recup

    if not df.empty:
        df["__label__"] = df["Datum"] + " – " + df["Opmerking"]
        geselecteerd = st.selectbox("Selecteer registratie:", df["__label__"])

        index = df[df["__label__"] == geselecteerd].index[0]
        record = df.loc[index]

        with st.form("bewerken_form"):
            edit_datum = st.date_input("Datum", pd.to_datetime(record["Datum"]))
            edit_start = st.text_input("Starttijd (HH:MM)", "08:00")
            edit_end = st.text_input("Eindtijd (HH:MM)", "17:00")
            edit_opmerking = st.text_input("Opmerking", record["Opmerking"])

            col1, col2 = st.columns([2, 1])
            with col1:
                if st.form_submit_button("✅ Wijzig opslaan"):
                    try:
                        s_dt = datetime.strptime(edit_start, "%H:%M")
                        e_dt = datetime.strptime(edit_end, "%H:%M")
                        if e_dt < s_dt:
                            e_dt += timedelta(days=1)
                        uren = round((e_dt - s_dt).total_seconds() / 3600, 2)

                        nieuwe_data = [
                            edit_datum.strftime("%Y-%m-%d"),
                            selectie,
                            uren if selectie == "Overuren" else -uren,
                            edit_opmerking
                        ]
                        sheet.update(f"A{int(index)+2}:D{int(index)+2}", [nieuwe_data])
                        st.success("✅ Wijziging opgeslagen!")
                        st.rerun()
                    except ValueError:
                        st.error("❌ Ongeldige tijd. Gebruik HH:MM (zoals 07:30).")
            with col2:
                if st.form_submit_button("🗑️ Verwijder registratie"):
                    sheet.delete_rows(int(index) + 2)
                    st.success("🗑️ Registratie verwijderd!")
                    st.rerun()
    else:
        st.info(f"Nog geen {selectie.lower()} geregistreerd.")
