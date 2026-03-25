# Smart Rename

Intelligently rename the current Claude Code session based on conversation context.

## When This Skill Is Invoked

The user runs `/smart-rename` or asks to rename the current session intelligently.

## Instructions

When this skill is invoked, follow these steps:

1. **Analyze the conversation so far.** Look at:
   - The user's initial request (what started this session)
   - The main topics and files discussed
   - Any key actions taken (debugging, refactoring, feature work, etc.)

2. **Generate a concise session name** following these rules:
   - Use kebab-case (e.g., `fix-login-bug`, `refactor-auth-module`)
   - 2-5 words maximum
   - Focus on the ACTION and TARGET (what + where)
   - Be specific enough to distinguish from other sessions

3. **Present the suggested name to the user:**
   > Based on our conversation, I suggest renaming this session to: `suggested-name-here`
   >
   > This captures [brief explanation of why this name fits].
   >
   > Should I apply this name?

4. **If the user approves**, execute:
   ```
   /rename suggested-name-here
   ```

5. **If the user wants changes**, iterate on the name until they're satisfied, then apply.

## Examples

| Session Context | Suggested Name |
|---|---|
| Debugging a failing login form | `fix-login-validation` |
| Adding OAuth2 to an Express API | `add-oauth2-auth` |
| Refactoring database models | `refactor-db-models` |
| Writing unit tests for payments | `test-payment-module` |
| General project exploration | `explore-project-setup` |
