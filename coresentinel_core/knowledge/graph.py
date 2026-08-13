"""
Graph construction and traversal.

Built from three sources that already exist, never from inference:

  discovery      project --uses--> language / framework / datastore / ci / container
  decisions      project --governed_by--> decision --concerns--> file
                 decision --caused_by--> incident, --supersedes--> decision
  memory         incident and pattern entities from the failures and patterns layers

Every edge carries the evidence that produced it, and `build` creates an entity
for anything an edge references — so a dangling edge cannot exist, and a query
never returns a neighbour that is not there.
"""

from datetime import datetime

from coresentinel_core.knowledge import entities as E

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# Discovery finding kind -> the entity type and relation it produces.
DISCOVERY_MAP = {
    "language": (E.LANGUAGE, "uses"),
    "framework": (E.FRAMEWORK, "uses"),
    "datastore": (E.DATASTORE, "uses"),
    "container": (E.CONTAINER, "uses"),
    "ci": (E.CI, "uses"),
    "test_tool": (E.TEST_TOOL, "tested_by"),
}

MAX_DEPTH = 5


class Graph:
    def __init__(self, nodes=None, edges=None):
        self.nodes = dict(nodes or {})
        self.edges = list(edges or [])

    def add_entity(self, item):
        self.nodes.setdefault(item["id"], item)
        return item["id"]

    def ensure(self, entity_type, key, label=None, attributes=None):
        return self.add_entity(E.entity(entity_type, key, label, attributes))

    def add_relation(self, source, relation_type, target, evidence=None):
        # An edge whose endpoints are not entities is a dangling edge, and a
        # graph with those in it answers queries with neighbours that do not exist.
        if source not in self.nodes or target not in self.nodes:
            return None
        edge = E.relation(source, relation_type, target, evidence)
        if not any(e["id"] == edge["id"] for e in self.edges):
            self.edges.append(edge)
        return edge

    def neighbours(self, node_id):
        """Every edge touching this node, oriented outward from it."""
        found = []
        for edge in self.edges:
            if edge["source"] == node_id:
                found.append({"direction": "out", "type": edge["type"],
                              "other": edge["target"], "evidence": edge["evidence"]})
            elif edge["target"] == node_id:
                found.append({"direction": "in",
                              "type": E.INVERSE.get(edge["type"], edge["type"]),
                              "other": edge["source"], "evidence": edge["evidence"]})
        return found

    def traverse(self, start, depth=1):
        """Breadth-first walk. Returns nodes with the depth each was reached at."""
        depth = max(0, min(int(depth), MAX_DEPTH))
        if start not in self.nodes:
            return {"error": f"unknown entity '{start}'"}

        seen = {start: 0}
        frontier, walked = [start], []
        for level in range(1, depth + 1):
            following = []
            for node_id in frontier:
                for link in self.neighbours(node_id):
                    walked.append({"from": node_id, "type": link["type"],
                                   "to": link["other"], "depth": level,
                                   "evidence": link["evidence"]})
                    if link["other"] not in seen:
                        seen[link["other"]] = level
                        following.append(link["other"])
            frontier = following
            if not frontier:
                break

        return {
            "start": self.nodes[start],
            "depth": depth,
            "nodes": [{**self.nodes[node_id], "depth": level}
                      for node_id, level in sorted(seen.items(), key=lambda kv: (kv[1], kv[0]))],
            "edges": walked,
        }

    def find(self, needle):
        """Entities matching an id, a key or part of a label."""
        text = str(needle or "").strip().lower()
        if not text:
            return []
        exact = [item for item in self.nodes.values() if item["id"].lower() == text]
        if exact:
            return exact
        return [item for item in self.nodes.values()
                if text == item["key"].lower() or text in item["label"].lower()]

    def dangling(self):
        return [edge for edge in self.edges
                if edge["source"] not in self.nodes or edge["target"] not in self.nodes]

    def describe(self):
        by_type = {}
        for item in self.nodes.values():
            by_type[item["type"]] = by_type.get(item["type"], 0) + 1
        by_relation = {}
        for edge in self.edges:
            by_relation[edge["type"]] = by_relation.get(edge["type"], 0) + 1
        return {"entities": len(self.nodes), "relations": len(self.edges),
                "by_type": by_type, "by_relation": by_relation}

    def as_dict(self):
        return {"nodes": list(self.nodes.values()), "edges": self.edges}


def build(target_dir=".", report=None):
    """Assemble the graph for one project from discovery, decisions and memory."""
    from coresentinel_core.project import discovery

    graph = Graph()
    report = report or discovery.inspect(target_dir)

    project_id = graph.ensure(E.PROJECT, report["project"]["name"],
                              attributes={"root": report["project"]["root"]})

    for dimension in report["dimensions"].values():
        for item in dimension["findings"]:
            mapping = DISCOVERY_MAP.get(item["kind"])
            if not mapping:
                continue
            entity_type, relation_type = mapping
            other = graph.ensure(entity_type, item["value"],
                                 attributes={"confidence": item["confidence"]})
            evidence = item["evidence"]
            graph.add_relation(project_id, relation_type, other,
                               evidence=f"{evidence['file']} ({evidence['locator']})")

    _add_decisions(graph, project_id, target_dir)
    _add_incidents(graph, project_id, target_dir)
    _add_memory(graph, target_dir)

    return graph


def _add_decisions(graph, project_id, target_dir):
    from coresentinel_core.decisions import ledger

    for record in ledger.load(target_dir):
        decision_id = graph.ensure(E.DECISION, record["id"], label=record.get("title"),
                                   attributes={"status": record.get("status"),
                                               "chosen": record.get("chosen")})
        graph.add_relation(project_id, "governed_by", decision_id,
                           evidence=f"{record.get('scope')} ledger")

        for path in record.get("related_files", []):
            graph.add_relation(decision_id, "concerns", graph.ensure(E.FILE, path),
                               evidence=f"{record['id']}.related_files")

        for incident in record.get("related_incidents", []):
            graph.add_relation(decision_id, "caused_by", graph.ensure(E.INCIDENT, incident),
                               evidence=f"{record['id']}.related_incidents")

        if record.get("supersedes"):
            other = graph.ensure(E.DECISION, record["supersedes"])
            graph.add_relation(decision_id, "supersedes", other,
                               evidence=f"{record['id']}.supersedes")

        for related in record.get("related_decisions", []):
            graph.add_relation(decision_id, "relates_to", graph.ensure(E.DECISION, related),
                               evidence=f"{record['id']}.related_decisions")


def _add_incidents(graph, project_id, target_dir):
    from coresentinel_core.incidents import ledger as incidents

    for record in incidents.load(target_dir):
        incident_id = graph.ensure(E.INCIDENT, record["id"], label=record.get("title"),
                                   attributes={"status": record.get("status"),
                                               "severity": record.get("severity"),
                                               "learning": record.get("learning")})
        graph.add_relation(project_id, "relates_to", incident_id,
                           evidence=f"{record.get('scope')} incident ledger")

        for path in record.get("related_files", []):
            graph.add_relation(incident_id, "concerns", graph.ensure(E.FILE, path),
                               evidence=f"{record['id']}.related_files")
        for decision in record.get("related_decisions", []):
            graph.add_relation(incident_id, "relates_to",
                               graph.ensure(E.DECISION, decision),
                               evidence=f"{record['id']}.related_decisions")
        for pattern in record.get("related_patterns", []):
            # The pattern was extracted FROM the incident, so the edge runs that way.
            graph.add_relation(graph.ensure(E.PATTERN, pattern), "learned_from",
                               incident_id, evidence=f"{record['id']}.related_patterns")


def _add_memory(graph, target_dir):
    import coresentinel_memory as mem

    for index, fact in enumerate(mem.layer_facts("failures", target_dir), start=1):
        key = fact.get("source") or f"INC-{index:04d}"
        graph.ensure(E.INCIDENT, key, label=fact.get("fact"),
                     attributes={"confidence": fact.get("confidence")})

    for index, fact in enumerate(mem.layer_facts("patterns", target_dir), start=1):
        key = fact.get("source") or f"PAT-{index:04d}"
        pattern_id = graph.ensure(E.PATTERN, key, label=fact.get("fact"),
                                  attributes={"confidence": fact.get("confidence")})
        # A pattern whose source names an incident was extracted from it — that
        # link is recorded, not inferred from wording.
        incident_id = E.entity_id(E.INCIDENT, key)
        if incident_id in graph.nodes:
            graph.add_relation(pattern_id, "learned_from", incident_id,
                               evidence="pattern source names the incident")


def render(result):
    if result.get("error"):
        return f"[!] {result['error']}"

    start = result["start"]
    lines = ["", "=" * 64,
             f"  🕸️  {start['type']}:{start['key']} — {start['label']}",
             "=" * 64,
             f"  Reached {len(result['nodes']) - 1} related entity(s) at depth {result['depth']}",
             "  " + "-" * 60]

    if len(result["nodes"]) <= 1:
        lines.append("  Nothing is linked to this entity yet.")
        lines.append("  Links come from what is recorded — a decision's --relates-to,")
        lines.append("  its related incidents, or a discovery finding. Nothing is inferred.")
        lines.append("=" * 64)
        return "\n".join(lines)

    for edge in result["edges"]:
        meaning = E.RELATION_TYPES.get(edge["type"], (edge["type"],))[0]
        lines.append(f"  {'  ' * (edge['depth'] - 1)}{edge['from']}")
        lines.append(f"  {'  ' * (edge['depth'] - 1)}   --{edge['type']}--> {edge['to']}")
        lines.append(f"  {'  ' * (edge['depth'] - 1)}      {meaning}"
                     + (f" · {edge['evidence']}" if edge["evidence"] else ""))

    lines.append("=" * 64)
    return "\n".join(lines)
