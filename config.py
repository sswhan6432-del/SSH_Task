"""Shared configuration constants for SSH_WEB.

Single source of truth for cost tables, token estimates,
and other shared values used across v1 API and analytics.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_VERCEL = os.environ.get("VERCEL", "") == "1"

if IS_VERCEL:
    DATA_DIR = "/tmp/ssh_web_data"
    os.makedirs(DATA_DIR, exist_ok=True)
else:
    DATA_DIR = os.path.join(BASE_DIR, "data")

WEBSITE_DIR = os.path.join(BASE_DIR, "website")

if IS_VERCEL:
    HISTORY_FILE = os.path.join(DATA_DIR, "task_history.json")
    PROMPTS_FILE = os.path.join(DATA_DIR, "prompts.json")
    FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.json")
else:
    HISTORY_FILE = os.path.join(BASE_DIR, "task_history.json")
    PROMPTS_FILE = os.path.join(BASE_DIR, "prompts.json")
    FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.json")

TOKEN_USAGE_FILE = os.path.join(DATA_DIR, "token_usage.json")

DEFAULT_PORT = 8080

# Cost per 1K tokens for v1 route types (legacy estimation)
ROUTE_COST_PER_1K = {
    "claude": 0.015,
    "cheap_llm": 0.0005,
    "split": 0.008,
}

# Estimated tokens per task for v1 route types (legacy estimation)
ROUTE_TOKENS_PER_TASK = {
    "claude": 2000,
    "cheap_llm": 500,
    "split": 1200,
}

DEFAULT_COST_PER_1K = 0.01
DEFAULT_TOKENS_PER_TASK = 1000
