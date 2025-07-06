"""
Advanced Search Query Parser

This module provides functionality to parse complex search queries with:
- Boolean operators (AND, OR, NOT)
- Phrase search with quotes ("road maintenance")
- Field prefixes (buyer:, province:, naics:)
- Wildcards (* and ?)
- Nested expressions with parentheses

Example queries:
- 'buyer:"Public Works" AND (province:BC OR province:AB)'
- 'construction NOT demolition'
- 'maint* AND "road repair"'
- 'naics:237* OR category:infrastructure'
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Types of tokens in the search query."""
    WORD = "word"
    PHRASE = "phrase"
    FIELD_PREFIX = "field_prefix"
    BOOLEAN_OP = "boolean_op"
    PARENTHESIS = "parenthesis"
    WILDCARD = "wildcard"
    WHITESPACE = "whitespace"


@dataclass
class Token:
    """Represents a token in the search query."""
    type: TokenType
    value: str
    start: int
    end: int


@dataclass
class ParsedQuery:
    """Result of parsing a search query."""
    fts_query: str  # PostgreSQL full-text search query
    filter_clauses: Dict[str, str]  # Field-specific filters
    field_filters: Dict[str, List[str]]  # Multi-value field filters
    wildcards: List[str]  # Wildcard patterns
    original_query: str  # Original query string
    has_errors: bool = False
    error_message: Optional[str] = None


class AdvancedSearchParser:
    """Parser for advanced search queries with boolean operators and field prefixes."""
    
    def __init__(self):
        # Regex patterns for different token types
        self.patterns = [
            (TokenType.FIELD_PREFIX, r'(\w+):("([^"]*)"|([^\s()]+))'),  # Field prefixes with optional quotes
            (TokenType.PHRASE, r'"([^"]*)"'),  # Quoted phrases
            (TokenType.BOOLEAN_OP, r'\b(AND|OR|NOT)\b'),  # Boolean operators
            (TokenType.PARENTHESIS, r'[()]'),  # Parentheses
            (TokenType.WILDCARD, r'\b\w*[\*?]\w*\b'),  # Wildcard patterns
            (TokenType.WORD, r'\b\w+\b'),  # Regular words
            (TokenType.WHITESPACE, r'\s+'),  # Whitespace
        ]
        
        # Compile regex patterns
        self.compiled_patterns = [
            (token_type, re.compile(pattern, re.IGNORECASE))
            for token_type, pattern in self.patterns
        ]
        
        # Valid field prefixes
        self.valid_fields = {
            'buyer', 'organization', 'province', 'naics', 'category', 
            'source', 'source_name', 'reference', 'contract_value'
        }
        
        # Field mappings for database columns
        self.field_mappings = {
            'buyer': 'organization',
            'org': 'organization',
            'organization': 'organization',
            'province': 'province',
            'naics': 'naics',
            'category': 'category',
            'source': 'source_name',
            'ref': 'reference',
            'reference': 'reference',
            'value': 'contract_value',
            'contract_value': 'contract_value'
        }

    def tokenize(self, query: str) -> List[Token]:
        """Tokenize the search query into a list of tokens."""
        tokens = []
        position = 0
        
        while position < len(query):
            match_found = False
            
            for token_type, pattern in self.compiled_patterns:
                match = pattern.match(query, position)
                if match:
                    value = match.group(0)
                    
                    # Skip whitespace tokens
                    if token_type != TokenType.WHITESPACE:
                        tokens.append(Token(
                            type=token_type,
                            value=value,
                            start=position,
                            end=position + len(value)
                        ))
                    
                    position += len(value)
                    match_found = True
                    break
            
            if not match_found:
                # Handle unmatched characters
                tokens.append(Token(
                    type=TokenType.WORD,
                    value=query[position],
                    start=position,
                    end=position + 1
                ))
                position += 1
        
        return tokens

    def parse_field_prefix(self, token: Token) -> Tuple[str, str]:
        """Parse a field prefix token into field and value."""
        # Extract field and value from patterns like "buyer:value" or "buyer:"value""
        match = re.match(r'(\w+):("([^"]*)"|([^\s()]+))', token.value)
        if match:
            field = match.group(1)
            # Check if value is quoted or not
            quoted_value = match.group(3)
            unquoted_value = match.group(4)
            value = quoted_value if quoted_value is not None else unquoted_value
            return field.lower(), value
        return None, None

    def build_fts_query(self, tokens: List[Token]) -> str:
        """Build PostgreSQL full-text search query from tokens."""
        fts_parts = []
        
        for token in tokens:
            if token.type == TokenType.WORD:
                # Convert word to tsquery format
                word = token.value.lower()
                if word not in ['and', 'or', 'not']:
                    fts_parts.append(word)
                    
            elif token.type == TokenType.PHRASE:
                # Convert phrase to tsquery format
                phrase = token.value.strip('"')
                # Replace spaces with & for phrase matching
                phrase_query = ' & '.join(phrase.lower().split())
                fts_parts.append(f'({phrase_query})')
                
            elif token.type == TokenType.BOOLEAN_OP:
                # Convert boolean operators to PostgreSQL format
                op_map = {'AND': '&', 'OR': '|', 'NOT': '!'}
                fts_parts.append(op_map.get(token.value.upper(), token.value))
                
            elif token.type == TokenType.WILDCARD:
                # Handle wildcards - convert to prefix matching
                wildcard = token.value.lower()
                if wildcard.endswith('*'):
                    prefix = wildcard[:-1]
                    fts_parts.append(f'{prefix}:*')
                elif '?' in wildcard:
                    # Replace ? with . for single character wildcard
                    pattern = wildcard.replace('?', '.')
                    fts_parts.append(pattern)
                else:
                    fts_parts.append(wildcard)
            
            # Skip field prefix tokens in FTS query - they're handled as filters
        
        return ' '.join(fts_parts)

    def extract_filters(self, tokens: List[Token]) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """Extract field-specific filters from tokens."""
        filter_clauses = {}
        field_filters = {}
        
        for token in tokens:
            if token.type == TokenType.FIELD_PREFIX:
                field, value = self.parse_field_prefix(token)
                if field and value:
                    # Map field name to database column
                    db_field = self.field_mappings.get(field, field)
                    
                    if db_field in self.valid_fields:
                        # Handle multi-value fields (comma-separated)
                        if ',' in value:
                            values = [v.strip() for v in value.split(',')]
                            field_filters[db_field] = values
                        else:
                            filter_clauses[db_field] = value
        
        return filter_clauses, field_filters

    def extract_wildcards(self, tokens: List[Token]) -> List[str]:
        """Extract wildcard patterns from tokens."""
        wildcards = []
        
        for token in tokens:
            if token.type == TokenType.WILDCARD:
                wildcards.append(token.value.lower())
        
        return wildcards

    def validate_query(self, tokens: List[Token]) -> Tuple[bool, Optional[str]]:
        """Validate the parsed query for common errors."""
        # Check for unmatched parentheses
        paren_count = 0
        for token in tokens:
            if token.value == '(':
                paren_count += 1
            elif token.value == ')':
                paren_count -= 1
                if paren_count < 0:
                    return False, "Unmatched closing parenthesis"
        
        if paren_count > 0:
            return False, "Unmatched opening parenthesis"
        
        # Check for invalid field prefixes
        for token in tokens:
            if token.type == TokenType.FIELD_PREFIX:
                field, _ = self.parse_field_prefix(token)
                if field and field not in self.field_mappings:
                    return False, f"Invalid field prefix: {field}"
        
        return True, None

    def parse(self, query: str) -> ParsedQuery:
        """
        Parse a search query into structured components.
        
        Args:
            query: The search query string
            
        Returns:
            ParsedQuery object with structured query components
        """
        try:
            if not query or not query.strip():
                return ParsedQuery(
                    fts_query="",
                    filter_clauses={},
                    field_filters={},
                    wildcards=[],
                    original_query=query
                )
            
            # Tokenize the query
            tokens = self.tokenize(query.strip())
            
            # Validate the query
            is_valid, error_msg = self.validate_query(tokens)
            if not is_valid:
                return ParsedQuery(
                    fts_query="",
                    filter_clauses={},
                    field_filters={},
                    wildcards=[],
                    original_query=query,
                    has_errors=True,
                    error_message=error_msg
                )
            
            # Extract different components
            fts_query = self.build_fts_query(tokens)
            filter_clauses, field_filters = self.extract_filters(tokens)
            wildcards = self.extract_wildcards(tokens)
            
            return ParsedQuery(
                fts_query=fts_query,
                filter_clauses=filter_clauses,
                field_filters=field_filters,
                wildcards=wildcards,
                original_query=query
            )
            
        except Exception as e:
            logger.error(f"Error parsing query '{query}': {e}")
            return ParsedQuery(
                fts_query="",
                filter_clauses={},
                field_filters={},
                wildcards=[],
                original_query=query,
                has_errors=True,
                error_message=f"Parsing error: {str(e)}"
            )

    def get_query_examples(self) -> List[Dict[str, str]]:
        """Get example queries for documentation."""
        return [
            {
                "query": 'construction AND maintenance',
                "description": "Find tenders with both 'construction' and 'maintenance'"
            },
            {
                "query": '"road maintenance"',
                "description": "Find exact phrase 'road maintenance'"
            },
            {
                "query": 'buyer:"Public Works" AND province:BC',
                "description": "Find tenders from Public Works in British Columbia"
            },
            {
                "query": 'construction NOT demolition',
                "description": "Find construction tenders excluding demolition"
            },
            {
                "query": 'maint* AND (province:BC OR province:AB)',
                "description": "Find maintenance-related tenders in BC or Alberta"
            },
            {
                "query": 'naics:237* OR category:infrastructure',
                "description": "Find tenders with NAICS starting with 237 or infrastructure category"
            }
        ]


# Global parser instance
parser = AdvancedSearchParser()


def parse_search_query(query: str) -> ParsedQuery:
    """
    Convenience function to parse a search query.
    
    Args:
        query: The search query string
        
    Returns:
        ParsedQuery object with structured components
    """
    return parser.parse(query)


def get_query_examples() -> List[Dict[str, str]]:
    """Get example queries for documentation."""
    return parser.get_query_examples()


if __name__ == "__main__":
    # Test the parser
    test_queries = [
        'construction AND maintenance',
        '"road maintenance"',
        'buyer:"Public Works" AND province:BC',
        'construction NOT demolition',
        'maint* AND (province:BC OR province:AB)',
        'naics:237* OR category:infrastructure'
    ]
    
    for query in test_queries:
        result = parse_search_query(query)
        print(f"\nQuery: {query}")
        print(f"FTS Query: {result.fts_query}")
        print(f"Filters: {result.filter_clauses}")
        print(f"Field Filters: {result.field_filters}")
        print(f"Wildcards: {result.wildcards}")
        print(f"Has Errors: {result.has_errors}")
        if result.error_message:
            print(f"Error: {result.error_message}") 