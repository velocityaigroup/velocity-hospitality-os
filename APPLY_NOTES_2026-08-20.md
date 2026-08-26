# Applying this pass to the repo — 20 Aug 2026

All files have been written straight into
`D:\Project\Velocity AI Group\04_Products\Velocity-Hospitality-OS\velocity-hospitality-os`
and into the war room. Nothing was deleted — one file needs to be removed by hand.

## The one manual step

`ui/velocity_console.html` was a 170 KB static console that **re-implemented retrieval and the
execution loop in client-side JavaScript**. It showed three agents while the live console showed
four, its Approve/Reject buttons changed nothing, and it would drift further from the product with
every change. It has been copied to `docs/legacy/velocity_console_static_v1.html` for the record.

Remove the original:

```powershell
cd "D:\Project\Velocity AI Group\04_Products\Velocity-Hospitality-OS\velocity-hospitality-os"
git rm ui/velocity_console.html
```

There is now exactly one console — `ui/server.py` — so the two surfaces can no longer contradict
each other in front of a judge.

## Verify (about two minutes)

```powershell
pytest -q                                          # 63 passed
ruff check .                                       # clean
python eval/run_eval.py                            # 95% / 100% / 100%  (unchanged — this matters)
python eval/firefly_eval.py                        # Firefly seed: 100% / 100% / 100% on 38 cases
python demo/run_demo.py --property firefly-bequia
python ui/server.py                                # http://localhost:8080
```

In the console: switch the property to **Firefly Estate Bequia**, run one operations cycle, then
approve a held item and watch the GM briefing change.

## Then commit

```powershell
git add -A
git commit -m "Firefly Bequia as a configured property; declared-gap guard; one live console with real approvals; 63 tests"
git push
```

Daily commits keep the repo-velocity signal alive — it is one of the things judges look at.

## Files written

**New**
- `src/velocity_hos/knowledge/firefly.py` — 24-record Firefly seed corpus + 11 declared gaps
- `src/velocity_hos/knowledge/properties.py` — the property registry
- `eval/firefly_eval.py` + `eval/firefly_report.md` / `.json` — the second evaluation harness
- `tests/test_properties.py`, `tests/test_console.py` — 33 new tests
- `docs/AUDIT_2026-08-20.md` — the full audit and remediation record
- `docs/DEMO_RUNBOOK.md` — the ten-step demo script and the Q&A drill
- `docs/screenshots/` — 13 screenshots at 1440 px, 820 px and 390 px
- `docs/legacy/velocity_console_static_v1.html` — the retired static console
- `demo/decision_trail_firefly-bequia.md` / `.json`
- War room: `Logbook_2026-08-20.md`, `Judging_Readiness_2026-08-20.md`

**Changed**
- `ui/server.py` — rebuilt: seven views, property switcher, four agents, real approvals, demo reset
- `src/velocity_hos/agents/sop_coach.py` — declared-gap guard (opt-in per property)
- `src/velocity_hos/knowledge/schema.py` — two optional provenance fields (`confidence`, `source`)
- `src/velocity_hos/knowledge/__init__.py` — exports the registry
- `src/velocity_hos/llm/local.py` — offline answer synthesis no longer returns the retrieval header
- `demo/run_demo.py` — reads the property registry, takes `--property`, dates relative to today
- `README.md` — multi-property section, both evaluation numbers, the console description

**Not changed, on purpose:** the retrieval configuration, the agent contracts, the loop phases, the
approval gate and the audit trail. The 95% metric was re-verified unchanged after every edit.
