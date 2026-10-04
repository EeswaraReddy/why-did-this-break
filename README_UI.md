# Why Did This Break? — UI

Streamlit console for the AI SRE POC. It is designed to compare **LLM Only** vs **LLM + Decider 2B** and show trajectory, evaluation, observability and decision-gate information without relying on terminal output.

## Files
- `app.py` — Streamlit dashboard
- `run_engine.py` — structured run engine
- `requirements-ui.txt` — UI dependencies

## Run from the project root
Copy these files into `why-did-this-break/`, then:

```powershell
pip install -r requirements-ui.txt
streamlit run app.py
```

The existing Decider service should remain running for the Decider mode:

```powershell
strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8099
```

The UI expects the existing `data/incidents/s3_access_denied.json`, `src/tools.py`, and `src/evaluation.py` to remain in the project.
