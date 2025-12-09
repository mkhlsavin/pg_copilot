## Systematic Hypothesis Generation for AI Copilot-Based Code Security Audits: Code Property Graphs and Multi-Criteria Vulnerability Discovery

### Overview and Core Concept

A concentrated security audit of large codebases (>1 million lines) using code property graphs (CPGs) and query-based analysis avoids traditional pattern scanning by replacing it with **systematic multi-criteria hypothesis generation**. This approach generates testable vulnerability hypotheses that are language-dependent, attack-method enumeration-based, and grounded in CWE weakness classification hierarchies.[1][2][3][4][5]

The foundational insight is that vulnerabilities can be modeled as **traversals across multiple code representation graphs simultaneously**. A code property graph integrates abstract syntax trees (ASTs), control flow graphs (CFGs), and program dependency graphs (PDGs), enabling the discovery of vulnerabilities that require joint inspection of code structure, data flow, and control dependencies. Rather than scanning for syntactic patterns, this method treats vulnerability discovery as a **constraint satisfaction and taint propagation problem** that can be formulated as graph queries.[6][7][1]

### Foundational Framework: Code Property Graphs and Query Languages

Code property graphs represent source code as directed graphs where nodes correspond to code elements (statements, expressions, function calls, variables) and edges represent syntactic, control-flow, or data-flow relationships. This unified representation enables expressing complex vulnerability patterns as graph traversals in query languages such as Joern (for C/C++), CodeQL (for multiple languages), or domain-specific languages (DSLs).[8][9][4][5][1][6]

The key advantage for large-scale audits is **inter-procedural analysis at scale**. Unlike pattern-based scanning that struggles with vulnerabilities spanning multiple functions or files, CPG-based queries can encode the complete path from a data source (attacker-controlled input) through sanitization (or lack thereof) to a sink (dangerous function).[7][6][8]

### Systematic Hypothesis Generation: Multi-Criteria Framework

Rather than manually specifying vulnerabilities, hypotheses are generated systematically along three orthogonal dimensions:

#### 1. **Language-Specific Semantic Patterns**

Different programming languages have distinct vulnerability manifestations. Research shows asymmetries in how vulnerabilities propagate across languages, even within the same paradigm. A systematic hypothesis generation framework must enumerate language-specific sinks and sources:[10]

- **C/C++**: Memory operations (malloc/free, buffer operations), pointer arithmetic, unsafe functions (strcpy, gets, sprintf)[9][1]
- **Java**: Reflection-based code execution, deserialization, Java Native Interface (JNI) boundary crossing
- **Python**: Dynamic code execution (eval, exec), weak type checking, implicit type conversions
- **JavaScript**: DOM manipulation, prototype pollution, callback-based asynchronous flows
- **PHP**: Variable variables, dynamic function calls, type juggling vulnerabilities

For each language, the hypothesis generator enumerates known dangerous APIs and their calling contexts, creating a **language-aware sink library**. This is distinct from pattern matching: sinks are discovered through inter-procedural type flow analysis across the CPG, ensuring that indirect paths to dangerous operations are also captured.[11]

#### 2. **CWE-Based Weakness Enumeration**

The Common Weakness Enumeration provides a hierarchical taxonomy of 800+ weakness types. Rather than treating CWEs as post-hoc classifications, they become **primary hypothesis generators**. For a selected CWE:[3][12][13]

1. **Identify abstract weakness properties**: What code patterns characterize this weakness? (e.g., CWE-79 XSS requires untrusted input flowing to HTML output without sanitization)

2. **Generate language-specific instantiations**: For each target language, enumerate the syntactic constructs and library functions that manifest this weakness. For example:
   - CWE-79 in Java: String concatenation to HTML output, JSP variables, template engines
   - CWE-79 in Python: jinja2 templates with unsafe autoescape, f-strings evaluated on user data
   - CWE-79 in C: sprintf/printf output not HTML-escaped

3. **Formalize as CPG queries**: Express the weakness as a query pattern specifying:
   - **Source nodes**: Functions or expressions that introduce untrusted data
   - **Sink nodes**: Functions or operations that are dangerous if receiving untrusted data
   - **Taint steps**: How data flows between sources and sinks (assignments, function arguments, field access)
   - **Sanitizers**: Code patterns that neutralize taint (input validation, output encoding)

#### 3. **Attack Method Enumeration**

Security vulnerabilities are fundamentally about exploitation. CAPEC (Common Attack Pattern Enumeration and Classification) and ATT&CK frameworks provide attack patterns that map to CWEs. Hypothesis generation can leverage known attack techniques:[14][15]

- **Attack pattern → CWE mapping**: Which weaknesses enable a specific attack? (e.g., "Privilege escalation" maps to CWE-269, CWE-276, CWE-862)
- **Resource type analysis**: What are the valuable resources in the application? (files, database records, configuration, authentication tokens). For each resource type and interaction pattern, enumerate plausible vulnerability hypotheses.
- **Threat actor methodology**: Different threat actors focus on different attack vectors. A hypothesis generator can enumerate vulnerabilities based on known threat tactics (e.g., "credential harvesting" directs focus to authentication and logging code).

This creates a **hypothesis priority queue**: hypotheses are ranked by likelihood based on:
- Frequency in vulnerability databases (CVE statistics per CWE)[3]
- Attack readiness (whether weaponized exploits exist, per EPSS scoring)[16]
- Applicability to the target language and framework

### Formalizing Hypotheses as CPG Queries

Once hypotheses are generated, they must be formalized as executable queries. This is where code property graphs enable precision:

#### Source-Sink Taint Analysis with Flow States

Taint tracking is the canonical vulnerability discovery pattern. A source is where untrusted data enters (user input, file reads). A sink is where that data could cause harm (SQL queries, shell commands, file operations). A hypothesis asserts that a taint path exists from a source to a sink without passing through sanitizers.[17][18][19][20][7]

CodeQL and similar tools support **flow states**, allowing fine-grained tracking of data properties. For example:
- Track whether an integer could overflow (state: "potentially_large")
- Track whether a path could be absolute vs. relative (for CWE-22 directory traversal)[7]
- Track whether HTML escaping has been applied (for CWE-79)

This enables hypotheses like: **"Integer read from untrusted source in a size calculation without overflow check flows to a memory allocation"** (CWE-190, buffer overflow).

#### Query Synthesis from Specifications

Manual query writing is labor-intensive and error-prone. Recent research demonstrates that Large Language Models can synthesize CodeQL queries from vulnerability specifications. The synthesis loop:[5]

1. **CVE metadata → initial query**: Given a CVE description and affected code, generate a candidate query
2. **Validator feedback**: Execute the query against both vulnerable and patched versions, measure recall/precision
3. **Iterative refinement**: Use validation results to refine the query (add taint steps, refine sources/sinks, add sanitizers)

This enables a **hypothesis-driven feedback cycle**: generate hypotheses from attack methods and CWEs, synthesize queries for each hypothesis, validate against known vulnerabilities, refine and re-apply.[5]

### Systematic Multi-Criteria Hypothesis Generation: Operational Workflow

A practical implementation would follow this workflow:

#### Phase 1: Hypothesis Space Construction

1. **Language characterization**: For the target language (C, Python, Java, etc.), enumerate:
   - Standard library unsafe functions (with reference to language documentation and CWE)
   - Framework-specific sinks (e.g., Django ORM methods that are vulnerable to SQL injection if misused)
   - Inter-language boundaries (e.g., JNI in Java, ctypes in Python) that introduce new attack surfaces

2. **CWE selection**: Prioritize CWEs based on:
   - Frequency in the target codebase's domain (e.g., memory errors are more likely in C/C++)[21][10]
   - Historical prevalence (MITRE's Most Dangerous Software Weaknesses list)[3]
   - Business context (a financial application prioritizes authentication/authorization CWEs)[16]

3. **Attack pattern mapping**: For each CWE, enumerate:
   - CAPEC attack patterns that exploit it
   - TTPs (Tactics, Techniques, Procedures) from threat intelligence
   - Known exploits and proof-of-concepts

4. **Weakness property formalization**: For each CWE, define:
   - Necessary code conditions for the weakness to exist (e.g., "buffer size is fixed at compile time" for classic buffer overflow)
   - Sufficient evidence of the weakness (e.g., "user-controlled value written to fixed buffer without bounds check")
   - Language-specific instantiations[22]

#### Phase 2: Hypothesis Enumeration and Prioritization

Generate candidate hypotheses by **Cartesian product** of:
- Language-specific sinks (from Phase 1)
- CWE weakness properties
- Data flow patterns (direct, indirect through function calls, through collections, etc.)
- Sanitization patterns (input validation, output encoding, etc.)

Prioritize by:
- Exploitability (EPSS scores for known CVEs mapping to this CWE-language combination)[16]
- Reachability (how many code paths can reach this sink from attacker-controlled sources?)
- Impact (what is the business consequence if exploited?)

#### Phase 3: Query Formalization and Execution

For each prioritized hypothesis:

1. **Encode as CPG query**: Specify sources, sinks, taint steps, and sanitizers
   - For interprocedural analysis, explicitly model function call semantics and library behavior
   - For context-sensitive analysis, track call stack and local variable ownership
   
2. **Execute against codebase**: Run the query over the CPG built from the target code
   
3. **Result post-processing**:
   - Group results by call chain (to identify common vulnerabilities across multiple code locations)
   - Filter false positives using syntactic or semantic checks
   - Correlate with code metrics (complexity, maintainability) to improve prioritization

#### Phase 4: Validation and Refinement

- **Known vulnerability validation**: If the codebase has historical vulnerabilities, validate that the hypothesis queries detect them
- **False positive analysis**: Mismatches between queries and actual vulnerabilities inform sanitizer pattern refinement
- **Hypothesis evolution**: As patterns of safe/unsafe code are discovered, update the CWE → query mapping for future use

### Language-Specific Pattern Instantiation: Concrete Examples

#### C/C++ Buffer Overflow (CWE-120)

Hypothesis components:
- **Language factors**: Fixed-size arrays, pointer arithmetic, unsafe string functions (strcpy, gets)
- **CWE property**: "Fixed buffer size < untrusted data length"
- **Attack method**: Overwrite return address or function pointer to gain code execution

CPG query pattern:
```
1. Find all buffer allocations with static size (array[N] or malloc(N))
2. Find all writes to that buffer (strcpy, memcpy, sprintf, direct assignment)
3. Trace the source of written data back to untrusted input
4. Check if the written length is checked against buffer size
5. If not, flag as potential overflow
```

#### Java Deserialization (CWE-502)

Hypothesis components:
- **Language factors**: ObjectInputStream.readObject(), Java reflection, gadget chains in libraries
- **CWE property**: "Untrusted serialized object deserialized without validation"
- **Attack method**: Malicious serialized object triggers code execution through gadget chains

CPG query pattern:
```
1. Find all ObjectInputStream.readObject() calls
2. Trace the InputStream source back to untrusted input
3. Check for presence of a ValidatingObjectInputStream or filter
4. Identify imported gadget libraries (commons-collections, ROME, etc.) that could chain
5. If no validation present, flag as potential RCE
```

#### Python SQL Injection (CWE-89)

Hypothesis components:
- **Language factors**: String formatting (f-strings, %), .format(), string concatenation in SQL queries
- **CWE property**: "SQL query constructed with user-controlled string without parameterized query"
- **Attack method**: Inject SQL keywords (UNION, DROP, etc.) to manipulate database logic

CPG query pattern:
```
1. Find all database query methods (cursor.execute(), session.query(), etc.)
2. Trace the query string argument back to its source
3. Check if the argument is constructed from untrusted data without parameterization
4. Distinguish between parameterized queries (safe) and string concatenation (unsafe)
5. If unsafe construction with untrusted data, flag as SQL injection
```

### Integration with Query Language Execution

For practical implementation, the hypothesis generation framework outputs queries in a target query language:

- **Joern** (C/C++): Domain-specific language for C/C++ code property graphs; traversals expressed as fluent API calls
- **CodeQL** (multi-language): SQL-like query language for querying code as relational data
- **Custom DSLs**: Domain-specific languages tailored to the target codebase (e.g., framework-specific vulnerability patterns)[4][23]

Query generation can be **semi-automated**: hypotheses are formalized as templates, and LLMs synthesize concrete queries for the target codebase and language. The synthesizer uses:[5]
- **In-context learning**: Examples of correct queries and incorrect patterns
- **Validator feedback**: Execution results guide query refinement
- **MCP interfaces**: Language server protocol integration enables syntax checking and API discovery[5]

### Addressing Scale and Precision

For codebases exceeding one million lines:

1. **Graph partitioning**: Divide the CPG into logical components (modules, packages, layers) and analyze independently before cross-module analysis

2. **Incremental analysis**: On code changes (commits), re-analyze only affected subgraphs rather than the entire CPG

3. **Hypothesis prioritization**: Execute high-confidence hypotheses (frequent in CVE databases) before exploratory ones

4. **Result correlation**: Cluster similar findings (e.g., all instances of unsafe strcpy in one module) to reduce false positives and actionable findings

5. **Feedback loop**: Integrate findings from manual code review and penetration testing to refine hypothesis priors

### Advantages Over Traditional Pattern Scanning

- **Precision**: Context-aware analysis reduces false positives by requiring evidence across multiple code properties (control flow, data flow, type information)
- **Completeness**: Inter-procedural analysis captures vulnerabilities spanning multiple functions and files
- **Adaptability**: New attack methods and CWEs are incorporated by extending the hypothesis space, not by writing new pattern rules
- **Explainability**: Each hypothesis corresponds to a known attack method, CWE, or exploit technique, making findings actionable
- **Language independence**: The framework can target multiple languages by instantiating language-specific sinks and sources

### Research Gaps and Future Directions

While code property graphs and query-based analysis are mature, several challenges remain:

1. **Implicit flows**: Vulnerabilities arising from implicit data flow (control dependencies, timing side channels) are difficult to capture in standard CPGs[17]

2. **Dynamic behavior**: Languages with late binding, reflection, or eval() complicate static analysis; taint propagation through dynamic calls requires heuristics

3. **Scalability of inter-procedural analysis**: Precise inter-procedural analysis has theoretical complexity bounds; practical tools often use approximations[24]

4. **Sanitizer specification**: Defining what counts as a "sanitizer" is context-dependent; automatic inference of sanitizer correctness remains an open problem

5. **CWE evolution**: The CWE hierarchy is continuously updated; maintaining alignment between vulnerability classification and code patterns is labor-intensive

### Conclusion

A systematic approach to source code security auditing at scale combines **code property graphs** (for unified code representation), **query languages** (for executable hypothesis formalization), and **multi-criteria hypothesis generation** (grounded in CWE weakness classification and attack method enumeration). This shifts vulnerability discovery from pattern matching toward **constraint satisfaction and taint tracking**, enabling precision and scalability for large codebases without requiring manual pattern specification for each vulnerability type.

The framework is language-dependent (exploiting language semantics for precision), hypothesis-driven (grounded in known attack methods and weakness types), and executable (queries can be synthesized, validated, and refined iteratively against known vulnerabilities). Integration with Large Language Models for query synthesis further reduces manual effort, enabling concentration of security audit resources on validation, prioritization, and remediation rather than hypothesis specification.

[1](https://comsecuris.com/papers/06956589.pdf)
[2](https://ieeexplore.ieee.org/document/11136289/)
[3](https://www.emergentmind.com/topics/common-weakness-enumeration-cwe)
[4](https://asankhaya.github.io/pdf/Security-Graph-Language.pdf)
[5](https://arxiv.org/html/2511.08462v1)
[6](https://fluidattacks.com/blog/code-property-graphs-for-analysis)
[7](https://codeql.github.com/docs/codeql-language-guides/using-flow-labels-for-precise-data-flow-analysis/)
[8](https://docs.joern.io/traversal-basics/)
[9](https://www.praetorian.com/blog/why-you-should-add-joern-to-your-source-code-audit-toolkit/)
[10](https://lilicoding.github.io/papers/li2022vulnerability.pdf)
[11](https://www.nist.gov/itl/ssd/software-quality-group/source-code-security-analyzers)
[12](https://nvd.nist.gov/vuln/categories)
[13](https://cwe.mitre.org)
[14](https://arxiv.org/abs/2309.02785)
[15](http://arxiv.org/pdf/2501.07131.pdf)
[16](https://www.wiz.io/academy/vulnerability-prioritization)
[17](http://bitblaze.cs.berkeley.edu/papers/dta++-ndss11.pdf)
[18](https://arxiv.org/html/2510.20739v1)
[19](https://users.ece.cmu.edu/~aavgerin/papers/Oakland10.pdf)
[20](https://www.ispras.ru/proceedings/isp_11_2006/isp_11_2006_83/)
[21](http://arxiv.org/pdf/2503.20244.pdf)
[22](https://gala.gre.ac.uk/id/eprint/49340/13/49340%20KHAN_Towards_Integration_Of_Syntactic_And_Semantic_Vulnerability_Patterns_(AAM)_2024.pdf)
[23](http://www.diva-portal.org/smash/get/diva2:1886206/FULLTEXT01.pdf)
[24](https://dl.acm.org/doi/10.1145/359588.359596)
[25](https://www.mdpi.com/1999-5903/15/10/326)
[26](https://dl.acm.org/doi/10.1145/3607199.3607242)
[27](https://linkinghub.elsevier.com/retrieve/pii/S0950584913000384)
[28](https://www.hindawi.com/journals/scn/2022/7972230/)
[29](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication500-268v1.1.pdf)
[30](https://www.scitepress.org/DigitalLibrary/Link.aspx?doi=10.5220/0013176200003899)
[31](https://www.semanticscholar.org/paper/1ad6a16ebcd8c2afbeb7eb5f989e48a98468353a)
[32](https://ieeexplore.ieee.org/document/9426068/)
[33](http://link.springer.com/10.1007/978-3-030-15235-2_66)
[34](http://journals.dut.edu.ua/index.php/dataprotect/article/view/2580)
[35](https://thescipub.com/pdf/jcssp.2019.1780.1794.pdf)
[36](https://arxiv.org/pdf/2311.16396.pdf)
[37](https://arxiv.org/pdf/1302.1338.pdf)
[38](https://arxiv.org/pdf/2502.07049.pdf)
[39](http://arxiv.org/pdf/2209.10414.pdf)
[40](http://arxiv.org/pdf/2405.16655.pdf)
[41](http://arxiv.org/pdf/2501.09191.pdf)
[42](https://arxiv.org/pdf/1803.06545.pdf)
[43](https://www.vaadata.com/blog/understanding-source-code-audit-methodology-and-process/)
[44](https://www.nature.com/articles/s41598-022-27059-0)
[45](https://xygeni.io/blog/source-code-security-best-practices-to-protect-your-code-integrity/)
[46](https://us.sagepub.com/sites/default/files/upm-assets/72259_book_item_72259.pdf)
[47](https://arxiv.org/pdf/2503.18175.pdf)
[48](https://checkmarx.com/learn/sast/effective-static-source-code-analysis/)
[49](https://aclanthology.org/2024.nlp4science-1.17.pdf)
[50](https://www.reddit.com/r/cybersecurity/comments/1mk6zia/how_do_you_tackle_source_code_security_its_a_huge/)
[51](https://www.e-informatyka.pl/EISEJ/papers/2025/1/3)
[52](https://www.tandfonline.com/doi/full/10.1080/1206212X.2025.2452849)
[53](https://www.mdpi.com/1424-8220/21/4/1133)
[54](https://www.mdpi.com/2073-431X/13/1/22)
[55](https://carijournals.org/journals/index.php/IJCE/article/view/2258)
[56](https://dl.acm.org/doi/10.1145/3722041.3723097)
[57](https://link.springer.com/10.1007/s00521-024-09819-3)
[58](https://dl.acm.org/doi/10.1145/3641399.3641405)
[59](https://ieeexplore.ieee.org/document/10958267/)
[60](http://arxiv.org/pdf/2403.15169.pdf)
[61](https://arxiv.org/pdf/2502.11143.pdf)
[62](http://downloads.hindawi.com/journals/tswj/2015/703713.pdf)
[63](https://arxiv.org/pdf/2309.03040.pdf)
[64](https://arxiv.org/pdf/1905.10328.pdf)
[65](https://pmc.ncbi.nlm.nih.gov/articles/PMC4433707/)
[66](http://ijece.iaescore.com/index.php/IJECE/article/download/24601/15124)
[67](https://arxiv.org/pdf/1707.08015.pdf)
[68](https://www.sciencedirect.com/science/article/abs/pii/S016740481830854X)
[69](https://www.hackerone.com/knowledge-center/what-vulnerability-assessment-benefits-tools-and-process)
[70](https://coderpad.io/blog/development/code-property-graph-oriented-databases-source-code-analysis/)
[71](https://orca.security/resources/blog/what-is-vulnerability-management/)
[72](http://ieeexplore.ieee.org/document/5304255/)
[73](http://ieeexplore.ieee.org/document/5999219/)
[74](https://ijsrcseit.com/CSEIT22857)
[75](https://ieeexplore.ieee.org/document/10706239/)
[76](https://dl.acm.org/doi/10.1145/3691621.3694950)
[77](https://www.nature.com/articles/s41598-024-56871-z)
[78](https://dl.acm.org/doi/10.1145/3665348.3665391)
[79](https://ieeexplore.ieee.org/document/10899694/)
[80](http://journals.uran.ua/tarp/article/view/233534)
[81](https://arxiv.org/pdf/2501.04510.pdf)
[82](https://arxiv.org/pdf/2311.05281.pdf)
[83](http://arxiv.org/pdf/2106.10478.pdf)
[84](https://arxiv.org/pdf/2104.09225.pdf)
[85](https://downloads.hindawi.com/journals/scn/2021/5566423.pdf)
[86](http://arxiv.org/pdf/2404.14719.pdf)
[87](http://arxiv.org/pdf/2410.18479.pdf)
[88](http://arxiv.org/pdf/2404.15596.pdf)
[89](https://pmc.ncbi.nlm.nih.gov/articles/PMC11945435/)
[90](https://www.arxiv.org/pdf/2507.22659.pdf)
[91](https://www.scitepress.org/Papers/2025/133815/133815.pdf)
[92](https://www.sciencedirect.com/topics/computer-science/vulnerability-pattern)
[93](https://www.sciencedirect.com/science/article/abs/pii/S221421262200148X)
[94](https://www.scirp.org/journal/paperinformation?paperid=128108)
[95](https://arxiv.org/html/2509.00882v3)
[96](https://www.semanticscholar.org/paper/9b189c9c914ebe4244856d69c129941c4ecd7adb)
[97](https://www.semanticscholar.org/paper/32f5afe79aa0f0893183f6dcb136c421fe06ef60)
[98](https://ojs.aaai.org/index.php/AAAI-SS/article/view/31190)
[99](https://ieeexplore.ieee.org/document/9708860/)
[100](http://ijece.iaescore.com/index.php/IJECE/article/view/25198)
[101](https://journals.sagepub.com/doi/10.1177/1088467X251348350)
[102](http://thesai.org/Publications/ViewPaper?Volume=15&Issue=4&Code=IJACSA&SerialNo=90)
[103](https://aclanthology.org/2023.clinicalnlp-1.32)
[104](https://arxiv.org/pdf/2308.11237.pdf)
[105](http://arxiv.org/pdf/2501.13291.pdf)
[106](https://arxiv.org/pdf/2309.02785.pdf)
[107](http://arxiv.org/pdf/2407.18877.pdf)
[108](http://arxiv.org/pdf/2410.00249.pdf)
[109](http://arxiv.org/pdf/2309.14677.pdf)
[110](https://downloads.hindawi.com/journals/cin/2022/2998448.pdf)
[111](https://arxiv.org/pdf/2112.04231.pdf)
[112](https://www.yeswehack.com/learn-bug-bounty/subdomain-enumeration-expand-attack-surface)
[113](https://www.cs.cmu.edu/~wing/publications/tr04-102.pdf)
[114](https://docs.gitlab.com/user/application_security/sast/)
[115](https://www.carlosrodriguez.info/papers/CAiSE19_Security_Vulnerabilities_Information_Service.pdf)
[116](https://capec.mitre.org/documents/documentation/CAPEC_Schema_Description_v1.3.pdf)
[117](https://snyk.io/articles/code-review/finding-vulnerabilities-in-source-code/)
[118](https://eelcovisser.org/publications/2007/Visser07.pdf)
[119](https://dl.acm.org/doi/10.1145/3755881.3755934)
[120](https://arxiv.org/abs/2401.10337)
[121](https://ieeexplore.ieee.org/document/10910820/)
[122](https://ieeexplore.ieee.org/document/10179994/)
[123](https://www.semanticscholar.org/paper/bfc8e99211cb4577a35ec6439aa7004a9288d758)
[124](https://ieeexplore.ieee.org/document/10775064/)
[125](http://link.springer.com/10.1007/978-3-319-93647-5_10)
[126](https://www.mdpi.com/2227-9709/12/3/67)
[127](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/12176/2636397/Research-on-Web-application-injection-vulnerabilities-detection-method-based-on/10.1117/12.2636397.full)
[128](https://ieeexplore.ieee.org/document/11088821/)
[129](http://arxiv.org/pdf/2310.20067.pdf)
[130](https://arxiv.org/abs/2306.06109)
[131](https://arxiv.org/pdf/1909.03496.pdf)
[132](https://dl.acm.org/doi/pdf/10.1145/3658644.3690214)
[133](http://arxiv.org/pdf/2406.05403.pdf)
[134](https://phoenixcyber.com/blog/testing-threat-hunting-hypotheses/)
[135](https://blog.securitybreak.io/introducing-nova-f4244216ae2c)
[136](https://www.splunk.com/en_us/blog/security/peak-hypothesis-driven-threat-hunting.html)
[137](https://www.sciencedirect.com/science/article/abs/pii/S0164121225001967)
[138](https://www.scip.ch/en/?labs.20240418)
[139](https://github.com/fr0gger/nova-framework)
[140](https://dl.acm.org/doi/10.1145/3617555.3617874)
[141](https://ieeexplore.ieee.org/document/11081727/)
[142](https://ieeexplore.ieee.org/document/10577942/)
[143](https://ieeexplore.ieee.org/document/10720350/)
[144](https://dl.acm.org/doi/10.1145/3689374)
[145](https://ieeexplore.ieee.org/document/11173504/)
[146](https://www.mdpi.com/2079-9292/13/23/4660)
[147](https://dl.acm.org/doi/10.1145/3719027.3765213)
[148](https://ieeexplore.ieee.org/document/10169022/)
[149](https://ieeexplore.ieee.org/document/10546867/)
[150](http://thesai.org/Downloads/Volume10No6/Paper_21-A_Review_on_the_Verification_Approaches.pdf)
[151](https://arxiv.org/pdf/2212.02626.pdf)
[152](http://arxiv.org/pdf/2307.02192.pdf)
[153](https://arxiv.org/pdf/1101.1815.pdf)
[154](https://arxiv.org/pdf/1201.5666.pdf)
[155](https://arxiv.org/pdf/2411.17926.pdf)
[156](https://arxiv.org/pdf/2109.01362.pdf)
[157](http://arxiv.org/pdf/0902.2137.pdf)
[158](https://www.sciencedirect.com/science/article/abs/pii/S0164121224002632)
[159](https://www.cybok.org/media/downloads/Formal_Methods_for_Security_v1.0.0.pdf)
[160](https://devv.ai/tools/sql-code-generator)
[161](https://chapering.github.io/pubs/icse23yu.pdf)
[162](https://www.eurecom.fr/publication/4974/download/sec-publi-4974.pdf)
[163](https://www.sqlai.ai)
[164](https://drops.dagstuhl.de/storage/01oasics/oasics-vol133-icpec2025/OASIcs.ICPEC.2025.4/OASIcs.ICPEC.2025.4.pdf)
[165](https://github.com/ElNiak/awesome-formal-verification)
[166](https://ieeexplore.ieee.org/document/10684618/)
[167](https://www.semanticscholar.org/paper/ef16b3439fe74345d42eeb26f25d9e30640145cb)
[168](https://ieeexplore.ieee.org/document/9687053/)
[169](https://arxiv.org/abs/2503.20244)
[170](https://dl.acm.org/doi/10.1145/3564625.3567985)
[171](https://arxiv.org/abs/2410.15288)
[172](https://ieeexplore.ieee.org/document/11127134/)
[173](https://ieeexplore.ieee.org/document/11237115/)
[174](https://ieeexplore.ieee.org/document/10471253/)
[175](https://www.mdpi.com/2504-4990/6/2/50)
[176](http://arxiv.org/pdf/2408.06428.pdf)
[177](http://arxiv.org/pdf/2309.08115v1.pdf)
[178](http://arxiv.org/pdf/2406.12415.pdf)
[179](https://arxiv.org/pdf/1901.11479.pdf)
[180](http://arxiv.org/pdf/2412.06166.pdf)
[181](https://arxiv.org/pdf/2303.06177.pdf)
[182](https://www.youtube.com/watch?v=0eazUsvqMvw)
[183](https://www.picussecurity.com/resource/blog/the-most-common-security-weaknesses-cwe-top-25-and-owasp-top-10)
[184](https://www.legitsecurity.com/aspm-knowledge-base/best-programming-language-for-cyber-security)
[185](https://cwe.mitre.org/data/definitions/1344.html)
[186](https://www.tandfonline.com/doi/full/10.1080/09540091.2024.2447373)
[187](https://www.open-std.org/jtc1/sc22/wg23/docs/ISO-IECJTC1-SC22-WG23_N0868-tr24772-1-language-independent-guidance-for-formal-editing-20190225.pdf)
[188](https://owasp.org/Top10/2025/A05_2025-Injection/)
[189](https://github.com/CGCL-codes/VulCNN)
[190](https://arxiv.org/html/2412.15905v2)