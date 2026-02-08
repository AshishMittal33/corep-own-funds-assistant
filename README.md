# PRA COREP Assistant

AI tool that helps banks fill regulatory forms automatically.

## What It Does
You describe a banking scenario in English, and it fills the COREP regulatory form for you.

## Quick Start

1. Install:
```bash
git clone https://github.com/AshishMittal33/corep-own-funds-assistant.git
cd corep-own-funds-assistant
pip install -r requirements.txt
```
2. Add your Groq API key (free from console.groq.com) to .env file:
```bash
GROQ_API_KEY=your_key_here
```
3. Run:
```bash
streamlit run app.py
```

## How It Works

You type this:
```bash
Bank has £50M shares, £20M premium, £80M earnings, £40M intangibles
```

It produces this COREP form:
```bash
Row  Description                    Amount
010  Ordinary share capital         £50,000,000
020  Share premium account          £20,000,000
030  Retained earnings              £80,000,000
070  (-) Intangible assets          (£40,000,000)
100  TOTAL CET1 CAPITAL             £110,000,000
```

And shows:

✅ Which banking rules were used

✅ Calculation: 50+20+80-40=110

✅ Any errors or missing data

Try These Examples

- "Bank has £150M shares, £75M premium, £300M earnings, £45M intangibles"

- "What fields are needed for CET1 reporting?"

- "Bank has £100M shares and £50M earnings only"

## Files

- app.py - Web interface

- corep_engine.py - Main code

- rules.txt - Banking regulations

- schema_c0100.json - Form template

## Demo

https://youtu.be/tYTNAVylQZc

## Author

Ashish Mittal
