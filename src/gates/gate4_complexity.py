"""
Gate 4: Size & Complexity Limits
- Context size caps
- Nested structure depth
- Repetition detection
"""

import re
import json
from collections import Counter
from dataclasses import dataclass
from typing import Optional, Tuple

from . import BaseGate, GateOutput, GateResult


@dataclass
class ComplexityConfig:
    max_input_tokens: int = 8000
    max_char_length: int = 32000  # ~4 chars per token fallback
    max_nesting_depth: int = 10
    max_repetition_ratio: float = 0.40  # 40% repeated content threshold
    min_unique_words_ratio: float = 0.20  # At least 20% unique words
    avg_chars_per_token: float = 4.0  # For token estimation


class Gate4Complexity(BaseGate):
    """
    Size and complexity gate.
    Prevents resource exhaustion and DoS via malformed inputs.
    """
    
    name = "Gate4_Complexity"
    is_blocking = True
    
    def __init__(self, config: Optional[ComplexityConfig] = None):
        self.config = config or ComplexityConfig()
    
    def _estimate_tokens(self, content: str) -> int:
        """
        Estimate token count.
        Simple heuristic: characters / avg_chars_per_token
        """
        # More accurate: count words and punctuation separately
        words = len(re.findall(r'\b\w+\b', content))
        punctuation = len(re.findall(r'[^\w\s]', content))
        whitespace_chunks = len(content.split()) - 1 if content.split() else 0
        
        # Rough estimate: each word + punctuation + some overhead
        estimated = words + punctuation // 2 + whitespace_chunks // 4
        
        # Also consider raw character count as a sanity check
        char_estimate = len(content) / self.config.avg_chars_per_token
        
        return int(max(estimated, char_estimate))
    
    def _check_nesting_depth(self, content: str) -> Tuple[int, str]:
        """
        Check nesting depth of brackets/braces.
        Returns (max_depth, structure_type).
        """
        max_depth = 0
        current_depth = 0
        deepest_type = "none"
        
        bracket_pairs = {
            '{': ('}', 'braces'),
            '[': (']', 'brackets'),
            '(': (')', 'parentheses'),
        }
        
        openers = set(bracket_pairs.keys())
        closers = {v[0]: k for k, v in bracket_pairs.items()}
        
        for char in content:
            if char in openers:
                current_depth += 1
                if current_depth > max_depth:
                    max_depth = current_depth
                    deepest_type = bracket_pairs[char][1]
            elif char in closers:
                current_depth = max(0, current_depth - 1)
        
        return max_depth, deepest_type
    
    def _check_json_depth(self, content: str) -> int:
        """Check JSON nesting depth if content is JSON."""
        try:
            data = json.loads(content)
            return self._measure_json_depth(data)
        except (json.JSONDecodeError, ValueError):
            return 0
    
    def _measure_json_depth(self, obj, current_depth: int = 0) -> int:
        """Recursively measure JSON depth."""
        if isinstance(obj, dict):
            if not obj:
                return current_depth + 1
            return max(
                self._measure_json_depth(v, current_depth + 1)
                for v in obj.values()
            )
        elif isinstance(obj, list):
            if not obj:
                return current_depth + 1
            return max(
                self._measure_json_depth(item, current_depth + 1)
                for item in obj
            )
        else:
            return current_depth
    
    def _check_repetition(self, content: str) -> Tuple[float, float]:
        """
        Check for repetitive content.
        Returns (repetition_ratio, unique_words_ratio).
        """
        # Tokenize to words
        words = re.findall(r'\b\w+\b', content.lower())
        if not words:
            return 0.0, 1.0
        
        # Word frequency analysis
        word_counts = Counter(words)
        total_words = len(words)
        unique_words = len(word_counts)
        
        unique_ratio = unique_words / total_words
        
        # Check for repeated phrases (n-grams)
        # Look for 3-grams that repeat more than expected
        ngrams = []
        for i in range(len(words) - 2):
            ngram = tuple(words[i:i+3])
            ngrams.append(ngram)
        
        ngram_counts = Counter(ngrams)
        repeated_ngrams = sum(1 for count in ngram_counts.values() if count > 2)
        
        # Calculate repetition ratio
        if ngrams:
            ngram_repetition = repeated_ngrams / len(ngrams)
        else:
            ngram_repetition = 0.0
        
        # Also check for long repeated substrings
        repeated_substring_ratio = self._check_repeated_substrings(content)
        
        # Combined repetition score
        repetition_ratio = max(ngram_repetition, repeated_substring_ratio, 1 - unique_ratio)
        
        return repetition_ratio, unique_ratio
    
    def _check_repeated_substrings(self, content: str, min_length: int = 50) -> float:
        """Check for repeated substrings of significant length."""
        if len(content) < min_length * 2:
            return 0.0
        
        # Simple approach: check if any chunk of min_length appears multiple times
        chunks_seen = set()
        repeat_count = 0
        
        for i in range(0, len(content) - min_length, min_length // 2):
            chunk = content[i:i + min_length]
            if chunk in chunks_seen:
                repeat_count += 1
            chunks_seen.add(chunk)
        
        if not chunks_seen:
            return 0.0
        
        return repeat_count / len(chunks_seen)
    
    def evaluate(self, request: dict, session_token: Optional[str] = None) -> GateOutput:
        """Check size and complexity limits."""
        content = request.get("content", "")
        
        violations = []
        metadata = {}
        
        # Check 1: Size limits
        char_length = len(content)
        estimated_tokens = self._estimate_tokens(content)
        metadata["char_length"] = char_length
        metadata["estimated_tokens"] = estimated_tokens
        
        if char_length > self.config.max_char_length:
            return GateOutput(
                gate_name=self.name,
                result=GateResult.TOO_LARGE,
                violations=[f"Content exceeds character limit: {char_length} > {self.config.max_char_length}"],
                metadata=metadata
            )
        
        if estimated_tokens > self.config.max_input_tokens:
            return GateOutput(
                gate_name=self.name,
                result=GateResult.TOO_LARGE,
                violations=[f"Estimated tokens exceed limit: {estimated_tokens} > {self.config.max_input_tokens}"],
                metadata=metadata
            )
        
        # Check 2: Nesting depth
        bracket_depth, deepest_type = self._check_nesting_depth(content)
        json_depth = self._check_json_depth(content)
        max_depth = max(bracket_depth, json_depth)
        metadata["max_nesting_depth"] = max_depth
        metadata["deepest_structure"] = deepest_type if bracket_depth >= json_depth else "json"
        
        if max_depth > self.config.max_nesting_depth:
            return GateOutput(
                gate_name=self.name,
                result=GateResult.TOO_COMPLEX,
                violations=[f"Nesting depth exceeds limit: {max_depth} > {self.config.max_nesting_depth}"],
                metadata=metadata
            )
        
        # Check 3: Repetition
        repetition_ratio, unique_ratio = self._check_repetition(content)
        metadata["repetition_ratio"] = round(repetition_ratio, 3)
        metadata["unique_words_ratio"] = round(unique_ratio, 3)
        
        if repetition_ratio > self.config.max_repetition_ratio:
            return GateOutput(
                gate_name=self.name,
                result=GateResult.REPETITIVE,
                violations=[f"Content too repetitive: {repetition_ratio:.1%} > {self.config.max_repetition_ratio:.0%}"],
                metadata=metadata
            )
        
        if unique_ratio < self.config.min_unique_words_ratio:
            return GateOutput(
                gate_name=self.name,
                result=GateResult.REPETITIVE,
                violations=[f"Too few unique words: {unique_ratio:.1%} < {self.config.min_unique_words_ratio:.0%}"],
                metadata=metadata
            )
        
        return GateOutput(
            gate_name=self.name,
            result=GateResult.PASS,
            metadata=metadata
        )
