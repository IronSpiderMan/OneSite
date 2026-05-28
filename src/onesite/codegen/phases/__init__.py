"""Code generation pipeline phases.

Each phase is implemented in its own module, exposing a ``phase_*``
function as its public entry point.  The orchestrator in
:mod:`~onesite.codegen.pipeline` calls them in sequence.
"""
