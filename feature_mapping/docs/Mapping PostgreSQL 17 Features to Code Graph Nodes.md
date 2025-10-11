# Mapping PostgreSQL 17 Features to Code Graph Nodes

## Overview

To support tasks like developer onboarding, security audits, documentation, and more, it is crucial to **trace** high-level product features to the source code that implements them. In PostgreSQL 17, a *feature matrix* enumerates all major functional features of the system[\[1\]](https://www.postgresql.org/about/featurematrix/#:~:text=Feature%20Matrix). By mapping each listed feature to the corresponding nodes in the PostgreSQL code’s **Code Property Graph (CPG)**, we create a bidirectional traceability link between **what** the system does (features) and **how/where** it’s implemented in code. These traceability links help engineers quickly identify which parts of the code implement a specific requirement or feature[\[2\]](https://arxiv.org/abs/2307.05188#:~:text=,on%20engineers%20and%20is%20error), maintaining a correct mental model of the system and easing future changes. Moreover, such mapping lays the foundation for **Retrieval-Augmented Generation (RAG)** scenarios – allowing a knowledge system or AI to retrieve relevant code sections given a feature-related query, benefiting the eight scenarios outlined (from new developer onboarding to regulatory compliance).

**Why Traceability Matters:** Maintaining explicit feature-to-code links greatly aids various use cases in a large codebase: developers can understand features faster (onboarding), security teams can focus on feature-specific code (auditing), documentation can be generated with code references, and so on. This kind of traceability matrix (mapping requirements/features to code modules) ensures changes are tracked and requirements are met throughout the software lifecycle[\[3\]](https://www.in-com.com/blog/code-traceability/#:~:text=One%20of%20the%20solutions%20to,test%20cases%2C%20and%20code%20modules)[\[4\]](https://www.in-com.com/blog/code-traceability/#:~:text=To%20implement%20traceability%20in%20software,numerous%20advantages%20for%20software%20quality). It improves software quality and maintainability by making it easier to locate relevant code for debugging, testing, optimization, or compliance checks[\[4\]](https://www.in-com.com/blog/code-traceability/#:~:text=To%20implement%20traceability%20in%20software,numerous%20advantages%20for%20software%20quality).

In the following sections, we propose an **automated approach** (using Joern’s CPG and scripting) to map PostgreSQL 17’s feature matrix to its source code. The solution involves: **(1)** parsing the official feature list, **(2)** identifying code nodes corresponding to each feature (using static analysis and search heuristics), and **(3)** annotating the CPG with *feature tags* to enable quick bidirectional queries. The end result will be an enriched code graph where each feature “knows” its implementing code and each code node “knows” which feature(s) it contributes to.

## 1\. Extracting Features from PostgreSQL’s Feature Matrix

The PostgreSQL website provides a **Feature Matrix** page listing all features and the version in which each was introduced[\[1\]](https://www.postgresql.org/about/featurematrix/#:~:text=Feature%20Matrix). We focus on features present in **v17** (the latest version at the time, ensuring we cover all features up through 17). An automated script can retrieve and parse this matrix as follows:

* **Fetch the Feature Matrix:** Download or scrape the HTML from the PostgreSQL feature matrix page (e.g., via an HTTP GET request). This table is organized by feature categories (Backend, Performance, Security, etc.) with rows for each feature and columns for versions. Each feature is also described by a name (and often has a tooltip or link for more info).

* **Parse the Table:** Use an HTML parser to extract feature names. Each row corresponds to a feature; we can gather the feature name text. We also identify if the feature is applicable to v17 – since v17 is the latest, nearly every feature introduced in any past version remains available. (If the table explicitly marks presence per version with checkmarks, filter out features not marked for 17; otherwise assume all listed features up to 17 are included.)

* **Organize Features:** Store the features in a structured list or dictionary. We may group them by category (as on the site) which could be useful context (e.g., knowing a feature is in “Security” or “JSON” might hint at code location), but grouping is optional. The main output is a list of feature names (e.g., "64-bit large objects", "Logical replication", "Parallelized CREATE INDEX for BRIN indexes", etc.).

This parsing step might be done with a small **Python** script or using Scala (with a library like JSoup) since Joern itself doesn’t include a web scraper by default. For example, one could load the HTML and use CSS selectors or DOM traversal to collect all feature name strings. These names will feed into the mapping algorithm.

*Rationale:* Automating this ensures we have the exact list of official features for PostgreSQL 17\. It avoids manual errors and can be rerun for future versions. At this stage, we also have the human-readable feature descriptions (from the matrix or detail pages), which can later assist in matching code or generating documentation.

## 2\. Identifying Code Implementations for Each Feature

For each feature from the list, the next challenge is to find which parts of the **codebase** implement or relate to that feature. We leverage the **Code Property Graph (CPG)** of PostgreSQL’s source (generated by Joern) to perform this analysis. The CPG contains nodes for files, functions, AST elements, etc., with rich property data like names, code snippets, relationships (calls, AST parent/child), and even comments. Our strategy is a combination of textual search and structural clues:

* **Keyword-Based Code Search:** Use Joern’s query language to search for identifiers, file names, or code constants that match the feature’s name or key terms. Often, feature names contain distinctive keywords that likely appear in code:

* **Function or Type Names:** For example, a feature *“64-bit large objects”* suggests that the large object API was extended – searching for “largeobject” or related terms in function names or type definitions (e.g., inv\_api.c, functions like inv\_seek or types like LargeObjectDesc) would find relevant code. We can query the CPG for any identifiers (function names, variable names, type names) containing “large” or “lo” etc.

* **File or Directory Names:** Many features reside in specific modules. E.g., *“Full Text Search”* feature might correspond to code in the /tsearch/ directory. The feature *“JSONB data type”* will have code in files with “jsonb” in their name. We can query file nodes by path/name (e.g., cpg.file.name(".\*jsonb.\*") to find JSONB-related source files).

* **Configuration or Constants:** Some features introduce GUC parameters or SQL syntax. For instance, *“Parallel query”* features might involve a GUC named max\_parallel\_workers or functions with “Parallel” in their name. *“MERGE command”* feature would involve the SQL parser (search in the grammar or commands for “MERGE”). Searching string literals can help if a feature adds error messages or keywords (e.g., the presence of the keyword "MERGE" in the parser).

* **Comments and Documentation in Code:** The CPG also includes comment nodes[\[5\]\[6\]](https://cpg.joern.io/#:~:text=). Sometimes developers mention feature names or related RFCs in comments (especially for large changes). For example, after a major feature is added, a comment might read “/ *Implemented parallel index build for BRIN (feature introduced in v11)* /”. We can query cpg.comment for keywords similar to the feature name.

* **Multiple Terms:** For multi-word features, it’s effective to ensure all significant terms appear in proximity. We can break the feature name into tokens and search for code containing all tokens (case-insensitively). For example, *“Parallelized CREATE INDEX for BRIN”* \-\> require “BRIN” and “parallel” in the same function or file. Joern’s query can use regex or logical AND conditions on name properties.

* **Heuristics by Category:** Use the feature’s category or context to narrow the search:

* Features under **“Performance”** often correspond to optimizer or executor improvements – likely in src/backend/optimizer/ or executor code.

* **SQL/DDL features** correspond to grammar changes (search in src/backend/parser/gram.y or parser.c for the keyword, and in execution functions in src/backend/commands/ or related areas).

* **Security features** (e.g., authentication methods like “SCRAM” or “SSL negotiation”) will be in authentication modules (src/backend/libpq, src/backend/security etc.) or relevant functions (search for “SCRAM” in function names or constants).

* **Replication features** (logical replication, etc.) have known subsystems (src/backend/replication/).

* This domain knowledge helps target likely files to search within the graph.

* **Iterative Refinement:** The initial keyword search results should be reviewed (automatically or manually) to refine the mapping:

* If a query returns too many hits (e.g., a common term), refine by adding another term or limiting to certain directories.

* If no obvious match, consider synonyms or related terminology. For instance, the feature name *“Channel binding for SCRAM authentication”* might not literally appear in code; however, one could search for “SCRAM” and find functions handling SCRAM in auth.c, which is the relevant code.

* For tricky cases, use the feature’s description (from the detail page) as clues – the description might mention an internal concept or function names.

* **Advanced Textual Analysis (Optional):** If simple matching is insufficient, one can employ a more advanced NLP approach. For example, treat the feature description and code content as documents and measure similarity (using vector embeddings or Latent Semantic Indexing). Research prototypes like *YamenTrace* have used LSI on code identifiers and comments to recover links between requirements and code[\[7\]](https://arxiv.org/abs/2307.05188#:~:text=approach%20and%20implementation%20to%20recover,TLs%20were%20correctly%20recovered). In our context, one could embed feature descriptions and all function comments into a vector space and find the closest matches. This can automatically surface code that is conceptually related to a feature even if naming differs. However, this is an optional enhancement – the primary approach is direct static analysis with Joern.

The output of this step is a mapping (for each feature, a set of one or more code nodes that implement it). In practice, these code nodes will typically be **function definitions or file nodes** in the CPG: \- Mapping to a *file* (or module) is useful for broad features implemented by a subsystem. \- Mapping to specific *functions* is useful for pinpointing the exact implementation points (e.g., a particular function that was added for the feature). We can choose a consistent granularity – for PostgreSQL, mapping to **files or major functions** is often sufficient, since each feature is usually encapsulated in a few source files. For example, we might map “64-bit large objects” to the inv\_api.c and related large object files, “MERGE statement” to changes in parser/analyze\_merge.c and the executor handling, etc.

Before proceeding, it’s wise to verify a few mappings with manual insight (spot-check). For instance, ensure that the code identified for “Full Text Search” indeed resides in the tsearch module, or that “B-tree deduplication” maps to btree index code. Once confident, we move to annotating the graph.

## 3\. Annotating the CPG with Feature Tags

With the feature-to-code mapping determined, we integrate this information **into the Code Property Graph** itself. Joern provides a mechanism for extending the graph with custom metadata via **tag nodes**. We will attach a “Feature” tag to each relevant code node, effectively labeling it with the feature name. This makes the mapping *bidirectional* and queryable within the graph (feature → code, and code → feature). The automation pipeline handles these tagging steps in batches, writes JSON summaries for every feature, and skips nodes that already carry the same tag so that reruns are safe and idempotent.

**Using Joern’s Tag API:** The CPG schema includes a TAG node type and a TAGGED\_BY edge to link tag nodes to code nodes[\[6\]](https://cpg.joern.io/#:~:text=). Joern’s console (or scripts) offers augmentation steps newTagNode and newTagNodePair to create these links. We will use newTagNodePair, which allows specifying a key and value for the tag: \- We choose a consistent tag key, e.g. **“Feature”**, and the tag value as the feature name string.  
\- For each feature’s set of code nodes (from step 2), we run a query that finds those nodes in the graph and suffix it with .newTagNodePair("Feature", \<FeatureName\>).store. This command generates tag nodes and associates them with all nodes in the current traversal[\[8\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=joern%3E%20cpg.call.name%28). We then call run.commit to merge these tags into the active graph, making the change permanent[\[8\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=joern%3E%20cpg.call.name%28). \- *Example:* Suppose “Full Text Search” is implemented in functions under tsvector.c and gistidx.c. We can do:

cpg.file.name("tsvector.c|gistidx.c").newTagNodePair("Feature", "Full Text Search").store

(or find by function names) then commit. This will create tag nodes (each with name="Feature", value="Full Text Search") attached to those file nodes. \- If multiple nodes are returned by the query, Joern will create multiple tag nodes (one per code node) each carrying the same key/value. That’s fine – later we can retrieve all of them by querying the tag value. \- This process is repeated (possibly in a loop) for all features. We generate a tag for each (feature, codeNode) pair. **Note:** It’s possible to attach multiple features to one code node if needed (e.g., a shared utility might be part of two features), and multiple nodes to one feature as expected. The tags ensure *many-to-many* linking.

**Storage and Schema:** Once tags are committed, they become part of the CPG. It’s advisable to save the modified graph (using save in Joern) so that the feature annotations persist across sessions. The use of the built-in tag mechanism means we’re not altering the core schema arbitrarily; we’re leveraging an intended extension point. The mapping lives *within* the graph database, which is what the question requires (no external lookup needed). We essentially extended the graph with a layer of semantic information about features. Keep the generated summary directory alongside the graph snapshot to preserve an audit trail of each tagging run.


After tagging, the graph’s query capability is enriched: \- We can list all tags or filter them by name/value. For example, cpg.tag.name("Feature").value.l would list all feature values tagged in the graph. \- Each tag node is connected to its code node via a TAGGED\_BY relation. Joern’s query language lets us seamlessly traverse these. For instance, from a tag we can navigate to the tagged method or file, and from a code node we can find its tag.

### Automation, Testing, and Audit

The implementation in this repository automates the entire workflow:

- `feature_mapping.pipeline.FeatureMappingPipeline` batches Joern invocations, persists per-feature summaries, and deduplicates tags so reruns remain safe.
- Command-line flags such as `--summary-dir`, `--skip-tagging`, `--resume-from`, and `--batch-size` support review-first runs, resumable jobs, and operational tuning.
- The automated test suite (`python -m pytest`) covers:
  - HTML parsing of the feature matrix (`tests/test_feature_matrix.py`).
  - Token expansion and scoring heuristics (`tests/test_heuristics.py`).
  - Pipeline smoke tests with a stub Joern client to validate summaries, resume behaviour, and idempotent tagging (`tests/test_pipeline_smoke.py`).

Audit guidance:

- Keep generated summary directories (one JSON per feature) under version control or archival storage to review differences between runs.
- After tagging, run targeted Joern queries to confirm representative features were updated as expected.
- Maintain a backup of `pg17_full.cpg` prior to each tagging cycle to enable quick rollback if new heuristics introduce noise.

## 4\. Querying the Enriched Graph (Bidirectional Mapping)

With the bidirectional links in place, answering questions about features or code components becomes straightforward graph queries:

* **From Feature to Code:** Given a feature name, retrieve the code implementing it. This can be done by finding tag nodes with that feature value and then the attached code:

* *Example:* To get the source files for feature “JSONB data type”, one could run:  
  cpg.tag.value("JSONB data type").file.name.l  
  This finds all tags whose value matches “JSONB data type”, then follows the edges to the file nodes and prints their names. Similarly, .method could list function names, etc.  
  In Joern’s console, one can also directly use the tag in a traversal: e.g., cpg.tag.value("Full Text Search").method.fullName.l would list methods tagged with Full Text Search.  
  The Joern documentation example shows that after tagging, a query like cpg.tag.value("MY\_VALUE").call.code.l returns the code of all call nodes tagged with that value[\[9\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=joern%3E%20cpg.tag.name%28,%22MY_VALUE%22%29). By analogy, using our feature value will return the relevant code elements we tagged.

* **From Code to Feature:** For a given code element, find what feature(s) it is part of. This is useful if you’re looking at a source file or function and want context of higher-level purpose. We can take a node (or a set of nodes) and use the .tagList step to get associated tags[\[10\]](https://docs.joern.io/cpgql/reference-card/#:~:text=methods%2C%20literals%2C%20types%20etc,to%20each%20of%20the%20nodes). For example:

* cpg.file.name("auth.c").tagList.l might return a list of Tag nodes attached to *auth.c* (perhaps values like “SCRAM-SHA-256 Authentication”, “OAuth Authentication” if that file implements those features). We could further filter to just the tag value property to see the feature names.

* Alternatively, starting from any arbitrary traversal, we can jump to tags: e.g., cpg.method.name("CommitTransaction").tag.value.l could show if that function is tied to any listed feature.

* **Graph traversals are bidirectional**, so one can also start at a feature tag and navigate inward. For instance, cpg.tag.value("FeatureX").method.definingType.name.l could show which class/structure (if any) those methods belong to, etc. Conversely, from a method, .\<relation to tag\>.value yields feature name.

This ability to query in both directions verifies that our mapping is indeed *inside the graph* and bidirectional. Each Tag node connects a feature to a code node, and by graph nature you can traverse from one to the other easily.

## 5\. Utilizing the Mapping in RAG Scenarios

With the feature-to-code mapping implemented in the CPG, we can leverage it for the mentioned scenarios, especially when using a Retrieval-Augmented Generation approach (where an AI assistant can query the graph to fetch relevant context):

* **Scenario 1: Onboarding a New Developer** – A newcomer can ask “Which parts of the code implement feature X?” The system can use the feature name to retrieve the list of relevant files/functions via the tag mapping. It might then present the code or summaries of those parts. This drastically reduces time spent grepping the codebase and helps the developer understand the architecture feature-by-feature.

* **Scenario 2: Security Audit of the Code Base** – Security analysts often focus on specific features like authentication, encryption, etc. Using the mapping, a query for security-related features (the “Security” category in the matrix) will directly point to the code modules (e.g. password authentication code, SSL handling code)[\[11\]](https://www.postgresql.org/about/featurematrix/#:~:text=18%2017%2016%2015%2014,side%20encryption)[\[12\]](https://www.postgresql.org/about/featurematrix/#:~:text=OAuth%20Authentication%20%2F%20Authorization%20,303%20security_barrier%20option%20on%20views). Auditors can systematically go through features tagged as security and review the associated code for vulnerabilities. The mapping ensures they don’t overlook code paths that implement relevant functionality.

* **Scenario 3: Automatic Documentation Generation** – We can generate higher-level documentation by iterating over each feature in the matrix, retrieving its description (from the matrix or docs) and the list of code locations from the graph. For example, an automated doc tool can produce an entry: *“Feature: Parallel Hash Joins –* *Description: Allows the use of multiple worker processes to perform a hash join in parallel (added in v11).* *Implementation: src/backend/executor/nodeHash.c, src/backend/executor/parallel.c (uses parallel coordination infrastructure).”* The code paths come from the tag query. This provides readers a mapping from concept to implementation, serving as valuable design documentation or a knowledge base.

* **Scenario 4: Developing New Functionality** – When adding a new feature or extending an existing one, developers benefit from examples of how similar features are implemented. With the mapping, one could query for a related feature’s code. For instance, if implementing a new index type, the developer might query the code tagged for “BRIN indexes” or “GIN indexes” to learn how those are integrated (e.g., see the IndexAM interface implementations). The mapping essentially turns the codebase into a searchable knowledge graph of features and examples. This reduces trial-and-error and ensures consistency with existing patterns.

* **Scenario 5: Refactoring and Technical Debt** – Suppose a team wants to refactor or improve a certain feature across the codebase. The feature tag immediately yields all code locations that need to be reviewed or changed, ensuring comprehensive coverage. If a bug is reported in a feature, the tag helps locate all related modules so the fix can be applied holistically. This is much more efficient than manually tracking down usages. As noted in traceability best practices, being able to trace requirements/features to code makes debugging and maintenance easier and less error-prone[\[4\]](https://www.in-com.com/blog/code-traceability/#:~:text=To%20implement%20traceability%20in%20software,numerous%20advantages%20for%20software%20quality).

* **Scenario 6: Performance Analysis** – When performance issues arise (e.g., slow query execution), knowing which feature or subsystem is involved allows targeted analysis. If a specific feature like “JIT compilation” or “Parallel query” is suspected to cause slowdowns, one can quickly retrieve all code tagged for that feature and inspect it or instrument it. Moreover, a proactive tool might iterate through performance-related features (those under the “Performance” category in the matrix) and check their code for known inefficiencies. The mapping provides a direct way to gather all relevant code for profiling or review.

* **Scenario 7: Test Coverage Gaps** – By combining the feature mapping with test coverage data, we can identify which features have untested code. For example, for each feature’s code nodes, check if they are touched by any test cases (this requires having coverage info mapped to code, which could be another overlay). The features whose implementation nodes have no associated tests can be flagged. This helps ensure all high-level capabilities are adequately tested. The mapping essentially elevates code coverage analysis to the feature level (“feature X is only 20% covered by tests, because these functions X, Y are not in any test”).

* **Scenario 8: Regulatory Compliance and API Management** – Many compliance requirements (licensing, security standards, etc.) are feature-specific. For instance, a requirement might be “all password storage must use SHA-256 hashing”. If PostgreSQL has a feature “SCRAM-SHA-256 Authentication”, one can directly trace to the code and verify compliance (e.g., check the code actually uses SHA-256 as intended). Traceability also provides an audit trail: if an external auditor asks *“Where in the code is feature X implemented and does it meet requirement Y?”*, the tagged graph can answer quickly. This aligns with the notion that traceability aids in proving requirements compliance by linking requirements to implementation artifacts[\[13\]](https://www.in-com.com/blog/code-traceability/#:~:text=implemented%20and%20tested%2C%20leading%20to,issues%2C%20saving%20time%20and%20effort). Additionally, for API governance, if certain features correspond to specific public APIs or extensions, the mapping can help track where those API endpoints are defined and used, ensuring they evolve under proper oversight.

In all these scenarios, the **feature-to-code mapping acts as an index or knowledge graph that connects high-level concepts to low-level details**. This dramatically improves the efficiency of queries in both manual analysis and AI-assisted Q\&A. Instead of treating the codebase as an unstructured blob of text, we have a semantic layer that understands *“Feature X”* as an entity and knows the parts of the code responsible for it. Queries that leverage this layer can retrieve focused, relevant information, which can then be fed into analysis tools or language models for explanation, summarization, or further inspection.

## 6\. Implementation Summary – Algorithm/Scripting Outline

To summarize, here is a high-level algorithm for automated mapping, which can be implemented as a combination of a parsing script and Joern (Scala or Python) commands:

1. **Parse Feature List (Version 17\)**: Scrape the PostgreSQL feature matrix page[\[1\]](https://www.postgresql.org/about/featurematrix/#:~:text=Feature%20Matrix) and extract all feature names (possibly with their category). Store them in a list features. (If scraping live is undesired, one can manually export the table to a CSV and read that – but automation is preferred for reproducibility.)

2. **Initialize Joern on the Codebase**: Load the PostgreSQL 17 source code into Joern to generate its Code Property Graph (if not already done). Ensure we have the CPG ready for queries.

3. **For each feature in features:**  
   a. Determine search keywords. By default, use the feature name (split into terms). Optionally, apply tweaks (e.g., remove very common words, add synonyms or related terms).  
   b. **Query the CPG** for likely related code nodes. Start with broad queries on names of files, methods, types, and maybe constants:

   * Example (Scala-based pseudo-code):

   * val terms \= feature.split("\\\\s+")  
     // Build a query that matches all terms in identifier or file names (case-insensitive)  
     val pattern \= (?i)terms.mkString(".\*")  // simple heuristic: all terms in order  
     val candidates \= cpg.file.name(pattern).l \++   
                      cpg.method.name(pattern).l \++   
                      cpg.typeDecl.name(pattern).l

   * (One could also do separate queries per term and intersect results.)  
     c. If the initial query yields no or too many results, refine: narrow by known directories or by looking into cpg.comment for the feature name. This step may involve some conditional logic or manual hints for certain features.  
     d. Collect the final set of code nodes that truly correspond to the feature. (This might require filtering out false positives by inspecting the code or requiring multiple keyword matches.) d. **Attach Feature Tag**: Take the resulting nodes (say we have a sequence nodes of type StoredNode from Joern) and create tag nodes:

   * nodes.newTagNodePair("Feature", feature).store

   * This schedules the creation of “Feature” tags with value equal to the feature name on all those nodes[\[8\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=joern%3E%20cpg.call.name%28). After processing all features (or periodically in batches), call run.commit to apply all pending tag additions to the graph[\[8\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=joern%3E%20cpg.call.name%28). Save the graph when done.

4. **Verification**: Optionally, query the graph for a few known feature-to-code mappings to ensure the tags are correct. For example, verify cpg.tag.value("WAL support for hash indexes").file.name.l returns the hash.c or related files. This sanity check can be manual or scripted.

5. **Use or Export the Mapping**: The graph now contains the mapping internally. We can use Joern queries or even export all feature→code pairs (by querying all tag nodes) to some report. But primarily, the mapping lives in the CPG for use in interactive queries or by an AI system performing RAG (which would query the graph as needed).

If the mapping process involves steps that can’t be done purely in Joern’s query language (like complex HTML parsing or very advanced text analysis), those can be done in a separate script, and the results (feature-to-code node matches) fed into the Joern augmentation steps. The end-to-end workflow can be automated so that updating the mapping for a new version or after code changes is straightforward.

## Conclusion

By following this approach, we achieve a robust, bidirectional mapping between **PostgreSQL 17’s features and its source code**, directly embedded in the code property graph. This solution provides traceability that is extremely useful for program comprehension, maintenance, and automated analysis. It leverages official data (the feature matrix) and powerful static analysis (Joern’s CPG) to connect the dots between high-level features and low-level implementation. The use of Joern’s tagging mechanism ensures the mapping is stored within the graph schema itself, making it queryable and maintainable (via Tag nodes and edges)[\[6\]](https://cpg.joern.io/#:~:text=).

Such a feature-tagged CPG can drive advanced tooling: new developers can ask questions about features and get pointed to relevant code, security tools can zero in on specific feature implementations, documentation generators can produce up-to-date references, and AI assistants can reason about the code at the feature level. In essence, we enrich the code graph with domain knowledge of the product, enabling smarter **RAG** workflows and more efficient development and analysis processes. The algorithm and example script described provide a blueprint to implement this mapping automatically. Going forward, this traceability can be continuously refined (using improved heuristics or feedback from engineers) to ensure it remains accurate and comprehensive, thereby serving as a valuable asset for the PostgreSQL developer community and any large-scale software engineering effort that requires aligning code with product features.

**Sources:**

* PostgreSQL Official Feature Matrix[\[1\]](https://www.postgresql.org/about/featurematrix/#:~:text=Feature%20Matrix)

* Joern Documentation – Augmenting CPG with Tags[\[8\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=joern%3E%20cpg.call.name%28)[\[9\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=joern%3E%20cpg.tag.name%28,%22MY_VALUE%22%29)

* Code Property Graph Schema (Tags)[\[6\]](https://cpg.joern.io/#:~:text=)

* Research on Requirements-to-Code Traceability (YamenTrace)[\[2\]](https://arxiv.org/abs/2307.05188#:~:text=,on%20engineers%20and%20is%20error)[\[7\]](https://arxiv.org/abs/2307.05188#:~:text=approach%20and%20implementation%20to%20recover,TLs%20were%20correctly%20recovered)

* Insights on Code Traceability Benefits[\[3\]](https://www.in-com.com/blog/code-traceability/#:~:text=One%20of%20the%20solutions%20to,test%20cases%2C%20and%20code%20modules)[\[4\]](https://www.in-com.com/blog/code-traceability/#:~:text=To%20implement%20traceability%20in%20software,numerous%20advantages%20for%20software%20quality)

---

[\[1\]](https://www.postgresql.org/about/featurematrix/#:~:text=Feature%20Matrix) [\[11\]](https://www.postgresql.org/about/featurematrix/#:~:text=18%2017%2016%2015%2014,side%20encryption) [\[12\]](https://www.postgresql.org/about/featurematrix/#:~:text=OAuth%20Authentication%20%2F%20Authorization%20,303%20security_barrier%20option%20on%20views) PostgreSQL: Feature Matrix

[https://www.postgresql.org/about/featurematrix/](https://www.postgresql.org/about/featurematrix/)

[\[2\]](https://arxiv.org/abs/2307.05188#:~:text=,on%20engineers%20and%20is%20error) [\[7\]](https://arxiv.org/abs/2307.05188#:~:text=approach%20and%20implementation%20to%20recover,TLs%20were%20correctly%20recovered) \[2307.05188\] Requirements Traceability: Recovering and Visualizing Traceability Links Between Requirements and Source Code of Object-oriented Software Systems

[https://arxiv.org/abs/2307.05188](https://arxiv.org/abs/2307.05188)

[\[3\]](https://www.in-com.com/blog/code-traceability/#:~:text=One%20of%20the%20solutions%20to,test%20cases%2C%20and%20code%20modules) [\[4\]](https://www.in-com.com/blog/code-traceability/#:~:text=To%20implement%20traceability%20in%20software,numerous%20advantages%20for%20software%20quality) [\[13\]](https://www.in-com.com/blog/code-traceability/#:~:text=implemented%20and%20tested%2C%20leading%20to,issues%2C%20saving%20time%20and%20effort) Understanding Code Traceability in Software Projects | IN-COM

[https://www.in-com.com/blog/code-traceability/](https://www.in-com.com/blog/code-traceability/)

[\[5\]](https://cpg.joern.io/#:~:text=) [\[6\]](https://cpg.joern.io/#:~:text=) Code Property Graph Specification Website | Code Property Graph Specification Website

[https://cpg.joern.io/](https://cpg.joern.io/)

[\[8\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=joern%3E%20cpg.call.name%28) [\[9\]](https://docs.joern.io/cpgql/augmentation-directives/#:~:text=joern%3E%20cpg.tag.name%28,%22MY_VALUE%22%29) Augmentation Directives | Joern Documentation

[https://docs.joern.io/cpgql/augmentation-directives/](https://docs.joern.io/cpgql/augmentation-directives/)

[\[10\]](https://docs.joern.io/cpgql/reference-card/#:~:text=methods%2C%20literals%2C%20types%20etc,to%20each%20of%20the%20nodes) Reference Card | Joern Documentation

[https://docs.joern.io/cpgql/reference-card/](https://docs.joern.io/cpgql/reference-card/)
