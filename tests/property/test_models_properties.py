"""Property-based tests for data models.

Feature: knowledge-atomizer
Property 6: Atom Field Completeness
Validates: Requirements 2.2
"""

import uuid
from hypothesis import given, settings, strategies as st

import sys
sys.path.insert(0, '.')

from src.models import KnowledgeAtom


# Custom strategies for generating valid KnowledgeAtom fields
valid_uuid = st.builds(lambda: str(uuid.uuid4()))
valid_title = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
valid_content = st.text(max_size=1000)
valid_level = st.integers(min_value=1, max_value=5)
valid_source_file = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
optional_uuid = st.one_of(st.none(), valid_uuid)
optional_title = st.one_of(st.none(), valid_title)
children_ids = st.lists(valid_uuid, max_size=10)


@given(
    id=valid_uuid,
    title=valid_title,
    content=valid_content,
    level=valid_level,
    parent_id=optional_uuid,
    parent_title=optional_title,
    source_file=valid_source_file,
    children_ids=children_ids
)
@settings(max_examples=100)
def test_atom_field_completeness_valid_atoms(
    id: str,
    title: str,
    content: str,
    level: int,
    parent_id: str,
    parent_title: str,
    source_file: str,
    children_ids: list
):
    """
    Feature: knowledge-atomizer
    Property 6: Atom Field Completeness
    Validates: Requirements 2.2
    
    For any KnowledgeAtom produced by the Transformer, it SHALL have non-null 
    values for: id (valid UUID), title (non-empty string), level (1-5), 
    and source_file (non-empty string).
    """
    atom = KnowledgeAtom(
        id=id,
        title=title,
        content=content,
        level=level,
        parent_id=parent_id,
        parent_title=parent_title,
        source_file=source_file,
        children_ids=children_ids
    )
    
    # Verify the atom passes validation
    assert atom.is_valid(), f"Valid atom should pass validation: {atom}"
    
    # Verify individual field constraints
    assert atom.id is not None, "id should not be None"
    uuid.UUID(atom.id)  # Should not raise
    
    assert atom.title is not None and atom.title.strip(), "title should be non-empty"
    assert 1 <= atom.level <= 5, f"level should be 1-5, got {atom.level}"
    assert atom.source_file is not None and atom.source_file.strip(), "source_file should be non-empty"


# Strategies for invalid atoms
invalid_uuid = st.one_of(
    st.just(""),
    st.just("not-a-uuid"),
    st.just("12345"),
    st.none()
)
invalid_title = st.one_of(
    st.just(""),
    st.just("   "),
    st.just("\t\n")
)
invalid_level = st.one_of(
    st.integers(max_value=0),
    st.integers(min_value=6)
)
invalid_source_file = st.one_of(
    st.just(""),
    st.just("   "),
    st.just("\t\n")
)


@given(invalid_id=invalid_uuid)
@settings(max_examples=100)
def test_atom_rejects_invalid_uuid(invalid_id):
    """
    Feature: knowledge-atomizer
    Property 6: Atom Field Completeness (negative case)
    Validates: Requirements 2.2
    
    Atoms with invalid UUIDs should fail validation.
    """
    atom = KnowledgeAtom(
        id=invalid_id if invalid_id is not None else "",
        title="Valid Title",
        content="Some content",
        level=1,
        parent_id=None,
        parent_title=None,
        source_file="test.docx",
        children_ids=[]
    )
    
    assert not atom.is_valid(), f"Atom with invalid UUID should fail validation: {invalid_id}"


@given(invalid_title=invalid_title)
@settings(max_examples=100)
def test_atom_rejects_invalid_title(invalid_title):
    """
    Feature: knowledge-atomizer
    Property 6: Atom Field Completeness (negative case)
    Validates: Requirements 2.2
    
    Atoms with empty or whitespace-only titles should fail validation.
    """
    atom = KnowledgeAtom(
        id=str(uuid.uuid4()),
        title=invalid_title,
        content="Some content",
        level=1,
        parent_id=None,
        parent_title=None,
        source_file="test.docx",
        children_ids=[]
    )
    
    assert not atom.is_valid(), f"Atom with invalid title should fail validation: '{invalid_title}'"


@given(invalid_level=invalid_level)
@settings(max_examples=100)
def test_atom_rejects_invalid_level(invalid_level):
    """
    Feature: knowledge-atomizer
    Property 6: Atom Field Completeness (negative case)
    Validates: Requirements 2.2
    
    Atoms with level outside 1-5 range should fail validation.
    """
    atom = KnowledgeAtom(
        id=str(uuid.uuid4()),
        title="Valid Title",
        content="Some content",
        level=invalid_level,
        parent_id=None,
        parent_title=None,
        source_file="test.docx",
        children_ids=[]
    )
    
    assert not atom.is_valid(), f"Atom with invalid level should fail validation: {invalid_level}"


@given(invalid_source=invalid_source_file)
@settings(max_examples=100)
def test_atom_rejects_invalid_source_file(invalid_source):
    """
    Feature: knowledge-atomizer
    Property 6: Atom Field Completeness (negative case)
    Validates: Requirements 2.2
    
    Atoms with empty or whitespace-only source_file should fail validation.
    """
    atom = KnowledgeAtom(
        id=str(uuid.uuid4()),
        title="Valid Title",
        content="Some content",
        level=1,
        parent_id=None,
        parent_title=None,
        source_file=invalid_source,
        children_ids=[]
    )
    
    assert not atom.is_valid(), f"Atom with invalid source_file should fail validation: '{invalid_source}'"
