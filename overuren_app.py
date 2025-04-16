import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

BESTAND = "overuren.csv"

# === Functies ===
def laad_data():
    try:
        df = pd.read_csv(BESTAND)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["Datum", "Type", "Starttijd", "Eindtijd", "Uren", "Opmerking"])

def bewaar_data(df):
    df.to_csv(BESTAND, index=False)

def bereken_uren(starttijd, eindtijd):
    try:
        start = datetime.strptime(starttijd, "%H:%M")
        end = datetime.strptime(eindtijd, "%H:%M")
        if end < start:
            end += timedelta(days=1)
        diff = end - start
        return round(diff.total_seconds() / 3600, 2)
    except:
        return None

# === Interface ===
st.set_page_config("Overuren Tracker", layout="centered")
st.title("⏱️ Overuren & Recup Tracker")

data = laad_data()

# === Nieuwe registratie ===
st.subheader("➕ Nieuwe registratie")

with st.form("toevoeg_formulier", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        datum = st.date_input("Datum", datetime.today())
        starttijd = st.text_input("Starttijd (HH:MM)")
    with col2:
        eindtijd = st.text_input("Eindtijd (HH:MM)")
        type_ = st.selectbox("Type", ["Overuren", "Recup"])
    opm = st.text_input("Opmerking")

    submitted = st.form_submit_button("Toevoegen")
    if submitted:
        uren = bereken_uren(starttijd, eindtijd)
        if uren is None or uren <= 0:
            st.error("❌ Tijdformaat ongeldig of eindtijd ligt vóór starttijd.")
        else:
            if type_ == "Recup":
                uren *= -1
            nieuwe = pd.DataFrame([{
                "Datum": datum.strftime("%Y-%m-%d"),
                "Type": type_,
                "Starttijd": starttijd,
                "Eindtijd": eindtijd,
                "Uren": uren,
                "Opmerking": opm
            }])
            data = pd.concat([data, nieuwe], ignore_index=True)
            bewaar_data(data)
            st.success("✅ Registratie toegevoegd")

# === Filters ===
st.subheader("📋 Overzicht & filters")

maanden = ["Alle"] + [datetime(2025, m, 1).strftime("%B") for m in range(1, 13)]
jaren = ["Alle"] + sorted(data["Datum"].str[:4].unique(), reverse=True)
types = ["Alle", "Overuren", "Recup"]

col1, col2, col3 = st.columns(3)
maand = col1.selectbox("Maand", maanden)
jaar = col2.selectbox("Jaar", jaren)
type_filter = col3.selectbox("Type", types)

# === Filter logica ===
gefilterd = data.copy()

if maand != "Alle":
    maand_nr = datetime.strptime(maand, "%B").month
    gefilterd = gefilterd[pd.to_datetime(gefilterd["Datum"]).dt.month == maand_nr]

if jaar != "Alle":
    gefilterd = gefilterd[gefilterd["Datum"].str.startswith(jaar)]

if type_filter != "Alle":
    gefilterd = gefilterd[gefilterd["Type"] == type_filter]

# Sorteer meest recent bovenaan
gefilterd = gefilterd.sort_values("Datum", ascending=False).reset_index(drop=True)

# === Bewerken van record ===
st.subheader("✏️ Bewerken of verwijderen")

if gefilterd.empty:
    st.info("Geen resultaten gevonden voor de huidige filters.")
else:
    bewerk_index = st.selectbox("Selecteer een lijn om te bewerken", gefilterd.index, format_func=lambda i: f"{gefilterd.loc[i, 'Datum']} | {gefilterd.loc[i, 'Starttijd']}-{gefilterd.loc[i, 'Eindtijd']} | {gefilterd.loc[i, 'Type']}")

    with st.form("bewerk_form"):
        record = gefilterd.loc[bewerk_index]
        datum_edit = st.date_input("Datum", datetime.strptime(record["Datum"], "%Y-%m-%d"), key="edit_datum")
        type_edit = st.selectbox("Type", ["Overuren", "Recup"], index=["Overuren", "Recup"].index(record["Type"]), key="edit_type")
        start_edit = st.text_input("Starttijd", record["Starttijd"], key="edit_start")
        eind_edit = st.text_input("Eindtijd", record["Eindtijd"], key="edit_eind")
        opm_edit = st.text_input("Opmerking", record["Opmerking"], key="edit_opm")

        col_a, col_b = st.columns(2)
        if col_a.form_submit_button("Verwijderen", type="secondary"):
            data = data.drop(gefilterd.index[bewerk_index]).reset_index(drop=True)
            bewaar_data(data)
            st.success("❌ Record verwijderd")
            st.rerun()

        if col_b.form_submit_button("Opslaan wijziging"):
            nieuwe_uren = bereken_uren(start_edit, eind_edit)
            if nieuwe_uren is None or nieuwe_uren <= 0:
                st.error("❌ Ongeldige tijd of negatief resultaat.")
            else:
                if type_edit == "Recup":
                    nieuwe_uren *= -1
                index_in_data = gefilterd.index[bewerk_index]
                data.loc[index_in_data] = {
                    "Datum": datum_edit.strftime("%Y-%m-%d"),
                    "Type": type_edit,
                    "Starttijd": start_edit,
                    "Eindtijd": eind_edit,
                    "Uren": nieuwe_uren,
                    "Opmerking": opm_edit
                }
                bewaar_data(data)
                st.success("✅ Wijziging opgeslagen")
                st.rerun()

# === Overzichtstabel en saldo ===
st.subheader("📊 Overzicht")

st.dataframe(gefilterd, use_container_width=True)

saldo = gefilterd["Uren"].sum()
st.markdown(f"### 💼 Saldo in selectie: **{round(saldo, 2)} uur**")
