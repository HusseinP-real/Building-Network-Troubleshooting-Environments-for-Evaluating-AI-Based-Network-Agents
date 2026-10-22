"""Credential preflight: abort before provisioning any lab; never expose values."""
import os
from .envfile import load_env


def missing_credentials(agents, *, judge=True):
    load_env()
    required=set()
    for agent in agents:
        if agent in ('sade','cc-baseline'):required.add('ANTHROPIC_API_KEY')
        elif agent=='react-full':required.add('OPENAI_API_KEY')
        else:raise ValueError(f'Unknown agent: {agent}')
    if judge:required.add('OPENAI_API_KEY')
    return sorted(name for name in required if not os.environ.get(name,'').strip())


def require_credentials(agents):
    missing=missing_credentials(agents)
    if missing:
        names=', '.join(missing)
        raise RuntimeError('Missing credentials before deployment: '+names+'. Configure ANTHROPIC_API_KEY and FAULTBENCH_OPENAI_API_KEY securely in environment settings (the latter aliases OPENAI_API_KEY). No lab was deployed and no model call was made.')
