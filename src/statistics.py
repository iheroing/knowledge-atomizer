"""Statistics computation for knowledge atoms."""

from dataclasses import dataclass
from typing import List, Dict

from .models import KnowledgeAtom


@dataclass
class AtomStatistics:
    """知识原子统计信息"""
    total_count: int
    level_counts: Dict[int, int]  # level -> count
    
    def __post_init__(self):
        """Ensure level_counts has all levels 1-5."""
        for level in range(1, 6):
            if level not in self.level_counts:
                self.level_counts[level] = 0


def compute_statistics(atoms: List[KnowledgeAtom]) -> AtomStatistics:
    """计算知识原子统计信息
    
    Args:
        atoms: List of KnowledgeAtom objects
        
    Returns:
        AtomStatistics with total count and per-level counts
    """
    total_count = len(atoms)
    
    # Count atoms per level
    level_counts: Dict[int, int] = {}
    for atom in atoms:
        level = atom.level
        level_counts[level] = level_counts.get(level, 0) + 1
    
    return AtomStatistics(
        total_count=total_count,
        level_counts=level_counts
    )
