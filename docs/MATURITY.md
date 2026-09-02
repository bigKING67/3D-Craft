# Maturity

## V0.1 status: local candidate

The current source implements the narrow product/prop vertical slice across
Blender, GLB, an R3F viewer, browser runtime evidence, and evidence-bound
validation. Local acceptance has exercised:

- current Codex Skill frontmatter validation;
- source, unit, schema-contract, and viewer type/build checks;
- deterministic package construction with two-build SHA-256 parity;
- validation of an independently extracted package;
- isolated, non-global local installation;
- the original coffee-grinder Blender-to-browser fixture;
- separate Skill discovery and invocation smokes for Codex, Pi, and Grok.

These checks establish a local candidate, not a published release. Evidence is
valid only for the exact source tree, host versions, providers, Blender build,
browser runtime, and artifacts recorded by the corresponding receipt.

## Not yet established

- immutable Git commit provenance;
- remote CI results for the candidate commit;
- tag, GitHub Release, registry publication, or public package parity;
- global user installation parity;
- Windows or Linux host acceptance;
- physical mobile-device GPU frame timing;
- the deferred V0.2+ profiles listed in `ROADMAP.md`.

Commit, push, tag, release, publish, and global installation remain separate
authorization boundaries. A local candidate gate must report
`release_eligible=false` whenever the source has no commit or the worktree is
dirty.
