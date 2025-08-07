from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, deque

# utils/helpers.py
class EdgeNavigator:
    def __init__(self, nodes: Dict, edges: Dict):
        self.nodes = nodes
        self.edges = edges
        self.adj = self._build_adjacency_list()

    def _build_adjacency_list(self) -> Dict[str, List[str]]:
        adj = {node_id: [] for node_id in self.nodes.keys()}
        for edge in self.edges.values():
            adj[edge["source"]].append(edge["target"])
        return adj
    
    def get_topological_order(self) -> List[str]:
        # Implementation of Kahn's algorithm or DFS for topological sort
        # For simplicity, here's a placeholder. This function should return
        # a list of node IDs in a valid processing order.
        
        # This is a complex implementation; for this example, we'll assume
        # a valid topological sort function exists and is correctly implemented.
        
        in_degree = {node_id: 0 for node_id in self.nodes.keys()}
        for edge in self.edges.values():
            in_degree[edge["target"]] += 1

        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        topo_order = []

        while queue:
            node_id = queue.pop(0)
            topo_order.append(node_id)
            for neighbor in self.adj.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return topo_order if len(topo_order) == len(self.nodes) else []

        
class WorkflowAnalyzer:
    """Analyze workflow structure and provide insights"""
    
    @staticmethod
    def analyze_complexity(nodes: Dict, edges: Dict) -> Dict:
        """Analyze workflow complexity"""
        navigator = EdgeNavigator(nodes, edges)
        
        # Find all user query nodes
        user_query_nodes = [
            node_id for node_id, node_data in nodes.items()
            if node_data.get("type") == "userQuery"
        ]
        
        complexity_metrics = {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "max_path_length": 0,
            "total_paths": 0,
            "branching_factor": 0,
            "depth": 0
        }
        
        if user_query_nodes:
            start_node = user_query_nodes[0]
            all_paths = navigator.find_all_paths_to_output(start_node)
            
            complexity_metrics.update({
                "total_paths": len(all_paths),
                "max_path_length": max(len(path) for path in all_paths) if all_paths else 0,
                "depth": complexity_metrics["max_path_length"],
                "branching_factor": len(edges) / len(nodes) if nodes else 0
            })
        
        # Determine complexity level
        if complexity_metrics["node_count"] <= 3:
            complexity_level = "Simple"
        elif complexity_metrics["node_count"] <= 6:
            complexity_level = "Moderate"
        else:
            complexity_level = "Complex"
        
        complexity_metrics["level"] = complexity_level
        return complexity_metrics
    
    @staticmethod
    def suggest_optimizations(nodes: Dict, edges: Dict) -> List[str]:
        """Suggest workflow optimizations"""
        suggestions = []
        navigator = EdgeNavigator(nodes, edges)
        
        # Check for unnecessary complexity
        validation = navigator.validate_workflow_connectivity()
        
        if validation["statistics"]["disconnected_nodes"] > 0:
            suggestions.append("Remove disconnected nodes to improve clarity")
        
        # Check for parallel processing opportunities
        node_types = [nodes.get(node_id, {}).get("type") for node_id in nodes]
        
        if node_types.count("knowledgeBase") > 1:
            suggestions.append("Consider combining multiple knowledge base nodes")
        
        if node_types.count("webSearch") > 1:
            suggestions.append("Consider combining multiple web search nodes")
        
        # Check for missing error handling
        if "llmEngine" in node_types and len([n for n in node_types if n in ["knowledgeBase", "webSearch"]]) == 0:
            suggestions.append("Consider adding knowledge base or web search for better context")
        
        return suggestions