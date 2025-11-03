# GQL/Cypher Query Reference for AICO Knowledge Graph

> **GQL (Graph Query Language)** is the ISO standard (ISO/IEC 39075:2024) for querying property graphs. AICO implements GQL/Cypher via GrandCypher, allowing powerful graph queries over your knowledge graph.

## Table of Contents

- [Quick Start](#quick-start)
- [Basic Queries](#basic-queries)
- [Pattern Matching](#pattern-matching)
- [Filtering](#filtering)
- [Aggregations](#aggregations)
- [Advanced Queries](#advanced-queries)
- [Best Practices](#best-practices)

---

## Quick Start

### Usage
```bash
# Semantic search (vector similarity)
aico kg query "people who work" --user-id <USER_ID>

# GQL query (pattern matching)
aico kg query --gql "MATCH (p:PERSON) RETURN p.name" --user-id <USER_ID>

# GQL from file
aico kg query --gql --file query.cypher --user-id <USER_ID>

# Different output formats
aico kg query --gql "MATCH (p:PERSON) RETURN p.name" --user-id <USER_ID> --format json
aico kg query --gql "MATCH (p:PERSON) RETURN p.name" --user-id <USER_ID> --format csv
```

> **Note:** AICO provides REST API endpoints at `/api/v1/kg/query` and `/api/v1/kg/stats`, but they require proper client implementation with encryption handshake support. For command-line usage and testing, use the CLI commands shown above.

---

## Basic Queries

Understanding basic query patterns is essential for exploring your knowledge graph. These queries form the foundation for more complex operations.

### 1. Match All Nodes

**What it does:** Returns all nodes in your knowledge graph, giving you a complete overview of stored entities.

**When to use:** 
- Initial exploration of your knowledge graph
- Understanding what types of entities are stored
- Debugging data extraction issues
- Getting a sense of graph size and content

**Real-world example:** You want to see what information AICO has extracted from your conversations. This query shows you all entities (people, places, organizations, etc.) that have been identified and stored.

**CLI:**
```bash
aico kg query --gql "MATCH (n) RETURN n LIMIT 10" --user-id <USER_ID>
```

**Pro tip:** Always use `LIMIT` to avoid overwhelming output. Start with 10-20 results, then increase if needed.

---

### 2. Match Nodes by Label

**What it does:** Filters nodes by their type (label), returning only entities of a specific category.

**When to use:**
- Finding all people mentioned in conversations
- Listing all companies or organizations you've discussed
- Identifying all locations you've referenced
- Analyzing specific entity types

**Real-world example:** You want to see all the people AICO knows about from your conversations. This could include colleagues, friends, family members, or anyone mentioned in your chats. Use this to verify that important people are being correctly identified and stored.

**CLI:**
```bash
aico kg query --gql "MATCH (p:PERSON) RETURN p.name LIMIT 10" --user-id <USER_ID>
```

**Available Labels:**
- `PERSON` - People (colleagues, friends, family, contacts)
- `ORGANIZATION` / `ORG` - Companies, institutions, teams
- `GPE` - Geopolitical entities (cities, countries, regions)
- `LOCATION` - Physical places (buildings, addresses, landmarks)
- `DATE` - Temporal references (dates, times, periods)
- `EVENT` - Occurrences (meetings, deadlines, milestones)

**Pro tip:** Labels are case-sensitive. Use uppercase for consistency (e.g., `PERSON` not `person`).

---

### 3. Return Specific Properties

**What it does:** Instead of returning entire node objects, selects only the properties you care about, making output cleaner and more focused.

**When to use:**
- Creating reports or summaries
- Exporting data to other systems
- Reducing output verbosity
- Focusing on specific attributes

**Real-world example:** You're preparing a contact list and only need names and email addresses, not all the metadata AICO has stored about each person. This query gives you exactly what you need without extra noise.

**CLI:**
```bash
aico kg query --gql "MATCH (p:PERSON) RETURN p.name, p.age" --user-id <USER_ID>
```

**Common properties:**
- `name` - Entity name (present on most nodes)
- `start`, `end` - Text position where entity was found
- Custom properties extracted from context (e.g., `role`, `email`, `phone`)

**Pro tip:** Use `RETURN p` to see all available properties first, then refine your query to select specific ones.

---

## Pattern Matching

Pattern matching is where graph queries become powerful. Instead of just finding isolated entities, you can discover how they're connected and explore the relationships between them.

### 4. Match Relationships

**What it does:** Discovers connections between entities by following relationship edges in the graph.

**When to use:**
- Understanding how entities are related
- Finding all connections for a specific person or organization
- Mapping out your professional or personal network
- Discovering indirect relationships

**Real-world example:** You mentioned your colleague "Sarah" works at "TechCorp" in a conversation. This query reveals that connection, showing you not just that Sarah exists as an entity, but specifically how she relates to other entities in your knowledge graph. It's like asking "who is connected to what?"

**CLI:**
```bash
aico kg query --gql "MATCH (p:PERSON)-[r]->(target) RETURN p.name, target.name" --user-id <USER_ID>
```

**What you'll see:** Pairs of entities with their connections, like:
- "Sarah" → "TechCorp"
- "John" → "New York"
- "Alice" → "Project Alpha"

**Pro tip:** The arrow `->` indicates direction. Use `--` for bidirectional matching when direction doesn't matter.

---

### 5. Match Specific Relationship Types

**What it does:** Filters relationships by type, showing only specific kinds of connections (e.g., employment, location, membership).

**When to use:**
- Finding everyone who works at a specific company
- Listing all people in a particular city
- Identifying team members or project participants
- Building org charts or network diagrams

**Real-world example:** You're preparing for a meeting and want to know everyone on your team who works at your company. Instead of manually remembering, this query pulls all WORKS_FOR relationships, giving you an instant roster of colleagues and their organizations.

**CLI:**
```bash
aico kg query --gql "MATCH (p:PERSON)-[r:WORKS_FOR]->(c:ORGANIZATION) RETURN p.name, c.name" --user-id <USER_ID>
```

**Common Relationship Types:**
- `WORKS_FOR` / `WORKS_AT` - Employment relationships (person → company)
- `LIVES_IN` / `LOCATED_IN` - Geographic relationships (person → city, company → location)
- `KNOWS` - Personal connections (person → person)
- `PART_OF` - Membership or belonging (person → team, team → organization)
- `HAPPENED_IN` - Event location (event → place)

**Pro tip:** Relationship types are extracted automatically from conversation context. Check what types exist in your graph with `MATCH ()-[r]->() RETURN DISTINCT type(r)`.

---

### 6. Multi-Hop Traversal

**What it does:** Follows multiple relationship steps in sequence, discovering indirect connections through intermediate entities.

**When to use:**
- Finding connections between seemingly unrelated entities
- Discovering paths through your network
- Understanding complex relationships (e.g., "who do I know who works at companies in Seattle?")
- Building recommendation systems

**Real-world example:** You want to find people you might know through mutual connections. A 2-hop query finds "friends of friends" - people connected to someone you know. A 3-hop query goes even further, revealing extended network connections you might not have considered.

**CLI:**
```bash
aico kg query --gql "MATCH (a)-[]->(b)-[]->(c) RETURN a.name, b.name, c.name LIMIT 10" --user-id <USER_ID>
```

**Practical example - Find colleagues in specific cities:**
```cypher
MATCH (person:PERSON)-[:WORKS_FOR]->(company:ORGANIZATION)-[:LOCATED_IN]->(city:GPE)
RETURN person.name, company.name, city.name
```

This reveals: "Sarah works at TechCorp which is located in Seattle"

**Pro tip:** Each hop multiplies the result set. Use `LIMIT` generously and start with 2-3 hops max to avoid performance issues.

---

### 7. Bidirectional Relationships

**What it does:** Matches relationships regardless of direction, useful when the relationship direction isn't important or when relationships are symmetric.

**When to use:**
- Finding mutual connections (e.g., "who knows whom")
- Discovering all entities connected to a specific node
- Exploring undirected relationships like "KNOWS" or "RELATED_TO"
- Simplifying queries when direction doesn't matter

**Real-world example:** You want to find everyone connected to your project, regardless of whether they're assigned to it, leading it, or participating in it. Bidirectional matching finds all these connections without worrying about the arrow direction.

**CLI:**
```bash
aico kg query --gql "MATCH (a)--(b) RETURN a.name, b.name LIMIT 10" --user-id <USER_ID>
```

**Pro tip:** Use `--` (no arrow) for bidirectional, `->` for outgoing, `<-` for incoming relationships.

---

## Filtering

### 8. Filter by Property Value

**Description:** Use `WHERE` clause to filter nodes by property values.

**CLI:**
```bash
aico kg query --gql 'MATCH (p:PERSON) WHERE p.age > 25 RETURN p.name, p.age' --user-id <USER_ID>
```

**Comparison Operators:**
- `=` - Equal
- `>` - Greater than
- `<` - Less than
- `>=` - Greater than or equal
- `<=` - Less than or equal
- `<>` - Not equal

---

### 9. Filter with AND/OR

**Description:** Combine multiple conditions.

**CLI:**
```bash
aico kg query --gql 'MATCH (p:PERSON) WHERE p.age > 25 AND p.name = "Alice" RETURN p' --user-id <USER_ID>
```

---

### 10. Filter by Relationship Properties

**Description:** Filter based on relationship attributes.

**CLI:**
```bash
aico kg query --gql 'MATCH (p)-[r:WORKS_FOR]->(c) WHERE r.since > 2020 RETURN p.name, c.name' --user-id <USER_ID>
```

---

## Aggregations

### 11. Count Nodes

**Description:** Count matching nodes.

**CLI:**
```bash
aico kg query --gql "MATCH (p:PERSON) RETURN COUNT(p)" --user-id <USER_ID>
```

---

### 12. Group and Count

**Description:** Group by property and count.

**CLI:**
```bash
aico kg query --gql "MATCH (p:PERSON)-[:WORKS_FOR]->(c) RETURN c.name, COUNT(p)" --user-id <USER_ID>
```

---

### 13. Sum, Average, Min, Max

**Description:** Aggregate numeric properties.

**CLI:**
```bash
aico kg query --gql "MATCH (p:PERSON) RETURN AVG(p.age), MIN(p.age), MAX(p.age)" --user-id <USER_ID>
```

**Available Aggregations:**
- `COUNT(x)` - Count items
- `SUM(x)` - Sum numeric values
- `AVG(x)` - Average
- `MIN(x)` - Minimum
- `MAX(x)` - Maximum

---

## Advanced Queries

### 14. Order Results

**Description:** Sort results by property.

**CLI:**
```bash
aico kg query --gql "MATCH (p:PERSON) RETURN p.name, p.age ORDER BY p.age DESC LIMIT 10" --user-id <USER_ID>
```

---

### 15. Skip and Limit (Pagination)

**Description:** Implement pagination with `SKIP` and `LIMIT`.

**CLI:**
```bash
# Page 1 (first 10)
aico kg query --gql "MATCH (p:PERSON) RETURN p.name LIMIT 10" --user-id <USER_ID>

# Page 2 (next 10)
aico kg query --gql "MATCH (p:PERSON) RETURN p.name SKIP 10 LIMIT 10" --user-id <USER_ID>
```

---

### 16. Distinct Results

**Description:** Remove duplicate results.

**CLI:**
```bash
aico kg query --gql "MATCH (p:PERSON)-[:WORKS_FOR]->(c) RETURN DISTINCT c.name" --user-id <USER_ID>
```

---

### 17. Complex Pattern: Find Colleagues

**Description:** Find people who work at the same company.

**CLI:**
```bash
aico kg query --gql "MATCH (p1:PERSON)-[:WORKS_FOR]->(c)<-[:WORKS_FOR]-(p2:PERSON) WHERE p1.name <> p2.name RETURN p1.name, p2.name, c.name" --user-id <USER_ID>
```

---

### 18. Complex Pattern: Find Common Connections

**Description:** Find entities that two people are both connected to.

**CLI:**
```bash
aico kg query --gql 'MATCH (p1:PERSON)-[]->(common)<-[]-(p2:PERSON) WHERE p1.name = "Alice" AND p2.name = "Bob" RETURN common.name' --user-id <USER_ID>
```

---

## Best Practices

### Performance Tips

1. **Always use LIMIT** - Prevent large result sets
   ```cypher
   MATCH (n) RETURN n LIMIT 100
   ```

2. **Filter early** - Use WHERE clauses to reduce data
   ```cypher
   MATCH (p:PERSON) WHERE p.age > 25 RETURN p
   ```

3. **Specify labels** - More efficient than matching all nodes
   ```cypher
   MATCH (p:PERSON)  -- Good
   MATCH (p)         -- Slower
   ```

4. **Use indexes** - Filter by indexed properties (name, id)
   ```cypher
   MATCH (p:PERSON) WHERE p.name = "Alice"
   ```

### Query Optimization

1. **Start with most specific patterns**
   ```cypher
   -- Good: Start with specific label
   MATCH (p:PERSON)-[:WORKS_FOR]->(c)
   
   -- Slower: Start with generic pattern
   MATCH (a)-[r]->(b) WHERE a.__labels__ = "PERSON"
   ```

2. **Limit relationship traversal depth**
   ```cypher
   -- Good: 1-2 hops
   MATCH (a)-[]->(b)-[]->(c)
   
   -- Avoid: Deep traversals
   MATCH (a)-[]->(b)-[]->(c)-[]->(d)-[]->(e)
   ```

3. **Use aggregations wisely**
   ```cypher
   -- Good: Aggregate after filtering
   MATCH (p:PERSON) WHERE p.age > 25 RETURN COUNT(p)
   
   -- Slower: Filter after aggregation
   MATCH (p:PERSON) WITH COUNT(p) as cnt WHERE cnt > 10 RETURN cnt
   ```

### Security Notes

- **All queries are automatically scoped to your user_id** - You can only query your own data
- **Query validation prevents injection attacks** - Dangerous patterns are blocked
- **Execution timeouts** - Queries are limited to 30 seconds
- **Result limits** - Maximum 10,000 rows per query

### Output Formats

**Available formats:**
- `dict` - Python dictionary (default)
- `json` - JSON string (pretty-printed)
- `csv` - CSV string
- `table` - ASCII table (CLI only)

**CLI:**
```bash
aico kg query --gql "MATCH (p:PERSON) RETURN p.name" --user-id <USER_ID> --format json
```

---

## Common Use Cases

### Find All Information About a Person
```cypher
MATCH (p:PERSON {name: "Alice"})-[r]->(target)
RETURN p, r, target
```

### Find People in a Location
```cypher
MATCH (p:PERSON)-[:LIVES_IN]->(city:GPE)
WHERE city.name = "New York"
RETURN p.name
```

### Find Company Employees
```cypher
MATCH (p:PERSON)-[:WORKS_FOR]->(c:ORGANIZATION)
WHERE c.name = "Acme Corp"
RETURN p.name, p.role
```

### Find Recent Events
```cypher
MATCH (e:EVENT)
WHERE e.date > "2024-01-01"
RETURN e.name, e.date
ORDER BY e.date DESC
```

### Network Analysis: Most Connected People
```cypher
MATCH (p:PERSON)-[r]->()
RETURN p.name, COUNT(r) as connections
ORDER BY connections DESC
LIMIT 10
```

---

## Troubleshooting

### Query Returns No Results

**Check:**
1. Are you using the correct label? (`PERSON` vs `person`)
2. Does the property exist? (`p.name` vs `p.fullname`)
3. Is the data in your user's graph?

**Debug:**
```cypher
-- Check what labels exist
MATCH (n) RETURN DISTINCT n.__labels__ LIMIT 10

-- Check what properties exist
MATCH (p:PERSON) RETURN p LIMIT 1
```

### Query Fails with Error

**Common issues:**
1. **Syntax error** - Check quotes (use `"` not `'`)
2. **Property doesn't exist** - Check property names
3. **Timeout** - Query too complex, add more filters

### Performance Issues

**Solutions:**
1. Add `LIMIT` clause
2. Use more specific labels
3. Filter early with `WHERE`
4. Reduce traversal depth

---

## Additional Resources

- **GQL Standard:** [ISO/IEC 39075:2024](https://www.iso.org/standard/76120.html)
- **GrandCypher Docs:** [GitHub](https://github.com/aplbrain/grand-cypher)
- **Cypher Cheat Sheet:** [Neo4j](https://neo4j.com/docs/cypher-cheat-sheet/)
- **AICO KG Concepts:** `/docs/concepts/memory/semantic_knowledge_graph_memory.md`

---

## Quick Reference Card

```cypher
# Basic patterns
MATCH (n)                          # All nodes
MATCH (n:LABEL)                    # Nodes with label
MATCH (n {property: "value"})      # Nodes with property
MATCH (a)-[r]->(b)                 # Any relationship
MATCH (a)-[r:TYPE]->(b)            # Specific relationship type
MATCH (a)--(b)                     # Bidirectional

# Filtering
WHERE n.property = "value"         # Equal
WHERE n.property > 10              # Comparison
WHERE n.property IN ["a", "b"]     # List membership
AND, OR, NOT                       # Logical operators

# Returning
RETURN n                           # Return node
RETURN n.property                  # Return property
RETURN DISTINCT n                  # Unique results
RETURN n ORDER BY n.property       # Sorted
RETURN n SKIP 10 LIMIT 10          # Pagination

# Aggregations
COUNT(n)                           # Count
SUM(n.property)                    # Sum
AVG(n.property)                    # Average
MIN(n.property), MAX(n.property)   # Min/Max
```

---

**Happy Querying! 🎉**
