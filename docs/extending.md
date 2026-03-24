# Extending the workflow

To adapt this repo to your own scientific ML project, the easiest path is:

1. keep your existing training code
2. expose a config file interface
3. make evaluation write a `metrics.json`
4. point `task.yaml` commands to your scripts

The current v0 assumes each experiment can be launched via:

- a train command with `{config_path}` and `{run_dir}` placeholders
- an eval command with `{run_dir}`

If your project already has training and evaluation scripts, integration should mainly be a matter of command wrapping and metric parsing.
