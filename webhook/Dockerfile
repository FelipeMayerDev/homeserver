FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
# Install additional dependencies needed for shared/ai_tools.py
RUN pip install --no-cache-dir groq google-search-results

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]