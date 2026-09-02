# Repair and security

## Repair loop

Limit automated repair to three attempts. Each attempt records:

1. failed gate and evidence;
2. root-cause hypothesis;
3. smallest targeted change;
4. new source or asset hash;
5. the same evidence rerun;
6. `improved`, `regressed`, or `unchanged`.

Do not restart modeling or change cameras merely to hide a failing comparison.
After three unsuccessful attempts, report the concrete blocker.

## Safety

- Arbitrary Blender Python executes with the current user's permissions. Run
  only reviewed local scripts within the declared task boundary.
- Do not enable unknown Blender add-ons or open untrusted files with embedded
  execution behavior.
- Do not download third-party models or textures without confirmed license and
  manifest attribution.
- Do not upload private assets to external services by default.
- Use a clean browser67-managed profile, not a personal logged-in profile.
- Never record credentials, cookies, tokens, raw personal browser data, or
  private model contents in evidence reports.
- Missing tools degrade results to `UNVERIFIED`; they do not expand authority.
