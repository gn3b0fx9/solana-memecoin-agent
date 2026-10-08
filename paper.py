import json, os, time
from market_data import build_candidates, helius_mint_info
from risk import score

STATE_FILE="paper_state.json"

def load():
    if os.path.exists(STATE_FILE):
        try: return json.load(open(STATE_FILE))
        except: pass
    return {"cash_eur":float(os.getenv("STARTING_EUR",20)),"positions":{},"trades":[],"last_scan":None}

def save(s): json.dump(s,open(STATE_FILE,"w"),indent=2)

def run_scan():
    if os.getenv("PAPER_MODE","true").lower()!="true": raise RuntimeError("PAPER_MODE must remain true")
    state=load(); candidates=build_candidates(int(os.getenv("SCAN_LIMIT",20))); ranked=[]
    for c in candidates:
        mi=helius_mint_info(c["mint"]); sc,reasons=score(c,mi); c.update({"score":sc,"reasons":reasons,"mint_checks":mi}); ranked.append(c)
    ranked.sort(key=lambda x:x["score"],reverse=True)
    state["last_scan"]=int(time.time()); state["candidates"]=ranked[:20]; save(state)
    return state
