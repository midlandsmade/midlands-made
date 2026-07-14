"""Regen Kildare product images via Higgsfield i2i — worker-pool version.

Respects the plan's 8-concurrent-job limit (keeps <=6 in flight), is idempotent
(skips products whose clean copy already exists), and salvages any job IDs
already created in regen_log.txt so we don't pay to regenerate them.
"""
import json, os, sys, io, time, re, subprocess, urllib.request
from PIL import Image, ImageDraw, ImageFont

BASE = r"D:\Midlands_Web\previews\kildare-stoves"
HF   = r"C:\Users\nojus\AppData\Roaming\npm\higgsfield.cmd"
REAL = os.path.join(BASE, "assets", "real")
OUT  = os.path.join(BASE, "assets", "products")
RAW  = os.path.join(BASE, "assets", "products_raw")
LOG  = os.path.join(BASE, "tools", "regen_log.txt")
MAX_INFLIGHT = 6
os.makedirs(RAW, exist_ok=True)

def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

STYLE_SCENE = {
 "freestanding":"installed freestanding on a slate hearth in a warm, tastefully decorated modern Irish living room, a real wood fire glowing behind the glass door, a neat stack of logs beside it, soft natural window light",
 "pellet":"installed freestanding on a hearth in a warm modern Irish living room, a real fire glow behind the glass, soft natural light, cosy premium mood",
 "insert":"built into a brick fireplace recess beneath a timber mantel in a cosy modern Irish living room, a real fire glowing behind the glass, soft warm light",
 "cassette":"inset flush into a clean plastered fireplace wall in a minimalist modern Irish living room, a wide real fire glowing behind the glass, soft warm light",
 "electric":"freestanding in a modern living room with a realistic glowing flame effect, soft warm light, cosy",
 "boiler":"installed freestanding on a slate hearth in a warm modern Irish living space, a real fire glowing behind the glass, soft light",
}
def prompt_for(p):
    scene = STYLE_SCENE.get(p.get("style"), STYLE_SCENE["freestanding"])
    return (f"Editorial interior photograph of this exact {p['name']} stove, {scene}. "
            "Front-on, centred composition with the whole stove clearly visible and sharply in focus; "
            "warm cosy lighting but bright enough to clearly read the stove's shape, door and detail. "
            "Photorealistic, ultra detailed, premium lifestyle mood, no people, no text, no watermark, no logos.")

def hf(args, timeout=240):
    r = subprocess.run(["cmd", "/c", HF] + args, capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.stderr, r.returncode

def create_job(p):
    """returns ('ok',jid) | ('rate',None) | ('err',None)"""
    real = os.path.join(REAL, p["id"] + ".webp")
    out, err, rc = hf(["generate", "create", "soul_cinematic", "--prompt", prompt_for(p),
                       "--image-references", real, "--aspect-ratio", "4:3", "--json"])
    blob = out + err
    if "rate_limit_reached" in blob or "concurrent_jobs_limit" in blob:
        return ("rate", None)
    try:
        data = json.loads(out)
        if isinstance(data, list):
            first = data[0]
            return ("ok", first if isinstance(first, str) else first.get("id"))
        return ("ok", data.get("id"))
    except Exception:
        log(f"  CREATE ERR {p['id']}: {blob[:140]}")
        return ("err", None)

def check(jid):
    """returns ('done',url) | ('pending',None) | ('failed',None)"""
    out, err, rc = hf(["generate", "get", jid, "--json"])
    try:
        data = json.loads(out)
        job = data[0] if isinstance(data, list) else data
    except Exception:
        return ("pending", None)
    st = job.get("status")
    if st == "completed":
        return ("done", job.get("result_url"))
    if st in ("failed", "cancelled", "error"):
        return ("failed", None)
    return ("pending", None)

def font(sz):
    for p in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\Arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def save(pid, url):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=90).read()
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = img.size
    if w > 1400:
        img = img.resize((1400, int(h*1400/w)), Image.LANCZOS); w, h = img.size
    img.save(os.path.join(RAW, pid + ".webp"), "WEBP", quality=88, method=6)
    d = ImageDraw.Draw(img); f = font(int(w*0.026))
    label = "KILDARE STOVES"; tw = d.textlength(label, font=f)
    padx, pady = int(w*0.035), int(h*0.065)
    d.text((w-tw-padx+2, h-pady+2), label, font=f, fill=(0,0,0))
    d.text((w-tw-padx, h-pady), label, font=f, fill=(255,224,186))
    img.save(os.path.join(OUT, pid + ".webp"), "WEBP", quality=88, method=6)

def salvage_ids():
    ids = {}
    if os.path.exists(LOG):
        for m in re.finditer(r"created (\S+) -> (\S+)", io.open(LOG, encoding="utf-8").read()):
            ids[m.group(1)] = m.group(2)   # last one wins
    return ids

def main():
    d = json.load(io.open(os.path.join(BASE, "data", "products.json"), encoding="utf-8"))
    realids = {os.path.splitext(f)[0] for f in os.listdir(REAL)}
    todo = [p for p in d["products"]
            if p["id"] in realids and not os.path.exists(os.path.join(RAW, p["id"] + ".webp"))]
    salvage = salvage_ids()
    log(f"=== pool run: {len(todo)} products need images; {len(salvage)} known job ids to salvage ===")

    queue = list(todo)
    inflight = {}   # pid -> jid
    # pre-seed from salvage
    for p in list(queue):
        if p["id"] in salvage:
            inflight[p["id"]] = salvage[p["id"]]
            queue.remove(p)
    log(f"  pre-seeded {len(inflight)} salvaged jobs; {len(queue)} to create")
    done = 0; failed = []
    while queue or inflight:
        # top up
        while queue and len(inflight) < MAX_INFLIGHT:
            p = queue[0]
            status, jid = create_job(p)
            if status == "ok":
                inflight[p["id"]] = jid; queue.pop(0)
                log(f"  created {p['id']} -> {jid}")
                time.sleep(1.2)
            elif status == "rate":
                break  # wait for slots to free
            else:
                queue.pop(0); failed.append(p["id"])
        # poll in-flight
        for pid, jid in list(inflight.items()):
            st, url = check(jid)
            if st == "done":
                try:
                    save(pid, url); done += 1
                    log(f"  saved {pid}  ({done}/{len(todo)})")
                except Exception as e:
                    log(f"  SAVE FAIL {pid}: {str(e)[:120]}")
                    failed.append(pid)
                del inflight[pid]
            elif st == "failed":
                log(f"  job failed for {pid} -> requeue")
                del inflight[pid]
                # requeue for a fresh generation
                pm = next((x for x in d["products"] if x["id"] == pid), None)
                if pm: queue.append(pm)
        time.sleep(6)
    # retry any hard-failed once more at the end
    log(f"=== DONE: {done} saved, {len(set(failed))} failed: {sorted(set(failed))} ===")

if __name__ == "__main__":
    main()
