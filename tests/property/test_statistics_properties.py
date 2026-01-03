"""Property-based tests for Statistics.

Feature: knowledge-atomizer
"""

import uuid
from typing import List

from hypothesis import given, settings, strategies as st

import sys
sys.path.insert(0, '.')

from src.models import KnowledgeAtom
from src.statistics import compute_statistics


# Strategies for generating KnowledgeAtom objects
valid_uuid = st.builds(lambda: str(uuid.uuid4()))
valid_title = st.text(
    min_size=1, 
    max_size=50, 
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=' _')
).filter(lambda x: x.strip())
valid_content = st.text(max_size=100)
valid_level = st.integers(min_value=1, max_value=5)
valid_source_file = st.text(
    min_size=1, 
    max_size=20, 
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_')
).filter(lambda x: x.strip()).map(lambda x: x + ".docx")


@st.composite
def knowledge_atom_strategy(draw):
    """Generate a valid KnowledgeAtom."""
    return KnowledgeAtom(
        id=draw(valid_uuid),
        title=draw(valid_title),
        content=draw(valid_content),
        level=draw(valid_level),
        parent_id=draw(st.one_of(st.none(), valid_uuid)),
        parent_title=draw(st.one_of(st.none(), valid_title)),
        source_file=draw(valid_source_file),
        children_ids=[],
        path=draw(valid_title)  # path field
    )


@st.composite
def knowledge_atom_list_strategy(draw, min_size=0, max_size=20):
    """Generate a list of KnowledgeAtoms."""
    return draw(st.lists(knowledge_atom_strategy(), min_size=min_size, max_size=max_size))


@given(atoms=knowledge_atom_list_strategy())
@settings(max_examples=100)
def test_statistics_count_consistency(atoms: List[KnowledgeAtom]):
    """
    Feature: knowledge-atomizer
    Property 13: Statistics Count Consistency
    Validates: Requirements 7.3
    
    For any list of KnowledgeAtoms, the computed statistics SHALL satisfy:
    total_count equals list length, and sum of level_counts[1..5] equals total_count.
    """
    stats = compute_statistics(atoms)
    
    # Verify total_count equals list length
    assert stats.total_count == len(atoms), \
        f"total_count should be {len(atoms)}, got {stats.total_count}"
    
    # Verify sum of level_counts equals total_count
    level_sum = sum(stats.level_counts.get(level, 0) for level in range(1, 6))
    assert level_sum == stats.total_count, \
        f"Sum of level_counts ({level_sum}) should equal total_count ({stats.total_count})"
    
    # Verify each level count is correct
    for level in range(1, 6):
        expected_count = sum(1 for atom in atoms if atom.level == level)
        actual_count = stats.level_counts.get(level, 0)
        assert actual_count == expected_count, \
            f"Level {level} count should be {expected_count}, got {actual_count}"


@given(atoms=knowledge_atom_list_strategy(min_size=0, max_size=0))
@settings(max_examples=10)
def test_statistics_empty_list(atoms: List[KnowledgeAtom]):
    """
    Test statistics for empty list.
    Validates: Requirements 7.3
    """
    stats = compute_statistics(atoms)
    
    assert stats.total_count == 0
    assert sum(stats.level_counts.values()) == 0
