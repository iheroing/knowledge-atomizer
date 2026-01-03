"""Property-based tests for Knowledge Transformer.

Feature: knowledge-atomizer
"""

import uuid
from typing import List

from hypothesis import given, settings, strategies as st, assume

import sys
sys.path.insert(0, '.')

from src.models import DocumentNode, DocumentTree, HeadingLevel, KnowledgeAtom
from src.transformer import KnowledgeTransformer


# Strategies for generating document structures
def create_document_node(level: int, title: str, content: str, children: List[DocumentNode]) -> DocumentNode:
    """Helper to create a DocumentNode."""
    return DocumentNode(
        id=str(uuid.uuid4()),
        title=title,
        content=content,
        level=HeadingLevel(level),
        children=children
    )


# Strategy for generating valid heading levels
heading_level = st.integers(min_value=1, max_value=5)
node_title = st.text(min_size=1, max_size=30).filter(lambda x: x.strip())
node_content = st.text(max_size=100)


@st.composite
def document_node_strategy(draw, max_depth: int = 3, current_level: int = 1):
    """Generate a random DocumentNode with optional children."""
    title = draw(node_title)
    content = draw(node_content)
    
    children = []
    if max_depth > 0 and current_level < 5:
        # Optionally add children at deeper levels
        num_children = draw(st.integers(min_value=0, max_value=2))
        for _ in range(num_children):
            child_level = current_level + 1
            child = draw(document_node_strategy(max_depth - 1, child_level))
            children.append(child)
    
    return create_document_node(current_level, title, content, children)


@st.composite
def document_tree_strategy(draw):
    """Generate a random DocumentTree."""
    source_file = draw(st.text(min_size=1, max_size=20).filter(lambda x: x.strip())) + ".docx"
    num_roots = draw(st.integers(min_value=1, max_value=3))
    
    root_nodes = []
    for _ in range(num_roots):
        node = draw(document_node_strategy(max_depth=2, current_level=1))
        root_nodes.append(node)
    
    return DocumentTree(source_file=source_file, root_nodes=root_nodes)


def count_nodes(nodes: List[DocumentNode]) -> int:
    """Count total nodes in a tree structure."""
    count = 0
    for node in nodes:
        count += 1
        count += count_nodes(node.children)
    return count


@given(tree=document_tree_strategy())
@settings(max_examples=100)
def test_atom_count_consistency(tree: DocumentTree):
    """
    Feature: knowledge-atomizer
    Property 5: Atom Count Consistency
    Validates: Requirements 2.1
    
    For any DocumentTree with N heading nodes, the Transformer SHALL produce
    exactly N KnowledgeAtom objects.
    """
    transformer = KnowledgeTransformer()
    atoms = transformer.transform(tree)
    
    expected_count = count_nodes(tree.root_nodes)
    actual_count = len(atoms)
    
    assert actual_count == expected_count, \
        f"Expected {expected_count} atoms, got {actual_count}"


@given(tree=document_tree_strategy())
@settings(max_examples=100)
def test_parent_child_relationship_integrity(tree: DocumentTree):
    """
    Feature: knowledge-atomizer
    Property 7: Parent-Child Relationship Integrity
    Validates: Requirements 2.3
    
    For any KnowledgeAtom with a non-null parent_id, there SHALL exist another
    KnowledgeAtom with that id, and the parent's level SHALL be less than
    the child's level.
    """
    transformer = KnowledgeTransformer()
    atoms = transformer.transform(tree)
    
    # Create a map of id -> atom
    atom_map = {atom.id: atom for atom in atoms}
    
    for atom in atoms:
        if atom.parent_id is not None:
            # Parent must exist
            assert atom.parent_id in atom_map, \
                f"Parent {atom.parent_id} not found for atom {atom.id}"
            
            parent = atom_map[atom.parent_id]
            
            # Parent level must be less than child level
            assert parent.level < atom.level, \
                f"Parent level ({parent.level}) should be less than child level ({atom.level})"
            
            # Parent's children_ids should contain this atom's id
            assert atom.id in parent.children_ids, \
                f"Atom {atom.id} should be in parent's children_ids"


@given(tree=document_tree_strategy())
@settings(max_examples=100)
def test_atom_field_completeness_from_transformer(tree: DocumentTree):
    """
    Feature: knowledge-atomizer
    Property 6: Atom Field Completeness (transformer output)
    Validates: Requirements 2.2
    
    For any KnowledgeAtom produced by the Transformer, it SHALL have non-null
    values for: id (valid UUID), title (non-empty string), level (1-5),
    and source_file (non-empty string).
    """
    transformer = KnowledgeTransformer()
    atoms = transformer.transform(tree)
    
    for atom in atoms:
        # Verify required fields
        assert atom.is_valid(), f"Atom should be valid: {atom}"
        
        # Additional checks
        assert atom.id is not None, "id should not be None"
        uuid.UUID(atom.id)  # Should not raise
        
        assert atom.title is not None and atom.title.strip(), \
            f"title should be non-empty, got: '{atom.title}'"
        
        assert 1 <= atom.level <= 5, \
            f"level should be 1-5, got: {atom.level}"
        
        assert atom.source_file is not None and atom.source_file.strip(), \
            f"source_file should be non-empty, got: '{atom.source_file}'"
        
        # source_file should match tree's source_file
        assert atom.source_file == tree.source_file, \
            f"source_file should be '{tree.source_file}', got '{atom.source_file}'"
