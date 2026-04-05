import type { HookHandler } from 'openclaw/hooks';

const GOVERNOR_CONTENT = `## Skill Usage Governor

When the user says “为我开启 skill-usage-governor” / “enable skill-usage-governor”, treat it as a request to activate skill governance mode for this OpenClaw environment.

### Governance intent
- manage skill usage rather than only documenting it
- prefer the single most relevant skill instead of reading many skills casually
- avoid repeated or unnecessary skill reads
- preserve protected skills from archive / suppression logic
- use skill-usage-governor as the entrypoint for enabling governance-oriented injection and review

### Behavioral expectations
- if governance is not yet wired at runtime, state that clearly and proceed with the activation / injection steps instead of pretending it is already active
- when asked to enable skill-usage-governor, inspect whether hooks/config/rules were actually injected
- if not injected, attempt the needed hook/config integration or report the exact missing layer
- keep user-facing wording focused on whether governance is active, partially active, or not yet active
- when a user explicitly triggers a skill via phrasing like use/使用/用 + skill name, treat that as one real skill usage event and count it silently (+1) for later governance and cleanup analysis
- this skill usage counting should be user-transparent: do not interrupt the response just to mention the count
- on first install / first enable, it is acceptable to inform the user once that explicit skill usage may be silently counted for governance purposes
- user-facing skill usage summaries should default to human-readable language rather than raw fields like uses_7d / uses_30d / score unless the user explicitly asks for raw stats
`;

const handler: HookHandler = async (event) => {
  if (!event || typeof event !== 'object') return;
  if (event.type !== 'agent' || event.action !== 'bootstrap') return;
  if (!event.context || typeof event.context !== 'object') return;

  const sessionKey = event.sessionKey || '';
  if (sessionKey.includes(':subagent:')) return;

  if (Array.isArray(event.context.bootstrapFiles)) {
    event.context.bootstrapFiles.push({
      path: 'SKILL_USAGE_GOVERNOR.md',
      content: GOVERNOR_CONTENT,
      virtual: true,
    });
  }
};

export default handler;
