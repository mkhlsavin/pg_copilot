# AI Copilot Security Audit Pipeline (CPG-based)

The copilot scans large codebases by first building a **Code Property Graph (CPG)** and then using multi-agent LLMs to drive queries and analysis. A CPG is a unified graph representation (AST+CFG+PDG) designed to mine codebases for programming patterns[\[1\]](https://docs.joern.io/code-property-graph/#:~:text=The%20code%20property%20graph%20is,and%20its%20commercial%20brother%20Ocular). We use **Joern** to ingest source code (C/C++ and Python) and generate the CPG, storing it in **DuckDB** with SQL/PGQ support for graph queries[\[2\]](https://duckdb.org/science/duckpgq/#:~:text=We%20outline%20our%20design%20of,iii). A multi-agent workflow (orchestrated by **LangGraph**) coordinates the steps, with agents specializing in tasks (e.g. hypothesis generation, query synthesis, execution)[\[3\]](https://docs.langchain.com/oss/python/langchain/multi-agent#:~:text=Multi,agent%20systems%20are%20useful%20when)[\[4\]](https://blog.langchain.com/langgraph-multi-agent-workflows/#:~:text=tools.%20,without%20breaking%20the%20larger%20application). Below is a step-by-step blueprint:

## 1\. Retrieval Pipeline (Code Ingestion & Graph Generation)

* **Fetch code:** Clone or import the target repository (Linux kernel, PostgreSQL, etc.). Identify language(s) (C/C++, Python).

* **Run Joern:**

* For each language, run Joern frontends (joern parse \--language=c for C/C++, joern parse \--language=python for Python) to create language-specific CPG fragments. Joern converts code into an **OverflowDB** graph internally, representing nodes (functions, calls, variables) and edges (AST, control flow, data flow).

* Optionally use *x2cpg* if needed to preprocess code.

* **Store CPG:** Export or directly save the combined CPG into DuckDB (using the DuckDB PGQ extension). This yields relational tables for nodes/edges or a property-graph table. DuckDB’s SQL/PGQ extension then allows querying the graph via MATCH/WHERE[\[2\]](https://duckdb.org/science/duckpgq/#:~:text=We%20outline%20our%20design%20of,iii).

* **Index code:** (Optional) Generate vector embeddings of code snippets (functions or modules) and index them in ChromaDB. This enables semantic code search if needed (e.g. finding similar code patterns across the codebase).

## 2\. Hypothesis Generation (Language-specific CWEs/CVEs)

* **Code summary:** A LangGraph agent uses an LLM to quickly parse project metadata (e.g. module names, third-party libs) and the list of languages. It retrieves relevant CWE/CVE lists from a knowledge base (using ChromaDB for semantic lookup). For example, ingest known vulnerabilities (OSV/CVE database) into ChromaDB with embeddings[\[5\]](https://medium.com/@vinayaksaokar/deep-dive-building-a-linux-vulnerability-analysis-system-with-gemini-2-0-and-chromadb-dbc86c3383ac#:~:text=The%20system%20begins%20by%20ingesting,0%E2%80%99s%20advanced%20language%20models). Then, for a C project it might retrieve “CWE-120 (Buffer Overflow)”, “CWE-476 (Null Pointer Deref)”, “CWE-416 (Use After Free)”, etc.; for Python it might retrieve “CWE-89 (SQL Injection)”, “CWE-94 (Code Injection via eval)”, “CWE-502 (Deserialization)”, etc.

* **LLM reasoning:** The agent chains-of-thought to pick the most likely attacks given the codebase. For instance, buffer overflows are endemic in C/C++ due to unchecked memory ops[\[6\]](https://owasp.org/www-community/vulnerabilities/Buffer_Overflow#:~:text=At%20the%20code%20level%2C%20buffer,cause%20of%20most%20buffer%20overflows), whereas Python’s main risks involve injections or unsafe eval of strings[\[7\]](https://www.codiga.io/blog/python-prevent-sql-injection/#:~:text=A%20SQL%20injection%20,SQL%20commands%20into%20the%20query). The LLM produces a prioritized list of hypotheses (vulnerability types, CWEs, CVE IDs if known) to investigate.

## 3\. Orchestration (LangGraph \+ ReAct Multi-Agent)

* **Agents & Roles:** We construct a LangGraph workflow with specialized agents (nodes) connected by edges. For example:

* *Supervisor Agent:* controls flow, deciding which subagent to invoke next.

* *Retrieval Agent:* runs Joern and populates DuckDB.

* *Hypothesis Agent:* generates vulnerability hypotheses (as above).

* *QueryAgent(s):* one or more agents that translate each hypothesis into a CPG query.

* *Execution Agent:* runs the queries on DuckDB/Joern and collects results.

* *Analysis Agent:* filters/prioritizes results, possibly re-invoking the LLM for ambiguous cases.

* *Reporting Agent:* formats the final findings.

Each agent has its own prompt/template and possibly a separate LLM instance, enabling **multi-agent specialization**[\[3\]](https://docs.langchain.com/oss/python/langchain/multi-agent#:~:text=Multi,agent%20systems%20are%20useful%20when)[\[4\]](https://blog.langchain.com/langgraph-multi-agent-workflows/#:~:text=tools.%20,without%20breaking%20the%20larger%20application). Edges in LangGraph define the control flow: e.g., Supervisor calls QueryAgent as a “tool” when a hypothesis is ready[\[8\]](https://docs.langchain.com/oss/python/langchain/multi-agent#:~:text=Pattern%20How%20it%20works%20Control,domain).

* **ReAct pattern:** Agents use the ReAct framework: in each step an agent emits a **Thought** (reasoning), then an **Action** (e.g. “run query” or “retrieve info”), then receives an **Observation** (results) to feed into the next Thought[\[9\]](https://www.ibm.com/think/topics/react-agent#:~:text=In%20a%20similar%20fashion%2C%20the,alternating%20thoughts%2C%20actions%20and%20observations). For example, the QueryAgent’s chain-of-thought might analyze the hypothesis and say “we need to find calls to strcpy or memcpy with unsafe size”; then it uses the Joern tool (Action) to perform that search and gets back a list of call sites (Observation). This loop continues until the agent is satisfied or passes control.

## 4\. Query Synthesis (PGQ / Joern DSL)

* **Pattern queries:** For each hypothesis, the QueryAgent constructs a graph query. It may choose between DuckDB’s **SQL/PGQ** syntax (if the graph is loaded there) or Joern’s Scala-based DSL. For example:

* *C Buffer Overflow:* Query patterns like calls to strcpy, memcpy, sprintf etc. and check if destination buffer size \< data length. In Joern DSL one can do:

* cpg.call("malloc").where(\_.argument(1).arithmetics).asSrc  
  cpg.call("memcpy").filter { call \=\>  
    call.argument(1).reachableBy(src) &&  
    \!call.argument(1).codeExact(call.argument(3).code)  
  }

* This finds malloc with arithmetic size whose buffer flows into a memcpy where the copy length doesn’t match the original size[\[10\]](https://joern.io/automate/#:~:text=1,the%20first%20argument%20of%20malloc).

* *Python SQL Injection:* Query calls to DB APIs (e.g. cursor.execute or ORM query builders) where user-controlled input is concatenated. For instance, in DuckDB PGQ one might match:

* MATCH (call:Call)  
  WHERE call.name IN ('execute','pyscopg2')   
    AND call.arguments ANY a WHERE a.containsParam AND NOT a.literal   
  RETURN call

* (This is conceptual; exact syntax depends on how function calls are represented).

* **DSL vs PGQ:** Both query languages traverse the same CPG. Joern DSL allows programmatic filtering, while SQL/PGQ (SQL:2023 MATCH) can express path patterns. We can generate them via template or LLM prompt: e.g., “write a SQL graph query to find calls to sprintf with no bounds check.” Agents may even edit or refine queries based on initial results.

* **Integration point:** The QueryAgent outputs the final query string and passes it to the Execution Agent. This shows how LangGraph bridges to DuckDB/Joern: e.g., a tool call run\_duckdb\_query(query) or joern.run(queryDSL).

## 5\. Query Execution & Result Post-Processing

* **Run queries:** The Execution Agent takes the synthesized queries and executes them. For SQL/PGQ, it invokes DuckDB’s Python API (duckdb.query(...)) to run MATCH queries on the CPG tables. For Joern DSL, it may call Joern’s Python API or subprocess.

* **Collect results:** Each query returns a set of graph nodes or code locations. We parse these into structured findings (file name, line number, code snippet, involved variables). Example: a result row might indicate file=parser.c, line=150, function=ParseText, call=memcpy.

* **Observation feeding:** The raw results become the “Observation” for the ReAct agent. An agent may loop: e.g., if initial query found 100 results, the agent might narrow focus (like filtering for user-input sources), run refined queries, or ask the LLM “Are these real sinks?”

* **LLM check for false positives:** The agent may use a secondary analysis step: feed a suspicious code snippet to an LLM asking “Does this pattern actually lead to overflow?” The LLM uses context (e.g. existence of bounds-check) to flag likely false positives.

## 6\. Prioritization & False-Positive Filtering

* **Prioritize by severity:** The copilot ranks findings by estimated risk. It uses CWEs/CVSS scores if available (via the knowledge DB) and code context. For example, a confirmed buffer overflow with high exploitability is “High” severity, whereas a questionable code pattern might be “Low/Info.” If a finding matches a known CVE (e.g. “glibc strcpy overflow CVE-XYZ”), mark it critical.

* **Filter FPs:** Apply heuristics or a validation agent. For memory issues, check if the length argument is a constant smaller than buffer size (likely safe) vs. a variable (flag). For injection, check if input is sanitized or parameterized. The Analysis Agent may cross-check patterns against known safe usage (e.g. use of parameterized queries in Python). Results failing security checks are demoted or dropped.

* **Grouping:** Merge duplicates (same location, same vulnerability type) and annotate. Also note related occurrences (e.g. multiple overflows in one function).

* **Integration:** The Analysis Agent may query ChromaDB for similar past findings (embedding similarity) to help triage, or refine vulnerability descriptions from external sources.

## 7\. Output Formatting (Markdown & JSON)

* **Markdown report:** The final Report Agent generates a human-readable summary in Markdown. For example:

* \# Security Audit Report

  \- \*\*BufferOverflow (CWE-120, High)\*\* in \`src/parser.c:150\`: \`memcpy\` with unchecked length (possible overflow).  
  \- \*\*SQLInjection (CWE-89, Medium)\*\* in \`app/db.py:42\`: raw SQL query using f-string with unsanitized input.  
  \- \*… and so on…\*

* This uses tables or bullet lists with code references for readability.

* **JSON output:** Simultaneously, a machine-readable JSON is produced for integration with CI/CD or dashboards. For instance:

* {  
    "project": "ExampleProject",  
    "findings": \[  
      {  
        "id": 1,  
        "file": "src/parser.c",  
        "line": 150,  
        "vulnerability": "BufferOverflow",  
        "description": "Unchecked memcpy size (CWE-120)",  
        "severity": "High"  
      },  
      {  
        "id": 2,  
        "file": "app/db.py",  
        "line": 42,  
        "vulnerability": "SQLInjection",  
        "description": "Unsanitized SQL query (CWE-89)",  
        "severity": "Medium"  
      }  
    \]  
  }

* The JSON includes key fields (CWE/CVE IDs, file, line, description, severity) for automated tools to consume. It is embedded as a code block in the markdown report for easy copying.

## 8\. Scalability Strategies (Partitioning & Incremental)

* **Graph partitioning:** For very large codebases (monorepos), partition the CPG by module or directory. Each partition can be loaded/queried independently to leverage parallelism. Queries can be scoped to subgraphs (e.g. only analyze the Linux driver folder). Graph slicing techniques (as in LLMxCPG) can reduce query size by focusing on relevant code segments[\[11\]](https://arxiv.org/abs/2507.16585#:~:text=robust%20vulnerability%20detection.%20Our%20CPG,analysis%20of%20larger%20code%20segments). DuckDB’s analytics engine can parallelize PGQ queries across data partitions.

* **Incremental auditing:** Track source control changes. Only re-run pipeline steps for modified files/directories[\[12\]](https://www.arnica.io/blog/incremental-sca-strategies-monorepos#:~:text=Incremental%20SCA%20scanning%20is%20a,that%20have%20actually%20been%20modified). For example, use Git diff to identify changed modules (“directory-based scoping”[\[13\]](https://www.arnica.io/blog/incremental-sca-strategies-monorepos#:~:text=Directory,tools%20like%20Mend%27s%20Unified%20Agent)) and only update those parts of the CPG. Joern can reparse changed files and incrementally augment the graph. Then only the queries relevant to those code areas are executed again. This dramatically reduces scan time and avoids reprocessing unchanged code.

Together, these strategies allow the copilot to scale to millions of LOC and to run continuously (e.g. nightly or on each commit) without starting from scratch. By combining LangGraph orchestration, ChromaDB/CVDB retrieval, DuckDB graph queries, and Joern analysis, the system automates a full static-security audit. It emphasizes C/C++ patterns (buffer overflows, pointer misuse) and Python patterns (injection, unsafe eval) through language-specific query templates and LLM reasoning[\[6\]](https://owasp.org/www-community/vulnerabilities/Buffer_Overflow#:~:text=At%20the%20code%20level%2C%20buffer,cause%20of%20most%20buffer%20overflows)[\[7\]](https://www.codiga.io/blog/python-prevent-sql-injection/#:~:text=A%20SQL%20injection%20,SQL%20commands%20into%20the%20query). The result is a detailed, prioritized vulnerability report in both Markdown and JSON, ready for developers or automated pipelines.

**Sources:** The above design draws on CPG and Joern concepts[\[1\]](https://docs.joern.io/code-property-graph/#:~:text=The%20code%20property%20graph%20is,and%20its%20commercial%20brother%20Ocular), ReAct agent patterns[\[9\]](https://www.ibm.com/think/topics/react-agent#:~:text=In%20a%20similar%20fashion%2C%20the,alternating%20thoughts%2C%20actions%20and%20observations), LangGraph multi-agent orchestration[\[4\]](https://blog.langchain.com/langgraph-multi-agent-workflows/#:~:text=tools.%20,without%20breaking%20the%20larger%20application)[\[3\]](https://docs.langchain.com/oss/python/langchain/multi-agent#:~:text=Multi,agent%20systems%20are%20useful%20when), Joern query examples[\[10\]](https://joern.io/automate/#:~:text=1,the%20first%20argument%20of%20malloc), and known SCA practices like incremental scanning[\[12\]](https://www.arnica.io/blog/incremental-sca-strategies-monorepos#:~:text=Incremental%20SCA%20scanning%20is%20a,that%20have%20actually%20been%20modified). It also leverages insights from recent research combining CPGs with LLMs[\[11\]](https://arxiv.org/abs/2507.16585#:~:text=robust%20vulnerability%20detection.%20Our%20CPG,analysis%20of%20larger%20code%20segments) and industry examples of vectorized vulnerability search[\[5\]](https://medium.com/@vinayaksaokar/deep-dive-building-a-linux-vulnerability-analysis-system-with-gemini-2-0-and-chromadb-dbc86c3383ac#:~:text=The%20system%20begins%20by%20ingesting,0%E2%80%99s%20advanced%20language%20models). All steps are concrete API calls or code queries, forming an implementable pipeline blueprint.

---

[\[1\]](https://docs.joern.io/code-property-graph/#:~:text=The%20code%20property%20graph%20is,and%20its%20commercial%20brother%20Ocular) Code Property Graph | Joern Documentation

[https://docs.joern.io/code-property-graph/](https://docs.joern.io/code-property-graph/)

[\[2\]](https://duckdb.org/science/duckpgq/#:~:text=We%20outline%20our%20design%20of,iii) DuckPGQ: Efficient Property Graph Queries in an analytical RDBMS – DuckDB

[https://duckdb.org/science/duckpgq/](https://duckdb.org/science/duckpgq/)

[\[3\]](https://docs.langchain.com/oss/python/langchain/multi-agent#:~:text=Multi,agent%20systems%20are%20useful%20when) [\[8\]](https://docs.langchain.com/oss/python/langchain/multi-agent#:~:text=Pattern%20How%20it%20works%20Control,domain) Multi-agent \- Docs by LangChain

[https://docs.langchain.com/oss/python/langchain/multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent)

[\[4\]](https://blog.langchain.com/langgraph-multi-agent-workflows/#:~:text=tools.%20,without%20breaking%20the%20larger%20application) LangGraph: Multi-Agent Workflows

[https://blog.langchain.com/langgraph-multi-agent-workflows/](https://blog.langchain.com/langgraph-multi-agent-workflows/)

[\[5\]](https://medium.com/@vinayaksaokar/deep-dive-building-a-linux-vulnerability-analysis-system-with-gemini-2-0-and-chromadb-dbc86c3383ac#:~:text=The%20system%20begins%20by%20ingesting,0%E2%80%99s%20advanced%20language%20models) Building a Linux Vulnerability Analysis System with Gemini 2.0 and ChromaDB | by Vinayak Saokar | Apr, 2025 | Medium

[https://medium.com/@vinayaksaokar/deep-dive-building-a-linux-vulnerability-analysis-system-with-gemini-2-0-and-chromadb-dbc86c3383ac](https://medium.com/@vinayaksaokar/deep-dive-building-a-linux-vulnerability-analysis-system-with-gemini-2-0-and-chromadb-dbc86c3383ac)

[\[6\]](https://owasp.org/www-community/vulnerabilities/Buffer_Overflow#:~:text=At%20the%20code%20level%2C%20buffer,cause%20of%20most%20buffer%20overflows) Buffer Overflow | OWASP Foundation

[https://owasp.org/www-community/vulnerabilities/Buffer\_Overflow](https://owasp.org/www-community/vulnerabilities/Buffer_Overflow)

[\[7\]](https://www.codiga.io/blog/python-prevent-sql-injection/#:~:text=A%20SQL%20injection%20,SQL%20commands%20into%20the%20query) Present SQL injection in Python (CWE-89)

[https://www.codiga.io/blog/python-prevent-sql-injection/](https://www.codiga.io/blog/python-prevent-sql-injection/)

[\[9\]](https://www.ibm.com/think/topics/react-agent#:~:text=In%20a%20similar%20fashion%2C%20the,alternating%20thoughts%2C%20actions%20and%20observations) What is a ReAct Agent? | IBM

[https://www.ibm.com/think/topics/react-agent](https://www.ibm.com/think/topics/react-agent)

[\[10\]](https://joern.io/automate/#:~:text=1,the%20first%20argument%20of%20malloc) Joern \- The Bug Hunter's Workbench | Automatic Scans. On desktop, and in your CI.

[https://joern.io/automate/](https://joern.io/automate/)

[\[11\]](https://arxiv.org/abs/2507.16585#:~:text=robust%20vulnerability%20detection.%20Our%20CPG,analysis%20of%20larger%20code%20segments) \[2507.16585\] LLMxCPG: Context-Aware Vulnerability Detection Through Code Property Graph-Guided Large Language Models

[https://arxiv.org/abs/2507.16585](https://arxiv.org/abs/2507.16585)

[\[12\]](https://www.arnica.io/blog/incremental-sca-strategies-monorepos#:~:text=Incremental%20SCA%20scanning%20is%20a,that%20have%20actually%20been%20modified) [\[13\]](https://www.arnica.io/blog/incremental-sca-strategies-monorepos#:~:text=Directory,tools%20like%20Mend%27s%20Unified%20Agent) Incremental SCA Scanning Strategies for Large-Scale Monorepos

[https://www.arnica.io/blog/incremental-sca-strategies-monorepos](https://www.arnica.io/blog/incremental-sca-strategies-monorepos)