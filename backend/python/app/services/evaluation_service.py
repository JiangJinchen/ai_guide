from dataclasses import asdict, dataclass
import json
from pathlib import Path
from time import perf_counter


@dataclass
class EvaluationReport:
    mode: str
    queries: int
    hit_rate: float
    mrr: float
    average_latency_ms: float
    min_hit_rate: float
    min_mrr: float
    passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


def load_evaluation_cases(path: str | Path) -> list[dict]:
    cases = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if not case.get("query") or not case.get("expected"):
                raise ValueError(
                    f"evaluation case {line_number} requires query and expected"
                )
            cases.append(case)
    if not cases:
        raise ValueError("evaluation dataset is empty")
    return cases


def evaluate_search(
    search,
    cases: list[dict],
    mode: str,
    top_k: int = 3,
    min_hit_rate: float = 0.0,
    min_mrr: float = 0.0,
) -> EvaluationReport:
    hits = 0
    reciprocal_ranks = []
    latency_ms = []

    for case in cases:
        started = perf_counter()
        results = search(case["query"], top_k=top_k)
        latency_ms.append((perf_counter() - started) * 1000)
        rank = _first_relevant_rank(results, case["expected"])
        if rank is not None:
            hits += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

    query_count = len(cases)
    hit_rate = hits / query_count
    mrr = sum(reciprocal_ranks) / query_count
    average_latency = sum(latency_ms) / query_count
    return EvaluationReport(
        mode=mode,
        queries=query_count,
        hit_rate=round(hit_rate, 6),
        mrr=round(mrr, 6),
        average_latency_ms=round(average_latency, 3),
        min_hit_rate=min_hit_rate,
        min_mrr=min_mrr,
        passed=hit_rate >= min_hit_rate and mrr >= min_mrr,
    )


def _first_relevant_rank(results: list[dict], expected: list[dict]):
    for rank, result in enumerate(results, start=1):
        for target in expected:
            if _matches(result, target):
                return rank
    return None


def _matches(result: dict, target: dict) -> bool:
    for field in ("source_type", "source_id", "chunk_index"):
        if field in target and result.get(field) != target[field]:
            return False
    return True
