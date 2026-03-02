FROM python:3.13-slim
RUN pip install --no-cache-dir pandas numpy scipy scikit-learn
COPY sandbox/entrypoint.py /sandbox/entrypoint.py
ENTRYPOINT ["python", "/sandbox/entrypoint.py"]
