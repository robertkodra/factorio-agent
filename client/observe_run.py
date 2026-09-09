"""Record first observed research and production milestones during one dry run."""
import time
import json
from .play import call, milestone, RUN

if __name__ == '__main__':
    seen={json.loads(line)['name'] for line in (RUN/'milestones.jsonl').read_text().splitlines()} if (RUN/'milestones.jsonl').exists() else set()
    for _ in range(720):
        if (RUN/'stop-monitor').exists():break
        result=call('research_state')
        for tech in result['researched']:
            key='Research: '+tech
            if key not in seen:
                seen.add(key);milestone(key, {'observed_tick':result['tick'],'sampling_interval_seconds':5})
        for item,count in result['produced'].items():
            key='First produced: '+item
            if count and key not in seen:
                seen.add(key);milestone(key, {'total_produced':count,'observed_tick':result['tick'],'sampling_interval_seconds':5})
        time.sleep(5)
