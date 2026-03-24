"""Generate embeddings for HRS Exit codebook variables using AWS Bedrock.

Reads Elastic/data/hrs_exit_codebook/**/variables_index.json, builds content per variable,
writes records.jsonl, doc_ids.txt, embedding shards (.npy), and embeddings_manifest.json
to AWS/data/embeddings/exit/ (or OUT_DIR).

Requires AWS Bedrock access (boto3 credentials).
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

try:
    from ._common_hrs import run
except ImportError:
    from _common_hrs import run

if __name__ == "__main__":
    run("exit")
