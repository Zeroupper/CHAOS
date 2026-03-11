"""RAG baseline: FAISS + sentence-transformers retrieval-augmented generation."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

from chaos.llm.structured_client import StructuredLLMClient

RAG_SYSTEM_PROMPT = """\
You are a data analyst. Answer the user's question using ONLY the provided data context.
Do not make up data. If the context doesn't contain enough information, say so.
Be precise with numbers and cite the source data when possible.
"""

MAX_CHUNK_CHARS = 3000


class RAGAnswer(BaseModel):
    answer: str


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

    def build_index(self, datasets_dir: Path) -> None:
        """Build FAISS index from dataset CSVs."""
        import faiss
        from sentence_transformers import SentenceTransformer

        self._embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self._chunks = []

        csv_files = sorted(datasets_dir.glob("**/*.csv"))
        print(f"  RAG: found {len(csv_files)} CSV files")
        for i, csv_file in enumerate(csv_files, 1):
            try:
                df = pd.read_csv(csv_file, low_memory=False)
            except Exception:
                continue
            name = csv_file.stem
            numeric = df.select_dtypes(include=[np.number])

            # Column listing
            self._chunks.append(
                f"Dataset {name} has {len(df)} rows and columns: {', '.join(df.columns)}"
            )

            # Column stats grouped by prefix (one chunk per group)
            if not numeric.empty:
                groups: dict[str, list[str]] = defaultdict(list)
                for col in numeric.columns:
                    prefix = col.split(":")[0] if ":" in col else "general"
                    groups[prefix].append(col)
                for prefix, cols in groups.items():
                    stats = numeric[cols].describe().T.to_string()
                    self._chunks.append(
                        f"Stats for {name} [{prefix}] ({len(cols)} columns, {len(df)} rows):\n{stats}"
                    )

            # Row batches (50 rows per chunk with column names)
            batch_size = 200
            for start in range(0, len(df), batch_size):
                batch = df.iloc[start : start + batch_size]
                self._chunks.append(
                    f"Rows from {name} ({start}-{start + len(batch) - 1} of {len(df)}):\n"
                    + batch.to_string(index=False)
                )

            print(f"  RAG: [{i}/{len(csv_files)}] {name}: {len(df)} rows x {len(df.columns)} cols")

        if not self._chunks:
            raise ValueError(f"No data found in {datasets_dir}")

        print(f"  RAG: embedding {len(self._chunks)} chunks...")
        embeddings = self._embedder.encode(self._chunks, show_progress_bar=True)
        embeddings = np.array(embeddings, dtype=np.float32)
        self._index = faiss.IndexFlatL2(embeddings.shape[1])
        self._index.add(embeddings)
        print(f"  RAG: index built ({self._index.ntotal} vectors)")

    def run(self, query: str, llm_client: StructuredLLMClient) -> dict[str, Any]:
        """Embed query, retrieve top-k chunks, generate answer."""
        if self._index is None or self._embedder is None:
            raise RuntimeError("Call build_index() first.")

        query_vec = np.array(self._embedder.encode([query]), dtype=np.float32)
        _, indices = self._index.search(query_vec, min(self.top_k, len(self._chunks)))
        retrieved = [self._chunks[i] for i in indices[0] if i < len(self._chunks)]
        # Cap each chunk to fit in context window
        retrieved = [c[:MAX_CHUNK_CHARS] for c in retrieved]
        context = "\n\n---\n\n".join(retrieved)

        user_prompt = f"Data context:\n{context}\n\nQuestion: {query}\n\nAnswer using ONLY the provided data."

        result = llm_client.chat(
            messages=[{"role": "user", "content": user_prompt}],
            response_model=RAGAnswer,
            system=RAG_SYSTEM_PROMPT,
        )

        return {
            "answer": result.answer,
            "retrieved_chunks": retrieved,
            "prompt": user_prompt,
        }
