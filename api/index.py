"""Vercel serverless entry point.

Exposes the Flask WSGI app for @vercel/python runtime.
"""

import os
import sys

# Ensure project root is on sys.path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()
