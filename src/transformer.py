"""Knowledge Transformer for converting document trees to knowledge atoms."""

from typing import List, Optional

from .models import DocumentNode, DocumentTree, KnowledgeAtom


class KnowledgeTransformer:
    """知识转换器 - 将文档树转换为扁平化的知识原子列表"""
    
    def transform(self, tree: DocumentTree) -> List[KnowledgeAtom]:
        """将文档树转换为知识原子列表
        
        Args:
            tree: DocumentTree containing the parsed document structure
            
        Returns:
            List of KnowledgeAtom objects
        """
        atoms: List[KnowledgeAtom] = []
        
        # Process each root node
        for node in tree.root_nodes:
            self._flatten_tree(node, None, tree.source_file, atoms)
        
        # Build children_ids for each atom
        self._build_children_ids(atoms)
        
        return atoms
    
    def _flatten_tree(
        self,
        node: DocumentNode,
        parent: Optional[KnowledgeAtom],
        source_file: str,
        atoms: List[KnowledgeAtom],
        parent_path: str = ""
    ) -> KnowledgeAtom:
        """递归扁平化文档树
        
        Args:
            node: Current document node to process
            parent: Parent KnowledgeAtom (if any)
            source_file: Source file name
            atoms: List to append atoms to
            parent_path: Parent's full path
            
        Returns:
            The created KnowledgeAtom for this node
        """
        # Build full path
        current_path = f"{parent_path} > {node.title}" if parent_path else node.title
        
        # Create atom for current node
        atom = KnowledgeAtom(
            id=node.id,
            title=node.title,
            content=node.content,
            level=node.level.value,
            parent_id=parent.id if parent else None,
            parent_title=parent.title if parent else None,
            source_file=source_file,
            children_ids=[],
            path=current_path
        )
        
        atoms.append(atom)
        
        # Process children recursively
        for child in node.children:
            self._flatten_tree(child, atom, source_file, atoms, current_path)
        
        return atom
    
    def _build_children_ids(self, atoms: List[KnowledgeAtom]) -> None:
        """Build children_ids for each atom based on parent_id relationships.
        
        Args:
            atoms: List of atoms to process
        """
        # Create a map of id -> atom for quick lookup
        atom_map = {atom.id: atom for atom in atoms}
        
        # For each atom, add its id to its parent's children_ids
        for atom in atoms:
            if atom.parent_id and atom.parent_id in atom_map:
                parent = atom_map[atom.parent_id]
                if atom.id not in parent.children_ids:
                    parent.children_ids.append(atom.id)
