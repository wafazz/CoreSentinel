"""
Knowledge entities and typed relations.

Deliberately not a graph database. The relationships CoreSentinel actually holds
number in the hundreds, they are already stored, and introducing a graph engine
to traverse them would be the kind of infrastructure the brief rules out.

An entity id is `type:key` — `decision:ADR-042`, `framework:Laravel`,
`file:src/auth.ts`. That makes an id self-describing, stable across rebuilds and
usable as a foreign key without a lookup table.

Nothing here infers structure from source code. Every edge comes from something
a human or an engine actually recorded: a discovery finding with its evidence, a
decision's related files, an incident linked to a pattern. A graph that guesses
at "this controller probably implements that feature" is a graph that quietly
misleads, and the whole point of this system is not doing that.
"""

PROJECT = "project"
LANGUAGE = "language"
FRAMEWORK = "framework"
DATASTORE = "datastore"
CONTAINER = "container"
CI = "ci"
TEST_TOOL = "test_tool"
FILE = "file"
DECISION = "decision"
INCIDENT = "incident"
PATTERN = "pattern"
FACT = "fact"

ENTITY_TYPES = [PROJECT, LANGUAGE, FRAMEWORK, DATASTORE, CONTAINER, CI,
                TEST_TOOL, FILE, DECISION, INCIDENT, PATTERN, FACT]

# Relation -> (what it means, its inverse). An inverse lets traversal walk an
# edge from either end without storing it twice.
RELATION_TYPES = {
    "uses": ("depends on this component", "used_by"),
    "governed_by": ("is constrained by this decision", "governs"),
    "concerns": ("names this file", "concerned_by"),
    "caused_by": ("was made because of this incident", "caused"),
    "supersedes": ("replaces this decision", "superseded_by"),
    "relates_to": ("is linked to", "relates_to"),
    "describes": ("states something about", "described_by"),
    "learned_from": ("was extracted from", "taught"),
    "tested_by": ("is verified with", "tests"),
}

INVERSE = {name: inverse for name, (_, inverse) in RELATION_TYPES.items()}


def entity_id(entity_type, key):
    return f"{entity_type}:{key}"


def split_id(identifier):
    text = str(identifier or "")
    return tuple(text.split(":", 1)) if ":" in text else ("", text)


def entity(entity_type, key, label=None, attributes=None):
    return {
        "id": entity_id(entity_type, key),
        "type": entity_type,
        "key": key,
        "label": label or key,
        "attributes": attributes or {},
    }


def relation(source, relation_type, target, evidence=None):
    return {
        "id": f"{source}--{relation_type}-->{target}",
        "source": source,
        "type": relation_type,
        "target": target,
        "evidence": evidence,
    }


def is_known_relation(relation_type):
    return relation_type in RELATION_TYPES
