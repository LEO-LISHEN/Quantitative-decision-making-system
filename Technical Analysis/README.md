# Technical Analysis

OpenAI-backed chart screenshot analysis module for the Quantitative Decision-Making System.

## Purpose

This module accepts:

- a user question
- optional chart screenshots as base64 image data URLs
- short conversation history

It returns a Chinese technical analysis covering chart observations, trend judgment, key levels, future scenarios, and risk notes.

## Runtime Entry

```python
from technical_service import TechnicalAnalysisService

service = TechnicalAnalysisService()
result = service.analyze(
    message="请分析这张日线图未来 1-2 周走势。",
    image_data_urls=["data:image/png;base64,..."],
    history=[],
)
```

## Configuration

The service reads environment variables from:

- project root `.env`
- `Technical Analysis/.env`

Supported variables:

```text
OPENAI_API_KEY=
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_TECHNICAL_ANALYSIS_MODEL=gpt-4.1-mini
OPENAI_TIMEOUT_SECONDS=90
OPENAI_TECHNICAL_MAX_OUTPUT_TOKENS=1800
```

## Notes

The module does not store uploaded screenshots. The frontend sends selected or pasted images as data URLs directly to the backend for the current request. Up to 6 screenshots are accepted per request.
