"""Property-based tests for Exporters.

Feature: knowledge-atomizer
"""

import os
import tempfile
import uuid
from typing import List

from hypothesis import given, settings, strategies as st

import sys
sys.path.insert(0, '.')

from src.models import KnowledgeAtom
from src.exporters.csv_exporter import CSVExporter


# Strategies for generating KnowledgeAtom objects
valid_uuid = st.builds(lambda: str(uuid.uuid4()))
# Use printable characters only to avoid YAML parsing issues
valid_title = st.text(
    min_size=1, 
    max_size=50, 
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S'), whitelist_characters=' ')
).filter(lambda x: x.strip())
valid_content = st.text(
    max_size=200,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S', 'Z'), whitelist_characters=' \n')
)
valid_level = st.integers(min_value=1, max_value=5)
valid_source_file = st.text(
    min_size=1, 
    max_size=30, 
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-')
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
        children_ids=draw(st.lists(valid_uuid, max_size=3)),
        path=draw(valid_title)  # path field
    )


@st.composite
def knowledge_atom_list_strategy(draw, min_size=1, max_size=10):
    """Generate a list of KnowledgeAtoms."""
    return draw(st.lists(knowledge_atom_strategy(), min_size=min_size, max_size=max_size))


@given(atoms=knowledge_atom_list_strategy())
@settings(max_examples=100)
def test_csv_round_trip_consistency(atoms: List[KnowledgeAtom]):
    """
    Feature: knowledge-atomizer
    Property 11: CSV Round-Trip Consistency
    Validates: Requirements 5.1, 5.3, 5.4
    
    For any list of KnowledgeAtoms, exporting to CSV and then parsing the CSV
    back SHALL produce records with equivalent id, title, content, level,
    parent_id, parent_title, and source_file values.
    """
    exporter = CSVExporter()
    
    # Export to CSV
    result = exporter.export(atoms)
    assert result.success, f"Export should succeed: {result.message}"
    assert result.file_path is not None, "File path should be set"
    
    try:
        # Parse CSV back
        records = CSVExporter.parse_csv(result.file_path)
        
        # Verify count matches
        assert len(records) == len(atoms), \
            f"Expected {len(atoms)} records, got {len(records)}"
        
        # Verify each record matches original atom
        for atom, record in zip(atoms, records):
            assert record['id'] == atom.id, \
                f"id mismatch: expected {atom.id}, got {record['id']}"
            
            assert record['title'] == atom.title, \
                f"title mismatch: expected {atom.title}, got {record['title']}"
            
            assert record['content'] == (atom.content or ''), \
                f"content mismatch: expected {atom.content}, got {record['content']}"
            
            assert record['level'] == atom.level, \
                f"level mismatch: expected {atom.level}, got {record['level']}"
            
            expected_parent_id = atom.parent_id or ''
            assert record['parent_id'] == expected_parent_id, \
                f"parent_id mismatch: expected {expected_parent_id}, got {record['parent_id']}"
            
            expected_parent_title = atom.parent_title or ''
            assert record['parent_title'] == expected_parent_title, \
                f"parent_title mismatch: expected {expected_parent_title}, got {record['parent_title']}"
            
            assert record['source_file'] == atom.source_file, \
                f"source_file mismatch: expected {atom.source_file}, got {record['source_file']}"
            
            expected_path = atom.path or ''
            assert record.get('path', '') == expected_path, \
                f"path mismatch: expected {expected_path}, got {record.get('path', '')}"
    finally:
        # Cleanup
        if result.file_path and os.path.exists(result.file_path):
            os.unlink(result.file_path)


@given(atoms=knowledge_atom_list_strategy())
@settings(max_examples=100)
def test_csv_utf8_bom_encoding(atoms: List[KnowledgeAtom]):
    """
    Feature: knowledge-atomizer
    Property 12: CSV UTF-8 BOM Encoding
    Validates: Requirements 5.2
    
    For any exported CSV file, the first three bytes SHALL be the UTF-8 BOM
    (0xEF, 0xBB, 0xBF).
    """
    exporter = CSVExporter()
    
    # Export to CSV
    result = exporter.export(atoms)
    assert result.success, f"Export should succeed: {result.message}"
    assert result.file_path is not None, "File path should be set"
    
    try:
        # Read first 3 bytes
        with open(result.file_path, 'rb') as f:
            first_bytes = f.read(3)
        
        expected_bom = b'\xef\xbb\xbf'
        assert first_bytes == expected_bom, \
            f"First 3 bytes should be UTF-8 BOM {expected_bom}, got {first_bytes}"
    finally:
        # Cleanup
        if result.file_path and os.path.exists(result.file_path):
            os.unlink(result.file_path)


import re
import yaml
from src.exporters.obsidian_exporter import ObsidianExporter


@given(atoms=knowledge_atom_list_strategy())
@settings(max_examples=100)
def test_obsidian_frontmatter_validity(atoms: List[KnowledgeAtom]):
    """
    Feature: knowledge-atomizer
    Property 9: Obsidian Frontmatter Validity
    Validates: Requirements 4.2
    
    For any KnowledgeAtom, the generated Markdown file SHALL contain valid
    YAML frontmatter with fields: title, level, parent (if applicable), and source.
    """
    exporter = ObsidianExporter()
    
    # Export to ZIP
    result = exporter.export(atoms)
    assert result.success, f"Export should succeed: {result.message}"
    assert result.file_path is not None, "File path should be set"
    
    try:
        # Read ZIP contents
        contents = ObsidianExporter.read_zip_contents(result.file_path)
        
        # Verify each file has valid frontmatter
        for filename, content in contents.items():
            # Extract frontmatter
            match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            assert match, f"File {filename} should have YAML frontmatter"
            
            frontmatter_text = match.group(1)
            
            # Parse YAML
            try:
                frontmatter = yaml.safe_load(frontmatter_text)
            except yaml.YAMLError as e:
                assert False, f"File {filename} has invalid YAML: {e}"
            
            # Verify required fields
            assert 'title' in frontmatter, f"File {filename} should have 'title' field"
            assert 'level' in frontmatter, f"File {filename} should have 'level' field"
            assert 'source' in frontmatter, f"File {filename} should have 'source' field"
            
            # Verify level is valid
            assert 1 <= frontmatter['level'] <= 5, \
                f"File {filename} level should be 1-5, got {frontmatter['level']}"
    finally:
        # Cleanup
        if result.file_path and os.path.exists(result.file_path):
            os.unlink(result.file_path)


@given(atoms=knowledge_atom_list_strategy(min_size=2, max_size=5))
@settings(max_examples=100)
def test_obsidian_bidirectional_links(atoms: List[KnowledgeAtom]):
    """
    Feature: knowledge-atomizer
    Property 10: Obsidian Bidirectional Links
    Validates: Requirements 4.3, 4.4
    
    For any KnowledgeAtom with a parent, the generated Markdown SHALL contain
    a link in the format [[parent_title]]. For any KnowledgeAtom with children,
    the generated Markdown SHALL contain links to all children.
    """
    # Create parent-child relationships
    if len(atoms) >= 2:
        # Make first atom the parent of second
        atoms[1] = KnowledgeAtom(
            id=atoms[1].id,
            title=atoms[1].title,
            content=atoms[1].content,
            level=atoms[1].level,
            parent_id=atoms[0].id,
            parent_title=atoms[0].title,
            source_file=atoms[1].source_file,
            children_ids=atoms[1].children_ids
        )
    
    exporter = ObsidianExporter()
    
    # Export to ZIP
    result = exporter.export(atoms)
    assert result.success, f"Export should succeed: {result.message}"
    
    try:
        # Read ZIP contents
        contents = ObsidianExporter.read_zip_contents(result.file_path)
        
        # Build atom map by title for lookup
        atom_by_title = {atom.title: atom for atom in atoms}
        
        # Check each file
        for filename, content in contents.items():
            # Find which atom this file is for
            title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
            if not title_match:
                continue
            
            title = title_match.group(1)
            atom = atom_by_title.get(title)
            if not atom:
                continue
            
            # If atom has parent, check for parent link
            if atom.parent_id:
                parent_atom = next((a for a in atoms if a.id == atom.parent_id), None)
                if parent_atom:
                    expected_link = f"[[{parent_atom.title}]]"
                    assert expected_link in content, \
                        f"File for '{title}' should contain parent link {expected_link}"
            
            # Check for children links
            children = [a for a in atoms if a.parent_id == atom.id]
            for child in children:
                expected_link = f"[[{child.title}]]"
                assert expected_link in content, \
                    f"File for '{title}' should contain child link {expected_link}"
    finally:
        # Cleanup
        if result.file_path and os.path.exists(result.file_path):
            os.unlink(result.file_path)


@given(atoms=knowledge_atom_list_strategy())
@settings(max_examples=100)
def test_obsidian_file_count(atoms: List[KnowledgeAtom]):
    """
    Feature: knowledge-atomizer
    Property 8: Obsidian File Count
    Validates: Requirements 4.1
    
    For any list of N KnowledgeAtoms, the ObsidianExporter SHALL generate
    exactly N Markdown files.
    """
    exporter = ObsidianExporter()
    
    # Export to ZIP
    result = exporter.export(atoms)
    assert result.success, f"Export should succeed: {result.message}"
    assert result.exported_count == len(atoms), \
        f"Exported count should be {len(atoms)}, got {result.exported_count}"
    
    try:
        # Read ZIP contents
        contents = ObsidianExporter.read_zip_contents(result.file_path)
        
        # Verify file count
        assert len(contents) == len(atoms), \
            f"Expected {len(atoms)} files, got {len(contents)}"
    finally:
        # Cleanup
        if result.file_path and os.path.exists(result.file_path):
            os.unlink(result.file_path)
