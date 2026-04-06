# Lab 3 Test Cases

Expected vs actual results for quick validation.

| # | Prompt | Expected | Actual |
|---|---|---|---|
| 1 | Find stock of iPhone, then calculate total with tax. | Agent calls `check_stock` then `apply_tax`, returns total `15840.0`. | (run `python lab3/agent.py`) |
| 2 | What is the capital of France? | Both chatbot and agent answer `Paris`. | (run `python lab3/agent.py`) |
| 3 | Find stock of AirPods, then calculate total with tax. | Agent can adapt tool calls when prompt/model logic updated. | Pending |
| 4 | Find stock of UnknownPhone. | Tool returns item-not-found observation. | Pending |
| 5 | Hello there | Chatbot baseline returns simple generic response. | Pending |

## Run

```bash
python lab3/agent.py
```

Logs are appended to `logs/YYYY-MM-DD.log`.
