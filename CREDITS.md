# Credits

The agents and skills codify how I work, so most of their instructions come from my own work, and the rest from the work of the people and organisations credited below. The pull request that adds or changes an instruction says where it comes from.

## My work at Relaycorp

The `programming`, `systems-architecture`, and `protocol-design` skills, and the agents that follow them, mostly codify my work at Relaycorp: the open source projects in [@relaycorp](https://github.com/relaycorp), [@AwalaApp](https://github.com/AwalaApp), and [@CheVeraId](https://github.com/CheVeraId), which others contributed to as well. Agents analysed their code, specs, issues, and websites (e.g., [the DDoS report](https://ddos.report/)) to find what I strive for:

- [As a programmer and software architect](https://github.com/gnarea/sdlc/issues/7#issuecomment-6507173356).
- [As a systems architect](https://github.com/gnarea/sdlc/issues/14#issuecomment-6507178257).
- [As a protocol designer](https://github.com/gnarea/sdlc/issues/14#issuecomment-6507178503).

## Principles and methods

Some agents and skills apply principles and methods that others devised:

- The robustness principle, which the `architect` agent follows, as Jon Postel stated it in the [specification of TCP](https://www.rfc-editor.org/rfc/rfc761) (1980).
- The principle of least privilege, which the `architect` and `ai-engineer` agents follow, as Jerome Saltzer and Michael Schroeder set it out in [The Protection of Information in Computer Systems](https://doi.org/10.1109/PROC.1975.9939) (1975).
- Making illegal states unrepresentable, which the `programmer` agent and the `programming` skill require, as Yaron Minsky put it in [Effective ML Revisited](https://blog.janestreet.com/effective-ml-revisited/) (2011).
- The STRIDE threat types in the `systems-architecture` skill's threat model template, from Loren Kohnfelder and Praerit Garg's [The Threats To Our Products](https://threatmodelingbook.com/files/microsoft/The-Threats-To-Our-Products.docx) (Microsoft, 1999).
- The risk responses in the `project-management` skill, from the Project Management Institute's [PMBOK Guide](https://www.pmi.org/standards/pmbok).

## AI engineering

Besides [the issue that set out its principles](https://github.com/gnarea/sdlc/issues/3) and my other work (e.g., how I run agents in [segnale](https://github.com/gnarea/segnale)), the `ai-engineer` agent and the `ai-engineering` skill adopt findings from research reports on [the five layers of AI engineering](https://github.com/gnarea/sdlc/issues/3#issuecomment-6645107299) and on [best practices with Anthropic Claude models](https://github.com/gnarea/sdlc/issues/3#issuecomment-6645277679). [What the skill took from them](https://github.com/gnarea/sdlc/issues/3#issuecomment-6705751897) and [its update for Claude Fable 5.2](https://github.com/gnarea/sdlc/pull/60) trace each instruction to its sources, which are credited below.

### Anthropic

- Claude Platform documentation: [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices), [Prompting Claude Fable 5.2](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2), [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5), [Prompting Claude Sonnet 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5), [Prompting Claude Haiku 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5), [Prompting Claude Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5), [Prompting Claude Sonnet 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5), [What's new in Claude Fable 5.2](https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2), [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview), [Choosing the right model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model), [Optimizing for cost and intelligence](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), [Effort](https://platform.claude.com/docs/en/build-with-claude/effort), [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [Preserved thinking](https://platform.claude.com/docs/en/build-with-claude/preserved-thinking), [Compaction](https://platform.claude.com/docs/en/build-with-claude/compaction), [Define tools](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools), [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview), [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), and [API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention).
- Claude Code documentation: [How Claude remembers your project](https://code.claude.com/docs/en/memory), [Extend Claude with skills](https://code.claude.com/docs/en/skills), [Automate actions with hooks](https://code.claude.com/docs/en/hooks-guide), [Hooks reference](https://code.claude.com/docs/en/hooks), [Run Claude Code programmatically](https://code.claude.com/docs/en/headless), [Model configuration](https://code.claude.com/docs/en/model-config), and [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices).
- Engineering and research posts: [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system), [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), [Introducing advanced tool use for Claude](https://www.anthropic.com/engineering/advanced-tool-use), [Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents), [Harness design for long-running apps](https://www.anthropic.com/engineering/harness-design-long-running-apps), [Building a C compiler with parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler), [Making Claude Code safer with sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing), [How we built Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode), [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), [A statistical approach to model evaluations](https://www.anthropic.com/research/statistical-approach-to-model-evals), [Infrastructure noise in agentic coding evals](https://www.anthropic.com/engineering/infrastructure-noise), and [Building agents: When to fold subagents into your main agent loop](https://claude.com/resources/articles/building-agents-when-to-fold-subagents-into-your-main-agent-loop).
- Model releases: the system cards of [Claude Opus 5.5](https://www.anthropic.com/claude-opus-5-5-system-card), [Claude Haiku 5.5](https://www.anthropic.com/claude-haiku-5-5-system-card), and [Claude Fable 5.1 and Mythos 5.1](https://www.anthropic.com/claude-fable-5-1-mythos-5-1-system-card), and the [announcement of Claude Fable 5.2 and Mythos 5.2](https://www.anthropic.com/claude-fable-and-mythos-5-2).
- The [skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) skill.

### Research papers

- [How Many Instructions Can LLMs Follow at Once?](https://arxiv.org/abs/2507.11538), by Daniel Jaroslawicz et al. (2025).
- [Instruction Adherence in Coding Agent Configuration Files: A Factorial Study of Four File-Structure Variables](https://arxiv.org/abs/2605.10039), by Damon McMillan (2026).
- [Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?](https://arxiv.org/abs/2602.11988), by Thibaud Gloaguen et al. (2026).
- [Do Context Files Help Coding Agents? A Two-Agent Ablation Study on Real Repositories](https://arxiv.org/abs/2607.27250), by Prakhar Khatri (2026).
- [SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks](https://arxiv.org/abs/2602.12670), by Xiangyi Li et al. (2026).
- [The Complexity Trap: Simple Observation Masking Is as Efficient as LLM Summarization for Agent Context Management](https://arxiv.org/abs/2508.21433), by Tobias Lindenbauer et al. (2025).
- [Scaling Discovery Requires Forgetting](https://arxiv.org/abs/2610.20563), by Shangyin Tan et al. (2026).
- [The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses Against LLM Jailbreaks and Prompt Injections](https://arxiv.org/abs/2510.09023), by Milad Nasr et al. (2025).
- [Design Patterns for Securing LLM Agents against Prompt Injections](https://arxiv.org/abs/2506.08837), by Luca Beurer-Kellner et al. (2025).
- [AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352), by Edoardo Debenedetti et al. (2024).
- [Quantifying Frontier LLM Capabilities for Container Sandbox Escape](https://arxiv.org/abs/2603.02277), by Rahul Marchand et al. (2026).
- [The Scaffold Effect in Coding Agents: Harness Choice as a Hidden Variable in Coding-Agent Evaluation](https://arxiv.org/abs/2607.22585), by Naman Vats and Oleg Golev (2026).
- [GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning](https://iclr.cc/virtual/2026/poster/10009493), by Lakshya A Agrawal et al. (2026).

### Other publications

- William Lodge's [Beyond Prompt Engineering: 5 Layers of Reliable AI](https://williamlodge.com/blog-ai-engineering-layers.html).
- Drew Breunig's [How to Fix Your Context](https://www.dbreunig.com/2025/06/26/how-to-fix-your-context.html), [Context Inertia](https://www.dbreunig.com/2026/10/14/context-inertia.html), and [The State of Context Engineering](https://www.dbreunig.com/2026/10/24/the-state-of-context-engineering.html).
- Simon Willison's [The lethal trifecta for AI agents](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) and [Designing agentic loops](https://simonwillison.net/2025/Sep/30/designing-agentic-loops/).
- Hamel Husain and Shreya Shankar's [AI Evals: Everything You Need to Know](https://hamel.dev/blog/posts/evals-faq/).
- Hamel Husain's [post on seeing the prompts that frameworks send](https://hamel.dev/blog/posts/prompt/).
- HumanLayer's [Own your prompts](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-02-own-your-prompts.md), from 12-Factor Agents.
- The [Agent Skills specification](https://agentskills.io/specification), and its guide to [evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills).
- Meta's [Agents Rule of Two](https://ai.meta.com/blog/practical-ai-agent-security/).
- Cognition's [Don't Build Multi-Agents](https://cognition.com/blog/dont-build-multi-agents) and [Multi-Agents: What's Actually Working](https://cognition.com/blog/multi-agents-working).
- Cursor's [Dynamic context discovery](https://cursor.com/blog/dynamic-context-discovery).
- Factory's [Evaluating Context Compression for AI Agents](https://factory.com/news/evaluating-compression).
- Vercel's [AGENTS.md outperforms skills in our agent evals](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals).
- Decagon's [Optimizing GEPA for production](https://decagon.ai/blog/optimizing-gepa-for-production).
- Docker's [Isolation layers](https://docs.docker.com/ai/sandboxes/security/isolation/).
- Manveer Chawla's [How to sandbox AI agents in 2026](https://manveerc.substack.com/p/ai-agent-sandboxing-guide).
- The Register's [Anthropic's Claude convinced to exfiltrate private data](https://www.theregister.com/2025/10/30/anthropics_claude_private_data/).
- The [nono](https://github.com/always-further/nono) sandbox.
