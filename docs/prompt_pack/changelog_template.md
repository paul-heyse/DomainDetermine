# Prompt Pack Changelog Template

## <template_id> <version> - <YYYY-MM-DD>
- Impact: <major|minor|patch>
- Owners: <owner1@example.com>, <owner2@example.com>
- Rationale: <One-line summary of the change>
- Expected metrics:
  - grounding_fidelity: <delta or target>
  - hallucination_rate: <delta or target>
  - acceptance_rate: <delta or target>
- Hash: <computed by `domain-determine prompt bump-version`>
- Approvals: <governance approvers>
- Related manifests: <manifest ids linked to this release>

> Run `domain-determine prompt bump-version` after drafting this entry to compute the definitive hash and append the entry into `docs/prompt_pack/CHANGELOG.md` and `releases.jsonl`.
