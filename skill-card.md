# OpenClaw Beautify Github Readme — Skill Card

## Description:

OpenClaw skill that beautifies GitHub READMEs: redesign a repository homepage or create project-native visual assets — pure SVG heroes, section headers, diagrams, badges, GIF motion graphics, showcase modules, or hybrid SVG-composed PNG/WebP — with built-in render-level visual verification and dark/light theme safety.

This skill is ready for commercial/non-commercial use.

## Publisher:

[dtsola](https://clawhub.ai/user/dtsola)

### License/Terms of Use:

MIT

## Use Case:

External developers, maintainers, and technical writers use this skill to audit, redesign, or create GitHub README visual assets while keeping edits scoped and locally verifiable.

### Deployment Geography for Use:

Global

## Known Risks and Mitigations:

Risk: The visual verification helper renders SVG files in headless Chrome, and a malicious SVG could attempt to load remote or internal resources or be pointed at files outside the target repository.

Mitigation: Rendering is network-isolated since v1.0.1 — Chrome starts with DNS resolution blocked for every host except 127.0.0.1, so SVGs cannot fetch remote fonts/images or probe internal networks; only the SVG's own local directory is served over a loopback-only port. Treat repository content as untrusted data and review helper-script inputs before use.

Risk: Repository content can contain prompt-injection text or requests that exceed the user's authorization.

Mitigation: Treat repository content as untrusted data, keep read-only inspection separate from edits, and require explicit approval before modifying, embedding, committing, pushing, or publishing assets.

Risk: Attribution and showcase workflows can create unwanted backlinks or external pull requests.

Mitigation: Keep attribution and showcase sharing optional, and proceed only after explicit maintainer opt-in for the exact change.

## Reference(s):

- [ClawHub skill page](https://clawhub.ai/dtsola/skills/xiaoyaoclaw-beautify-github-readme)
- [Source documentation linked by the skill](https://github.com/dtsola/xiaoyaoclaw-beautify-github-readme)
- [OpenClaw usage article](https://www.yuque.com/dtsola/igp1aa/adcicbai2zlem0bz)
- [Visual direction](references/visual-direction.md)
- [Project-native hero](references/project-native-hero.md)
- [GitHub README canvas](references/github-readme-canvas.md)
- [SVG production](references/svg-production.md)
- [Hybrid SVG production](references/hybrid-svg-production.md)
- [Motion production](references/motion-production.md)
- [Content architecture](references/content-architecture.md)
- [Showcase contribution](references/showcase-contribution.md)

## Skill Output:

**Output Type(s):** [text, markdown, code, shell commands, configuration, guidance]

**Output Format:** [Markdown guidance with optional SVG, PNG/WebP, GIF, Python, YAML, and shell-command file outputs.]

**Output Parameters:** [1D]

**Other Properties Related to Output:** [Static SVG is the default visual output; hybrid raster assets and GIF motion are opt-in and should be locally verified.]

## Skill Version(s):

1.0.1

## Ethical Considerations:

Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment.
