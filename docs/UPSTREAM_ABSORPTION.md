# Upstream absorption policy

Upstreams are research inputs, not install-time dependencies or wholesale Skill
bundles. Every reviewed source is pinned in `upstreams.lock.json` with an exact
commit, license, source paths, absorbed concepts, and local validation cases.

The V0.1 weighting is architectural, not a code-copy ratio:

- Blender Agent Studio: reproducible production and evidence loop;
- cc-blender-skill: reference-reconstruction concepts reserved for V0.3;
- r3f-skills: version-aware examples and browser verification;
- img2threejs: state machine and identity-feature ledger reserved for V0.3;
- official Blender, glTF, and Three.js documentation: API authority.

An upstream update produces a reviewable difference report. It never merges
automatically. Copied code or assets require license mapping and a notice;
absorbed ideas are independently expressed and covered by local tests.
