/**
 * Cypher/GQL Keywords and Functions
 */

export const CYPHER_KEYWORDS = [
  'MATCH', 'CREATE', 'MERGE', 'DELETE', 'REMOVE', 'SET',
  'RETURN', 'WITH', 'WHERE', 'AND', 'OR', 'NOT', 'XOR',
  'ORDER BY', 'SKIP', 'LIMIT', 'DISTINCT', 'AS',
  'OPTIONAL MATCH', 'UNWIND', 'UNION', 'UNION ALL',
  'CALL', 'YIELD', 'FOREACH', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
  'IN', 'IS', 'NULL', 'EXISTS', 'ALL', 'ANY', 'NONE', 'SINGLE',
];

export const CYPHER_FUNCTIONS = [
  // Aggregation
  'count', 'sum', 'avg', 'min', 'max', 'collect',
  // String
  'toString', 'toUpper', 'toLower', 'trim', 'substring', 'replace', 'split',
  // Math
  'abs', 'ceil', 'floor', 'round', 'sqrt', 'sign',
  // List
  'size', 'head', 'tail', 'last', 'reverse', 'range',
  // Type
  'type', 'labels', 'keys', 'properties',
  // Temporal
  'date', 'datetime', 'time', 'duration',
  // Spatial
  'point', 'distance',
  // Predicate
  'exists', 'isEmpty',
];

export const CYPHER_CLAUSES = [
  'MATCH', 'OPTIONAL MATCH', 'CREATE', 'MERGE', 'DELETE', 'REMOVE',
  'SET', 'RETURN', 'WITH', 'UNWIND', 'UNION', 'CALL', 'YIELD',
];

export const CYPHER_FORBIDDEN_OPERATIONS = ['DELETE', 'REMOVE', 'DROP'];
