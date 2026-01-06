/**
 * SQL Keywords and Functions
 */

export const SQL_KEYWORDS = [
  'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
  'ON', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL',
  'ORDER BY', 'GROUP BY', 'HAVING', 'LIMIT', 'OFFSET', 'DISTINCT',
  'AS', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER',
  'TABLE', 'INDEX', 'VIEW', 'UNION', 'INTERSECT', 'EXCEPT',
  'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'EXISTS', 'ALL', 'ANY',
];

export const SQL_FUNCTIONS = [
  'COUNT', 'SUM', 'AVG', 'MIN', 'MAX',
  'UPPER', 'LOWER', 'LENGTH', 'TRIM', 'SUBSTR',
  'COALESCE', 'NULLIF', 'CAST', 'ROUND', 'ABS',
  'NOW', 'DATE', 'TIME', 'DATETIME', 'STRFTIME',
];

export const SQL_FORBIDDEN_OPERATIONS = ['DROP', 'TRUNCATE', 'ALTER'];
