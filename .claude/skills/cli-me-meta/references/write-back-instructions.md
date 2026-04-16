# Write-Back Instructions

Append this section verbatim to every generated SKILL.md. This is what
makes skills self-evolving.

---

```markdown
## After Completing Your Task

Before ending, update the knowledge base in `references/`:

1. If you discovered a technique that worked well, add or update the relevant
   page in `references/techniques/`
2. If something failed or had unexpected behavior, document it in
   `references/gotchas.md`
3. If you found a better approach than what the wiki suggests, update the page
4. Log what you did: `clime log append --skill <name> --message "<what you did and learned>" --log-file references/log.md`
5. Update `references/index.md` if you added new pages
6. Include source URLs for any external knowledge you referenced
```
