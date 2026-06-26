# Push this repo to GitHub (run on your computer)

A stray `.git` folder may exist from an earlier attempt on the synced drive.
Delete it first, then initialize cleanly:

## Windows (PowerShell, from this folder)
```powershell
Remove-Item -Recurse -Force .git   # only if a .git folder exists
git init -b main
git add .
git commit -m "Initial scaffold: agentic execution layer (7 agents, loop, human-in-the-loop, AWS infra)"
```

## Create the GitHub repo and push
Option A — GitHub CLI (easiest):
```powershell
gh repo create velocity-hospitality-os --public --source=. --remote=origin --push
```

Option B — manual: create an empty repo named `velocity-hospitality-os` on github.com, then:
```powershell
git remote add origin https://github.com/<your-username>/velocity-hospitality-os.git
git push -u origin main
```

## After pushing
- Pin the repo on your GitHub profile (it's a required field on the application).
- Paste the repo URL into application field 9 (GitHub Profile) / mention in field 50.
- Confirm the README renders and the workflow diagram shows under `docs/`.
