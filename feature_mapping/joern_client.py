from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from .models import CandidateNode

JOERN_BIN = "joern"
DEFAULT_MAX_PER_KIND = 40
OUTPUT_PREFIX = "__CANDIDATE__|"
UNTAGGED_PREFIX = "__UNTAGGED__|"
COVERAGE_PREFIX = "__COVERAGE__|"
logger = logging.getLogger(__name__)


class JoernClientError(RuntimeError):
    """Raised when Joern invocations fail."""


@dataclass(slots=True)
class JoernClient:
    """Thin wrapper around the Joern CLI to run scripted analysis."""

    binary: str = JOERN_BIN
    cpg_path: Optional[Path] = None
    workdir: Optional[Path] = None
    env: Optional[dict] = None
    retry_attempts: int = 2
    retry_delay: float = 1.0
    retry_backoff: float = 2.0

    def run_script(self, script: str, *, timeout: float = 600.0) -> subprocess.CompletedProcess[str]:
        """Execute a Joern script and return the raw completed process."""
        if self.cpg_path:
            script = f"{_build_import_block(self.cpg_path)}\n{script}"
        script_path = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".sc", delete=False) as handle:
                handle.write(script)
                handle.flush()
                script_path = Path(handle.name)
            cmd = [str(self.binary), "--script", str(script_path)]
            # Note: --cpg option removed, using importCpg/loadCpg in script instead
            attempts = max(0, self.retry_attempts) + 1
            delay = max(0.0, self.retry_delay)
            completed: Optional[subprocess.CompletedProcess[str]] = None
            last_error: Optional[JoernClientError] = None
            for attempt in range(1, attempts + 1):
                completed = subprocess.run(
                    cmd,
                    cwd=str(self.workdir) if self.workdir else None,
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                if completed.returncode == 0:
                    return completed
                error = JoernClientError(
                    f"Joern command failed with exit code {completed.returncode} (attempt {attempt}/{attempts}).\n"
                    f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
                )
                last_error = error
                if attempt < attempts:
                    logger.warning("Retrying Joern script after failure: %s", error)
                    if delay > 0:
                        time.sleep(delay)
                        delay *= max(1.0, self.retry_backoff)
            if last_error:
                raise last_error
            raise JoernClientError("Joern script execution failed without producing a result.")
        finally:
            if script_path:
                try:
                    script_path.unlink(missing_ok=True)
                except OSError:
                    pass
        if completed.returncode != 0:
            raise JoernClientError(
                f"Joern command failed with exit code {completed.returncode}:\n"
                f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return completed

    def find_candidates(
        self,
        feature_name: str,
        tokens: Sequence[str],
        *,
        directory_hints: Sequence[str] | None = None,
        max_per_kind: int = DEFAULT_MAX_PER_KIND,
        max_total_results: int = 0,
        include_calls: bool = False,
        include_namespaces: bool = False,
    ) -> List[CandidateNode]:
        """Return candidate nodes that match the given feature tokens."""
        script = _build_candidate_script(
            tokens,
            directory_hints or (),
            max_per_kind,
            max_total_results=max_total_results,
            include_calls=include_calls,
            include_namespaces=include_namespaces,
        )
        completed = self.run_script(script)
        return _parse_candidate_output(completed.stdout, feature_name, tokens)

    def tag_feature(
        self,
        feature_name: str,
        node_ids: Iterable[int],
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
            self.run_script(script)

    def filter_untagged_nodes(self, feature_name: str, node_ids: Sequence[int]) -> List[int]:
        """Return the subset of node_ids that are not yet tagged with the feature."""
        node_ids = [int(node_id) for node_id in node_ids]
        if not node_ids:
            return []
        script = _build_filter_script(feature_name, node_ids)
        completed = self.run_script(script)
        return _parse_filter_output(completed.stdout, node_ids)

    def feature_tag_counts(self, feature_names: Sequence[str]) -> dict[str, int]:
        """Return the number of tagged nodes for each feature name."""
        names = [name for name in feature_names if name]
        if not names:
            return {}
        script = _build_coverage_script(names)
        completed = self.run_script(script)
        return _parse_coverage_output(completed.stdout)


def _scala_list(items: Sequence[str]) -> str:
    escaped = [json.dumps(item) for item in items]
    return f"List({', '.join(escaped)})"


def _build_candidate_script(
    tokens: Sequence[str],
    directory_hints: Sequence[str],
    max_per_kind: int,
    *,
    max_total_results: int = 0,
    include_calls: bool = False,
    include_namespaces: bool = False,
) -> str:
    token_list = _scala_list([tok.lower() for tok in tokens if tok])
    hint_list = _scala_list([hint.lower() for hint in directory_hints if hint])
    max_total_literal = max(0, int(max_total_results))
    include_calls_literal = "true" if include_calls else "false"
    include_namespaces_literal = "true" if include_namespaces else "false"
    return f"""
import io.shiftleft.semanticcpg.language._
import io.shiftleft.codepropertygraph.generated.nodes.StoredNode

val tokens: List[String] = {token_list}
val directoryHints: List[String] = {hint_list}
val maxPerKind: Int = {max_per_kind}
val maxTotal: Int = {max_total_literal}
val includeCalls: Boolean = {include_calls_literal}
val includeNamespaces: Boolean = {include_namespaces_literal}
var emitted: Int = 0
val requireAllTokens: Boolean = tokens.nonEmpty && tokens.size <= 1

def normalise(text: String): String = text.toLowerCase

def matchesAll(text: String): Boolean = {{
  val lower = normalise(text)
  tokens.forall(lower.contains)
}}

def matchesAny(text: String): Boolean = {{
  val lower = normalise(text)
  tokens.exists(lower.contains)
}}

def matchesCandidate(text: String): Boolean =
  if (tokens.isEmpty) false
  else if (requireAllTokens) matchesAll(text)
  else matchesAll(text) || matchesAny(text)

def passesDirectory(filenameOpt: Option[String]): Boolean = {{
  if (directoryHints.isEmpty) true
  else filenameOpt.exists {{ filename =>
    val lower = filename.toLowerCase
    directoryHints.exists(lower.contains)
  }}
}}

def shouldEmit(): Boolean =
  maxTotal <= 0 || emitted < maxTotal

def sanitise(value: String): String =
  Option(value).getOrElse("")
    .replace("\\n", " ")
    .replace("|", "/")
    .trim
def emit(kind: String, id: Long, name: String, filename: Option[String], line: Option[Int]): Unit = {{
  if (shouldEmit()) {{
    val safeName = sanitise(name)
    val safeFile = filename.map(sanitise).getOrElse("")
    val lineText = line.map(_.toString).getOrElse("")
    println("{OUTPUT_PREFIX}" + Seq(kind, id.toString, safeName, safeFile, lineText).mkString("|"))
    emitted += 1
  }}
}}

def filenameOf(node: StoredNode): Option[String] =
  Option(node.location.filename)

def lineNumberOf(node: StoredNode): Option[Int] =
  Option(node.location.lineNumber).flatten

def matchesAllOpt(opt: Option[String]): Boolean =
  opt.exists(matchesAll)

def matchesCandidateOpt(opt: Option[String]): Boolean =
  opt.exists(matchesCandidate)

if (tokens.nonEmpty) {{
  cpg.file.l
    .filter(f => matchesCandidate(f.name))
    .filter(f => passesDirectory(Some(f.name)))
    .take(maxPerKind)
    .foreach(f => if (shouldEmit()) emit("file", f.id, f.name, Some(f.name), None))

  cpg.method.l
    .filter(m => matchesCandidate(m.name) || matchesCandidate(m.fullName) || matchesCandidateOpt(Option(m.code)))
    .filter(m => passesDirectory(filenameOf(m)))
    .take(maxPerKind)
    .foreach(m => if (shouldEmit()) emit("method", m.id, m.fullName, filenameOf(m), lineNumberOf(m)))

  cpg.typeDecl.l
    .filter(t => matchesCandidate(t.name) || matchesCandidate(t.fullName))
    .filter(t => passesDirectory(filenameOf(t)))
    .take(maxPerKind)
    .foreach(t => if (shouldEmit()) emit("typeDecl", t.id, t.fullName, filenameOf(t), lineNumberOf(t)))

  if (includeCalls) {{
    cpg.call.l
      .filter(c => matchesCandidateOpt(Option(c.name)) || matchesCandidateOpt(Option(c.code)))
      .filter(c => passesDirectory(filenameOf(c)))
      .take(maxPerKind)
      .foreach(c => if (shouldEmit()) emit("call", c.id, Option(c.name).getOrElse(c.code), filenameOf(c), lineNumberOf(c)))
  }}

  if (includeNamespaces) {{
    cpg.namespaceBlock.l
      .filter(n => matchesCandidateOpt(Option(n.name)) || matchesCandidateOpt(Option(n.fullName)))
      .filter(n => passesDirectory(filenameOf(n)))
      .take(maxPerKind)
      .foreach(n => if (shouldEmit()) emit("namespaceBlock", n.id, n.fullName, filenameOf(n), lineNumberOf(n)))
  }}
}}
"""


def _parse_candidate_output(
    stdout: str,
    feature_name: str,
    tokens: Sequence[str],
) -> List[CandidateNode]:
    from .heuristics import score_path, score_text, combine_scores

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
        filename_score = score_path(filename, tokens) if filename else 0.0
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


def _build_filter_script(feature_name: str, node_ids: Sequence[int]) -> str:
    feature_literal = json.dumps(feature_name)
    if node_ids:
        id_list = ", ".join(f"{int(node_id)}L" for node_id in node_ids)
        nodes_literal = f"List[Long]({id_list})"
    else:
        nodes_literal = "List.empty[Long]"
    return f"""
import io.shiftleft.semanticcpg.language._

val featureName = {feature_literal}
val nodeIds: List[Long] = {nodes_literal}

nodeIds.foreach {{ nodeId =>
  val alreadyTagged = cpg
    .id(nodeId)
    .tag
    .nameExact("Feature")
    .valueExact(featureName)
    .nonEmpty
  if (!alreadyTagged) {{
    println("{UNTAGGED_PREFIX}" + nodeId.toString)
  }}
}}
"""


def _parse_filter_output(stdout: str, original_ids: Sequence[int]) -> List[int]:
    untagged_ids = set()
    for line in stdout.splitlines():
        if not line.startswith(UNTAGGED_PREFIX):
            continue
        payload = line[len(UNTAGGED_PREFIX) :].strip()
        if not payload:
            continue
        try:
            untagged_ids.add(int(payload))
        except ValueError:
            continue
    return [node_id for node_id in original_ids if node_id in untagged_ids]


def _build_coverage_script(feature_names: Sequence[str]) -> str:
    feature_list = _scala_list([name for name in feature_names if name])
    return f"""
import io.shiftleft.semanticcpg.language._
val featureNames: List[String] = {feature_list}
featureNames.foreach {{ featureName =>
  val count = cpg.tag
    .nameExact("Feature")
    .valueExact(featureName)
    .in("TAGGED_BY")
    .dedup
    .size
  println("{COVERAGE_PREFIX}" + featureName + "|" + count.toString)
}}
"""


def _parse_coverage_output(stdout: str) -> dict[str, int]:
    coverage: dict[str, int] = {}
    for line in stdout.splitlines():
        if not line.startswith(COVERAGE_PREFIX):
            continue
        payload = line[len(COVERAGE_PREFIX) :].split("|", 1)
        if len(payload) != 2:
            continue
        name, count_text = payload
        name = name.strip()
        try:
            coverage[name] = int(count_text)
        except ValueError:
            continue
    return coverage


def _build_tag_script(feature_name: str, node_ids: Sequence[int]) -> str:
    id_list = ", ".join(f"{int(node_id)}L" for node_id in node_ids)
    feature_literal = json.dumps(feature_name)
    return f"""
import io.shiftleft.semanticcpg.language._
import io.joern.console._

val featureName = {feature_literal}
val nodeIds = List({id_list})

nodeIds.foreach {{ nodeId =>
  cpg.id(nodeId).newTagNodePair("Feature", featureName).store()
}}
run.commit
"""


def _build_import_block(cpg_path: Path) -> str:
    # Convert Windows path to forward slashes for Joern
    path_str = str(cpg_path).replace('\\', '/')
    project_name = cpg_path.name
    path_literal = json.dumps(path_str)
    project_literal = json.dumps(project_name)
    return f"""
// Import CPG from filesystem
import scala.util.Try
val projectName = {project_literal}
val opened = Try(open(projectName)).isSuccess
if (!opened) {{
  importCpg({path_literal}, projectName, true)
}}
"""
