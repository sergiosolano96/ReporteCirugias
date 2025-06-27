#!/bin/sh
gunicorn --bind 0.0.0.0:$PORT app_web:app
