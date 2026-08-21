# Install AEDT Student on Windows

Download Ansys Electronics Desktop Student only from the official Ansys student page and follow its current installer and clickwrap. AEDT Student is separate from the Workbench-based Student bundle and can have release-specific HFSS/Maxwell limits.

After official installation:

```bash
python tools/bootstrap.py --extras dev,aedt
agentic-sim doctor
agentic-sim info electromagnetics electrostatic
agentic-sim run electromagnetics --case electrostatic --dry-run
```

Do not use undocumented transport workarounds, patch executable checks, alter licenses, or launch an arbitrary `ansysedt` binary. The adapter may use only a validated official installation. Preserve `BLOCKED` when the Student edition lacks a requested solver mode.
