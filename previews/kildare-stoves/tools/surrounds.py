"""Regenerate the 16 surround/fireplace images (no real photo -> blind t2i) with the
same clean corner-mark + 4:3 aspect as the stove batch, for a cohesive shop grid.
"""
import json, os, io, time
import regen_images2 as R  # reuse hf/check/save/font/log + pool constants

def create_blind(p):
    prompt = (f"Editorial interior photograph of an elegant {p['name']} fireplace surround and mantelpiece "
              "in a warm, tastefully decorated premium Irish living room, a real fire glowing in the hearth. "
              "Front-on, centred composition with the whole surround clearly visible and sharply in focus; "
              "warm cosy lighting but bright enough to read the surround's material and detail. "
              "Photorealistic, ultra detailed, premium lifestyle mood, no people, no text, no watermark, no logos.")
    out, err, rc = R.hf(["generate", "create", "soul_cinematic", "--prompt", prompt,
                         "--aspect-ratio", "4:3", "--json"])
    blob = out + err
    if "rate_limit_reached" in blob or "concurrent_jobs_limit" in blob:
        return ("rate", None)
    try:
        data = json.loads(out)
        first = data[0] if isinstance(data, list) else data
        return ("ok", first if isinstance(first, str) else first.get("id"))
    except Exception:
        R.log(f"  CREATE ERR {p['id']}: {blob[:140]}")
        return ("err", None)

def main():
    d = json.load(io.open(os.path.join(R.BASE, "data", "products.json"), encoding="utf-8"))
    realids = {os.path.splitext(f)[0] for f in os.listdir(R.REAL)}
    todo = [p for p in d["products"] if p["id"] not in realids]
    R.log(f"=== surrounds blind regen: {len(todo)} items ===")
    queue = list(todo); inflight = {}; done = 0
    while queue or inflight:
        while queue and len(inflight) < R.MAX_INFLIGHT:
            p = queue[0]; st, jid = create_blind(p)
            if st == "ok":
                inflight[p["id"]] = jid; queue.pop(0); R.log(f"  created {p['id']} -> {jid}"); time.sleep(1.2)
            elif st == "rate":
                break
            else:
                queue.pop(0)
        for pid, jid in list(inflight.items()):
            s, url = R.check(jid)
            if s == "done":
                try: R.save(pid, url); done += 1; R.log(f"  saved {pid} ({done}/{len(todo)})")
                except Exception as e: R.log(f"  SAVE FAIL {pid}: {str(e)[:120]}")
                del inflight[pid]
            elif s == "failed":
                del inflight[pid]; queue.append(next(x for x in d["products"] if x["id"] == pid))
        time.sleep(6)
    R.log(f"=== surrounds DONE: {done}/{len(todo)} ===")

if __name__ == "__main__":
    main()
