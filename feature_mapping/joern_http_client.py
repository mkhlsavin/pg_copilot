"""HTTP-based Joern client for feature mapping using running Joern server."""
from __future__ import annotations

import json
import requests
from dataclasses import dataclass
from typing import List, Sequence, Optional
from .models import CandidateNode

OUTPUT_PREFIX = "__CANDIDATE__|"
DEFAULT_MAX_PER_KIND = 40


class JoernHTTPClientError(RuntimeError):
    """Raised when Joern HTTP requests fail."""


@dataclass(slots=True)
class JoernHTTPClient:
    """HTTP client for Joern server (running on localhost:8080)."""

    server_url: str = "http://localhost:8080"

    def execute_query(self, query: str, timeout: float = 120.0) -> dict:
        """Execute CPGQL query via HTTP API."""
        try:
            response = requests.post(
                f"{self.server_url}/query",
                json={"query": query},
                timeout=timeout
            )
            if response.status_code != 200:
                raise JoernHTTPClientError(
                    f"HTTP {response.status_code}: {response.text}"
                )
            return response.json()
        except requests.RequestException as e:
            raise JoernHTTPClientError(f"Request failed: {e}")

    def find_candidates(
        self,
        feature_name: str,
        tokens: Sequence[str],
        *,
        directory_hints: Sequence[str] | None = None,
        max_per_kind: int = DEFAULT_MAX_PER_KIND,
    ) -> List[CandidateNode]:
        """Return candidate nodes that match the given feature tokens."""
        script = _build_candidate_script(tokens, directory_hints or (), max_per_kind)
        result = self.execute_query(script)

        # Extract stdout from result
        if not result.get('success'):
            error_msg = result.get('stderr', result.get('err', 'Unknown error'))
            raise JoernHTTPClientError(f"Query failed: {error_msg}")

        stdout = result.get('stdout', result.get('out', ''))
        return _parse_candidate_output(stdout, feature_name, tokens)

    def tag_feature(
        self,
        feature_name: str,
        node_ids: list[int],
        *,
        batch_size: int = 50,
    ) -> None:
        """Attach a feature tag to each node id."""
        batches: List[List[int]] = []
        current: List[int] = []
        for node_id in node_ids:
            current.append(int(node_id))
            if len(current) >= batch_size:
                batches.append(current)
                current = []
        if current:
            batches.append(current)

        for batch in batches:
            script = _build_tag_script(feature_name, batch)
            result = self.execute_query(script)
            if not result.get('success'):
                error_msg = result.get('stderr', result.get('err', 'Unknown error'))
                raise JoernHTTPClientError(f"Tagging failed: {error_msg}")


def _scala_list(items: Sequence[str]) -> str:
    escaped = [json.dumps(item) for item in items]
    return f"List({', '.join(escaped)})"


def _build_candidate_script(tokens: Sequence[str], directory_hints: Sequence[str], max_per_kind: int) -> str:
    token_list = _scala_list([tok.lower() for tok in tokens if tok])
    hint_list = _scala_list([hint.lower() for hint in directory_hints if hint])
    return f"""
import io.shiftleft.semanticcpg.language._
import io.shiftleft.codepropertygraph.generated.nodes.StoredNode

val tokens: List[String] = {token_list}
val directoryHints: List[String] = {hint_list}
val maxPerKind: Int = {max_per_kind}

def normalise(text: String): String = text.toLowerCase

def matchesAll(text: String): Boolean = {{
  val lower = normalise(text)
  tokens.forall(lower.contains)
}}

def matchesAny(text: String): Boolean = {{
  val lower = normalise(text)
  tokens.exists(lower.contains)
}}

def passesDirectory(filenameOpt: Option[String]): Boolean = {{
  if (directoryHints.isEmpty) true
  else filenameOpt.exists {{ filename =>
    val lower = filename.toLowerCase
    directoryHints.exists(lower.contains)
  }}
}}

def sanitise(value: String): String =
  Option(value).getOrElse("")
    .replace("\\n", " ")
    .replace("|", "/")
    .trim

def emit(kind: String, id: Long, name: String, filename: Option[String], line: Option[Int]): Unit = {{
  val safeName = sanitise(name)
  val safeFile = filename.map(sanitise).getOrElse("")
  val lineText = line.map(_.toString).getOrElse("")
  println("{OUTPUT_PREFIX}" + Seq(kind, id.toString, safeName, safeFile, lineText).mkString("|"))
}}

def filenameOf(node: StoredNode): Option[String] =
  Option(node.location.filename)

def lineNumberOf(node: StoredNode): Option[Int] =
  Option(node.location.lineNumber).flatten

def matchesAllOpt(opt: Option[String]): Boolean =
  opt.exists(matchesAll)

if (tokens.nonEmpty) {{
  cpg.file.l
    .filter(f => matchesAll(f.name))
    .filter(f => passesDirectory(Some(f.name)))
    .take(maxPerKind)
    .foreach(f => emit("file", f.id, f.name, Some(f.name), None))

  cpg.method.l
    .filter(m => matchesAll(m.name) || matchesAll(m.fullName) || matchesAllOpt(Option(m.code)))
    .filter(m => passesDirectory(filenameOf(m)))
    .take(maxPerKind)
    .foreach(m => emit("method", m.id, m.fullName, filenameOf(m), lineNumberOf(m)))

  cpg.typeDecl.l
    .filter(t => matchesAll(t.name) || matchesAll(t.fullName))
    .filter(t => passesDirectory(filenameOf(t)))
    .take(maxPerKind)
    .foreach(t => emit("typeDecl", t.id, t.fullName, filenameOf(t), lineNumberOf(t)))
}}
"""


def _parse_candidate_output(
    stdout: str,
    feature_name: str,
    tokens: Sequence[str],
) -> List[CandidateNode]:
    from .heuristics import score_text, combine_scores

    candidates: List[CandidateNode] = []
    for line in stdout.splitlines():
        if not line.startswith(OUTPUT_PREFIX):
            continue
        payload = line[len(OUTPUT_PREFIX) :].split("|")
        if len(payload) < 5:
            continue
        kind, id_text, name, filename, line_text = payload[:5]
        try:
            node_id = int(id_text)
        except ValueError:
            continue
        line_number = int(line_text) if line_text and line_text.isdigit() else None
        name_score = score_text(name, tokens)
        filename_score = score_text(filename, tokens) if filename else 0.0
        combined = combine_scores(name_score, filename_score)
        candidates.append(
            CandidateNode(
                node_id=node_id,
                kind=kind,
                name=name,
                filename=filename if filename else None,
                line_number=line_number,
                score=combined,
            )
        )
    # Order by score descending while preserving stability
    candidates.sort(key=lambda cand: cand.score, reverse=True)
    return candidates


def _build_tag_script(feature_name: str, node_ids: Sequence[int]) -> str:
    id_list = ", ".join(f"{int(node_id)}L" for node_id in node_ids)
    feature_literal = json.dumps(feature_name)
    return f"""
import io.shiftleft.semanticcpg.language._

val featureName = {feature_literal}
val nodeIds = List({id_list})

nodeIds.foreach {{ nodeId =>
  cpg.id(nodeId).newTagNodePair("Feature", featureName).store
}}
run.commit
"""
