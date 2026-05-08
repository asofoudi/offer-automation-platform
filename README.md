# Unified Streamlit App

This repository contains a unified Streamlit shell for the existing business
apps. The migrated pages are:

- Heat-pump questionnaire
- Solar-water-heater questions and proposal calculator
- Insulation BOM and pricing
- Radiator pricing

The old repositories/files are not modified. Their business logic has been
refactored into `utils/`, while each Streamlit screen lives under `pages/`.

## Run

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## Structure

```text
app.py
pages/
  01_Heat_Pump_Questionnaire.py
  02_Solar_Questions.py
  03_Insulation.py
  04_Radiators.py
data/
  insulation_prices.csv
  radiators.csv
utils/
  heat_pump_questionnaire.py
  insulation.py
  radiators.py
  solar_questions.py
```
