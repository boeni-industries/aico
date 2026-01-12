/**
 * Flux Language Keywords and Functions
 * 
 * Comprehensive list of Flux language keywords, functions, and operators
 */

// Flux keywords
export const FLUX_KEYWORDS = [
  'from',
  'range',
  'filter',
  'map',
  'reduce',
  'group',
  'window',
  'aggregateWindow',
  'limit',
  'sort',
  'distinct',
  'keep',
  'drop',
  'rename',
  'duplicate',
  'set',
  'yield',
  'union',
  'join',
  'pivot',
  'fill',
  'interpolate',
  'derivative',
  'difference',
  'increase',
  'movingAverage',
  'cumulativeSum',
  'histogram',
  'quantile',
  'stddev',
  'covariance',
  'pearsonr',
  'import',
  'option',
  'builtin',
  'testcase',
  'and',
  'or',
  'not',
  'if',
  'then',
  'else',
  'return',
  'fn',
  'exists',
  'die',
];

// Flux aggregate functions
export const FLUX_AGGREGATE_FUNCTIONS = [
  'count',
  'sum',
  'mean',
  'median',
  'min',
  'max',
  'first',
  'last',
  'unique',
  'mode',
  'stddev',
  'spread',
  'skew',
];

// Flux selector functions
export const FLUX_SELECTOR_FUNCTIONS = [
  'top',
  'bottom',
  'sample',
  'highestMax',
  'highestAverage',
  'highestCurrent',
  'lowestMin',
  'lowestAverage',
  'lowestCurrent',
];

// Flux transformation functions
export const FLUX_TRANSFORMATION_FUNCTIONS = [
  'derivative',
  'difference',
  'increase',
  'movingAverage',
  'cumulativeSum',
  'exponentialMovingAverage',
  'timedMovingAverage',
  'doubleEMA',
  'tripleEMA',
  'kaufmansER',
  'kaufmansAMA',
];

// Flux type conversion functions
export const FLUX_TYPE_FUNCTIONS = [
  'bool',
  'bytes',
  'duration',
  'float',
  'int',
  'string',
  'time',
  'uint',
];

// Flux string functions
export const FLUX_STRING_FUNCTIONS = [
  'strlen',
  'substring',
  'toLower',
  'toUpper',
  'trim',
  'trimPrefix',
  'trimSuffix',
  'trimSpace',
  'title',
  'containsStr',
  'hasPrefix',
  'hasSuffix',
  'indexStr',
  'lastIndexStr',
  'replaceAll',
  'split',
  'joinStr',
];

// Flux math functions
export const FLUX_MATH_FUNCTIONS = [
  'abs',
  'ceil',
  'floor',
  'round',
  'pow',
  'sqrt',
  'log',
  'log10',
  'log2',
  'exp',
  'exp2',
  'sin',
  'cos',
  'tan',
  'asin',
  'acos',
  'atan',
  'atan2',
  'hypot',
];

// Flux date/time functions
export const FLUX_TIME_FUNCTIONS = [
  'now',
  'today',
  'date',
  'duration',
  'truncateTimeColumn',
  'hourSelection',
  'timeShift',
  'timeWeightedAvg',
];

// Common filter predicates
export const FLUX_FILTER_PREDICATES = [
  'r._measurement',
  'r._field',
  'r._value',
  'r._time',
  'r._start',
  'r._stop',
];

// All Flux functions combined
export const FLUX_FUNCTIONS = [
  ...FLUX_AGGREGATE_FUNCTIONS,
  ...FLUX_SELECTOR_FUNCTIONS,
  ...FLUX_TRANSFORMATION_FUNCTIONS,
  ...FLUX_TYPE_FUNCTIONS,
  ...FLUX_STRING_FUNCTIONS,
  ...FLUX_MATH_FUNCTIONS,
  ...FLUX_TIME_FUNCTIONS,
];

// Common Flux snippets
export const FLUX_SNIPPETS = [
  {
    label: 'from bucket',
    insertText: 'from(bucket: "${1:bucket_name}")',
    detail: 'Query data from a bucket',
    documentation: 'Start a query by specifying the bucket to query from',
  },
  {
    label: 'range time',
    insertText: 'range(start: ${1:-1h})',
    detail: 'Filter by time range',
    documentation: 'Filter data by time range (e.g., -1h, -7d, 2023-01-01T00:00:00Z)',
  },
  {
    label: 'filter measurement',
    insertText: 'filter(fn: (r) => r._measurement == "${1:measurement_name}")',
    detail: 'Filter by measurement',
    documentation: 'Filter records by measurement name',
  },
  {
    label: 'filter field',
    insertText: 'filter(fn: (r) => r._field == "${1:field_name}")',
    detail: 'Filter by field',
    documentation: 'Filter records by field name',
  },
  {
    label: 'aggregateWindow',
    insertText: 'aggregateWindow(every: ${1:1h}, fn: ${2:mean})',
    detail: 'Aggregate data into windows',
    documentation: 'Downsample data by aggregating values into time windows',
  },
  {
    label: 'group by',
    insertText: 'group(columns: [${1:"tag_name"}])',
    detail: 'Group data',
    documentation: 'Group data by specified columns',
  },
  {
    label: 'yield result',
    insertText: 'yield(name: "${1:result}")',
    detail: 'Yield result',
    documentation: 'Output the result of the query',
  },
];
