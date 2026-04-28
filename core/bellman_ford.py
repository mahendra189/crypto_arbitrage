class BellmanFord:
    def __init__(self, graph):
        self.graph = graph

    def find_negative_cycle(self):
        # Collect all unique nodes from the graph
        nodes = set()
        for u, v in self.graph.keys():
            nodes.add(u)
            nodes.add(v)

        distances = {node: float('inf') for node in nodes}
        predecessors = {node: None for node in nodes}

        start_node = next(iter(nodes))  # Pick an arbitrary start node
        distances[start_node] = 0

        for _ in range(len(nodes) - 1):
            for (u, v), weight in self.graph.items():
                if distances[u] + weight < distances[v]:
                    distances[v] = distances[u] + weight
                    predecessors[v] = u

        for (u, v), weight in self.graph.items():
            if distances[u] + weight < distances[v]:
                return self._reconstruct_cycle(predecessors, v)

        return None

    def _reconstruct_cycle(self, predecessors, start):
        cycle = []
        current = start
        while True:
            cycle.append(current)
            current = predecessors[current]
            if current == start or current is None:
                break
        cycle.append(start)
        cycle.reverse()
        return cycle