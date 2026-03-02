"""RAG baseline: FAISS + sentence-transformers retrieval-augmented generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from pydantic import BaseModel

from chaos.llm.structured_client import StructuredLLMClient

RAG_SYSTEM_PROMPT = """\
You are a data analyst. Answer the user's question using ONLY the provided data context.
Do not make up data. If the context doesn't contain enough information, say so.
Be precise with numbers and cite the source data when possible.
"""


class RAGAnswer(BaseModel):
    answer: str
    confidence: float = 0.0


class RAGBaseline:
    """RAG baseline using FAISS + sentence-transformers for retrieval.

    build_index() creates the searchable index from CSV data.
    run() takes a query and an LLM client, retrieves relevant chunks,
    and generates an answer.
    """

    def __init__(self, top_k: int = 10) -> None:
        self.top_k = top_k
        self._chunks: list[str] = []
        self._index: Any = None
        self._embedder: Any = None

    def build_index(self, datasets_dir: Path, chunk_rows: int = 50) -> None:
        """Build FAISS index from dataset CSVs."""
        import faiss
        from sentence_transformers import SentenceTransformer

        self._embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self._chunks = []

        # Schema chunks from data_schema.yaml
        schema_path = datasets_dir / "data_schema.yaml"
        if schema_path.exists():
            with open(schema_path) as f:
                schema = yaml.safe_load(f)
            for name, ds_info in schema.get("datasets", {}).items():
                lines = [f"Dataset: {name}", f"Description: {ds_info.get('description', '')}"]
                for col, info in ds_info.get("columns", {}).items():
                    unit = f" [{info['unit']}]" if info.get("unit") else ""
                    desc = f": {info['description']}" if info.get("description") else ""
                    lines.append(f"  - {col} ({info.get('type', 'unknown')}){unit}{desc}")
                self._chunks.append("\n".join(lines))

        # Summary + row chunks from each CSV
        for csv_file in sorted(datasets_dir.glob("*.csv")):
            try:
                df = pd.read_csv(csv_file)
            except Exception:
                continue
            name = csv_file.stem

            # Statistical summary
            summary = f"Statistical summary for {name} ({len(df)} rows):\n"
            numeric = df.select_dtypes(include=[np.number])
            if not numeric.empty:
                summary += numeric.describe().to_string()
            for col in df.select_dtypes(include=["object"]).columns:
                vc = df[col].value_counts().head(10)
                if not vc.empty:
                    summary += f"\n\n{col} value counts (top 10):\n{vc.to_string()}"
            self._chunks.append(summary)

            # Row groups as markdown tables
            for start in range(0, len(df), chunk_rows):
                subset = df.iloc[start : start + chunk_rows]
                chunk = f"Data from {name} (rows {start}-{start + len(subset) - 1}):\n"
                chunk += subset.to_string(index=False)
                self._chunks.append(chunk)

        if not self._chunks:
            raise ValueError(f"No data found in {datasets_dir}")

        embeddings = self._embedder.encode(self._chunks, show_progress_bar=False)
        embeddings = np.array(embeddings, dtype=np.float32)
        self._index = faiss.IndexFlatL2(embeddings.shape[1])
        self._index.add(embeddings)

    def run(self, query: str, llm_client: StructuredLLMClient) -> dict[str, Any]:
        """Embed query, retrieve top-k chunks, generate answer."""
        if self._index is None or self._embedder is None:
            raise RuntimeError("Call build_index() first.")

        query_vec = np.array(self._embedder.encode([query]), dtype=np.float32)
        _, indices = self._index.search(query_vec, min(self.top_k, len(self._chunks)))
        retrieved = [self._chunks[i] for i in indices[0] if i < len(self._chunks)]
        context = "\n\n---\n\n".join(retrieved)

        result = llm_client.chat(
            messages=[{
                "role": "user",
                "content": f"Data context:\n{context}\n\nQuestion: {query}\n\nAnswer using ONLY the provided data.",
            }],
            response_model=RAGAnswer,
            system=RAG_SYSTEM_PROMPT,
        )

        return {
            "answer": result.answer,
            "confidence": result.confidence,
            "retrieved_chunks": retrieved,
        }
