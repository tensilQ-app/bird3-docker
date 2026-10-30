# Development

The project is maintained by tensilQ.app (GitHub organization: tensilQ-app, info@tensilq.app).

For manual and AI-assisted commits made on behalf of the organization, use the approved author and committer identity:

```sh
git config user.name 'tensilQ-app'
git config user.email 'info@tensilq.app'
```

Do not identify manual or ChatGPT-assisted commits as bot commits. Do not add OpenAI or ChatGPT to contributors, authors, maintainers or copyright holders. Preserve upstream license and copyright notices. Independent external contributors keep their own identities.

For commits actually created by GitHub Actions, use:

```sh
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
```

Dependabot retains its own bot identity. Never merge branches descended from the pre-migration history into main. Recreate dependency changes on the current main instead.
