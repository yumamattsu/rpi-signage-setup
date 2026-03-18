---
description: Push latest signage setup files to GitHub repository
---

This workflow automates the process of copying the latest artifact files to the workspace and pushing them to the GitHub repository.

1. Ensure you are in the workspace root.
2. Copy the latest files from artifacts to the staging area.
// turbo
3. Run the following command to stage and push:
```bash
git add -A && git commit -m "Update signage setup files" && git push origin main
```
