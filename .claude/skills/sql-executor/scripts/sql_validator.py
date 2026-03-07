#!/usr/bin/env python3
"""
SQL Validator Script
Validates SQL queries for security and safety.

Features:
- SQL injection detection
- Read-only mode enforcement
- Query timeout recommendations
- Result size estimation
"""

import argparse
import re
import sys
from typing import Dict, List, Any, Optional


class SQLValidator:
    """Validates SQL queries for security and safety."""

    # SQL injection patterns
    INJECTION_PATTERNS = [
        (r";\s*\w", "semicolon_statement", "Multiple statements detected"),
        (r"--", "sql_comment", "SQL comment detected"),
        (r"/\*", "multiline_comment", "Multi-line comment detected"),
        (r"xp_\w+", "extended_stored_proc", "Extended stored procedure detected"),
        (r"sp_executesql", "dynamic_execution", "Dynamic SQL execution detected"),
        (r"EXEC\s*\(", "exec_command", "EXEC command detected"),
        (r"EXECUTE\s*\(", "execute_command", "EXECUTE command detected"),
        (r"\'\s*OR\s*\'.*\'\s*=\s*\'", "sql_injection_or", "SQL injection pattern (OR) detected"),
        (r"\'\s*AND\s*\'.*\'\s*=\s*\'", "sql_injection_and", "SQL injection pattern (AND) detected"),
        (r"\bor\s+1\s*=\s*1\b", "boolean_injection", "Boolean-based injection detected"),
        (r"\band\s+1\s*=\s*1\b", "boolean_injection", "Boolean-based injection detected"),
        (r"union\s+select", "union_injection", "UNION SELECT injection detected", re.IGNORECASE),
    ]

    # Dangerous keywords for write operations
    WRITE_KEYWORDS = [
        "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE",
        "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
        "REPLACE", "MERGE", "CALL", "DECLARE", "CURSOR"
    ]

    # Safe query starters
    SAFE_PREFIXES = [
        "SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN", "ANALYZE"
    ]

    def __init__(self, read_only: bool = True):
        """
        Initialize SQL validator.

        Args:
            read_only: If True, only allow SELECT queries
        """
        self.read_only = read_only

    def validate(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL query.

        Args:
            sql: SQL query to validate

        Returns:
            Dictionary with keys:
            - valid: Boolean indicating if SQL is valid
            - errors: List of error messages
            - warnings: List of warning messages
            - recommendations: List of recommendations
        """
        sql_stripped = sql.strip()
        sql_upper = sql_stripped.upper()

        errors = []
        warnings = []
        recommendations = []

        # Check for SQL injection patterns
        injection_errors = self._check_injection(sql_stripped)
        errors.extend(injection_errors)

        # Check for write operations if read-only mode
        if self.read_only:
            write_errors = self._check_read_only(sql_upper)
            errors.extend(write_errors)

        # Check for unsafe functions
        unsafe_warnings = self._check_unsafe_functions(sql_upper)
        warnings.extend(unsafe_warnings)

        # Check query complexity
        complexity_warnings = self._check_complexity(sql_stripped)
        warnings.extend(complexity_warnings)

        # Provide recommendations
        recommendations.extend(self._get_recommendations(sql_stripped))

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "recommendations": recommendations
        }

    def _check_injection(self, sql: str) -> List[str]:
        """Check for SQL injection patterns."""
        errors = []

        for pattern in self.INJECTION_PATTERNS:
            pattern_regex = pattern[0]
            pattern_name = pattern[1]
            pattern_desc = pattern[2]

            flags = pattern[3] if len(pattern) > 3 else 0

            if re.search(pattern_regex, sql, flags):
                errors.append(f"[{pattern_name}] {pattern_desc}")

        return errors

    def _check_read_only(self, sql_upper: str) -> List[str]:
        """Check if query attempts write operations."""
        errors = []

        # Check if query starts with safe prefix
        starts_safe = any(sql_upper.startswith(prefix) for prefix in self.SAFE_PREFIXES)

        if not starts_safe:
            errors.append(f"Query must start with one of: {', '.join(self.SAFE_PREFIXES)}")
            return errors

        # Check for dangerous keywords in SELECT queries
        for keyword in self.WRITE_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r"\b" + keyword + r"\b"
            if re.search(pattern, sql_upper):
                errors.append(f"Write operation detected: {keyword}. Not allowed in read-only mode")

        return errors

    def _check_unsafe_functions(self, sql_upper: str) -> List[str]:
        """Check for potentially unsafe database functions."""
        warnings = []

        unsafe_functions = {
            "SLEEP": "May cause query to hang",
            "WAITFOR": "May cause query to delay",
            "BENCHMARK": "May cause resource exhaustion",
            "LOAD_FILE": "May read arbitrary files",
            "INTO OUTFILE": "May write arbitrary files",
            "SYSTEM_USER": "Information disclosure",
            "CURRENT_USER": "Information disclosure",
            "SESSION_USER": "Information disclosure",
        }

        for func, reason in unsafe_functions.items():
            if func in sql_upper:
                warnings.append(f"Unsafe function {func}: {reason}")

        return warnings

    def _check_complexity(self, sql: str) -> List[str]:
        """Check query complexity for potential performance issues."""
        warnings = []

        # Check for SELECT *
        if re.search(r"SELECT\s+\*\s+FROM", sql, re.IGNORECASE):
            warnings.append("SELECT * detected - specify columns explicitly for better performance")

        # Check for nested subqueries (depth > 3)
        depth = self._count_subquery_depth(sql)
        if depth > 3:
            warnings.append(f"Deep subquery nesting detected (depth: {depth}) - consider refactoring")

        # Check for multiple JOINs
        join_count = len(re.findall(r"\bJOIN\b", sql, re.IGNORECASE))
        if join_count > 5:
            warnings.append(f"Multiple JOINs detected (count: {join_count}) - may impact performance")

        # Check for LIKE with leading wildcard
        if re.search(r"LIKE\s+'%[^']", sql, re.IGNORECASE):
            warnings.append("LIKE with leading wildcard prevents index usage")

        return warnings

    def _count_subquery_depth(self, sql: str) -> int:
        """Count maximum subquery nesting depth."""
        max_depth = 0
        current_depth = 0

        for char in sql:
            if char == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ')':
                current_depth -= 1

        return max_depth

    def _get_recommendations(self, sql: str) -> List[str]:
        """Generate recommendations for query optimization."""
        recommendations = []

        # Recommend LIMIT if not present
        if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE) and not re.search(r"\bTOP\b", sql, re.IGNORECASE):
            recommendations.append("Consider adding LIMIT to restrict result set size")

        # Recommend indexing hints for JOINs
        if re.search(r"\bJOIN\b", sql, re.IGNORECASE):
            recommendations.append("Ensure JOIN columns are properly indexed")

        # Recommend EXPLAIN for complex queries
        if len(sql) > 500 or self._count_subquery_depth(sql) > 2:
            recommendations.append("Consider running EXPLAIN to analyze query execution plan")

        return recommendations

    def suggest_timeout(self, sql: str) -> int:
        """
        Suggest appropriate timeout based on query complexity.

        Args:
            sql: SQL query

        Returns:
            Suggested timeout in seconds
        """
        complexity_score = 0

        # Add points for complexity factors
        if re.search(r"\bJOIN\b", sql, re.IGNORECASE):
            complexity_score += 10
        if re.search(r"\bGROUP BY\b", sql, re.IGNORECASE):
            complexity_score += 5
        if re.search(r"\bORDER BY\b", sql, re.IGNORECASE):
            complexity_score += 5
        if re.search(r"\bHAVING\b", sql, re.IGNORECASE):
            complexity_score += 5

        subquery_depth = self._count_subquery_depth(sql)
        complexity_score += subquery_depth * 5

        # Base timeout + complexity
        base_timeout = 10
        suggested_timeout = base_timeout + complexity_score

        return min(suggested_timeout, 300)  # Cap at 5 minutes

    def estimate_result_size(self, sql: str, table_rows: Optional[int] = None) -> Dict[str, Any]:
        """
        Estimate result set size.

        Args:
            sql: SQL query
            table_rows: Estimated total rows in table (if known)

        Returns:
            Dictionary with estimation data
        """
        has_limit = bool(re.search(r"\bLIMIT\s+(\d+)", sql, re.IGNORECASE))
        has_where = bool(re.search(r"\bWHERE\b", sql, re.IGNORECASE))
        has_join = bool(re.search(r"\bJOIN\b", sql, re.IGNORECASE))

        limit_value = None
        if has_limit:
            match = re.search(r"\bLIMIT\s+(\d+)", sql, re.IGNORECASE)
            if match:
                limit_value = int(match.group(1))

        # Rough estimation
        if limit_value:
            estimated_rows = min(limit_value, table_rows) if table_rows else limit_value
            confidence = "high"
        elif has_where:
            estimated_rows = table_rows * 0.1 if table_rows else 1000
            confidence = "low"
        elif has_join:
            estimated_rows = table_rows * 0.5 if table_rows else 5000
            confidence = "low"
        else:
            estimated_rows = table_rows if table_rows else 10000
            confidence = "very_low"

        return {
            "estimated_rows": int(estimated_rows),
            "confidence": confidence,
            "has_limit": has_limit,
            "has_where": has_where,
            "has_join": has_join
        }


def main():
    """CLI interface for SQL validator."""
    parser = argparse.ArgumentParser(description="Validate SQL queries for security and safety")
    parser.add_argument("--sql", required=True, help="SQL query to validate")
    parser.add_argument("--read-only", action="store_true", default=True, help="Only allow SELECT queries")
    parser.add_argument("--suggest-timeout", action="store_true", help="Suggest query timeout")
    parser.add_argument("--estimate-size", action="store_true", help="Estimate result set size")
    parser.add_argument("--table-rows", type=int, help="Estimated table row count (for size estimation)")

    args = parser.parse_args()

    validator = SQLValidator(read_only=args.read_only)
    result = validator.validate(args.sql)

    # Print validation results
    print(json.dumps(result, indent=2))

    # Suggest timeout if requested
    if args.suggest_timeout:
        timeout = validator.suggest_timeout(args.sql)
        print(f"\nSuggested timeout: {timeout} seconds")

    # Estimate result size if requested
    if args.estimate_size:
        size = validator.estimate_result_size(args.sql, args.table_rows)
        print(f"\nEstimated result size:")
        print(f"  Rows: {size['estimated_rows']}")
        print(f"  Confidence: {size['confidence']}")

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    import json
    main()