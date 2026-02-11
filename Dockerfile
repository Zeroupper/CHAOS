FROM python:3.13-slim
RUN pip install --no-cache-dir pandas numpy scipy scikit-learn
COPY sandbox/executor.py /sandbox/executor.py
ENTRYPOINT ["python", "/sandbox/executor.py"]
